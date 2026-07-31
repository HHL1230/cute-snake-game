"""實際開視窗執行 3 秒並自動關閉，用於驗證真實顯示 / 音效裝置與 FPS。

執行：python tools\\window_check.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from game import settings as S  # noqa: E402
from game.app import Game  # noqa: E402


def main() -> int:
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        pygame.mixer.init(22050, -16, 1, 512)
        print("音效裝置:", pygame.mixer.get_init())
    except pygame.error as exc:
        print("無音效裝置:", exc)

    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption(S.TITLE + " (self check)")
    game = Game(screen)
    print("視窗建立:", pygame.display.get_surface().get_size(),
          "| driver:", pygame.display.get_driver())
    if game.audio.enabled:
        print(f"音效格式 channels={game.audio.channels} "
              f"shoot={game.audio.sounds['shoot'].get_length() * 1000:.0f}ms (應約 70ms)")
        game.audio.play_music("stage1")
        print(f"BGM 長度={game.audio._music_cache['stage1'].get_length():.1f}s (應約 14.5s)")

    game.start_new_game()
    frames = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 4.0:
        dt = min(game.clock.tick(S.FPS) / 1000.0, 1 / 30)
        for e in pygame.event.get():
            pass
        if game.player is not None and frames % 9 == 0:
            game.player.fire(game)
        game.update(dt)
        game.draw()
        frames += 1
    elapsed = time.perf_counter() - t0
    print(f"實測 FPS: {frames / elapsed:.1f}（目標 {S.FPS}）")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
