"""程式產生的捲動背景（每關不同主題）。"""

from __future__ import annotations

import math
import random

import pygame

from .settings import PLAY_W, SCREEN_H


TILE_H = SCREEN_H


class Background:
    """垂直無縫捲動背景 + 視差雲層。"""

    def __init__(self, theme: str, speed: float = 70.0, seed: int = 0) -> None:
        self.theme = theme
        self.speed = speed
        self.offset = 0.0
        self.rnd = random.Random(seed or hash(theme) & 0xFFFF)
        self.tile = self._build_tile()
        self.clouds = self._build_clouds()
        self.cloud_offset = 0.0

    # ------------------------------------------------------------------
    def _build_tile(self) -> pygame.Surface:
        s = pygame.Surface((PLAY_W, TILE_H))
        theme = self.theme
        if theme == "ocean":
            self._ocean(s, (14, 46, 96), (24, 74, 140), islands=3, ships=2)
        elif theme == "islands":
            self._ocean(s, (16, 58, 108), (30, 92, 156), islands=7, ships=3)
        elif theme == "night":
            self._ocean(s, (8, 14, 38), (16, 26, 62), islands=2, ships=3, night=True)
        elif theme == "desert":
            self._desert(s)
        else:  # fortress
            self._fortress(s)
        return s

    # -- 海洋 ----------------------------------------------------------
    def _ocean(self, s: pygame.Surface, deep, shallow, *, islands: int,
               ships: int, night: bool = False) -> None:
        s.fill(deep)
        rnd = self.rnd
        # 水波（以 y 週期函數保證上下接縫連續）
        wave_color = tuple(min(255, c + (18 if night else 40)) for c in shallow)
        for i in range(150):
            y = rnd.uniform(0, TILE_H)
            x = rnd.uniform(0, PLAY_W)
            length = rnd.uniform(10, 34)
            shade = math.sin(y / TILE_H * math.tau * 3) * 0.5 + 0.5
            col = tuple(int(deep[k] + (wave_color[k] - deep[k]) * (0.35 + shade * 0.65))
                        for k in range(3))
            pygame.draw.line(s, col, (x, y), (x + length, y), 2)

        if night:
            for _ in range(60):
                x, y = rnd.uniform(0, PLAY_W), rnd.uniform(0, TILE_H)
                pygame.draw.circle(s, (200, 210, 240), (x, y), 1)

        for _ in range(islands):
            self._island(s, rnd.uniform(40, PLAY_W - 40), rnd.uniform(80, TILE_H - 80),
                         rnd.uniform(34, 78), night)
        for _ in range(ships):
            self._ship(s, rnd.uniform(30, PLAY_W - 30), rnd.uniform(60, TILE_H - 60), night)

    def _island(self, s: pygame.Surface, cx: float, cy: float, r: float, night: bool) -> None:
        rnd = self.rnd
        sand = (196, 172, 118) if not night else (72, 68, 60)
        grass = (78, 128, 72) if not night else (32, 48, 38)
        rock = (120, 116, 106) if not night else (48, 50, 56)
        pts = []
        n = 12
        for i in range(n):
            a = i / n * math.tau
            rr = r * rnd.uniform(0.72, 1.15)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.8))
        pygame.draw.polygon(s, sand, pts)
        inner = [(cx + (x - cx) * 0.74, cy + (y - cy) * 0.74) for x, y in pts]
        pygame.draw.polygon(s, grass, inner)
        pygame.draw.circle(s, rock, (int(cx), int(cy)), int(r * 0.28))

    def _ship(self, s: pygame.Surface, cx: float, cy: float, night: bool) -> None:
        hull = (96, 102, 112) if not night else (44, 48, 60)
        deck = (128, 134, 146) if not night else (60, 64, 78)
        w, h = 20, 54
        rect = pygame.Rect(cx - w / 2, cy - h / 2, w, h)
        pygame.draw.ellipse(s, hull, rect)
        pygame.draw.rect(s, deck, pygame.Rect(cx - w * 0.28, cy - h * 0.16,
                                              w * 0.56, h * 0.34), border_radius=2)
        pygame.draw.line(s, (200, 200, 210), (cx, cy - h * 0.3), (cx, cy + h * 0.3), 1)
        # 尾浪
        pygame.draw.ellipse(s, (210, 226, 240, 90) if not night else (120, 140, 170),
                            pygame.Rect(cx - w * 0.6, cy + h * 0.42, w * 1.2, h * 0.20), 1)

    # -- 沙漠 ----------------------------------------------------------
    def _desert(self, s: pygame.Surface) -> None:
        rnd = self.rnd
        s.fill((196, 158, 96))
        for i in range(220):
            y = rnd.uniform(0, TILE_H)
            x = rnd.uniform(0, PLAY_W)
            shade = math.sin(y / TILE_H * math.tau * 4 + x * 0.01) * 0.5 + 0.5
            col = (int(180 + shade * 40), int(146 + shade * 34), int(88 + shade * 26))
            pygame.draw.ellipse(s, col, pygame.Rect(x, y, rnd.uniform(50, 140), rnd.uniform(8, 20)))
        for _ in range(9):  # 岩石
            x, y = rnd.uniform(20, PLAY_W - 20), rnd.uniform(20, TILE_H - 20)
            r = rnd.uniform(10, 26)
            pygame.draw.circle(s, (140, 112, 76), (x, y), r)
            pygame.draw.circle(s, (166, 136, 96), (x - r * 0.2, y - r * 0.2), r * 0.7)
        for _ in range(4):  # 跑道
            x = rnd.uniform(60, PLAY_W - 60)
            y = rnd.uniform(60, TILE_H - 160)
            pygame.draw.rect(s, (120, 114, 104), pygame.Rect(x - 16, y, 32, 130))
            for k in range(6):
                pygame.draw.rect(s, (230, 226, 210), pygame.Rect(x - 2, y + 10 + k * 20, 4, 10))

    # -- 要塞 ----------------------------------------------------------
    def _fortress(self, s: pygame.Surface) -> None:
        rnd = self.rnd
        s.fill((58, 62, 72))
        for _ in range(300):
            x, y = rnd.uniform(0, PLAY_W), rnd.uniform(0, TILE_H)
            c = rnd.randint(52, 78)
            pygame.draw.rect(s, (c, c + 4, c + 12), pygame.Rect(x, y, rnd.uniform(6, 26), rnd.uniform(6, 26)))
        for _ in range(22):  # 建築物
            w = rnd.uniform(24, 60)
            h = rnd.uniform(24, 80)
            x = rnd.uniform(4, PLAY_W - w - 4)
            y = rnd.uniform(4, TILE_H - h - 4)
            base = rnd.randint(74, 104)
            pygame.draw.rect(s, (base, base + 6, base + 16), pygame.Rect(x, y, w, h))
            pygame.draw.rect(s, (base - 26, base - 20, base - 8), pygame.Rect(x, y, w, h), 2)
            for gx in range(int(x) + 6, int(x + w) - 4, 10):
                for gy in range(int(y) + 6, int(y + h) - 4, 12):
                    pygame.draw.rect(s, (220, 200, 130), pygame.Rect(gx, gy, 3, 4))
        for _ in range(6):  # 探照燈 / 砲塔
            x, y = rnd.uniform(20, PLAY_W - 20), rnd.uniform(20, TILE_H - 20)
            pygame.draw.circle(s, (40, 44, 54), (x, y), 12)
            pygame.draw.circle(s, (150, 40, 40), (x, y), 5)

    # ------------------------------------------------------------------
    def _build_clouds(self) -> list[tuple[pygame.Surface, float, float, float]]:
        rnd = self.rnd
        clouds = []
        count = 5 if self.theme in ("ocean", "islands") else 4
        for _ in range(count):
            w = rnd.uniform(80, 190)
            h = w * rnd.uniform(0.34, 0.5)
            surf = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
            alpha = 70 if self.theme == "night" else 110
            col = (18, 22, 40, alpha) if self.theme == "night" else (250, 250, 255, alpha)
            for _ in range(9):
                cx = rnd.uniform(w * 0.18, w * 0.82)
                cy = rnd.uniform(h * 0.3, h * 0.7)
                r = rnd.uniform(h * 0.25, h * 0.5)
                pygame.draw.circle(surf, col, (cx, cy), r)
            clouds.append((surf, rnd.uniform(-40, PLAY_W - 40),
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
        for surf, x, base_y, par in self.clouds:
            y = (base_y + self.cloud_offset * par) % (TILE_H + surf.get_height())
            surface.blit(surf, (x, y - surf.get_height()))
