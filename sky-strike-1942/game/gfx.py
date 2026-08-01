"""以程式繪製所有精靈圖（不使用任何外部圖檔）。"""

from __future__ import annotations

import math
import random

import pygame

from .settings import (
    BLACK, BLUE, BROWN, CYAN, DARK, DEEP_RED, GREEN, GREY, NAVY, ORANGE,
    PURPLE, RED, SAND, SILVER, STEEL, WHITE, YELLOW,
)


def _surf(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)  # type: ignore[return-value]


# --------------------------------------------------------------------------
# 通用飛機繪製（機頭朝上）
# --------------------------------------------------------------------------
def _draw_plane(w: int, h: int, body: tuple[int, int, int],
                wing: tuple[int, int, int], accent: tuple[int, int, int],
                *, twin_boom: bool = False, engines: int = 0,
                canopy: tuple[int, int, int] = CYAN,
                star: bool = False) -> pygame.Surface:
    s = _surf(w, h)
    cx = w / 2
    dark = _shade(body, 0.55)
    wing_dark = _shade(wing, 0.6)

    # 主翼
    wing_y = h * 0.46
    wing_h = h * 0.20
    pygame.draw.polygon(s, wing, [
        (cx - w * 0.48, wing_y + wing_h * 0.9),
        (cx - w * 0.42, wing_y),
        (cx + w * 0.42, wing_y),
        (cx + w * 0.48, wing_y + wing_h * 0.9),
        (cx + w * 0.30, wing_y + wing_h),
        (cx - w * 0.30, wing_y + wing_h),
    ])
    pygame.draw.line(s, wing_dark, (cx - w * 0.45, wing_y + wing_h * 0.75),
                     (cx + w * 0.45, wing_y + wing_h * 0.75), 1)

    # 尾翼
    tail_y = h * 0.84
    pygame.draw.polygon(s, wing, [
        (cx - w * 0.22, tail_y),
        (cx + w * 0.22, tail_y),
        (cx + w * 0.16, tail_y + h * 0.10),
        (cx - w * 0.16, tail_y + h * 0.10),
    ])

    if twin_boom:
        for sign in (-1, 1):
            bx = cx + sign * w * 0.26
            pygame.draw.rect(s, dark, pygame.Rect(bx - w * 0.05, h * 0.22,
                                                  w * 0.10, h * 0.70), border_radius=3)
            pygame.draw.circle(s, accent, (int(bx), int(h * 0.26)), int(w * 0.05))

    # 機身
    pygame.draw.polygon(s, body, [
        (cx, h * 0.02),
        (cx + w * 0.11, h * 0.28),
        (cx + w * 0.12, h * 0.80),
        (cx + w * 0.06, h * 0.96),
        (cx - w * 0.06, h * 0.96),
        (cx - w * 0.12, h * 0.80),
        (cx - w * 0.11, h * 0.28),
    ])
    pygame.draw.line(s, dark, (cx, h * 0.05), (cx, h * 0.94), 1)

    # 引擎（機翼上的發動機艙）
    for i in range(engines):
        offset = (i + 1) / (engines + 1)
        ex = cx - w * 0.40 + w * 0.80 * offset
        pygame.draw.rect(s, dark, pygame.Rect(ex - w * 0.055, wing_y - h * 0.08,
                                              w * 0.11, h * 0.22), border_radius=2)

    # 座艙
    pygame.draw.ellipse(s, canopy, pygame.Rect(cx - w * 0.075, h * 0.26,
                                               w * 0.15, h * 0.20))
    pygame.draw.ellipse(s, _shade(canopy, 0.6), pygame.Rect(cx - w * 0.075, h * 0.26,
                                                            w * 0.15, h * 0.20), 1)

    # 機身識別色帶 / 標誌
    if star:
        for sign in (-1, 1):
            pygame.draw.circle(s, WHITE, (int(cx + sign * w * 0.28), int(wing_y + wing_h * 0.45)),
                               max(2, int(w * 0.055)))
            pygame.draw.circle(s, NAVY, (int(cx + sign * w * 0.28), int(wing_y + wing_h * 0.45)),
                               max(1, int(w * 0.03)))
    else:
        for sign in (-1, 1):
            pygame.draw.circle(s, accent, (int(cx + sign * w * 0.28), int(wing_y + wing_h * 0.45)),
                               max(2, int(w * 0.05)))
    return s


def _prop_overlay(base: pygame.Surface, frame: int) -> pygame.Surface:
    """在機頭疊上旋轉的螺旋槳殘影。"""
    s = base.copy()
    w, h = s.get_size()
    cx = w / 2
    r = w * 0.30
    ang = frame * 0.9
    disc = _surf(w, h)
    for k in range(2):
        a = ang + k * math.pi
        x1 = cx + math.cos(a) * r
        y1 = h * 0.10 + math.sin(a) * r * 0.35
        x2 = cx - math.cos(a) * r
        y2 = h * 0.10 - math.sin(a) * r * 0.35
        pygame.draw.line(disc, (220, 220, 230, 90), (x1, y1), (x2, y2), 2)
    s.blit(disc, (0, 0))
    return s


# --------------------------------------------------------------------------
# 各種機體
# --------------------------------------------------------------------------
def make_player(size: int = 46) -> pygame.Surface:
    return _draw_plane(size, size, SILVER, (170, 178, 190), RED,
                       twin_boom=True, engines=0, star=True)


def make_wingman(size: int = 26) -> pygame.Surface:
    return _draw_plane(size, size, (200, 206, 216), (160, 168, 182), BLUE, star=True)


def _enemy_variant(kind: str, size: int) -> pygame.Surface:
    if kind == "scout":
        s = _draw_plane(size, size, (150, 158, 150), (120, 130, 122), RED)
    elif kind == "red":
        s = _draw_plane(size, size, (214, 74, 66), (176, 52, 48), WHITE)
    elif kind == "green":
        s = _draw_plane(size, size, (96, 150, 92), (72, 118, 70), RED, engines=0)
    elif kind == "bomber":
        s = _draw_plane(size, int(size * 0.9), (126, 134, 146), (100, 108, 122),
                        RED, engines=2)
    elif kind == "heavy":
        s = _draw_plane(size, int(size * 0.95), (108, 112, 128), (86, 90, 106),
                        ORANGE, engines=4)
    elif kind == "jet":
        s = _draw_plane(size, size, (86, 92, 120), (66, 72, 100), PURPLE)
    else:
        s = _draw_plane(size, size, GREY, STEEL, RED)
    return pygame.transform.flip(s, False, True)


def make_boss(stage: int) -> pygame.Surface:
    """依關卡產生不同外觀的巨型敵機（機頭朝下）。"""
    palettes = [
        ((130, 138, 150), (104, 112, 126), RED),
        ((120, 148, 120), (92, 118, 94), ORANGE),
        ((116, 112, 148), (90, 88, 122), CYAN),
        ((150, 96, 92), (118, 70, 68), YELLOW),
        ((96, 100, 112), (72, 76, 88), PURPLE),
    ]
    body, wing, accent = palettes[(stage - 1) % len(palettes)]
    w, h = 210 + stage * 8, 150
    s = _surf(w, h)
    cx = w / 2
    dark = _shade(body, 0.55)

    # 主翼
    pygame.draw.polygon(s, wing, [
        (cx - w * 0.49, h * 0.34), (cx + w * 0.49, h * 0.34),
        (cx + w * 0.44, h * 0.56), (cx - w * 0.44, h * 0.56)])
    pygame.draw.line(s, _shade(wing, 0.7), (cx - w * 0.47, h * 0.50),
                     (cx + w * 0.47, h * 0.50), 2)

    # 引擎艙（四發）
    for sign in (-1, 1):
        for k in (0.20, 0.34):
            ex = cx + sign * w * k
            pygame.draw.rect(s, dark, pygame.Rect(ex - w * 0.035, h * 0.30,
                                                  w * 0.07, h * 0.32), border_radius=4)
            pygame.draw.circle(s, accent, (int(ex), int(h * 0.62)), int(w * 0.018))

    # 機身
    pygame.draw.polygon(s, body, [
        (cx, h * 0.99), (cx + w * 0.075, h * 0.72), (cx + w * 0.085, h * 0.22),
        (cx + w * 0.05, h * 0.04), (cx - w * 0.05, h * 0.04),
        (cx - w * 0.085, h * 0.22), (cx - w * 0.075, h * 0.72)])
    pygame.draw.line(s, dark, (cx, h * 0.06), (cx, h * 0.96), 2)

    # 尾翼（上方）
    pygame.draw.polygon(s, wing, [
        (cx - w * 0.20, h * 0.02), (cx + w * 0.20, h * 0.02),
        (cx + w * 0.14, h * 0.16), (cx - w * 0.14, h * 0.16)])

    # 駕駛艙 / 機鼻玻璃
    pygame.draw.ellipse(s, CYAN, pygame.Rect(cx - w * 0.045, h * 0.74,
                                             w * 0.09, h * 0.16))
    pygame.draw.ellipse(s, _shade(CYAN, 0.6), pygame.Rect(cx - w * 0.045, h * 0.74,
                                                          w * 0.09, h * 0.16), 2)
    # 砲塔
    for sign in (-1, 1):
        pygame.draw.circle(s, dark, (int(cx + sign * w * 0.13), int(h * 0.60)),
                           int(w * 0.035))
        pygame.draw.circle(s, accent, (int(cx + sign * w * 0.13), int(h * 0.60)),
                           int(w * 0.018))
    # 識別標誌
    for sign in (-1, 1):
        pygame.draw.circle(s, accent, (int(cx + sign * w * 0.40), int(h * 0.45)),
                           int(w * 0.028))
    return s


# --------------------------------------------------------------------------
# 子彈、道具、爆炸
# --------------------------------------------------------------------------
def make_player_bullet() -> pygame.Surface:
    s = _surf(6, 16)
    pygame.draw.rect(s, YELLOW, pygame.Rect(1, 0, 4, 16), border_radius=2)
    pygame.draw.rect(s, WHITE, pygame.Rect(2, 2, 2, 8))
    return s


def make_laser_bullet(width: int = 10, height: int = 40) -> pygame.Surface:
    """穿透雷射光束：中央亮白、外圍青色輝光。"""
    s = _surf(width, height)
    pygame.draw.rect(s, (90, 220, 255, 110), pygame.Rect(0, 0, width, height),
                     border_radius=width // 2)
    inner = max(2, width - 4)
    pygame.draw.rect(s, (150, 240, 255, 220),
                     pygame.Rect((width - inner) // 2, 1, inner, height - 2),
                     border_radius=inner // 2)
    core = max(1, width - 7)
    pygame.draw.rect(s, (255, 255, 255, 255),
                     pygame.Rect((width - core) // 2, 2, core, height - 4),
                     border_radius=max(1, core // 2))
    return s


def make_enemy_bullet() -> pygame.Surface:
    s = _surf(12, 12)
    pygame.draw.circle(s, (255, 236, 160), (6, 6), 6)
    pygame.draw.circle(s, ORANGE, (6, 6), 4)
    pygame.draw.circle(s, DEEP_RED, (6, 6), 2)
    return s


def make_boss_bullet() -> pygame.Surface:
    s = _surf(16, 16)
    pygame.draw.circle(s, (255, 200, 220), (8, 8), 8)
    pygame.draw.circle(s, (232, 92, 150), (8, 8), 5)
    pygame.draw.circle(s, WHITE, (8, 8), 2)
    return s


_POWERUP_STYLE = {
    "power": ("P", RED, WHITE),
    "wing": ("W", BLUE, WHITE),
    "bomb": ("B", (60, 62, 74), YELLOW),
    "loop": ("L", GREEN, WHITE),
    "life": ("1UP", PURPLE, WHITE),
    "laser": ("Z", (18, 122, 158), CYAN),
    "vulcan": ("V", (168, 96, 16), YELLOW),
}


def make_powerup(kind: str, font: pygame.font.Font) -> pygame.Surface:
    label, bg, fg = _POWERUP_STYLE[kind]
    w, h = 30, 24
    s = _surf(w, h)
    pygame.draw.rect(s, WHITE, pygame.Rect(0, 0, w, h), border_radius=5)
    pygame.draw.rect(s, bg, pygame.Rect(2, 2, w - 4, h - 4), border_radius=4)
    txt = font.render(label, True, fg)
    s.blit(txt, txt.get_rect(center=(w // 2, h // 2)))
    return s


def make_explosion_frames(size: int, count: int = 9) -> list[pygame.Surface]:
    frames: list[pygame.Surface] = []
    rnd = random.Random(size * 7 + 13)
    sparks = [(rnd.uniform(0, math.tau), rnd.uniform(0.45, 1.0)) for _ in range(10)]
    for i in range(count):
        t = i / (count - 1)
        s = _surf(size, size)
        c = size / 2
        radius = c * (0.22 + 0.78 * t)
        alpha = int(255 * (1.0 - t) ** 0.8)
        pygame.draw.circle(s, (60, 40, 40, int(alpha * 0.5)), (c, c), radius)
        pygame.draw.circle(s, (255, 170, 60, alpha), (c, c), radius * 0.72)
        pygame.draw.circle(s, (255, 240, 190, alpha), (c, c), radius * 0.38)
        for ang, dist in sparks:
            r = radius * dist
            x = c + math.cos(ang) * r
            y = c + math.sin(ang) * r
            pygame.draw.circle(s, (255, 200, 110, alpha), (x, y), max(1, size * 0.035 * (1 - t)))
        frames.append(s)
    return frames


def _flashed(surf: pygame.Surface, tint: tuple[int, int, int]) -> pygame.Surface:
    img = surf.copy()
    img.fill((*tint, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return img


# --------------------------------------------------------------------------
# 資源總表
# --------------------------------------------------------------------------
class Assets:
    def __init__(self) -> None:
        pygame.font.init()
        self.font_tiny = pygame.font.SysFont("consolas,couriernew,monospace", 12, bold=True)
        self.font_small = pygame.font.SysFont("consolas,couriernew,monospace", 16, bold=True)
        self.font = pygame.font.SysFont("consolas,couriernew,monospace", 22, bold=True)
        self.font_big = pygame.font.SysFont("consolas,couriernew,monospace", 34, bold=True)
        self.font_huge = pygame.font.SysFont("consolas,couriernew,monospace", 52, bold=True)
        # 中文字型（找不到時 pygame 會退回預設字型）
        _cjk = "microsoftjhenghei,microsoftyahei,mingliu,pmingliu,simsun,notosanscjktc"
        self.font_cjk = pygame.font.SysFont(_cjk, 20, bold=True)
        self.font_cjk_small = pygame.font.SysFont(_cjk, 15, bold=True)

        base_player = make_player()
        # 螺旋槳動畫 + 左右傾斜
        self.player_frames: dict[int, list[pygame.Surface]] = {}
        for bank in (-2, -1, 0, 1, 2):
            scale = 1.0 - abs(bank) * 0.16
            frames = []
            for f in range(4):
                img = _prop_overlay(base_player, f)
                if scale != 1.0:
                    w = max(6, int(img.get_width() * scale))
                    img = pygame.transform.smoothscale(img, (w, img.get_height()))
                frames.append(img)
            self.player_frames[bank] = frames

        # 翻滾（loop-the-loop）動畫：機身橫向壓縮 + 亮邊
        self.player_roll: list[pygame.Surface] = []
        for i in range(12):
            t = i / 11
            scale = abs(math.cos(t * math.pi * 2)) * 0.9 + 0.10
            img = pygame.transform.smoothscale(
                base_player, (max(5, int(base_player.get_width() * scale)),
                              base_player.get_height()))
            glow = img.copy()
            glow.fill((120, 190, 255, 70), special_flags=pygame.BLEND_RGBA_ADD)
            self.player_roll.append(glow)

        self.wingman = make_wingman()

        self.enemies: dict[str, pygame.Surface] = {
            "scout": _enemy_variant("scout", 34),
            "red": _enemy_variant("red", 34),
            "green": _enemy_variant("green", 38),
            "bomber": _enemy_variant("bomber", 54),
            "heavy": _enemy_variant("heavy", 72),
            "jet": _enemy_variant("jet", 32),
        }
        self.bosses: dict[int, pygame.Surface] = {i: make_boss(i) for i in range(1, 6)}
        # 受擊閃白版本（預先產生，避免遊戲中重複配置 Surface）
        self.enemies_hit = {k: _flashed(v, (90, 90, 90)) for k, v in self.enemies.items()}
        self.bosses_hit = {k: _flashed(v, (55, 22, 22)) for k, v in self.bosses.items()}

        self.player_bullet = make_player_bullet()
        self.laser_bullet = make_laser_bullet(10, 40)
        self.laser_bullet_small = make_laser_bullet(6, 30)
        self.enemy_bullet = make_enemy_bullet()
        self.boss_bullet = make_boss_bullet()
        self.powerups = {k: make_powerup(k, self.font_tiny) for k in _POWERUP_STYLE}

        self.explosions: dict[str, list[pygame.Surface]] = {
            "small": make_explosion_frames(40),
            "big": make_explosion_frames(96),
            "huge": make_explosion_frames(190, 12),
        }
