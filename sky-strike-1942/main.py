"""Sky Strike 1942 - 垂直捲軸射擊遊戲進入點。

執行方式：
    python main.py
"""

from __future__ import annotations

import os
import sys

import pygame

from game import settings as S
from game.app import Game


def focus_window() -> None:
    """把遊戲視窗帶到前景並取得鍵盤焦點（Windows）。

    從主控台/批次檔啟動時，SDL 視窗有時會停在主控台後面而拿不到鍵盤焦點，
    造成「畫面有動但按鍵沒反應」。這裡用標準的視窗 API 主動聚焦。
    """
    try:
        import ctypes

        hwnd = pygame.display.get_wm_info().get("window")
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, 5)          # SW_SHOW
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
        user32.SetFocus(hwnd)
    except Exception:  # noqa: BLE001 - 非 Windows 或 API 失敗時忽略
        pass


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
    focus_window()

    game = Game(screen)
    game.run()

    if pygame.mixer.get_init():
        pygame.mixer.stop()
        pygame.mixer.quit()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
