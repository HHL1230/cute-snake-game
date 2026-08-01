"""程式產生的捲動背景（每關不同主題）。

所有地形都先以 2 倍解析度繪製再縮小，讓海岸線、船艦與建築邊緣平滑；
並統一使用「左上方光源」的陰影規則，讓地物看起來有高度。
"""

from __future__ import annotations

import math
import random

import pygame

from .settings import PLAY_W, SCREEN_H


TILE_H = SCREEN_H
SS = 2  # 背景超取樣倍率


def _shade(color, f: float):
    return tuple(max(0, min(255, int(c * f))) for c in color[:3])


def _mix(c1, c2, t: float):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


class Background:
    """垂直無縫捲動背景 + 視差雲層。"""

    def __init__(self, theme: str, speed: float = 70.0, seed: int = 0) -> None:
        self.theme = theme
        self.speed = speed
        self.offset = 0.0
        self.rnd = random.Random(seed or hash(theme) & 0xFFFF)
        self.W = PLAY_W * SS
        self.H = TILE_H * SS
        self.tile = self._build_tile()
        self.clouds = self._build_clouds()
        self.cloud_offset = 0.0

    # ------------------------------------------------------------------
    def _build_tile(self) -> pygame.Surface:
        s = pygame.Surface((self.W, self.H))
        theme = self.theme
        if theme == "ocean":
            self._ocean(s, (12, 44, 92), (34, 96, 156), islands=3, ships=2)
        elif theme == "islands":
            self._ocean(s, (14, 56, 106), (44, 118, 172), islands=7, ships=3)
        elif theme == "night":
            self._ocean(s, (7, 13, 34), (18, 34, 72), islands=2, ships=3, night=True)
        elif theme == "desert":
            self._desert(s)
        elif theme == "volcano":
            self._volcano(s)
        elif theme == "fleet":
            self._fleet(s)
        else:  # fortress
            self._fortress(s)
        self._vignette(s)
        return pygame.transform.smoothscale(s, (PLAY_W, TILE_H))

    def _vignette(self, s: pygame.Surface) -> None:
        """左右邊緣輕微壓暗，增加景深。"""
        w, h = s.get_size()
        band = int(w * 0.16)
        veil = pygame.Surface((band, h), pygame.SRCALPHA)
        for x in range(band):
            a = int(58 * (1 - x / band) ** 1.6)
            pygame.draw.line(veil, (0, 0, 0, a), (x, 0), (x, h))
        s.blit(veil, (0, 0))
        s.blit(pygame.transform.flip(veil, True, False), (w - band, 0))

    # -- 海洋 ----------------------------------------------------------
    def _ocean(self, s: pygame.Surface, deep, shallow, *, islands: int,
               ships: int, night: bool = False) -> None:
        w, h = self.W, self.H
        rnd = self.rnd
        # 深淺漸層帶（以 y 週期函數保證上下接縫連續）
        for y in range(h):
            t = math.sin(y / h * math.tau * 2) * 0.5 + 0.5
            pygame.draw.line(s, _mix(deep, _shade(shallow, 0.72), t * 0.55), (0, y), (w, y))

        # 水面折射光斑
        caustic = pygame.Surface((w, h), pygame.SRCALPHA)
        crest = _mix(shallow, (255, 255, 255), 0.55 if not night else 0.18)
        for _ in range(520):
            y = rnd.uniform(0, h)
            x = rnd.uniform(0, w)
            length = rnd.uniform(16, 62)
            phase = math.sin(y / h * math.tau * 3) * 0.5 + 0.5
            a = int((22 + phase * 58) * (0.4 if night else 1.0))
            pygame.draw.line(caustic, (*crest, a), (x, y),
                             (x + length, y + rnd.uniform(-2, 2)), rnd.randint(2, 4))
        # 長浪紋
        for k in range(26):
            base = k / 26 * h
            pts = [(x, base + math.sin(x / w * math.tau * 3 + k) * 7 * SS)
                   for x in range(0, w + 1, 12)]
            a = 26 if not night else 12
            pygame.draw.lines(caustic, (*crest, a), False, pts, 2)
        s.blit(caustic, (0, 0))

        if night:
            for _ in range(90):
                x, y = rnd.uniform(0, w), rnd.uniform(0, h)
                pygame.draw.circle(s, (180, 195, 235), (x, y), rnd.uniform(0.8, 2.0) * SS)

        for _ in range(islands):
            self._island(s, rnd.uniform(70, w - 70), rnd.uniform(150, h - 150),
                         rnd.uniform(34, 80) * SS, night)
        for _ in range(ships):
            self._ship(s, rnd.uniform(50, w - 50), rnd.uniform(120, h - 120),
                       night, scale=1.0)

    def _island(self, s: pygame.Surface, cx: float, cy: float, r: float,
                night: bool) -> None:
        rnd = self.rnd
        shoal = (72, 158, 176) if not night else (26, 48, 72)
        foam = (232, 244, 248) if not night else (110, 130, 160)
        sand = (206, 184, 132) if not night else (76, 72, 62)
        grass = (86, 132, 72) if not night else (34, 50, 38)
        grass_hi = (112, 158, 88) if not night else (44, 62, 46)
        rock = (128, 122, 110) if not night else (52, 54, 60)

        n = 18
        offs = [rnd.uniform(0.74, 1.16) for _ in range(n)]

        def ring(k: float, squash: float = 0.82):
            return [(cx + math.cos(i / n * math.tau) * r * offs[i] * k,
                     cy + math.sin(i / n * math.tau) * r * offs[i] * k * squash)
                    for i in range(n)]

        pygame.draw.polygon(s, shoal, ring(1.34))       # 淺灘
        pygame.draw.polygon(s, foam, ring(1.12))        # 白浪
        pygame.draw.polygon(s, sand, ring(1.04))        # 沙灘
        pygame.draw.polygon(s, _shade(grass, 0.72), ring(0.86))
        pygame.draw.polygon(s, grass, [(x - r * 0.035, y - r * 0.045)
                                       for x, y in ring(0.84)])
        # 林地質感
        for _ in range(int(r * 0.9)):
            a = rnd.uniform(0, math.tau)
            d = rnd.uniform(0, 0.74)
            x = cx + math.cos(a) * r * d
            y = cy + math.sin(a) * r * d * 0.82
            pygame.draw.circle(s, grass_hi if rnd.random() < 0.5 else _shade(grass, 0.8),
                               (x, y), rnd.uniform(1.2, 3.0) * SS)
        # 山脊（左上受光）
        pygame.draw.circle(s, _shade(rock, 0.72), (cx + r * 0.05, cy + r * 0.06), r * 0.30)
        pygame.draw.circle(s, rock, (cx, cy), r * 0.27)
        pygame.draw.circle(s, _shade(rock, 1.25), (cx - r * 0.07, cy - r * 0.08), r * 0.16)

    def _ship(self, s: pygame.Surface, cx: float, cy: float, night: bool,
              scale: float = 1.0, carrier: bool = False) -> None:
        hull = (86, 94, 104) if not night else (40, 46, 58)
        deck = (120, 128, 140) if not night else (56, 62, 76)
        light = (168, 176, 188) if not night else (74, 82, 98)
        wake = (218, 234, 246) if not night else (110, 132, 164)

        w = (44 if carrier else 22) * SS * scale
        h = (150 if carrier else 62) * SS * scale

        # 尾浪
        wk = pygame.Surface((int(w * 3.4), int(h * 1.1)), pygame.SRCALPHA)
        for i in range(10):
            t = i / 9
            a = int(72 * (1 - t))
            spread = w * (0.5 + t * 1.6)
            yy = h * 0.02 + t * h * 0.95
            pygame.draw.line(wk, (*wake, a), (w * 1.7 - spread, yy),
                             (w * 1.7 + spread, yy), 3)
        s.blit(wk, (cx - w * 1.7, cy + h * 0.42))

        # 艦體陰影
        sh = pygame.Surface((int(w * 1.4), int(h * 1.2)), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
        s.blit(sh, (cx - w * 0.62, cy - h * 0.5 + 4 * SS))

        # 艦體（艦首尖）
        pts = [(cx, cy - h * 0.5), (cx + w * 0.5, cy - h * 0.22),
               (cx + w * 0.46, cy + h * 0.42), (cx + w * 0.30, cy + h * 0.5),
               (cx - w * 0.30, cy + h * 0.5), (cx - w * 0.46, cy + h * 0.42),
               (cx - w * 0.5, cy - h * 0.22)]
        pygame.draw.polygon(s, hull, pts)
        pygame.draw.polygon(s, deck, [(cx + (x - cx) * 0.80, y) for x, y in pts])

        if carrier:
            pygame.draw.rect(s, _shade(deck, 0.86),
                             pygame.Rect(cx - w * 0.34, cy - h * 0.40, w * 0.68, h * 0.86))
            for k in range(9):  # 跑道中線
                pygame.draw.rect(s, (235, 232, 216),
                                 pygame.Rect(cx - 1.5 * SS, cy - h * 0.36 + k * h * 0.09,
                                             3 * SS, h * 0.045))
            pygame.draw.rect(s, light,  # 艦島
                             pygame.Rect(cx + w * 0.16, cy - h * 0.12, w * 0.20, h * 0.22))
            pygame.draw.rect(s, _shade(light, 0.6),
                             pygame.Rect(cx + w * 0.16, cy - h * 0.12, w * 0.20, h * 0.22), SS)
        else:
            pygame.draw.rect(s, light, pygame.Rect(cx - w * 0.22, cy - h * 0.16,
                                                   w * 0.44, h * 0.30), border_radius=SS * 2)
            pygame.draw.rect(s, _shade(light, 0.62),
                             pygame.Rect(cx - w * 0.22, cy - h * 0.16,
                                         w * 0.44, h * 0.30), SS, border_radius=SS * 2)
            for ty in (-0.34, 0.30):  # 砲塔
                pygame.draw.circle(s, _shade(hull, 0.75), (cx, cy + h * ty), w * 0.17)
                pygame.draw.rect(s, _shade(hull, 0.55),
                                 pygame.Rect(cx - w * 0.03, cy + h * ty - w * 0.55,
                                             w * 0.06, w * 0.45))
            pygame.draw.line(s, (210, 214, 224), (cx, cy - h * 0.30),
                             (cx, cy + h * 0.30), SS)

    # -- 沙漠 ----------------------------------------------------------
    def _desert(self, s: pygame.Surface) -> None:
        w, h = self.W, self.H
        rnd = self.rnd
        base = (198, 162, 104)
        for y in range(h):
            t = math.sin(y / h * math.tau * 3) * 0.5 + 0.5
            pygame.draw.line(s, _mix(_shade(base, 0.86), _shade(base, 1.08), t),
                             (0, y), (w, y))
        # 沙丘（脊線亮、背風面暗）
        for _ in range(90):
            y = rnd.uniform(0, h)
            x = rnd.uniform(-60, w)
            dw = rnd.uniform(80, 260) * SS / 2
            dh = rnd.uniform(16, 42) * SS / 2
            pygame.draw.ellipse(s, _shade(base, 0.74),
                                pygame.Rect(x, y + dh * 0.35, dw, dh))
            pygame.draw.ellipse(s, _shade(base, 1.10), pygame.Rect(x, y, dw, dh))
            pygame.draw.ellipse(s, _shade(base, 1.22),
                                pygame.Rect(x + dw * 0.1, y, dw * 0.7, dh * 0.5))
        # 風紋
        for _ in range(260):
            y = rnd.uniform(0, h)
            x = rnd.uniform(0, w)
            pygame.draw.arc(s, _shade(base, 0.90),
                            pygame.Rect(x, y, rnd.uniform(30, 90), 14 * SS),
                            0.2, math.pi - 0.2, SS)
        # 岩石（左上受光 + 右下投影）
        for _ in range(16):
            x, y = rnd.uniform(30, w - 30), rnd.uniform(30, h - 30)
            r = rnd.uniform(9, 26) * SS
            pygame.draw.circle(s, (128, 100, 66), (x + r * 0.22, y + r * 0.26), r)
            pygame.draw.circle(s, (150, 122, 82), (x, y), r * 0.92)
            pygame.draw.circle(s, (182, 154, 108), (x - r * 0.24, y - r * 0.26), r * 0.52)
        # 機場：跑道 + 掩體 + 油槽
        for _ in range(4):
            x = rnd.uniform(90, w - 90)
            y = rnd.uniform(90, h - 340)
            rw, rh = 36 * SS, 280 * SS / 2
            pygame.draw.rect(s, (122, 116, 106), pygame.Rect(x - rw / 2, y, rw, rh))
            pygame.draw.rect(s, (96, 92, 84), pygame.Rect(x - rw / 2, y, rw, rh), SS)
            for k in range(int(rh // (22 * SS))):
                pygame.draw.rect(s, (232, 228, 212),
                                 pygame.Rect(x - 2 * SS, y + 12 * SS + k * 22 * SS,
                                             4 * SS, 10 * SS))
            for side in (-1, 1):
                for k in range(3):
                    bx = x + side * rw * 0.95
                    by = y + 30 * SS + k * 60 * SS
                    pygame.draw.rect(s, (100, 104, 92),
                                     pygame.Rect(bx - 11 * SS, by, 22 * SS, 14 * SS),
                                     border_radius=4 * SS)
                    pygame.draw.rect(s, (128, 132, 116),
                                     pygame.Rect(bx - 11 * SS, by, 22 * SS, 7 * SS),
                                     border_radius=3 * SS)

    # -- 火山 ----------------------------------------------------------
    def _volcano(self, s: pygame.Surface) -> None:
        w, h = self.W, self.H
        rnd = self.rnd
        rock = (52, 44, 46)
        for y in range(h):
            t = math.sin(y / h * math.tau * 2 + 1.1) * 0.5 + 0.5
            pygame.draw.line(s, _mix(_shade(rock, 0.72), _shade(rock, 1.22), t),
                             (0, y), (w, y))
        # 玄武岩塊
        for _ in range(420):
            x, y = rnd.uniform(0, w), rnd.uniform(0, h)
            r = rnd.uniform(6, 26) * SS / 2
            c = rnd.randint(-12, 16)
            pygame.draw.polygon(s, (max(0, 58 + c), max(0, 50 + c), max(0, 52 + c)),
                                [(x + math.cos(a) * r * rnd.uniform(0.7, 1.2),
                                  y + math.sin(a) * r * rnd.uniform(0.7, 1.2))
                                 for a in (0.4, 1.6, 2.7, 3.9, 5.2)])
        # 熔岩河（沿 y 貫穿，保證接縫連續）
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        for k in range(3):
            bx = w * (0.20 + 0.30 * k) + rnd.uniform(-30, 30)
            width = rnd.uniform(8, 13) * SS
            amp = 18 * SS
            freq = 2 + k

            def band(half: float, _bx=bx, _amp=amp, _freq=freq):
                left = [(_bx + math.sin(y / h * math.tau * _freq + k) * _amp - half, y)
                        for y in range(0, h + 1, 10)]
                right = [(_bx + math.sin(y / h * math.tau * _freq + k) * _amp + half, y)
                         for y in range(h, -1, -10)]
                return left + right

            pygame.draw.polygon(glow, (255, 88, 18, 26), band(width * 1.15))
            pygame.draw.polygon(s, (146, 40, 10), band(width * 0.5))
            pygame.draw.polygon(s, (226, 104, 20), band(width * 0.30))
            pygame.draw.polygon(s, (255, 206, 110), band(width * 0.11))
        s.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        # 裂縫
        for _ in range(70):
            x, y = rnd.uniform(0, w), rnd.uniform(0, h)
            pts = [(x, y)]
            for _ in range(4):
                x += rnd.uniform(-16, 16) * SS
                y += rnd.uniform(4, 18) * SS
                pts.append((x, y))
            pygame.draw.lines(s, (196, 78, 22), False, pts, SS)
        # 火山口
        for _ in range(4):
            x, y = rnd.uniform(70, w - 70), rnd.uniform(120, h - 120)
            r = rnd.uniform(34, 62) * SS
            pygame.draw.circle(s, (36, 30, 32), (x + r * 0.12, y + r * 0.14), r)
            pygame.draw.circle(s, (74, 62, 62), (x, y), r * 0.94)
            pygame.draw.circle(s, (96, 82, 80), (x - r * 0.16, y - r * 0.18), r * 0.62)
            pygame.draw.circle(s, (198, 60, 14), (x, y), r * 0.44)
            pygame.draw.circle(s, (255, 148, 32), (x, y), r * 0.28)
            pygame.draw.circle(s, (255, 240, 170), (x, y), r * 0.13)

    # -- 敵艦隊 --------------------------------------------------------
    def _fleet(self, s: pygame.Surface) -> None:
        w, h = self.W, self.H
        rnd = self.rnd
        self._ocean(s, (10, 30, 66), (26, 78, 128), islands=0, ships=0)
        # 主力艦隊：航艦 + 護衛
        for cy in (h * 0.20, h * 0.62):
            self._ship(s, w * rnd.uniform(0.34, 0.62), cy, False, scale=1.0, carrier=True)
        for _ in range(6):
            self._ship(s, rnd.uniform(50, w - 50), rnd.uniform(90, h - 90),
                       False, scale=rnd.uniform(0.75, 1.05))
        # 浮油與探照燈光斑
        for _ in range(10):
            x, y = rnd.uniform(0, w), rnd.uniform(0, h)
            r = rnd.uniform(20, 60) * SS
            spot = pygame.Surface((int(r * 2), int(r * 2)), pygame.SRCALPHA)
            pygame.draw.circle(spot, (140, 190, 220, 26), (r, r), r)
            s.blit(spot, (x - r, y - r))

    # -- 要塞 ----------------------------------------------------------
    def _fortress(self, s: pygame.Surface) -> None:
        w, h = self.W, self.H
        rnd = self.rnd
        s.fill((56, 60, 70))
        # 混凝土板塊
        for _ in range(520):
            x, y = rnd.uniform(0, w), rnd.uniform(0, h)
            c = rnd.randint(50, 78)
            pygame.draw.rect(s, (c, c + 4, c + 12),
                             pygame.Rect(x, y, rnd.uniform(10, 46), rnd.uniform(10, 46)))
        # 主幹道
        for k in range(3):
            x = w * (0.18 + 0.32 * k) + rnd.uniform(-20, 20)
            pygame.draw.rect(s, (44, 46, 54), pygame.Rect(x - 16 * SS, 0, 32 * SS, h))
            for yy in range(0, h, 26 * SS):
                pygame.draw.rect(s, (150, 146, 128),
                                 pygame.Rect(x - 1.5 * SS, yy, 3 * SS, 12 * SS))
        # 建築物（含右下投影與屋頂細節）
        for _ in range(30):
            bw = rnd.uniform(24, 62) * SS
            bh = rnd.uniform(24, 82) * SS
            x = rnd.uniform(4, w - bw - 4)
            y = rnd.uniform(4, h - bh - 4)
            base = rnd.randint(74, 106)
            pygame.draw.rect(s, (24, 26, 32),
                             pygame.Rect(x + 5 * SS, y + 6 * SS, bw, bh))
            pygame.draw.rect(s, (base, base + 6, base + 16), pygame.Rect(x, y, bw, bh))
            pygame.draw.rect(s, (base + 22, base + 28, base + 38),
                             pygame.Rect(x, y, bw, bh * 0.18))
            pygame.draw.rect(s, (base - 28, base - 22, base - 10),
                             pygame.Rect(x, y, bw, bh), SS)
            for gx in range(int(x + 6 * SS), int(x + bw - 6 * SS), 11 * SS):
                for gy in range(int(y + 8 * SS), int(y + bh - 6 * SS), 14 * SS):
                    if rnd.random() < 0.75:
                        pygame.draw.rect(s, (226, 206, 136),
                                         pygame.Rect(gx, gy, 3 * SS, 5 * SS))
        # 儲油槽
        for _ in range(8):
            x, y = rnd.uniform(40, w - 40), rnd.uniform(40, h - 40)
            r = rnd.uniform(14, 24) * SS
            pygame.draw.circle(s, (22, 24, 30), (x + r * 0.22, y + r * 0.26), r)
            pygame.draw.circle(s, (96, 100, 112), (x, y), r)
            pygame.draw.circle(s, (128, 134, 148), (x - r * 0.2, y - r * 0.22), r * 0.6)
            pygame.draw.circle(s, (60, 64, 76), (x, y), r, SS)
        # 高射砲台
        for _ in range(9):
            x, y = rnd.uniform(30, w - 30), rnd.uniform(30, h - 30)
            r = 13 * SS
            pygame.draw.circle(s, (20, 22, 28), (x + 3 * SS, y + 4 * SS), r)
            pygame.draw.circle(s, (46, 50, 60), (x, y), r)
            pygame.draw.circle(s, (86, 90, 102), (x, y), r * 0.66)
            pygame.draw.circle(s, (168, 48, 44), (x, y), r * 0.34)
            pygame.draw.rect(s, (34, 36, 44),
                             pygame.Rect(x - 1.5 * SS, y - r * 1.6, 3 * SS, r * 1.1))

    # ------------------------------------------------------------------
    def _build_clouds(self):
        rnd = self.rnd
        clouds = []
        count = {"ocean": 5, "islands": 5, "fleet": 6}.get(self.theme, 4)
        night = self.theme == "night"
        for _ in range(count):
            w = rnd.uniform(90, 210)
            h = w * rnd.uniform(0.36, 0.52)
            big = pygame.Surface((int(w * 2), int(h * 2)), pygame.SRCALPHA)
            if night:
                body, edge, alpha = (26, 30, 52), (44, 50, 78), 78
            elif self.theme == "volcano":
                body, edge, alpha = (86, 74, 78), (150, 128, 122), 96
            else:
                body, edge, alpha = (226, 230, 244), (255, 255, 255), 104
            blobs = [(rnd.uniform(w * 0.30, w * 1.70), rnd.uniform(h * 0.62, h * 1.38),
                      rnd.uniform(h * 0.42, h * 0.86)) for _ in range(11)]
            for cx, cy, r in blobs:  # 底部陰影
                pygame.draw.circle(big, (*_shade(body, 0.74), 255),
                                   (cx, cy + r * 0.20), r)
            for cx, cy, r in blobs:  # 主體
                pygame.draw.circle(big, (*body, 255), (cx, cy), r)
            for cx, cy, r in blobs:  # 頂部受光
                pygame.draw.circle(big, (*edge, 255), (cx - r * 0.12, cy - r * 0.24),
                                   r * 0.62)
            big.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            surf = pygame.transform.smoothscale(big, (int(w), int(h)))
            shadow = surf.copy()
            shadow.fill((0, 0, 0, 55), special_flags=pygame.BLEND_RGBA_MULT)
            clouds.append((surf, shadow, rnd.uniform(-40, PLAY_W - 40),
                           rnd.uniform(0, TILE_H), rnd.uniform(1.5, 2.6)))
        return clouds

    # ------------------------------------------------------------------
    def update(self, dt: float, speed_scale: float = 1.0) -> None:
        self.offset = (self.offset + self.speed * speed_scale * dt) % TILE_H
        self.cloud_offset = (self.cloud_offset + self.speed * speed_scale * dt) % TILE_H

    def draw(self, surface: pygame.Surface) -> None:
        y = self.offset
        surface.blit(self.tile, (0, y - TILE_H))
        surface.blit(self.tile, (0, y))
        if y < 0:
            surface.blit(self.tile, (0, y + TILE_H))

    def draw_clouds(self, surface: pygame.Surface) -> None:
        for surf, shadow, x, base_y, par in self.clouds:
            y = (base_y + self.cloud_offset * par) % (TILE_H + surf.get_height())
            surface.blit(shadow, (x - 14, y - surf.get_height() + 20))
            surface.blit(surf, (x, y - surf.get_height()))
