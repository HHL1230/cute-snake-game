"""無視窗（headless）煙霧測試：模擬跑完全部關卡與頭目戰。

執行：python tests\\smoke_test.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from game import settings as S  # noqa: E402
from game.app import Game  # noqa: E402
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

        wait_for(game, ("intro", "play"), 8.0, autofire=False)  # 進入下一關
        expected = (stage_i + 1) % len(STAGES)
        assert game.stage_index == expected, (game.stage_index, expected)
        print(f"  OK  STAGE {stage_i + 1}  {name:<14} score={game.score:>8}")

    assert game.loop_count == 1, "全破後應進入二週目"

    # 測試道具、炸彈、翻滾、死亡與 Game Over 流程
    step(game, 3.0, autofire=False)
    assert game.player is not None
    game.player.clear_wingmen(game)
    game.player.power = 0
    for kind in ("power", "wing", "bomb", "loop", "life"):
        game._apply_powerup(kind)
    assert game.player.power == 1, game.player.power
    assert len(game.player.wingmen) == 1
    game._apply_powerup("wing")
    assert len(game.player.wingmen) == 2
    game.player.invuln = 0
    assert game.player.start_roll(game)
    step(game, 1.5, god=False)
    game.use_bomb()
    step(game, 1.0, god=False)

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
