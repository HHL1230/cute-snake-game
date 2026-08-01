"""無視窗（headless）煙霧測試：模擬跑完全部關卡與頭目戰。

執行：python tests\\smoke_test.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from game import settings as S  # noqa: E402
from game.app import Game  # noqa: E402
from game.entities import Enemy  # noqa: E402
from game.stages import STAGES  # noqa: E402

DT = 1 / 60


def step(game: Game, seconds: float, autofire: bool = True, god: bool = True) -> None:
    frames = int(seconds / DT)
    for i in range(frames):
        if game.player is not None:
            if god:
                game.player.invuln = 5.0  # 測試用無敵，確保能跑完整關卡
            if autofire and i % 8 == 0:
                game.player.fire(game)
        game.update(DT)
        game.draw()


def wait_for(game: Game, states: tuple[str, ...], timeout: float = 8.0,
             autofire: bool = True) -> None:
    elapsed = 0.0
    while game.state not in states and elapsed < timeout:
        step(game, 0.25, autofire=autofire)
        elapsed += 0.25
    assert game.state in states, f"timeout waiting for {states}, got {game.state}"


def main() -> int:
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        pygame.mixer.init(22050, -16, 1, 512)
    except pygame.error:
        print("[warn] 無音效裝置，改以靜音模式測試")
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))

    game = Game(screen)
    assert game.state == "title"
    if game.audio.enabled:
        length = game.audio.sounds["shoot"].get_length()
        assert abs(length - 0.07) < 0.02, f"音效長度不符（格式錯誤？）: {length:.3f}s"
        print(f"  OK  音效格式 {pygame.mixer.get_init()} shoot={length * 1000:.0f}ms")
    step(game, 1.0, autofire=False)

    game.start_new_game()
    assert game.state == "intro"

    for stage_i in range(len(STAGES)):
        name = STAGES[stage_i]["name"]
        game.lives = 5  # 讓模擬跑完整關卡
        step(game, 3.0, autofire=False)          # 關卡開場動畫
        assert game.state == "play", game.state

        # 跑完整個波次腳本（最長的波次時間 + 緩衝）
        last_wave = max(w["t"] for w in STAGES[stage_i]["waves"])
        step(game, last_wave + 8.0)

        # 加速：清掉殘餘敵機，逼出頭目
        if game.state == "play":
            game.pending_i = len(game.pending)
            for e in list(game.enemies):
                e.kill()
        wait_for(game, ("boss_alarm", "boss"), 6.0)
        wait_for(game, ("boss",), 6.0)
        assert game.boss is not None

        step(game, 4.0)                           # 打一段頭目戰（測試各種彈幕）
        assert game.boss is not None
        game.boss.damage(10 ** 6, game)           # 直接擊破
        wait_for(game, ("clear",), 8.0, autofire=False)

        if stage_i == len(STAGES) - 1:
            # 最終關破關後應進入 ALL CLEAR 結局，而不是回到第 1 關
            wait_for(game, ("allclear",), 8.0, autofire=False)
            assert game.stage_index == stage_i, game.stage_index
            assert game.loop_count == 0, "全破後不應再從頭循環"
            assert game.allclear_bonus > 0, game.allclear_bonus
            print(f"  OK  STAGE {stage_i + 1}  {name:<14} score={game.score:>8}")
            break

        wait_for(game, ("intro", "play"), 8.0, autofire=False)  # 進入下一關
        expected = stage_i + 1
        assert game.stage_index == expected, (game.stage_index, expected)
        print(f"  OK  STAGE {stage_i + 1}  {name:<14} score={game.score:>8}")

    assert game.state == "allclear", game.state
    print(f"  OK  ALL CLEAR 結局   bonus={game.allclear_bonus}")

    # ALL CLEAR 畫面按 ENTER 回標題（需先過 2 秒鎖定時間）
    step(game, 2.5, autofire=False)
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert game.state == "title", game.state

    # 重新開一局，接著測試道具、炸彈、翻滾、死亡與 Game Over 流程
    game.start_new_game()
    step(game, 3.0, autofire=False)
    game.lives = 5
    assert game.player is not None
    game.player.clear_wingmen(game)
    game.player.power = 0
    for kind in ("power", "wing", "bomb", "roll", "life"):
        game._apply_powerup(kind)
    assert game.player.power == 1, game.player.power
    assert len(game.player.wingmen) == 1
    game._apply_powerup("wing")
    assert len(game.player.wingmen) == 2

    # 武器切換：雷射 / 機砲
    assert game.player.weapon == S.WEAPON_VULCAN, game.player.weapon
    game._apply_powerup("laser")
    assert game.player.weapon == S.WEAPON_LASER, game.player.weapon
    game.player.fire_timer = 0.0
    game.player_bullets.empty()
    game.player.power = S.MAX_POWER
    game.player.fire(game)
    assert len(game.player_bullets) == 1, f"雷射應只有一道光束，實際 {len(game.player_bullets)}"
    assert all(b.pierce for b in game.player_bullets), "雷射彈應可穿透"
    assert all(b.vel.x == 0 for b in game.player_bullets), "雷射不應散射"

    # 雷射應能貫穿縱列上的多架敵機
    def _line_of_targets() -> list:
        for e in list(game.enemies):
            e.kill()
        game.player_bullets.empty()
        out = []
        for i in range(3):
            en = Enemy(game.assets, "scout", (S.PLAY_W / 2, 150 + i * 60), "none", {})
            en.hp = 99
            game.enemies.add(en)
            game.all_sprites.add(en)
            out.append(en)
        return out

    game.player.pos.update(S.PLAY_W / 2, S.SCREEN_H - 110)
    game.player.power = 0
    targets = _line_of_targets()
    game.player.fire_timer = 0.0
    game.player.fire(game)
    for _ in range(int(1.2 / DT)):
        for b in list(game.player_bullets):
            b.update(DT, game)
        game._collisions()
    hurt = sum(1 for t in targets if t.hp < 99)
    assert hurt == 3, f"雷射應貫穿 3 架，實際 {hurt}"

    game._apply_powerup("vulcan")
    assert game.player.weapon == S.WEAPON_VULCAN, game.player.weapon
    targets = _line_of_targets()
    game.player.fire_timer = 0.0
    game.player.fire(game)
    assert not any(b.pierce for b in game.player_bullets), "機砲彈不應穿透"
    for _ in range(int(1.2 / DT)):
        for b in list(game.player_bullets):
            b.update(DT, game)
        game._collisions()
    hurt = sum(1 for t in targets if t.hp < 99)
    assert hurt == 1, f"機砲只應打中 1 架，實際 {hurt}"
    for e in list(game.enemies):
        e.kill()
    game.player_bullets.empty()
    print("  OK  雷射 / 機砲 武器切換與穿透判定")

    # 掉落配置：僚機最多、不再掉落 1UP
    rewards = Counter(w["reward"] for st in STAGES for w in st["waves"] if w["reward"])
    assert rewards["wing"] >= 12, rewards
    assert rewards["wing"] == max(rewards.values()), rewards
    assert rewards["life"] == 0, rewards
    assert rewards["laser"] >= 1 and rewards["vulcan"] >= 1, rewards
    assert S.EXTEND_SCORE >= 60000, S.EXTEND_SCORE
    print(f"  OK  道具掉落配置 {dict(rewards)}")

    game.player.invuln = 0
    assert game.player.start_roll(game)
    step(game, 1.5, god=False)
    game.use_bomb()
    step(game, 1.0, god=False)

    # 炸彈 / 翻滾用完時應顯示中央提示
    game.notice = None
    game.notice_t = 0.0
    game.player.bombs = 0
    game.use_bomb()
    assert game.notice is not None and game.notice_t > 0, "炸彈用完應顯示提示"
    assert game.notice[0] == "NO BOMBS LEFT", game.notice
    game.notice = None
    game.notice_t = 0.0
    game.player.rolls = 0
    game.player.rolling = 0.0
    assert not game.player.start_roll(game)
    assert game.notice is not None and game.notice[0] == "NO ROLLS LEFT", game.notice
    # 提示會自動消失
    step(game, 2.0, autofire=False, god=True)
    assert game.notice is None and game.notice_t == 0.0, game.notice
    print("  OK  炸彈 / 翻滾用完提示")

    game.lives = 0
    game.player.invuln = 0
    game._player_hit()
    step(game, 4.0, autofire=False, god=False)
    assert game.state == "gameover", game.state
    print(f"  OK  GAME OVER 流程   final score={game.score}")

    # 回到標題畫面
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert game.state == "title", game.state
    step(game, 1.0, autofire=False)

    pygame.quit()
    print("\n全部煙霧測試通過 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
