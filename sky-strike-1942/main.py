"""Sky Strike 1942 - 垂直捲軸射擊遊戲進入點。

執行方式：
    python main.py
"""

from __future__ import annotations

import sys

import pygame

from game import settings as S
from game.app import Game


def main() -> int:
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        pygame.mixer.init(22050, -16, 1, 512)
    except pygame.error:
        pass  # 無音效裝置時照常執行

    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption(S.TITLE)
    pygame.mouse.set_visible(False)

    game = Game(screen)
    game.run()

    if pygame.mixer.get_init():
        pygame.mixer.stop()
        pygame.mixer.quit()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
