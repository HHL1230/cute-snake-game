"""Sky Strike 1942 - 垂直捲軸射擊遊戲進入點。

執行方式：
    python main.py
"""

from __future__ import annotations

import os
import sys
import time

import pygame

from game import settings as S
from game.app import Game
from game.winfocus import focus_window, has_keyboard_focus


def grab_focus(timeout: float = 2.0) -> None:
    """啟動時把遊戲視窗帶到前景，最多重試 timeout 秒。

    從主控台/批次檔啟動時，SDL 視窗有時會停在主控台後面而拿不到鍵盤焦點，
    造成「畫面有動但按鍵沒反應」。
    """
    deadline = time.time() + timeout
    aggressive = False
    while True:
        pygame.event.pump()
        if focus_window(aggressive=aggressive) or has_keyboard_focus():
            return
        if time.time() >= deadline:
            return
        # 前半段用溫和手法，仍失敗才改用最小化/還原強制取得前景
        aggressive = time.time() > deadline - timeout / 2
        time.sleep(0.1)


def main() -> int:
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        pygame.mixer.init(22050, -16, 1, 512)
    except pygame.error:
        pass  # 無音效裝置時照常執行

    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption(S.TITLE)
    pygame.mouse.set_visible(False)
    grab_focus()

    game = Game(screen)
    game.run()

    if pygame.mixer.get_init():
        pygame.mixer.stop()
        pygame.mixer.quit()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
