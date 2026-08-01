"""以程式繪製所有精靈圖（不使用任何外部圖檔）。

為了讓外觀更精緻，機體 / 頭目 / 爆炸都先以數倍解析度繪製再等比縮小
（supersampling），藉此得到平滑邊緣；並加上圓柱漸層機身、座艙玻璃反光、
發動機罩、翼面板線與投影陰影，讓平面圖看起來更立體。
"""

from __future__ import annotations

import math
import random

import pygame

from .settings import (
    BLUE, CYAN, DEEP_RED, GREEN, GREY, NAVY, ORANGE,
    PURPLE, RED, SILVER, STEEL, WHITE, YELLOW,
)

SS = 4  # 超取樣倍率


def _surf(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((int(w), int(h)), pygame.SRCALPHA)


def _shade(color, factor: float):
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


def _mix(c1, c2, t: float):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _down(s: pygame.Surface, w: int, h: int) -> pygame.Surface:
    return pygame.transform.smoothscale(s, (int(w), int(h)))


def _with_shadow(art: pygame.Surface, dx: float = 2.0, dy: float = 3.0,
                 alpha: int = 105) -> pygame.Surface:
    """在原圖下方疊一層半透明黑色剪影，做出離地投影的立體感。"""
    w, h = art.get_size()
    out = _surf(w, h)
    sh = art.copy()
    sh.fill((0, 0, 0, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(sh, (dx, dy))
    out.blit(art, (0, 0))
    return out


def _with_outline(art: pygame.Surface, pad: int = 3, alpha: int = 150) -> pygame.Surface:
    """在精靈外圍加一圈暗色光暈，讓機體在複雜背景上仍清楚可辨。"""
    w, h = art.get_size()
    out = _surf(w + pad * 2, h + pad * 2)
    sil = art.copy()
    sil.fill((8, 10, 16, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(pygame.transform.smoothscale(sil, (w + pad * 2, h + pad * 2)), (0, 0))
    out.blit(art, (pad, pad))
    return out


def _star_points(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.42
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts


# --------------------------------------------------------------------------
# 通用飛機繪製（機頭朝上）
# --------------------------------------------------------------------------
def _draw_plane(w: int, h: int, body, wing, accent, *,
                twin_boom: bool = False, engines: int = 0,
                canopy=CYAN, star: bool = False, jet: bool = False) -> pygame.Surface:
    W, H = int(w * SS), int(h * SS)
    s = _surf(W, H)
    cx = W / 2

    hi = _shade(body, 1.26)
    mid = body
    lo = _shade(body, 0.70)
    dk = _shade(body, 0.44)
    whi = _shade(wing, 1.22)
    wmid = wing
    wlo = _shade(wing, 0.66)
    wdk = _shade(wing, 0.42)

    def toward(pts, y0: float, k: float):
        """把多邊形往 y0 這條基準線壓縮，用來做翼面受光帶。"""
        base = H * y0
        return [(x, base + (y - base) * k) for x, y in pts]

    # ---- 水平尾翼 ----------------------------------------------------
    ts = 0.215
    tail = [(cx - W * ts, H * 0.840), (cx + W * ts, H * 0.840),
            (cx + W * ts * 0.76, H * 0.940), (cx - W * ts * 0.76, H * 0.940)]
    pygame.draw.polygon(s, wlo, tail)
    pygame.draw.polygon(s, wmid, toward(tail, 0.840, 0.60))
    pygame.draw.polygon(s, whi, toward(tail, 0.840, 0.24))

    # ---- 主翼 --------------------------------------------------------
    le, te, span = 0.430, 0.655, 0.470
    wing_pts = [
        (cx - W * 0.335, H * le),
        (cx - W * span, H * (le + 0.052)),
        (cx - W * span * 0.985, H * (te - 0.060)),
        (cx - W * 0.300, H * te),
        (cx + W * 0.300, H * te),
        (cx + W * span * 0.985, H * (te - 0.060)),
        (cx + W * span, H * (le + 0.052)),
        (cx + W * 0.335, H * le),
    ]
    pygame.draw.polygon(s, wlo, wing_pts)
    pygame.draw.polygon(s, wmid, toward(wing_pts, le, 0.66))
    pygame.draw.polygon(s, whi, toward(wing_pts, le, 0.28))
    # 翼面板線 / 副翼
    for sign in (-1, 1):
        for k in (0.255, 0.360):
            x = cx + sign * W * k
            pygame.draw.line(s, wdk, (x, H * (le + 0.020)), (x, H * (te - 0.006)),
                             max(1, SS // 2))
        pygame.draw.line(s, wdk, (cx + sign * W * 0.30, H * (te - 0.030)),
                         (cx + sign * W * span * 0.96, H * (te - 0.072)), max(1, SS // 2))

    # ---- 雙尾桁（P-38 風格）------------------------------------------
    if twin_boom:
        for sign in (-1, 1):
            bx = cx + sign * W * 0.265
            bw = W * 0.052
            pygame.draw.rect(s, lo, pygame.Rect(bx - bw, H * 0.215, bw * 2, H * 0.700),
                             border_radius=int(bw))
            pygame.draw.rect(s, mid, pygame.Rect(bx - bw * 0.62, H * 0.225,
                                                 bw * 1.24, H * 0.680),
                             border_radius=int(bw * 0.62))
            pygame.draw.rect(s, hi, pygame.Rect(bx - bw * 0.26, H * 0.235,
                                                bw * 0.52, H * 0.640),
                             border_radius=int(bw * 0.3))
            # 尾桁前端的發動機罩
            pygame.draw.ellipse(s, dk, pygame.Rect(bx - bw * 1.05, H * 0.205,
                                                   bw * 2.1, H * 0.095))
            pygame.draw.ellipse(s, accent, pygame.Rect(bx - bw * 0.45, H * 0.222,
                                                       bw * 0.9, H * 0.055))
            # 垂直尾翼
            pygame.draw.polygon(s, wmid, [
                (bx - bw * 0.9, H * 0.870), (bx + bw * 0.9, H * 0.870),
                (bx + bw * 0.55, H * 0.965), (bx - bw * 0.55, H * 0.965)])

    # ---- 翼上發動機艙 ------------------------------------------------
    for i in range(engines):
        offset = (i + 1) / (engines + 1)
        ex = cx - W * 0.395 + W * 0.790 * offset
        nw = W * 0.056
        pygame.draw.rect(s, lo, pygame.Rect(ex - nw, H * (le - 0.055), nw * 2, H * 0.255),
                         border_radius=int(nw * 0.8))
        pygame.draw.rect(s, mid, pygame.Rect(ex - nw * 0.60, H * (le - 0.045),
                                             nw * 1.2, H * 0.235),
                         border_radius=int(nw * 0.5))
        pygame.draw.ellipse(s, dk, pygame.Rect(ex - nw * 1.02, H * (le - 0.062),
                                               nw * 2.04, H * 0.070))
        pygame.draw.ellipse(s, accent, pygame.Rect(ex - nw * 0.34, H * (le - 0.048),
                                                   nw * 0.68, H * 0.040))

    # ---- 機身（以層層內縮的多邊形做出圓柱受光）-----------------------
    fus = [
        (cx, H * 0.012),
        (cx + W * 0.060, H * 0.105),
        (cx + W * 0.086, H * 0.300),
        (cx + W * 0.080, H * 0.720),
        (cx + W * 0.048, H * 0.930),
        (cx - W * 0.048, H * 0.930),
        (cx - W * 0.080, H * 0.720),
        (cx - W * 0.086, H * 0.300),
        (cx - W * 0.060, H * 0.105),
    ]
    pygame.draw.polygon(s, lo, fus)
    pygame.draw.polygon(s, mid, [(cx + (x - cx) * 0.74, y) for x, y in fus])
    pygame.draw.polygon(s, hi, [(cx - W * 0.016 + (x - cx) * 0.34, y) for x, y in fus])
    # 機身接縫
    for fy in (0.36, 0.50, 0.76):
        pygame.draw.line(s, dk, (cx - W * 0.070, H * fy), (cx + W * 0.070, H * fy), 1)

    # ---- 機首：發動機罩 + 排氣管 + 螺旋槳轂 ---------------------------
    if jet:
        pygame.draw.polygon(s, dk, [
            (cx, H * 0.005), (cx + W * 0.055, H * 0.09),
            (cx - W * 0.055, H * 0.09)])
        pygame.draw.ellipse(s, _mix(canopy, WHITE, 0.4),
                            pygame.Rect(cx - W * 0.022, H * 0.020, W * 0.044, H * 0.042))
    else:
        cowl = pygame.Rect(cx - W * 0.100, H * 0.045, W * 0.200, H * 0.120)
        pygame.draw.ellipse(s, dk, cowl)
        pygame.draw.ellipse(s, _shade(body, 0.92),
                            cowl.inflate(-W * 0.022, -H * 0.020))
        pygame.draw.ellipse(s, hi, pygame.Rect(cx - W * 0.082, H * 0.058,
                                               W * 0.075, H * 0.048))
        # 排氣管
        for sign in (-1, 1):
            for k in range(3):
                pygame.draw.rect(s, dk, pygame.Rect(
                    cx + sign * W * 0.082 - (W * 0.016 if sign > 0 else 0),
                    H * (0.175 + k * 0.030), W * 0.016, H * 0.018))
        # 槳轂
        pygame.draw.ellipse(s, accent, pygame.Rect(cx - W * 0.034, H * 0.002,
                                                   W * 0.068, H * 0.078))
        pygame.draw.ellipse(s, _mix(accent, WHITE, 0.6),
                            pygame.Rect(cx - W * 0.016, H * 0.012, W * 0.022, H * 0.032))

    # ---- 座艙 --------------------------------------------------------
    cp = pygame.Rect(cx - W * 0.064, H * 0.250, W * 0.128, H * 0.180)
    pygame.draw.ellipse(s, _shade(canopy, 0.32), cp)
    pygame.draw.ellipse(s, canopy, cp.inflate(-W * 0.018, -H * 0.024))
    pygame.draw.ellipse(s, _mix(canopy, WHITE, 0.80),
                        pygame.Rect(cx - W * 0.042, H * 0.268, W * 0.030, H * 0.062))
    pygame.draw.line(s, _shade(canopy, 0.3), (cx, H * 0.256), (cx, H * 0.424),
                     max(1, SS // 2))

    # ---- 國籍標誌 ----------------------------------------------------
    iy = H * (le + 0.115)
    for sign in (-1, 1):
        ix = cx + sign * W * 0.300
        if star:
            r = W * 0.062
            pygame.draw.circle(s, WHITE, (ix, iy), r)
            pygame.draw.circle(s, NAVY, (ix, iy), r * 0.82)
            pygame.draw.polygon(s, WHITE, _star_points(ix, iy, r * 0.74))
        else:
            r = W * 0.058
            pygame.draw.circle(s, WHITE, (ix, iy), r)
            pygame.draw.circle(s, accent, (ix, iy), r * 0.78)

    return _down(s, w, h)


def _prop_disc(w: int, h: int, frame: int) -> pygame.Surface:
    """半透明螺旋槳殘影（另存一張以 alpha blit，避免蓋掉機身）。"""
    W, H = w * SS, h * SS
    d = _surf(W, H)
    cx, cy = W / 2, H * 0.085
    r = W * 0.34
    pygame.draw.ellipse(d, (215, 220, 235, 26),
                        pygame.Rect(cx - r, cy - r * 0.34, r * 2, r * 0.68))
    ang = frame * 0.85
    for k in range(2):
        a = ang + k * math.pi
        x1, y1 = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.34
        x2, y2 = cx - math.cos(a) * r, cy - math.sin(a) * r * 0.34
        pygame.draw.line(d, (235, 238, 250, 120), (x1, y1), (x2, y2), max(2, SS))
    return _down(d, w, h)


# --------------------------------------------------------------------------
# 各種機體
# --------------------------------------------------------------------------
def make_player(size: int = 46) -> pygame.Surface:
    return _draw_plane(size, size, (206, 212, 222), (176, 184, 198), RED,
                       twin_boom=True, star=True)


def make_wingman(size: int = 26) -> pygame.Surface:
    return _with_outline(_with_shadow(
        _draw_plane(size, size, (204, 210, 220), (166, 174, 190), BLUE, star=True),
        1.5, 2.0), 2)


_ENEMY_LOOK = {
    "scout":  ((156, 164, 152), (124, 134, 124), RED, 1.00, 0, False),
    "red":    ((216, 78, 68), (178, 54, 48), WHITE, 1.00, 0, False),
    "green":  ((98, 152, 94), (74, 120, 72), RED, 1.00, 0, False),
    "bomber": ((132, 140, 152), (104, 112, 126), RED, 0.90, 2, False),
    "heavy":  ((112, 116, 132), (88, 92, 108), ORANGE, 0.95, 4, False),
    "jet":    ((92, 98, 128), (70, 76, 104), PURPLE, 1.00, 0, True),
}


def _enemy_variant(kind: str, size: int) -> pygame.Surface:
    body, wing, accent, ratio, engines, jet = _ENEMY_LOOK.get(
        kind, (GREY, STEEL, RED, 1.0, 0, False))
    s = _draw_plane(size, int(size * ratio), body, wing, accent,
                    engines=engines, jet=jet)
    s = pygame.transform.flip(s, False, True)
    return _with_shadow(s, 2.0, 2.5)


# --------------------------------------------------------------------------
# 頭目
# --------------------------------------------------------------------------
_BOSS_PALETTE = [
    ((136, 144, 158), (108, 116, 132), RED),          # 1 超重爆
    ((124, 152, 124), (94, 122, 96), ORANGE),         # 2 空中要塞
    ((118, 114, 152), (90, 88, 124), CYAN),           # 3 夜戰母機
    ((156, 100, 94), (122, 72, 68), YELLOW),          # 4 陸上戰艦
    ((100, 104, 118), (74, 78, 92), PURPLE),          # 5 要塞核心
    ((160, 88, 62), (124, 62, 42), YELLOW),           # 6 熔岩機龍
    ((80, 92, 112), (58, 68, 88), CYAN),              # 7 旗艦
]


def make_boss(stage: int) -> pygame.Surface:
    """依關卡產生不同外觀的巨型敵機（機頭朝下）。"""
    body, wing, accent = _BOSS_PALETTE[(stage - 1) % len(_BOSS_PALETTE)]
    w, h = 210 + stage * 8, 150
    ss = 3
    W, H = w * ss, h * ss
    s = _surf(W, H)
    cx = W / 2

    hi = _shade(body, 1.24)
    mid = body
    lo = _shade(body, 0.72)
    dk = _shade(body, 0.44)
    whi = _shade(wing, 1.20)
    wlo = _shade(wing, 0.66)
    wdk = _shade(wing, 0.42)

    # ---- 上方尾翼 ----
    pygame.draw.polygon(s, wlo, [
        (cx - W * 0.205, H * 0.010), (cx + W * 0.205, H * 0.010),
        (cx + W * 0.140, H * 0.165), (cx - W * 0.140, H * 0.165)])
    pygame.draw.polygon(s, whi, [
        (cx - W * 0.185, H * 0.020), (cx + W * 0.185, H * 0.020),
        (cx + W * 0.135, H * 0.110), (cx - W * 0.135, H * 0.110)])

    # ---- 主翼 ----
    wing_pts = [
        (cx - W * 0.492, H * 0.330), (cx + W * 0.492, H * 0.330),
        (cx + W * 0.452, H * 0.575), (cx - W * 0.452, H * 0.575)]
    pygame.draw.polygon(s, wlo, wing_pts)
    pygame.draw.polygon(s, wing, [(x, H * 0.330 + (y - H * 0.330) * 0.66)
                                  for x, y in wing_pts])
    pygame.draw.polygon(s, whi, [(x, H * 0.330 + (y - H * 0.330) * 0.26)
                                 for x, y in wing_pts])
    for sign in (-1, 1):
        for k in (0.20, 0.29, 0.38, 0.46):
            x = cx + sign * W * k
            pygame.draw.line(s, wdk, (x, H * 0.336), (x, H * 0.570), max(1, ss // 2))

    # ---- 發動機艙（四發，含排氣輝光）----
    for sign in (-1, 1):
        for k in (0.205, 0.345):
            ex = cx + sign * W * k
            nw = W * 0.040
            pygame.draw.rect(s, lo, pygame.Rect(ex - nw, H * 0.295, nw * 2, H * 0.330),
                             border_radius=int(nw))
            pygame.draw.rect(s, mid, pygame.Rect(ex - nw * 0.6, H * 0.305,
                                                 nw * 1.2, H * 0.310),
                             border_radius=int(nw * 0.6))
            pygame.draw.rect(s, hi, pygame.Rect(ex - nw * 0.24, H * 0.315,
                                                nw * 0.48, H * 0.290),
                             border_radius=int(nw * 0.3))
            pygame.draw.ellipse(s, dk, pygame.Rect(ex - nw * 1.05, H * 0.595,
                                                   nw * 2.1, H * 0.060))
            pygame.draw.ellipse(s, accent, pygame.Rect(ex - nw * 0.55, H * 0.605,
                                                       nw * 1.1, H * 0.038))

    # ---- 機身 ----
    fus = [
        (cx, H * 0.992),
        (cx + W * 0.070, H * 0.720),
        (cx + W * 0.088, H * 0.215),
        (cx + W * 0.048, H * 0.035),
        (cx - W * 0.048, H * 0.035),
        (cx - W * 0.088, H * 0.215),
        (cx - W * 0.070, H * 0.720),
    ]
    pygame.draw.polygon(s, lo, fus)
    pygame.draw.polygon(s, mid, [(cx + (x - cx) * 0.74, y) for x, y in fus])
    pygame.draw.polygon(s, hi, [(cx - W * 0.014 + (x - cx) * 0.34, y) for x, y in fus])
    for fy in (0.25, 0.40, 0.55, 0.70):
        pygame.draw.line(s, dk, (cx - W * 0.075, H * fy), (cx + W * 0.075, H * fy), 1)

    # ---- 機鼻玻璃（下方）----
    nose = pygame.Rect(cx - W * 0.052, H * 0.730, W * 0.104, H * 0.180)
    pygame.draw.ellipse(s, _shade(CYAN, 0.30), nose)
    pygame.draw.ellipse(s, CYAN, nose.inflate(-W * 0.012, -H * 0.024))
    pygame.draw.ellipse(s, _mix(CYAN, WHITE, 0.8),
                        pygame.Rect(cx - W * 0.034, H * 0.750, W * 0.026, H * 0.055))

    # ---- 砲塔 ----
    for sign in (-1, 1):
        tx, ty = cx + sign * W * 0.128, H * 0.610
        r = W * 0.036
        pygame.draw.circle(s, dk, (tx, ty), r)
        pygame.draw.circle(s, _shade(body, 0.85), (tx, ty), r * 0.78)
        pygame.draw.circle(s, accent, (tx, ty), r * 0.40)
        pygame.draw.rect(s, dk, pygame.Rect(tx - r * 0.16, ty + r * 0.6,
                                            r * 0.32, r * 1.5))

    # ---- 識別標誌 ----
    for sign in (-1, 1):
        ix, iy = cx + sign * W * 0.400, H * 0.452
        r = W * 0.030
        pygame.draw.circle(s, WHITE, (ix, iy), r)
        pygame.draw.circle(s, accent, (ix, iy), r * 0.76)

    return _down(s, w, h)


# --------------------------------------------------------------------------
# 子彈、道具、爆炸
# --------------------------------------------------------------------------
def make_player_bullet() -> pygame.Surface:
    ss = 4
    w, h = 7, 18
    s = _surf(w * ss, h * ss)
    pygame.draw.ellipse(s, (255, 190, 70), pygame.Rect(0, 0, w * ss, h * ss))
    pygame.draw.ellipse(s, YELLOW, pygame.Rect(ss, ss * 2, (w - 2) * ss, (h - 4) * ss))
    pygame.draw.ellipse(s, (255, 255, 225),
                        pygame.Rect(ss * 2, ss * 3, (w - 4) * ss, (h - 10) * ss))
    return _down(s, w, h)


def make_laser_bullet(width: int = 10, height: int = 40) -> pygame.Surface:
    """穿透雷射光束：外圈輝光、中央亮白。"""
    ss = 3
    W, H = width * ss, height * ss
    s = _surf(W, H)
    pygame.draw.rect(s, (70, 200, 255, 90), pygame.Rect(0, 0, W, H),
                     border_radius=W // 2)
    inner = max(2, W - 3 * ss)
    pygame.draw.rect(s, (140, 235, 255, 210),
                     pygame.Rect((W - inner) // 2, ss, inner, H - 2 * ss),
                     border_radius=inner // 2)
    core = max(1, W - 6 * ss)
    pygame.draw.rect(s, (255, 255, 255, 255),
                     pygame.Rect((W - core) // 2, 2 * ss, core, H - 4 * ss),
                     border_radius=max(1, core // 2))
    return _down(s, width, height)


def make_enemy_bullet() -> pygame.Surface:
    ss, d = 4, 12
    s = _surf(d * ss, d * ss)
    c = d * ss / 2
    pygame.draw.circle(s, (255, 220, 120, 60), (c, c), c)
    pygame.draw.circle(s, (26, 14, 6), (c, c), c * 0.88)          # 暗色外框提高辨識度
    pygame.draw.circle(s, (255, 238, 170), (c, c), c * 0.72)
    pygame.draw.circle(s, ORANGE, (c, c), c * 0.50)
    pygame.draw.circle(s, DEEP_RED, (c, c), c * 0.24)
    pygame.draw.circle(s, (255, 255, 226), (c - c * 0.22, c - c * 0.24), c * 0.15)
    return _down(s, d, d)


def make_boss_bullet() -> pygame.Surface:
    ss, d = 4, 16
    s = _surf(d * ss, d * ss)
    c = d * ss / 2
    pygame.draw.circle(s, (255, 150, 200, 60), (c, c), c)
    pygame.draw.circle(s, (32, 8, 20), (c, c), c * 0.88)
    pygame.draw.circle(s, (255, 206, 226), (c, c), c * 0.72)
    pygame.draw.circle(s, (232, 92, 150), (c, c), c * 0.48)
    pygame.draw.circle(s, WHITE, (c - c * 0.18, c - c * 0.20), c * 0.18)
    return _down(s, d, d)


_POWERUP_STYLE = {
    "power": ("P", RED, WHITE),
    "wing": ("W", BLUE, WHITE),
    "bomb": ("B", (60, 62, 74), YELLOW),
    "roll": ("R", GREEN, WHITE),
    "life": ("1UP", PURPLE, WHITE),
    "laser": ("Z", (18, 122, 158), CYAN),
    "vulcan": ("V", (168, 96, 16), YELLOW),
}


def make_powerup(kind: str, font: pygame.font.Font) -> pygame.Surface:
    label, bg, fg = _POWERUP_STYLE[kind]
    w, h = 30, 24
    ss = 3
    s = _surf(w * ss, h * ss)
    pygame.draw.rect(s, (20, 22, 30), pygame.Rect(0, 0, w * ss, h * ss),
                     border_radius=5 * ss)
    pygame.draw.rect(s, WHITE, pygame.Rect(ss, ss, (w - 2) * ss, (h - 2) * ss),
                     border_radius=4 * ss)
    pygame.draw.rect(s, _shade(bg, 1.25),
                     pygame.Rect(3 * ss, 3 * ss, (w - 6) * ss, (h - 6) * ss),
                     border_radius=3 * ss)
    pygame.draw.rect(s, bg, pygame.Rect(3 * ss, int(5.5 * ss),
                                        (w - 6) * ss, int((h - 8.5) * ss)),
                     border_radius=3 * ss)
    out = _down(s, w, h)
    txt = font.render(label, True, fg)
    shadow = font.render(label, True, (0, 0, 0))
    r = txt.get_rect(center=(w // 2, h // 2))
    out.blit(shadow, r.move(1, 1))
    out.blit(txt, r)
    return out


def make_explosion_frames(size: int, count: int = 9) -> list[pygame.Surface]:
    """火球 + 衝擊波環 + 煙塵 + 碎片的多層爆炸動畫。"""
    frames: list[pygame.Surface] = []
    rnd = random.Random(size * 7 + 13)
    ss = 2
    S_ = size * ss
    sparks = [(rnd.uniform(0, math.tau), rnd.uniform(0.45, 1.05),
               rnd.uniform(0.6, 1.4)) for _ in range(14)]
    smoke = [(rnd.uniform(0, math.tau), rnd.uniform(0.20, 0.72),
              rnd.uniform(0.16, 0.34)) for _ in range(9)]
    for i in range(count):
        t = i / (count - 1)
        s = _surf(S_, S_)
        c = S_ / 2
        radius = c * (0.20 + 0.80 * t)
        fade = (1.0 - t) ** 0.75

        # 衝擊波環
        if t < 0.55:
            ring = c * (0.30 + 1.35 * t)
            a = int(150 * (1 - t / 0.55))
            pygame.draw.circle(s, (255, 240, 210, a), (c, c), ring,
                               max(1, int(S_ * 0.018)))

        # 煙塵
        for ang, dist, rr in smoke:
            d = radius * (0.55 + dist * (0.4 + t))
            x, y = c + math.cos(ang) * d, c + math.sin(ang) * d
            a = int(120 * fade)
            pygame.draw.circle(s, (72, 62, 58, a), (x, y), radius * rr)

        # 火球（外焰 -> 內焰 -> 核心）
        pygame.draw.circle(s, (150, 60, 24, int(190 * fade)), (c, c), radius)
        pygame.draw.circle(s, (255, 150, 48, int(225 * fade)), (c, c), radius * 0.76)
        pygame.draw.circle(s, (255, 214, 120, int(240 * fade)), (c, c), radius * 0.48)
        pygame.draw.circle(s, (255, 252, 226, int(250 * fade)), (c, c), radius * 0.22)

        # 噴散碎片
        for ang, dist, spd in sparks:
            d = radius * dist * (0.7 + spd * t)
            x, y = c + math.cos(ang) * d, c + math.sin(ang) * d
            rr = max(1.0, S_ * 0.020 * (1 - t) * spd)
            pygame.draw.circle(s, (255, 206, 120, int(235 * fade)), (x, y), rr)
        frames.append(_down(s, size, size))
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
        size = base_player.get_width()
        # 螺旋槳動畫 + 左右傾斜（含投影陰影）
        self.player_frames: dict[int, list[pygame.Surface]] = {}
        for bank in (-2, -1, 0, 1, 2):
            scale = 1.0 - abs(bank) * 0.16
            frames = []
            for f in range(4):
                img = base_player.copy()
                img.blit(_prop_disc(size, size, f), (0, 0))
                img = _with_outline(_with_shadow(img, 2.0, 3.0), 3)
                if scale != 1.0:
                    w = max(6, int(img.get_width() * scale))
                    img = pygame.transform.smoothscale(img, (w, img.get_height()))
                frames.append(img)
            self.player_frames[bank] = frames

        # 翻滾（roll）動畫：機身橫向壓縮 + 亮邊
        self.player_roll: list[pygame.Surface] = []
        for i in range(12):
            t = i / 11
            scale = abs(math.cos(t * math.pi * 2)) * 0.9 + 0.10
            img = pygame.transform.smoothscale(
                base_player, (max(5, int(size * scale)), size))
            glow = img.copy()
            glow.fill((120, 190, 255, 70), special_flags=pygame.BLEND_RGBA_ADD)
            self.player_roll.append(_with_outline(glow, 3))

        self.wingman = make_wingman()

        self.enemies: dict[str, pygame.Surface] = {
            "scout": _enemy_variant("scout", 34),
            "red": _enemy_variant("red", 34),
            "green": _enemy_variant("green", 38),
            "bomber": _enemy_variant("bomber", 54),
            "heavy": _enemy_variant("heavy", 72),
            "jet": _enemy_variant("jet", 32),
        }
        self.bosses: dict[int, pygame.Surface] = {i: make_boss(i) for i in range(1, 8)}
        # 受擊閃白版本（預先產生，避免遊戲中重複配置 Surface）
        self.enemies_hit = {k: _flashed(v, (90, 90, 90)) for k, v in self.enemies.items()}
        self.bosses_hit = {k: _flashed(v, (55, 22, 22)) for k, v in self.bosses.items()}

        self.player_bullet = make_player_bullet()
        self.laser_bullet = make_laser_bullet(10, 40)
        self.laser_bullet_wide = make_laser_bullet(14, 52)
        self.laser_bullet_small = make_laser_bullet(6, 30)
        self.enemy_bullet = make_enemy_bullet()
        self.boss_bullet = make_boss_bullet()
        self.powerups = {k: make_powerup(k, self.font_tiny) for k in _POWERUP_STYLE}

        self.explosions: dict[str, list[pygame.Surface]] = {
            "small": make_explosion_frames(40),
            "big": make_explosion_frames(96),
            "huge": make_explosion_frames(190, 12),
        }
