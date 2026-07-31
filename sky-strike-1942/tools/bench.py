"""效能量測：模擬最終關卡的重載場景，統計每幀更新 + 繪製耗時。

執行：python tools\\bench.py
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from game import settings as S  # noqa: E402
from game.app import Game  # noqa: E402

DT = 1 / 60


def main() -> int:
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        pygame.mixer.init(22050, -16, 1, 512)
    except pygame.error:
        pass
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    game = Game(screen)

    t0 = time.perf_counter()
    game.start_new_game()
    game.start_stage(4)          # 最終關（敵機最多）
    boot = time.perf_counter() - t0

    times: list[float] = []
    peak_sprites = 0
    for i in range(60 * 40):     # 模擬 40 秒
        if game.player is not None:
            game.player.invuln = 5.0
            game.player.power = 4
            if i % 8 == 0:
                game.player.fire(game)
        t = time.perf_counter()
        game.update(DT)
        game.draw()
        times.append((time.perf_counter() - t) * 1000)
        peak_sprites = max(peak_sprites, len(game.all_sprites) + len(game.effects))

    times.sort()
    print(f"資源初始化 + 關卡建立: {boot * 1000:.0f} ms")
    print(f"每幀耗時  平均 {statistics.mean(times):.2f} ms | "
          f"中位 {statistics.median(times):.2f} ms | "
          f"p95 {times[int(len(times) * 0.95)]:.2f} ms | "
          f"最大 {times[-1]:.2f} ms")
    print(f"同時存在精靈數峰值: {peak_sprites}")
    print(f"對應可達 FPS（平均）: {1000 / statistics.mean(times):.0f}")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
