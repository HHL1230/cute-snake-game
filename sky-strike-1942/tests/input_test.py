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

    print("\nALL INPUT TESTS PASSED")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
