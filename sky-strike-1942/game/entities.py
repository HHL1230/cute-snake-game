"""遊戲中的所有精靈實體。"""

from __future__ import annotations

import math
import random

import pygame

from . import settings as S
from .utils import clamp, vector_to


# --------------------------------------------------------------------------
# 特效
# --------------------------------------------------------------------------
class Explosion(pygame.sprite.Sprite):
    def __init__(self, frames: list[pygame.Surface], center: tuple[float, float],
                 duration: float = 0.55) -> None:
        super().__init__()
        self.frames = frames
        self.duration = duration
        self.t = 0.0
        self.image = frames[0]
        self.rect = self.image.get_rect(center=center)

    def update(self, dt: float, game) -> None:  # noqa: ANN001
        self.t += dt
        idx = int(self.t / self.duration * len(self.frames))
        if idx >= len(self.frames):
            self.kill()
            return
        center = self.rect.center
        self.image = self.frames[idx]
        self.rect = self.image.get_rect(center=center)


class FloatingText(pygame.sprite.Sprite):
    def __init__(self, text: str, center: tuple[float, float],
                 font: pygame.font.Font, color=S.YELLOW) -> None:
        super().__init__()
        self.image = font.render(text, True, color)
        self.rect = self.image.get_rect(center=center)
        self.pos = pygame.Vector2(self.rect.center)
        self.t = 0.0

    def update(self, dt: float, game) -> None:  # noqa: ANN001
        self.t += dt
        self.pos.y -= 26 * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        if self.t > 0.9:
            self.kill()


# --------------------------------------------------------------------------
# 子彈
# --------------------------------------------------------------------------
class Bullet(pygame.sprite.Sprite):
    def __init__(self, image: pygame.Surface, pos: tuple[float, float],
                 velocity: tuple[float, float], damage: int = 1,
                 radius: float = 4.0, pierce: bool = False) -> None:
        super().__init__()
        self.image = image
        self.rect = image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(velocity)
        self.damage = damage
        self.radius = radius
        self.pierce = pierce
        # 穿透彈記錄「目標 id → 冷卻」，避免同一目標每幀被重複扣血
        self.hit_cd: dict[int, float] = {}

    def can_hit(self, target) -> bool:  # noqa: ANN001
        """穿透彈是否可對此目標造成傷害（並登記冷卻）。"""
        if not self.pierce:
            return True
        key = id(target)
        if self.hit_cd.get(key, 0.0) > 0.0:
            return False
        self.hit_cd[key] = S.LASER_PIERCE_INTERVAL
        return True

    def update(self, dt: float, game) -> None:  # noqa: ANN001
        self.pos += self.vel * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        if self.hit_cd:
            for key in list(self.hit_cd):
                self.hit_cd[key] -= dt
                if self.hit_cd[key] <= 0.0:
                    del self.hit_cd[key]
        if (self.rect.bottom < -30 or self.rect.top > S.SCREEN_H + 30
                or self.rect.right < -40 or self.rect.left > S.PLAY_W + 40):
            self.kill()


# --------------------------------------------------------------------------
# 道具
# --------------------------------------------------------------------------
class PowerUp(pygame.sprite.Sprite):
    def __init__(self, image: pygame.Surface, kind: str, pos: tuple[float, float]) -> None:
        super().__init__()
        self.image = image
        self.kind = kind
        self.rect = image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)
        self.t = 0.0

    def update(self, dt: float, game) -> None:  # noqa: ANN001
        self.t += dt
        self.pos.y += 62 * dt
        self.pos.x += math.sin(self.t * 3.0) * 34 * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        if self.rect.top > S.SCREEN_H:
            self.kill()


# --------------------------------------------------------------------------
# 玩家
# --------------------------------------------------------------------------
class Wingman(pygame.sprite.Sprite):
    def __init__(self, image: pygame.Surface, player: "Player", side: int) -> None:
        super().__init__()
        self.image = image
        self.player = player
        self.side = side
        self.rect = image.get_rect(center=player.rect.center)
        self.cooldown = 0.0

    def update(self, dt: float, game) -> None:  # noqa: ANN001
        target_x = self.player.pos.x + self.side * 46
        target_y = self.player.pos.y + 18
        cur = pygame.Vector2(self.rect.center)
        cur += (pygame.Vector2(target_x, target_y) - cur) * min(1.0, 9.0 * dt)
        self.rect.center = (round(cur.x), round(cur.y))
        self.cooldown -= dt
        if self.player.firing and self.cooldown <= 0:
            if self.player.weapon == S.WEAPON_LASER:
                self.cooldown = 0.28
                game.spawn_player_bullet((self.rect.centerx, self.rect.top),
                                         (0, -S.LASER_BULLET_SPEED), damage=1,
                                         kind="laser_bolt")
            else:
                self.cooldown = 0.22
                game.spawn_player_bullet((self.rect.centerx, self.rect.top),
                                         (0, -S.PLAYER_BULLET_SPEED), damage=1)


class Player(pygame.sprite.Sprite):
    def __init__(self, assets, pos: tuple[float, float]) -> None:  # noqa: ANN001
        super().__init__()
        self.assets = assets
        self.frames = assets.player_frames
        self.image = self.frames[0][0]
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)

        self.power = 0
        self.bombs = 2
        self.rolls = S.PLAYER_START_ROLLS
        self.wingmen: list[Wingman] = []
        self.weapon = S.WEAPON_VULCAN

        self.fire_timer = 0.0
        self.firing = False
        self.anim_t = 0.0
        self.bank = 0

        self.invuln = S.PLAYER_RESPAWN_INVULN
        self.rolling = 0.0
        self.roll_t = 0.0
        self.alive_flag = True

    # ------------------------------------------------------------------
    @property
    def hitbox(self) -> pygame.Rect:
        r = pygame.Rect(0, 0, *S.PLAYER_HITBOX)
        r.center = self.rect.center
        return r

    @property
    def invulnerable(self) -> bool:
        return self.invuln > 0 or self.rolling > 0

    def start_roll(self, game) -> bool:  # noqa: ANN001
        if self.rolling > 0:
            return False
        if self.rolls <= 0:
            game.notify("NO ROLLS LEFT", "翻滾次數已用完")
            return False
        self.rolls -= 1
        self.rolling = S.PLAYER_ROLL_TIME
        self.roll_t = 0.0
        game.audio.play("roll")
        return True

    def add_power(self, game) -> None:  # noqa: ANN001
        if self.power < S.MAX_POWER:
            self.power += 1
        else:
            game.add_score(2000)

    def add_wingman(self, game) -> None:  # noqa: ANN001
        if len(self.wingmen) >= 2:
            game.add_score(2000)
            return
        side = -1 if not self.wingmen else -self.wingmen[0].side
        w = Wingman(self.assets.wingman, self, side)
        self.wingmen.append(w)
        game.wingmen.add(w)
        game.all_sprites.add(w)

    def set_weapon(self, game, weapon: str) -> None:  # noqa: ANN001
        """切換武器；撿到相同武器道具時改為加分。"""
        if self.weapon == weapon:
            game.add_score(1000)
            return
        self.weapon = weapon
        self.fire_timer = 0.0

    def clear_wingmen(self, game) -> None:  # noqa: ANN001
        for w in self.wingmen:
            w.kill()
        self.wingmen.clear()

    # ------------------------------------------------------------------
    def update(self, dt: float, game) -> None:  # noqa: ANN001
        keys = pygame.key.get_pressed()
        held = getattr(game, "held", ())

        def down(*codes: int) -> bool:
            return any(keys[c] for c in codes) or any(c in held for c in codes)

        # 數字鍵盤：8/2/4/6 為上下左右，5 同樣是下，7/9/1/3 為四個對角
        right = down(pygame.K_RIGHT, pygame.K_d,
                     pygame.K_KP6, pygame.K_KP9, pygame.K_KP3)
        left = down(pygame.K_LEFT, pygame.K_a,
                    pygame.K_KP4, pygame.K_KP7, pygame.K_KP1)
        up = down(pygame.K_UP, pygame.K_w,
                  pygame.K_KP8, pygame.K_KP7, pygame.K_KP9)
        downward = down(pygame.K_DOWN, pygame.K_s,
                        pygame.K_KP2, pygame.K_KP5, pygame.K_KP1, pygame.K_KP3)

        dx = int(right) - int(left)
        dy = int(downward) - int(up)
        move = pygame.Vector2(dx, dy)
        if move.length_squared() > 0:
            move = move.normalize()
        self.pos += move * S.PLAYER_SPEED * dt
        self.pos.x = clamp(self.pos.x, 20, S.PLAY_W - 20)
        self.pos.y = clamp(self.pos.y, 30, S.SCREEN_H - 24)

        self.firing = down(pygame.K_z, pygame.K_SPACE, pygame.K_j, pygame.K_KP0)
        self.fire_timer -= dt
        if self.firing and self.fire_timer <= 0 and self.rolling <= 0:
            self.fire(game)

        if self.invuln > 0:
            self.invuln -= dt
        if self.rolling > 0:
            self.rolling -= dt
            self.roll_t += dt

        # 動畫
        self.anim_t += dt
        target_bank = int(clamp(dx * 2, -2, 2))
        self.bank = target_bank
        if self.rolling > 0:
            idx = int((1 - self.rolling / S.PLAYER_ROLL_TIME) * len(self.assets.player_roll))
            self.image = self.assets.player_roll[min(idx, len(self.assets.player_roll) - 1)]
        else:
            frames = self.frames[self.bank]
            self.image = frames[int(self.anim_t * 22) % len(frames)]
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def fire(self, game) -> None:  # noqa: ANN001
        if self.weapon == S.WEAPON_LASER:
            self._fire_laser(game)
            return
        self.fire_timer = S.PLAYER_FIRE_COOLDOWN
        x, y = self.pos.x, self.rect.top + 6
        v = S.PLAYER_BULLET_SPEED
        shots: list[tuple[tuple[float, float], tuple[float, float], int]] = []
        p = self.power
        shots.append(((x - 8, y), (0, -v), 1))
        shots.append(((x + 8, y), (0, -v), 1))
        if p >= 1:
            shots.append(((x, y - 6), (0, -v * 1.12), 2))
        if p >= 2:
            shots.append(((x - 14, y + 6), (-v * 0.22, -v * 0.97), 1))
            shots.append(((x + 14, y + 6), (v * 0.22, -v * 0.97), 1))
        if p >= 3:
            shots.append(((x - 18, y + 10), (-v * 0.45, -v * 0.88), 1))
            shots.append(((x + 18, y + 10), (v * 0.45, -v * 0.88), 1))
        if p >= 4:
            shots.append(((x - 20, y + 14), (-v * 0.72, -v * 0.68), 1))
            shots.append(((x + 20, y + 14), (v * 0.72, -v * 0.68), 1))
        for pos, vel, dmg in shots:
            game.spawn_player_bullet(pos, vel, dmg)
        game.audio.play("shoot")

    def _fire_laser(self, game) -> None:  # noqa: ANN001
        """穿透雷射：只有一道正前方光束，不散射；貫穿整條敵機縱列。"""
        self.fire_timer = S.LASER_FIRE_COOLDOWN
        x, y = self.pos.x, self.rect.top - 10
        kind = "laser_wide" if self.power >= 2 else "laser"
        game.spawn_player_bullet((x, y), (0, -S.LASER_BULLET_SPEED),
                                 3 + self.power // 2, kind=kind)
        game.audio.play("laser")


# --------------------------------------------------------------------------
# 敵機
# --------------------------------------------------------------------------
ENEMY_STATS = {
    # kind:      hp, score, speed, fire_pattern, fire_interval
    "scout":  (1, 100, 170.0, "none", 0.0),
    "red":    (1, 150, 200.0, "aimed", 2.0),
    "green":  (3, 300, 140.0, "aimed", 1.6),
    "bomber": (6, 600, 100.0, "spread", 2.2),
    "heavy":  (14, 1500, 78.0, "stream", 1.3),
    "jet":    (2, 250, 300.0, "aimed", 1.8),
}


class Enemy(pygame.sprite.Sprite):
    def __init__(self, assets, kind: str, pos: tuple[float, float], pattern: str,  # noqa: ANN001
                 params: dict | None = None, formation: int | None = None,
                 hp_scale: float = 1.0, speed_scale: float = 1.0) -> None:
        super().__init__()
        self.kind = kind
        hp, score, speed, fire_pattern, fire_interval = ENEMY_STATS[kind]
        self.image = assets.enemies[kind]
        self.base_image = self.image
        self.hit_image = assets.enemies_hit[kind]
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)
        self.start = pygame.Vector2(pos)
        self.max_hp = max(1, int(round(hp * hp_scale)))
        self.hp = self.max_hp
        self.score = score
        self.speed = speed * speed_scale
        self.fire_pattern = fire_pattern
        self.fire_interval = fire_interval
        self.fire_timer = random.uniform(0.4, 1.4)
        self.pattern = pattern
        self.p = params or {}
        self.formation = formation
        self.t = 0.0
        self.flash = 0.0
        self.state = 0
        self.vel = pygame.Vector2(0, self.speed)
        self.counted = False

        if pattern == "arc":
            r = self.p.get("radius", 120.0)
            a0 = self.p.get("start_angle", -math.pi / 2)
            self.p.setdefault("start_angle", a0)
            self.p["cx"] = self.start.x - math.cos(a0) * r
            self.p["cy"] = self.start.y - math.sin(a0) * r

    # ------------------------------------------------------------------
    def _move(self, dt: float, game) -> None:  # noqa: ANN001
        p = self.p
        pat = self.pattern
        if pat == "down":
            self.pos.y += self.speed * dt
            self.pos.x += p.get("vx", 0.0) * dt
        elif pat == "sine":
            self.pos.y += self.speed * dt
            amp = p.get("amp", 70.0)
            freq = p.get("freq", 1.6)
            self.pos.x = self.start.x + math.sin(self.t * freq + p.get("phase", 0.0)) * amp
        elif pat == "dive":
            target = p.setdefault("target", game.player.pos.x if game.player else self.pos.x)
            self.pos.y += self.speed * dt * (1.0 + self.t * 0.35)
            self.pos.x += (target - self.pos.x) * min(1.0, 1.6 * dt)
        elif pat == "arc":
            r = p.get("radius", 120.0)
            w = p.get("omega", 1.5) * p.get("dir", 1)
            ang = p.get("start_angle", 0.0) + w * self.t
            self.pos.x = p.get("cx", self.start.x) + math.cos(ang) * r
            self.pos.y = p.get("cy", self.start.y) + math.sin(ang) * r + self.t * p.get("drift", 26.0)
        elif pat == "swoop":
            hold_y = p.get("hold_y", 150.0)
            if self.state == 0:
                self.pos.y += self.speed * dt
                if self.pos.y >= hold_y:
                    self.state = 1
                    self.p["turn_t"] = self.t
            else:
                self.pos.x += p.get("dir", 1) * self.speed * dt
                self.pos.y += math.sin((self.t - p["turn_t"]) * 2.2) * 40 * dt
                if self.pos.x < -60 or self.pos.x > S.PLAY_W + 60:
                    self.kill()
        elif pat == "hover":
            hold_y = p.get("hold_y", 130.0)
            hold_time = p.get("hold_time", 3.5)
            if self.state == 0:
                self.pos.y += self.speed * dt
                if self.pos.y >= hold_y:
                    self.state = 1
                    self.p["hold_start"] = self.t
            elif self.state == 1:
                self.pos.x += math.sin(self.t * 1.3) * 60 * dt
                if self.t - self.p["hold_start"] > hold_time:
                    self.state = 2
            else:
                self.pos.y += self.speed * 1.4 * dt
        elif pat == "sidesweep":
            self.pos.x += p.get("dir", 1) * self.speed * dt
            self.pos.y += math.sin(self.t * p.get("freq", 2.0)) * p.get("amp", 60.0) * dt
            if self.pos.x < -70 or self.pos.x > S.PLAY_W + 70:
                self.kill()
        elif pat == "zigzag":
            self.pos.y += self.speed * 0.7 * dt
            phase = int(self.t / p.get("period", 0.9)) % 2
            self.pos.x += (1 if phase == 0 else -1) * p.get("dir", 1) * self.speed * dt
        else:
            self.pos.y += self.speed * dt

    def update(self, dt: float, game) -> None:  # noqa: ANN001
        self.t += dt
        self._move(dt, game)
        self.rect.center = (round(self.pos.x), round(self.pos.y))

        if self.flash > 0:
            self.flash -= dt
            if self.flash <= 0:
                self.image = self.base_image

        if self.fire_pattern != "none" and game.player is not None and self.rect.bottom > 0:
            self.fire_timer -= dt
            if self.fire_timer <= 0:
                self.fire_timer = self.fire_interval * random.uniform(0.75, 1.3)
                self.shoot(game)

        if (self.rect.top > S.SCREEN_H + 60 or self.rect.right < -120
                or self.rect.left > S.PLAY_W + 120):
            self.escape(game)

    def escape(self, game) -> None:  # noqa: ANN001
        if self.formation is not None and not self.counted:
            self.counted = True
            game.formation_escaped(self.formation)
        self.kill()

    def shoot(self, game) -> None:  # noqa: ANN001
        if game.player is None:
            return
        speed = S.ENEMY_BULLET_SPEED * game.stage_data.get("bullet_speed", 1.0)
        origin = (self.rect.centerx, self.rect.bottom - 4)
        if self.fire_pattern == "aimed":
            d = vector_to(origin, game.player.rect.center)
            game.spawn_enemy_bullet(origin, (d[0] * speed, d[1] * speed))
        elif self.fire_pattern == "spread":
            d = vector_to(origin, game.player.rect.center)
            base = math.atan2(d[1], d[0])
            for off in (-0.30, 0.0, 0.30):
                a = base + off
                game.spawn_enemy_bullet(origin, (math.cos(a) * speed, math.sin(a) * speed))
        elif self.fire_pattern == "stream":
            d = vector_to(origin, game.player.rect.center)
            for k in (0.85, 1.0, 1.15):
                game.spawn_enemy_bullet(origin, (d[0] * speed * k, d[1] * speed * k))
        game.audio.play("enemy_shoot")

    def damage(self, amount: int, game) -> bool:  # noqa: ANN001
        self.hp -= amount
        if self.hp <= 0:
            self.destroy(game)
            return True
        self.flash = 0.06
        self.image = self.hit_image
        game.audio.play("hit")
        return False

    def destroy(self, game) -> None:  # noqa: ANN001
        size = "big" if self.kind in ("bomber", "heavy") else "small"
        game.spawn_explosion(self.rect.center, size)
        game.audio.play("explode" if size == "small" else "big_explode")
        game.add_score(self.score, self.rect.center)
        if self.formation is not None and not self.counted:
            self.counted = True
            game.formation_killed(self.formation, self.rect.center)
        self.kill()


# --------------------------------------------------------------------------
# 頭目
# --------------------------------------------------------------------------
class Boss(pygame.sprite.Sprite):
    def __init__(self, assets, stage: int, hp: int, score: int) -> None:  # noqa: ANN001
        super().__init__()
        self.assets = assets
        self.stage = stage
        self.base_image = assets.bosses[min(stage, 5)]
        self.hit_image = assets.bosses_hit[min(stage, 5)]
        self.image = self.base_image
        self.rect = self.image.get_rect(midbottom=(S.PLAY_W // 2, 0))
        self.pos = pygame.Vector2(self.rect.center)
        self.max_hp = hp
        self.hp = hp
        self.score = score
        self.t = 0.0
        self.state = "enter"
        self.flash = 0.0
        self.attack_timer = 1.4
        self.burst = 0
        self.burst_timer = 0.0
        self.dying = 0.0
        self.dir = 1
        self.phase = 1

    @property
    def hitbox(self) -> pygame.Rect:
        return self.rect.inflate(-self.rect.width * 0.16, -self.rect.height * 0.28)

    # ------------------------------------------------------------------
    def update(self, dt: float, game) -> None:  # noqa: ANN001
        self.t += dt
        if self.flash > 0:
            self.flash -= dt
            if self.flash <= 0:
                self.image = self.base_image

        if self.state == "enter":
            self.pos.y += 70 * dt
            if self.pos.y >= 130:
                self.pos.y = 130
                self.state = "fight"
        elif self.state == "fight":
            self.pos.x += self.dir * (66 + self.phase * 24) * dt
            if self.pos.x < self.rect.width * 0.45:
                self.pos.x = self.rect.width * 0.45
                self.dir = 1
            elif self.pos.x > S.PLAY_W - self.rect.width * 0.45:
                self.pos.x = S.PLAY_W - self.rect.width * 0.45
                self.dir = -1
            self.pos.y = 130 + math.sin(self.t * 1.1) * 26
            self._attack(dt, game)
        elif self.state == "dying":
            self.dying += dt
            self.pos.y += 16 * dt
            if self.dying > 0.22:
                self.dying = 0.0
                offset = (random.uniform(-0.4, 0.4) * self.rect.width,
                          random.uniform(-0.4, 0.4) * self.rect.height)
                game.spawn_explosion((self.rect.centerx + offset[0],
                                      self.rect.centery + offset[1]), "big")
                game.audio.play("explode")

        ratio = self.hp / self.max_hp
        self.phase = 3 if ratio < 0.35 else 2 if ratio < 0.7 else 1
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def _attack(self, dt: float, game) -> None:  # noqa: ANN001
        if game.player is None:
            return
        speed = S.ENEMY_BULLET_SPEED * 1.05 * game.stage_data.get("bullet_speed", 1.0)
        self.attack_timer -= dt
        guns = [(self.rect.centerx - self.rect.width * 0.13, self.rect.centery + 10),
                (self.rect.centerx + self.rect.width * 0.13, self.rect.centery + 10)]

        if self.burst > 0:
            self.burst_timer -= dt
            if self.burst_timer <= 0:
                self.burst -= 1
                self.burst_timer = 0.12
                for g in guns:
                    d = vector_to(g, game.player.rect.center)
                    game.spawn_enemy_bullet(g, (d[0] * speed * 1.25, d[1] * speed * 1.25))
                game.audio.play("enemy_shoot")
            return

        if self.attack_timer > 0:
            return

        mode = random.choice(["fan", "burst", "rain"] if self.phase == 1
                             else ["fan", "burst", "rain", "ring"])
        self.attack_timer = max(0.7, 2.2 - self.phase * 0.35)
        nose = (self.rect.centerx, self.rect.bottom - 12)

        if mode == "fan":
            n = 5 + self.phase * 2
            spread = 0.9
            d = vector_to(nose, game.player.rect.center)
            base = math.atan2(d[1], d[0])
            for i in range(n):
                a = base - spread / 2 + spread * i / (n - 1)
                game.spawn_enemy_bullet(nose, (math.cos(a) * speed, math.sin(a) * speed), boss=True)
        elif mode == "burst":
            self.burst = 3 + self.phase
            self.burst_timer = 0.0
        elif mode == "rain":
            for i in range(6 + self.phase):
                x = random.uniform(self.rect.left + 10, self.rect.right - 10)
                game.spawn_enemy_bullet((x, self.rect.bottom - 10),
                                        (random.uniform(-40, 40), speed * random.uniform(0.8, 1.2)))
        else:  # ring
            n = 12 + self.phase * 3
            for i in range(n):
                a = math.tau * i / n
                game.spawn_enemy_bullet(self.rect.center,
                                        (math.cos(a) * speed * 0.8, math.sin(a) * speed * 0.8),
                                        boss=True)
        game.audio.play("enemy_shoot")

    # ------------------------------------------------------------------
    def damage(self, amount: int, game) -> bool:  # noqa: ANN001
        if self.state != "fight":
            return False
        self.hp -= amount
        self.flash = 0.05
        self.image = self.hit_image
        if self.hp <= 0:
            self.hp = 0
            self.state = "dying"
            game.on_boss_defeated(self)
            return True
        game.audio.play("hit")
        return False
