"""輸入路徑測試：偽造 pygame.key.get_pressed()，驗證移動與射擊實際生效。

涵蓋 smoke_test 沒測到的 key.get_pressed() 路徑（含死亡重生後）。
執行：python tests\\input_test.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game import settings as S  # noqa: E402
from game.app import Game  # noqa: E402


class FakeKeys:
    """模擬 pygame.key.get_pressed() 的 ScancodeWrapper。"""

    def __init__(self, pressed: set[int]) -> None:
        self.pressed = pressed

    def __getitem__(self, key: int) -> bool:
        return key in self.pressed


def install(pressed: set[int]) -> None:
    pygame.key.get_pressed = lambda: FakeKeys(pressed)  # type: ignore[assignment]


def step(game: Game, frames: int, dt: float = 1 / 60) -> None:
    for _ in range(frames):
        game.update(dt)


def enter_play(game: Game) -> None:
    game.start_new_game()
    while game.state == "intro":
        game.update(1 / 60)
    assert game.state == "play", game.state


def check(name: str, cond: bool) -> None:
    print(f"  [{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        raise AssertionError(name)


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    install(set())
    game = Game(screen)
    enter_play(game)

    print("1. 移動")
    p = game.player
    assert p is not None
    x0, y0 = p.pos.x, p.pos.y

    install({pygame.K_RIGHT})
    step(game, 20)
    check("按住 RIGHT 會向右移動", game.player is p and p.pos.x > x0 + 20)

    install({pygame.K_LEFT})
    step(game, 40)
    check("按住 LEFT 會向左移動", p.pos.x < x0)

    install({pygame.K_UP})
    step(game, 20)
    check("按住 UP 會向上移動", p.pos.y < y0 - 20)

    install({pygame.K_DOWN})
    step(game, 40)
    check("按住 DOWN 會向下移動", p.pos.y > y0)

    install(set())
    step(game, 10)
    x1 = p.pos.x
    step(game, 20)
    check("放開按鍵後停止移動", abs(p.pos.x - x1) < 0.01)

    print("2. 射擊")
    for key, label in ((pygame.K_z, "Z"), (pygame.K_SPACE, "SPACE"), (pygame.K_j, "J")):
        for b in list(game.player_bullets):
            b.kill()
        install({key})
        step(game, 8)
        check(f"按住 {label} 會射出子彈", len(game.player_bullets) > 0)
        install(set())

    print("3. 死亡重生後仍可操作")
    install(set())
    game.player.invuln = 0.0
    game.kill_player() if hasattr(game, "kill_player") else game.player.kill()
    if game.player is not None and not game.player.alive():
        game.player = None
    # 走完重生流程
    for _ in range(600):
        game.update(1 / 60)
        if game.player is not None and game.state == "play":
            break
    check("玩家已重生", game.player is not None)

    p2 = game.player
    assert p2 is not None
    check("重生後的玩家在 all_sprites 內", p2 in game.all_sprites)
    x2 = p2.pos.x
    install({pygame.K_RIGHT})
    step(game, 20)
    check("重生後可移動", p2.pos.x > x2 + 20)

    for b in list(game.player_bullets):
        b.kill()
    install({pygame.K_z})
    step(game, 8)
    check("重生後可射擊", len(game.player_bullets) > 0)

    print("4. 事件驅動按鍵（get_pressed 失效時的備援）")
    install(set())  # get_pressed 永遠回傳未按下
    p3 = game.player
    assert p3 is not None
    x3 = p3.pos.x
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    step(game, 20)
    check("KEYDOWN LEFT 可移動", p3.pos.x < x3 - 20)

    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_LEFT))
    step(game, 5)
    x4 = p3.pos.x
    step(game, 20)
    check("KEYUP 後停止移動", abs(p3.pos.x - x4) < 0.01)

    for b in list(game.player_bullets):
        b.kill()
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    step(game, 8)
    check("KEYDOWN SPACE 可射擊", len(game.player_bullets) > 0)
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE))

    print("5. 視窗焦點")
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    check("失焦後清空按鍵狀態", not game.held and not game.has_focus)
    x5 = p3.pos.x
    step(game, 30)
    check("失焦時遊戲凍結", abs(p3.pos.x - x5) < 0.01)

    game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
    check("重新聚焦後恢復", game.has_focus)
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    step(game, 20)
    check("重新聚焦後可移動", p3.pos.x > x5 + 20)
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))

    print("6. 數字鍵盤方向控制")
    install(set())
    game.held.clear()
    p4 = game.player
    assert p4 is not None
    npad = [
        (pygame.K_KP6, "KP6 右", lambda a, b: b.x > a.x + 15 and abs(b.y - a.y) < 1),
        (pygame.K_KP4, "KP4 左", lambda a, b: b.x < a.x - 15 and abs(b.y - a.y) < 1),
        (pygame.K_KP8, "KP8 上", lambda a, b: b.y < a.y - 15 and abs(b.x - a.x) < 1),
        (pygame.K_KP2, "KP2 下", lambda a, b: b.y > a.y + 15 and abs(b.x - a.x) < 1),
        (pygame.K_KP5, "KP5 下", lambda a, b: b.y > a.y + 15 and abs(b.x - a.x) < 1),
        (pygame.K_KP7, "KP7 左上", lambda a, b: b.x < a.x - 8 and b.y < a.y - 8),
        (pygame.K_KP9, "KP9 右上", lambda a, b: b.x > a.x + 8 and b.y < a.y - 8),
        (pygame.K_KP1, "KP1 左下", lambda a, b: b.x < a.x - 8 and b.y > a.y + 8),
        (pygame.K_KP3, "KP3 右下", lambda a, b: b.x > a.x + 8 and b.y > a.y + 8),
    ]
    for key, label, ok in npad:
        p4.pos.update(S.PLAY_W / 2, S.SCREEN_H / 2)
        before = pygame.Vector2(p4.pos)
        install({key})
        step(game, 20)
        check(f"{label} 可移動", ok(before, p4.pos))
        install(set())

    for b in list(game.player_bullets):
        b.kill()
    install({pygame.K_KP5})
    step(game, 8)
    check("KP5 不射擊（改為下移）", len(game.player_bullets) == 0)
    install(set())

    for b in list(game.player_bullets):
        b.kill()
    install({pygame.K_KP0})
    step(game, 8)
    check("KP0 可射擊", len(game.player_bullets) > 0)
    install(set())
    for b in list(game.player_bullets):
        b.kill()

    print("7. 全螢幕置中")
    vp = game.frame_viewport()
    check("視窗大小相同時 1:1 不縮放",
          vp.topleft == (0, 0) and vp.size == (S.SCREEN_W, S.SCREEN_H))

    big = pygame.Surface((1920, 1080))
    game.screen = big
    vp = game.frame_viewport()
    scale = min(1920 / S.SCREEN_W, 1080 / S.SCREEN_H)
    check("全螢幕等比縮放", vp.size == (int(S.SCREEN_W * scale), int(S.SCREEN_H * scale)))
    check("全螢幕水平置中", abs(vp.centerx - 960) <= 1)
    check("全螢幕垂直置中", abs(vp.centery - 540) <= 1)
    check("不再貼齊左上角", vp.left > 0)

    game.draw()
    check("縮放後畫面確實繪製到中央區域",
          big.get_at((vp.centerx, 8))[:3] != (0, 0, 0)
          and big.get_at((4, vp.centery))[:3] == tuple(S.BLACK))

    wide = pygame.Surface((1000, 3000))
    game.screen = wide
    vp = game.frame_viewport()
    check("極端長寬比仍完整置中",
          vp.width <= 1000 and vp.height <= 3000 and abs(vp.centerx - 500) <= 1)

    game.screen = screen

    print("7b. 全螢幕切換")
    check("預設為視窗模式", not game.fullscreen)
    game.toggle_fullscreen()
    check("F11 切換為全螢幕", game.fullscreen)
    fs_vp = game.frame_viewport()
    sw, sh = game.screen.get_size()
    check("全螢幕畫面置中",
          abs(fs_vp.centerx - sw // 2) <= 1 and abs(fs_vp.centery - sh // 2) <= 1)
    check("全螢幕畫面未超出視窗", fs_vp.width <= sw and fs_vp.height <= sh)
    game.toggle_fullscreen()
    check("再按 F11 回到視窗模式",
          not game.fullscreen and game.screen.get_size() == (S.SCREEN_W, S.SCREEN_H))

    # 以真實按鍵事件驗證 F / F11 都能切換
    for key, name in ((pygame.K_F11, "F11"), (pygame.K_f, "F")):
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        check(f"按 {name} 進入全螢幕", game.fullscreen)
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        check(f"再按 {name} 回到視窗模式",
              not game.fullscreen and game.screen.get_size() == (S.SCREEN_W, S.SCREEN_H))
        game.held.clear()

    print("8. 離開遊戲按鍵")
    game.confirm_quit = False
    game.running = True
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
    check("遊戲中按 Q 先顯示確認", game.confirm_quit and game.running)

    x6 = game.player.pos.x
    install({pygame.K_RIGHT})
    step(game, 30)
    check("確認畫面中遊戲凍結", abs(game.player.pos.x - x6) < 0.01)
    install(set())

    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
    check("按 N 取消離開", not game.confirm_quit and game.running)

    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    check("確認畫面按 ESC 也可取消", not game.confirm_quit and game.running)

    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y))
    check("按 Q 再按 Y 會離開遊戲", not game.running)

    game.running = True
    game.state = "title"
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
    check("標題畫面按 Q 直接離開", not game.running and not game.confirm_quit)

    # ------------------------------------------------------------------
    print("9. 視窗未取得鍵盤焦點時會顯示提示並主動搶回前景")
    import game.app as app_mod

    focus_calls = {"n": 0}
    os_focus = {"v": False}
    orig_has = app_mod.has_keyboard_focus
    orig_focus = app_mod.focus_window
    app_mod.has_keyboard_focus = lambda: os_focus["v"]  # type: ignore[assignment]

    def fake_focus() -> bool:
        focus_calls["n"] += 1
        return os_focus["v"]

    app_mod.focus_window = fake_focus  # type: ignore[assignment]
    try:
        game2 = Game(screen)
        game2.track_os_focus = True
        game2.has_focus = True
        game2._focus_grab_t = 3.0
        game2._focus_grab_cd = 0.0
        game2._unfocus_t = 0.0
        enter_play(game2)
        install(set())

        for _ in range(60):
            game2._sync_focus(1 / 60)
            game2.update(1 / 60)
        check("沒有鍵盤焦點時 has_focus 會轉為 False", not game2.has_focus)
        check("沒有鍵盤焦點時會主動嘗試搶回前景", focus_calls["n"] >= 2)

        x0 = game2.player.pos.x
        install({pygame.K_RIGHT})
        for _ in range(30):
            game2._sync_focus(1 / 60)
            game2.update(1 / 60)
        check("沒有鍵盤焦點時遊戲凍結（不會偷偷把命耗光）",
              abs(game2.player.pos.x - x0) < 0.01)
        game2.draw()  # 確認失焦提示可正常繪製

        os_focus["v"] = True
        game2._sync_focus(1 / 60)
        check("重新取得鍵盤焦點後自動恢復", game2.has_focus)
        for _ in range(20):
            game2.update(1 / 60)
        check("恢復後可以移動", game2.player.pos.x > x0 + 1)
        install(set())

        # get_focused() 誤判時，只要仍收得到按鍵事件就不可凍結遊戲
        os_focus["v"] = False
        game2.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        for _ in range(30):
            game2._sync_focus(1 / 60)
        check("收得到按鍵時不因焦點誤判凍結", game2.has_focus)
        game2.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))
        for _ in range(150):
            game2._sync_focus(1 / 60)
        check("按鍵停止後才依焦點狀態凍結", not game2.has_focus)
        os_focus["v"] = True
        game2._sync_focus(1 / 60)


        # 點擊視窗也可取回焦點
        game2.has_focus = False
        game2.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                              pos=(10, 10)))
        check("點擊視窗可取回焦點", game2.has_focus)
    finally:
        app_mod.has_keyboard_focus = orig_has  # type: ignore[assignment]
        app_mod.focus_window = orig_focus  # type: ignore[assignment]

    # ------------------------------------------------------------------
    print("10. 所有控制鍵總覽")
    install(set())
    game3 = Game(screen)

    # 標題畫面：ENTER / KP_ENTER / Z / SPACE 都能開始遊戲
    for key, label in ((pygame.K_RETURN, "ENTER"), (pygame.K_KP_ENTER, "KP_ENTER"),
                       (pygame.K_z, "Z"), (pygame.K_SPACE, "SPACE")):
        game3.state = "title"
        game3.state_t = 0.0
        game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        check(f"標題畫面 {label} 可開始遊戲", game3.state == "intro")

    enter_play(game3)

    # 移動：方向鍵 / WASD / 數字鍵盤
    move_keys = (
        (pygame.K_RIGHT, "RIGHT", 1, 0), (pygame.K_LEFT, "LEFT", -1, 0),
        (pygame.K_UP, "UP", 0, -1), (pygame.K_DOWN, "DOWN", 0, 1),
        (pygame.K_d, "D", 1, 0), (pygame.K_a, "A", -1, 0),
        (pygame.K_w, "W", 0, -1), (pygame.K_s, "S", 0, 1),
        (pygame.K_KP6, "KP6", 1, 0), (pygame.K_KP4, "KP4", -1, 0),
        (pygame.K_KP8, "KP8", 0, -1), (pygame.K_KP2, "KP2", 0, 1),
        (pygame.K_KP5, "KP5", 0, 1),
        (pygame.K_KP7, "KP7", -1, -1), (pygame.K_KP9, "KP9", 1, -1),
        (pygame.K_KP1, "KP1", -1, 1), (pygame.K_KP3, "KP3", 1, 1),
    )
    for key, label, ex, ey in move_keys:
        game3.player.pos.update(S.PLAY_W / 2, S.SCREEN_H / 2)
        start = pygame.Vector2(game3.player.pos)
        install({key})
        step(game3, 12)
        d = pygame.Vector2(game3.player.pos) - start
        ok = ((ex == 0 and abs(d.x) < 0.01) or (ex and d.x * ex > 1)) and \
             ((ey == 0 and abs(d.y) < 0.01) or (ey and d.y * ey > 1))
        check(f"移動鍵 {label}", ok)
        install(set())

    # 射擊：Z / SPACE / J / KP0
    for key, label in ((pygame.K_z, "Z"), (pygame.K_SPACE, "SPACE"),
                       (pygame.K_j, "J"), (pygame.K_KP0, "KP0")):
        game3.player_bullets.empty()
        game3.player.fire_timer = 0.0
        install({key})
        step(game3, 4)
        check(f"射擊鍵 {label}", len(game3.player_bullets) > 0)
        install(set())
    game3.player_bullets.empty()

    # 翻滾：X / K / LSHIFT / RSHIFT
    for key, label in ((pygame.K_x, "X"), (pygame.K_k, "K"),
                       (pygame.K_LSHIFT, "LSHIFT"), (pygame.K_RSHIFT, "RSHIFT")):
        game3.player.rolling = 0.0
        game3.player.rolls = 3
        game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        check(f"翻滾鍵 {label}", game3.player.rolling > 0 and game3.player.rolls == 2)
        game3.handle_event(pygame.event.Event(pygame.KEYUP, key=key))
    game3.player.rolling = 0.0

    # 炸彈：C / L
    for key, label in ((pygame.K_c, "C"), (pygame.K_l, "L")):
        game3.player.bombs = 2
        game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        check(f"炸彈鍵 {label}", game3.player.bombs == 1)
        game3.handle_event(pygame.event.Event(pygame.KEYUP, key=key))

    # 暫停：P（切換）與 ESC（暫停 / 解除）
    game3.paused = False
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    check("暫停鍵 P 可暫停", game3.paused)
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    check("暫停鍵 P 可解除暫停", not game3.paused)
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    check("ESC 可暫停", game3.paused)
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    check("ESC 可解除暫停", not game3.paused)

    # 靜音：M
    before_mute = game3.audio.muted
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
    check("靜音鍵 M 可切換", game3.audio.muted != before_mute)
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
    check("靜音鍵 M 可切回", game3.audio.muted == before_mute)

    # 全螢幕：F / F11
    for key, label in ((pygame.K_f, "F"), (pygame.K_F11, "F11")):
        game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        check(f"全螢幕鍵 {label} 進入全螢幕", game3.fullscreen)
        game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        check(f"全螢幕鍵 {label} 離開全螢幕", not game3.fullscreen)

    # 離開：Q → Y / N
    game3.running = True
    game3.confirm_quit = False
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
    check("離開鍵 Q 顯示確認", game3.confirm_quit and game3.running)
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
    check("確認畫面 N 取消", not game3.confirm_quit and game3.running)
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
    game3.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y))
    check("確認畫面 Y 離開", not game3.running)
    install(set())

    print("\nALL INPUT TESTS PASSED")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
