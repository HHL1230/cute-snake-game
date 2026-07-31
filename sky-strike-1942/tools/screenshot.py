"""無視窗截圖工具：輸出各狀態畫面到 shots\\ 以便檢查視覺效果。

執行：python tools\\screenshot.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from game import settings as S  # noqa: E402
from game.app import Game  # noqa: E402

DT = 1 / 60
OUT = ROOT / "shots"


def run(game: Game, seconds: float, autofire: bool = True) -> None:
    for i in range(int(seconds / DT)):
        if game.player is not None:
            game.player.invuln = 5.0
            if autofire and i % 8 == 0:
                game.player.fire(game)
        game.update(DT)
        game.draw()


def shot(game: Game, name: str) -> None:
    OUT.mkdir(exist_ok=True)
    if game.player is not None:
        game.player.invuln = 0.0  # 避免無敵閃爍導致截圖看不到自機
    game.draw()
    pygame.image.save(game.screen, str(OUT / f"{name}.png"))
    print("saved", name)


def main() -> int:
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        pygame.mixer.init(22050, -16, 1, 512)
    except pygame.error:
        pass
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    game = Game(screen)

    run(game, 1.2, autofire=False)
    shot(game, "01_title")

    game.start_new_game()
    run(game, 1.0, autofire=False)
    shot(game, "02_intro")

    run(game, 9.0)
    shot(game, "03_stage1_play")

    run(game, 6.0, autofire=False)   # 不開火，看清楚敵機編隊
    shot(game, "03b_stage1_enemies")

    game.player.power = 4
    game.player.add_wingman(game)
    game.player.add_wingman(game)
    run(game, 8.0)
    shot(game, "04_stage1_power")

    # 直接跳到頭目戰
    game.pending_i = len(game.pending)
    for e in list(game.enemies):
        e.kill()
    run(game, 4.0)
    shot(game, "05_boss_alarm")
    run(game, 6.0)
    shot(game, "06_boss1")

    # 各關卡背景
    for idx, name in ((1, "07_stage2"), (2, "08_stage3_night"),
                      (3, "09_stage4_desert"), (4, "10_stage5_fortress")):
        game.start_stage(idx)
        game.player.power = 3
        run(game, 3.0, autofire=False)
        run(game, 10.0)
        shot(game, name)
        game.pending_i = len(game.pending)
        for e in list(game.enemies):
            e.kill()
        run(game, 10.0)
        shot(game, f"{name}_boss")

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
