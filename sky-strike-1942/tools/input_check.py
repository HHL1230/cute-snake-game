"""真實視窗輸入診斷：同時記錄 KEYDOWN 事件與 key.get_pressed() 狀態。

執行：python tools\\input_check.py [秒數]
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

WATCH = {
    pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT", pygame.K_UP: "UP",
    pygame.K_DOWN: "DOWN", pygame.K_z: "Z", pygame.K_SPACE: "SPACE",
    pygame.K_x: "X", pygame.K_RETURN: "ENTER",
}


def _make_injector():
    """讓本行程自己送出按鍵（合規的 keybd_event UI 自動化，不做跨行程記憶體操作）。"""
    import ctypes

    user32 = ctypes.windll.user32
    hwnd = pygame.display.get_wm_info().get("window")
    if hwnd:
        user32.SetForegroundWindow(hwnd)

    # (起始秒, 結束秒, 虛擬鍵碼, 名稱)
    plan = [
        (1.0, 2.2, 0x27, "RIGHT"),
        (2.6, 3.8, 0x25, "LEFT"),
        (4.2, 5.4, 0x28, "DOWN"),
        (5.8, 7.0, 0x5A, "Z"),
        (7.4, 8.6, 0x20, "SPACE"),
    ]
    state = {vk: False for _, _, vk, _ in plan}

    def tick(now: float) -> None:
        for start, end, vk, name in plan:
            want = start <= now < end
            if want != state[vk]:
                state[vk] = want
                user32.keybd_event(vk, 0, 0 if want else 2, 0)
                print(f"    inject {'DOWN' if want else 'UP  '} {name} @ {now:4.1f}s",
                      flush=True)

    return tick


def main() -> int:
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        pygame.mixer.init(22050, -16, 1, 512)
    except pygame.error:
        pass
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption(S.TITLE)
    from main import focus_window  # noqa: PLC0415

    focus_window()
    game = Game(screen)
    if "--auto" in sys.argv:
        game.start_new_game()
    print("READY", flush=True)

    inject = _make_injector() if "--inject" in sys.argv else None

    keydowns: list[str] = []
    frames = 0
    last_log = 0.0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < duration:
        dt = min(game.clock.tick(S.FPS) / 1000.0, 1 / 30)
        if inject:
            inject(time.perf_counter() - t0)
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                keydowns.append(WATCH.get(e.key, str(e.key)))
            game.handle_event(e)
        game.update(dt)
        game.draw()
        frames += 1

        now = time.perf_counter() - t0
        if now - last_log >= 0.5:
            keys = pygame.key.get_pressed()
            held = [n for k, n in WATCH.items() if keys[k]]
            pos = (round(game.player.pos.x), round(game.player.pos.y)) if game.player else None
            print(f"t={now:5.1f}s fps={frames / now:5.1f} state={game.state:<10} "
                  f"pos={pos} held={held} keydown={keydowns} "
                  f"bullets={len(game.player_bullets)} focus={pygame.key.get_focused()}",
                  flush=True)
            keydowns = []
            last_log = now

    pygame.quit()
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
