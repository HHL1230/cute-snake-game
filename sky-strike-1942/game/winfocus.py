"""Windows 視窗焦點與鍵盤輸入工具。

兩個在 Windows 上會讓「按鍵全部沒反應」的坑：

1. 從主控台 / 批次檔啟動時，SDL 視窗常常拿不到鍵盤焦點：畫面有動、但所有按鍵
   都被前面的主控台視窗吃掉。Windows 會拒絕非前景程式呼叫 ``SetForegroundWindow``，
   標準且安全的解法是先用 ``AttachThreadInput`` 把自己的輸入佇列附加到目前前景
   視窗的執行緒，取得前景權限後再切換，最後解除附加。此處不做任何跨程序記憶體存取。

2. SDL2 建立視窗後預設是「開啟文字輸入」的狀態。在中文（注音／倉頡等）輸入法
   啟用時，輸入法會攔截按鍵去做組字，SDL 因此完全收不到 KEYDOWN，遊戲看起來
   就像所有控制鍵都壞掉 —— 而且視窗焦點、滑鼠指標一切正常，非常難查。
   遊戲不需要文字輸入，開場就關掉即可。
"""

from __future__ import annotations

import sys

__all__ = [
    "window_handle",
    "focus_window",
    "has_keyboard_focus",
    "disable_text_input",
]


def _user32():
    if not sys.platform.startswith("win"):
        return None, None
    import ctypes
    from ctypes import wintypes

    u = ctypes.windll.user32
    k = ctypes.windll.kernel32

    u.SetForegroundWindow.argtypes = [wintypes.HWND]
    u.SetForegroundWindow.restype = wintypes.BOOL
    u.SetActiveWindow.argtypes = [wintypes.HWND]
    u.SetFocus.argtypes = [wintypes.HWND]
    u.BringWindowToTop.argtypes = [wintypes.HWND]
    u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    u.GetForegroundWindow.restype = wintypes.HWND
    u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
    u.GetWindowThreadProcessId.restype = wintypes.DWORD
    u.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    u.AttachThreadInput.restype = wintypes.BOOL
    k.GetCurrentThreadId.restype = wintypes.DWORD
    return u, k


def window_handle():
    """取得目前 SDL 視窗的 HWND（失敗時回傳 None）。"""
    try:
        import pygame

        info = pygame.display.get_wm_info()
    except Exception:  # noqa: BLE001 - 沒有視窗或非 Windows
        return None
    hwnd = info.get("window") if isinstance(info, dict) else None
    return hwnd or None


def focus_window(hwnd=None, aggressive: bool = False) -> bool:
    """把遊戲視窗帶到前景並取得鍵盤焦點。回傳是否確定成功。

    aggressive=True 時，若一般手法失敗會再用「最小化後還原」的方式強制取得前景
    （Windows 對還原中的視窗會放行），代價是畫面會閃一下。
    """
    if not sys.platform.startswith("win"):
        return False
    hwnd = hwnd or window_handle()
    if not hwnd:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        u, k = _user32()
        if u is None:
            return False

        hwnd = wintypes.HWND(hwnd)

        # 取消前景鎖定逾時，否則 Windows 會直接拒絕切換前景（只讓工作列閃爍）
        SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001
        SPIF_SENDCHANGE = 0x02
        try:
            u.SystemParametersInfoW(SPI_SETFOREGROUNDLOCKTIMEOUT, 0,
                                    ctypes.c_void_p(0), SPIF_SENDCHANGE)
        except Exception:  # noqa: BLE001
            pass

        u.ShowWindow(hwnd, 5)  # SW_SHOW

        def _try_switch() -> bool:
            fg = u.GetForegroundWindow()
            if fg == hwnd.value:
                return True
            cur = k.GetCurrentThreadId()
            tgt = u.GetWindowThreadProcessId(fg, None) if fg else 0
            attached = bool(tgt) and tgt != cur and bool(u.AttachThreadInput(tgt, cur, True))
            try:
                u.BringWindowToTop(hwnd)
                u.SetForegroundWindow(hwnd)
                u.SetActiveWindow(hwnd)
                u.SetFocus(hwnd)
            finally:
                if attached:
                    u.AttachThreadInput(tgt, cur, False)
            return bool(u.GetForegroundWindow() == hwnd.value)

        if _try_switch():
            return True

        if aggressive:
            # 最小化再還原：Windows 允許正在還原的視窗取得前景
            u.ShowWindow(hwnd, 6)   # SW_MINIMIZE
            u.ShowWindow(hwnd, 9)   # SW_RESTORE
            return _try_switch()
        return False
    except Exception:  # noqa: BLE001 - API 失敗時不影響遊戲
        return False


def has_keyboard_focus() -> bool:
    """SDL 是否認為自己有鍵盤焦點。"""
    try:
        import pygame

        return bool(pygame.key.get_focused())
    except Exception:  # noqa: BLE001
        return True


def disable_text_input() -> bool:
    """關閉 SDL 的文字輸入模式，避免中文輸入法攔截遊戲按鍵。

    SDL2 每次 ``pygame.display.set_mode()`` 建立視窗後都會重新開啟文字輸入，
    所以切換全螢幕之後必須再呼叫一次。回傳是否確實關閉。
    """
    try:
        import pygame

        pygame.key.stop_text_input()
    except Exception:  # noqa: BLE001 - 舊版 pygame 或無視窗時忽略
        return False
    return True
