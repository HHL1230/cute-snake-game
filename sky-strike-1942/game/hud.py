"""右側資訊面板與畫面覆蓋文字。"""

from __future__ import annotations

import math

import pygame

from . import settings as S


class Hud:
    def __init__(self, assets) -> None:  # noqa: ANN001
        self.a = assets
        self.panel_x = S.PLAY_W

    # ------------------------------------------------------------------
    def draw_panel(self, surf: pygame.Surface, game) -> None:  # noqa: ANN001
        a = self.a
        panel = pygame.Rect(self.panel_x, 0, S.HUD_W, S.SCREEN_H)
        pygame.draw.rect(surf, (18, 20, 28), panel)
        pygame.draw.line(surf, (60, 66, 84), (self.panel_x, 0), (self.panel_x, S.SCREEN_H), 2)

        x = self.panel_x + 10
        y = 14

        def label(text: str, color=S.STEEL) -> None:
            nonlocal y
            surf.blit(a.font_tiny.render(text, True, color), (x, y))
            y += 15

        def value(text: str, color=S.WHITE) -> None:
            nonlocal y
            surf.blit(a.font_small.render(text, True, color), (x, y))
            y += 22

        label("1UP")
        value(f"{game.score:07d}", S.YELLOW)
        label("HI-SCORE")
        value(f"{game.highscore:07d}", S.CYAN)

        y += 6
        label("STAGE")
        loop_txt = f" L{game.loop_count + 1}" if game.loop_count else ""
        value(f"{game.stage_index + 1}/{game.total_stages}{loop_txt}")
        surf.blit(a.font_tiny.render(game.stage_data["name"][:13], True, S.SILVER), (x, y))
        y += 22

        # 剩餘機數
        label("PLANES")
        for i in range(min(game.lives, 5)):
            icon = pygame.transform.smoothscale(a.wingman, (18, 18))
            surf.blit(icon, (x + i * 20, y))
        if game.lives > 5:
            surf.blit(a.font_tiny.render(f"+{game.lives - 5}", True, S.WHITE), (x + 100, y + 4))
        y += 26

        # 火力
        label("POWER")
        p = game.player.power if game.player else 0
        for i in range(S.MAX_POWER):
            col = S.ORANGE if i < p else (52, 56, 68)
            pygame.draw.rect(surf, col, pygame.Rect(x + i * 22, y, 18, 10), border_radius=2)
        y += 22

        # 僚機
        label("WINGMEN")
        wm = len(game.player.wingmen) if game.player else 0
        for i in range(2):
            col = S.BLUE if i < wm else (52, 56, 68)
            pygame.draw.circle(surf, col, (x + 9 + i * 24, y + 6), 7)
        y += 24

        # 翻滾
        label("LOOPS  [X]")
        lp = game.player.loops if game.player else 0
        for i in range(min(lp, 5)):
            pygame.draw.circle(surf, S.GREEN, (x + 9 + i * 20, y + 6), 6, 2)
        y += 24

        # 炸彈
        label("BOMBS  [C]")
        bombs = game.player.bombs if game.player else 0
        for i in range(min(bombs, 4)):
            pygame.draw.circle(surf, S.YELLOW, (x + 9 + i * 22, y + 7), 6)
            pygame.draw.rect(surf, S.DARK, pygame.Rect(x + 7 + i * 22, y, 5, 4))
        y += 30

        pygame.draw.line(surf, (52, 58, 74), (x - 2, y), (self.panel_x + S.HUD_W - 8, y))
        y += 10
        for line in ("ARROWS/WASD", "or NUMPAD", " MOVE", "Z / SPACE", " SHOOT",
                     "X  ROLL", "C  BOMB", "P  PAUSE", "M  MUTE",
                     "F11 FULLSCR", "Q  QUIT"):
            surf.blit(a.font_tiny.render(line, True, S.STEEL), (x, y))
            y += 14

    # ------------------------------------------------------------------
    def draw_boss_bar(self, surf: pygame.Surface, boss) -> None:  # noqa: ANN001
        w = S.PLAY_W - 40
        rect = pygame.Rect(20, 12, w, 12)
        pygame.draw.rect(surf, (30, 30, 38), rect.inflate(4, 4), border_radius=3)
        ratio = max(0.0, boss.hp / boss.max_hp)
        col = S.GREEN if ratio > 0.6 else S.YELLOW if ratio > 0.3 else S.RED
        pygame.draw.rect(surf, col, pygame.Rect(rect.x, rect.y, int(w * ratio), rect.h),
                         border_radius=3)
        pygame.draw.rect(surf, S.SILVER, rect, 1, border_radius=3)

    def draw_center_text(self, surf: pygame.Surface, lines: list[tuple[str, pygame.font.Font,
                                                                      tuple[int, int, int]]],
                         y0: int | None = None, shadow: bool = True) -> None:
        total = sum(f.get_height() + 8 for _, f, _ in lines)
        y = (S.SCREEN_H - total) // 2 if y0 is None else y0
        for text, font, color in lines:
            img = font.render(text, True, color)
            r = img.get_rect(center=(S.PLAY_W // 2, y + img.get_height() // 2))
            if shadow:
                sh = font.render(text, True, (0, 0, 0))
                surf.blit(sh, r.move(2, 2))
            surf.blit(img, r)
            y += img.get_height() + 8

    def draw_banner(self, surf: pygame.Surface, alpha: int = 150) -> None:
        veil = pygame.Surface((S.PLAY_W, S.SCREEN_H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, alpha))
        surf.blit(veil, (0, 0))

    def blink(self, t: float, speed: float = 2.4) -> bool:
        return math.sin(t * speed * math.pi) > -0.2
