"""遊戲主體：狀態機、生成器、碰撞與繪製。"""

from __future__ import annotations

import math
import random

import pygame

from . import settings as S
from .audio import Audio
from .background import Background
from .entities import (
    Boss, Bullet, Enemy, Explosion, FloatingText, Player, PowerUp,
)
from .gfx import Assets
from .hud import Hud
from .stages import STAGES
from .utils import load_highscore, save_highscore
from .winfocus import focus_window, has_keyboard_focus


class Game:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.play_surf = pygame.Surface((S.PLAY_W, S.SCREEN_H))
        # 固定尺寸的完整畫格（遊戲區 + HUD），最後再等比縮放置中貼到實際視窗
        self.frame = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
        self.fullscreen = False
        self.assets = Assets()
        self.audio = Audio()
        self.hud = Hud(self.assets)
        self.clock = pygame.time.Clock()
        self.running = True

        self.highscore = load_highscore()
        self.total_stages = len(STAGES)

        # 群組
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.player_bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()
        self.wingmen = pygame.sprite.Group()

        self.player: Player | None = None
        self.boss: Boss | None = None

        self.state = "title"
        self.state_t = 0.0
        self.shake = 0.0
        self.flash = 0.0
        self.stage_index = 0
        self.loop_count = 0
        self.score = 0
        self.lives = S.PLAYER_START_LIVES
        self.next_extend = S.EXTEND_SCORE
        self.stage_data = STAGES[0]
        self.stage_time = 0.0
        self.pending: list[dict] = []
        self.pending_i = 0
        self.formations: dict[int, dict] = {}
        self.respawn_timer = 0.0
        self.paused = False
        self.stage_kills = 0
        self.stage_shots_hit = 0
        self.clear_bonus = 0
        self.allclear_bonus = 0

        # 輸入狀態：事件驅動的按鍵集合，與 key.get_pressed() 互為備援
        self.held: set[int] = set()
        self.has_focus = True
        self.confirm_quit = False

        # 真實視窗焦點追蹤：只在真的有視窗時才依作業系統焦點判定，
        # 這樣「主控台搶走鍵盤焦點」時才會顯示提示，而不是靜靜地吃掉所有按鍵。
        try:
            self.track_os_focus = pygame.display.get_driver() != "dummy"
        except pygame.error:
            self.track_os_focus = False
        self._unfocus_t = 0.0
        # 啟動後的前幾秒主動搶回前景（從 run.bat / 主控台啟動時很常需要）
        self._focus_grab_t = 3.0 if self.track_os_focus else 0.0
        self._focus_grab_cd = 0.0
        # 最近收到真實按鍵事件的殘留時間：有按鍵進來就代表真的有焦點，
        # 用來擋掉 get_focused() 誤判造成的永久凍結
        self._key_evt_t = 0.0
        if self.track_os_focus:
            self.has_focus = has_keyboard_focus()

        # 畫面中央的短暫提示（例如炸彈 / 翻滾用完）
        self.notice: tuple[str, str] | None = None
        self.notice_t = 0.0

        self.background = Background(STAGES[0]["theme"], STAGES[0]["scroll"], seed=1)
        self.title_bg = Background("ocean", 60.0, seed=7)
        self.title_planes: list[list[float]] = []
        self.audio.play_music("title")

    # ==================================================================
    # 流程控制
    # ==================================================================
    def start_new_game(self) -> None:
        self.score = 0
        self.lives = S.PLAYER_START_LIVES
        self.next_extend = S.EXTEND_SCORE
        self.stage_index = 0
        self.loop_count = 0
        self.allclear_bonus = 0
        self.player = None
        self._clear_groups()
        self.start_stage(0)
        self.audio.play("start")

    def _clear_groups(self) -> None:
        for g in (self.all_sprites, self.enemies, self.player_bullets,
                  self.enemy_bullets, self.powerups, self.effects, self.wingmen):
            g.empty()
        self.boss = None

    def start_stage(self, index: int) -> None:
        self.stage_index = index
        self.stage_data = STAGES[index]
        self._clear_groups()
        self.notice = None
        self.notice_t = 0.0

        loop_hp = 1.0 + 0.4 * self.loop_count
        loop_speed = 1.0 + 0.07 * self.loop_count
        self.hp_scale = self.stage_data["hp_scale"] * loop_hp
        self.speed_scale = self.stage_data["speed_scale"] * loop_speed

        self.background = Background(self.stage_data["theme"], self.stage_data["scroll"],
                                     seed=index * 31 + self.loop_count * 7 + 1)
        self.stage_time = 0.0
        self.pending_i = 0
        self.stage_kills = 0
        self.formations = {}
        self.pending = self._expand_waves(self.stage_data["waves"])

        if self.player is None:
            self._spawn_player()
        else:
            self.player.pos.update(S.PLAY_W / 2, S.SCREEN_H - 110)
            self.player.invuln = S.PLAYER_RESPAWN_INVULN
            self.all_sprites.add(self.player)
            for w in self.player.wingmen:
                self.wingmen.add(w)
                self.all_sprites.add(w)

        self.state = "intro"
        self.state_t = 0.0
        self.audio.play_music(self.stage_data["music"])

    def _expand_waves(self, waves: list[dict]) -> list[dict]:
        """把波次腳本展開成依時間排序的生成清單。"""
        out: list[dict] = []
        fid = 0
        for w in waves:
            formation = None
            if w["reward"]:
                fid += 1
                formation = fid

            spawns: list[tuple[float, float, float]] = []  # (time, x, y)
            if w["xs"]:
                for i, xf in enumerate(w["xs"]):
                    spawns.append((w["t"] + i * w["gap"], xf * S.PLAY_W, w["y"] * S.SCREEN_H))
            elif w["side"]:
                x = -50.0 if w["side"] == "left" else S.PLAY_W + 50.0
                for i in range(w["count"]):
                    spawns.append((w["t"] + i * w["gap"], x, w["y"] * S.SCREEN_H))
            else:
                x = (w["x"] if w["x"] is not None else 0.5) * S.PLAY_W
                for i in range(w["count"]):
                    spawns.append((w["t"] + i * w["gap"], x, w["y"] * S.SCREEN_H))

            if formation is not None:
                self.formations[formation] = {
                    "total": len(spawns), "killed": 0, "escaped": 0,
                    "reward": w["reward"],
                }
            for idx, (t, x, y) in enumerate(spawns):
                out.append({
                    "t": t, "kind": w["kind"], "x": x, "y": y,
                    "pattern": w["pattern"],
                    "params": dict(w["params"], phase=w["params"].get("phase", idx * 0.5)),
                    "formation": formation,
                })
        out.sort(key=lambda d: d["t"])
        return out

    # ==================================================================
    # 生成
    # ==================================================================
    def _spawn_player(self) -> None:
        self.player = Player(self.assets, (S.PLAY_W / 2, S.SCREEN_H - 110))
        self.all_sprites.add(self.player)

    def spawn_player_bullet(self, pos, vel, damage: int = 1, kind: str = "vulcan") -> None:
        if kind == "laser":
            b = Bullet(self.assets.laser_bullet, pos, vel, damage,
                       radius=5.0, pierce=True)
        elif kind == "laser_wide":
            b = Bullet(self.assets.laser_bullet_wide, pos, vel, damage,
                       radius=7.0, pierce=True)
        elif kind == "laser_bolt":
            # 僚機的小型光束：外觀是雷射，但不穿透，威力與機砲相當
            b = Bullet(self.assets.laser_bullet_small, pos, vel, damage, radius=3.5)
        else:
            b = Bullet(self.assets.player_bullet, pos, vel, damage)
        self.player_bullets.add(b)
        self.all_sprites.add(b)

    def spawn_enemy_bullet(self, pos, vel, boss: bool = False) -> None:
        img = self.assets.boss_bullet if boss else self.assets.enemy_bullet
        b = Bullet(img, pos, vel, 1, radius=6.0 if boss else 4.5)
        self.enemy_bullets.add(b)
        self.all_sprites.add(b)

    def spawn_explosion(self, center, size: str = "small") -> None:
        dur = {"small": 0.42, "big": 0.6, "huge": 1.0}[size]
        e = Explosion(self.assets.explosions[size], center, dur)
        self.effects.add(e)
        if size != "small":
            self.shake = max(self.shake, 0.25 if size == "big" else 0.6)

    def spawn_powerup(self, kind: str, pos) -> None:
        p = PowerUp(self.assets.powerups[kind], kind, pos)
        self.powerups.add(p)
        self.all_sprites.add(p)

    # ==================================================================
    # 分數與編隊
    # ==================================================================
    def add_score(self, amount: int, pos=None) -> None:
        self.score += amount
        if pos is not None and amount >= 500:
            self.effects.add(FloatingText(str(amount), pos, self.assets.font_tiny))
        if self.score >= self.next_extend:
            self.next_extend += S.EXTEND_SCORE
            self.lives += 1
            self.audio.play("extend")
        if self.score > self.highscore:
            self.highscore = self.score

    def formation_killed(self, fid: int, pos) -> None:
        f = self.formations.get(fid)
        if not f:
            return
        f["killed"] += 1
        self.stage_kills += 1
        if f["killed"] >= f["total"] and f["escaped"] == 0:
            self.spawn_powerup(f["reward"], pos)
            self.add_score(1000, pos)

    def formation_escaped(self, fid: int) -> None:
        f = self.formations.get(fid)
        if f:
            f["escaped"] += 1

    # ==================================================================
    # 事件
    # ==================================================================
    def handle_event(self, e: pygame.event.Event) -> None:
        if e.type == pygame.QUIT:
            self.quit_game()
            return

        # --- 視窗焦點：失焦時清空按鍵並顯示提示，避免「按鍵無反應」 ---
        if e.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self.has_focus = False
            self._unfocus_t = 1.0
            self.held.clear()
            pygame.mouse.set_visible(True)
            return
        if e.type == getattr(pygame, "WINDOWFOCUSGAINED", -1):
            self.has_focus = True
            self._unfocus_t = 0.0
            self._focus_grab_t = 0.0
            self.held.clear()
            pygame.mouse.set_visible(False)
            return

        if e.type == pygame.KEYUP:
            self.held.discard(e.key)
            return
        # 點擊視窗即可取回鍵盤焦點（失焦提示就是叫玩家這樣做）
        if e.type == pygame.MOUSEBUTTONDOWN:
            self._unfocus_t = 0.0
            focus_window()
            if not self.has_focus:
                self.has_focus = True
                self.held.clear()
            pygame.mouse.set_visible(False)
            return
        if e.type != pygame.KEYDOWN:
            return

        # 收到按鍵代表確實有鍵盤焦點（保險機制）
        self.has_focus = True
        self._unfocus_t = 0.0
        self._key_evt_t = 1.5
        self.held.add(e.key)

        # --- 離開遊戲確認（Q 開啟，避免遊戲中誤按直接結束）---
        if self.confirm_quit:
            if e.key in (pygame.K_y, pygame.K_q, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.quit_game()
            elif e.key in (pygame.K_n, pygame.K_ESCAPE):
                self.confirm_quit = False
            return
        if e.key == pygame.K_q:
            if self.state == "title":
                self.quit_game()
            else:
                self.confirm_quit = True
                self.held.clear()
            return

        if e.key == pygame.K_ESCAPE:
            if self.state in ("play", "boss", "boss_alarm") and not self.paused:
                self.paused = True
            elif self.paused:
                self.paused = False
            else:
                self.quit_game()
            return
        if e.key == pygame.K_m:
            self.audio.toggle_mute()
            return
        if e.key in (pygame.K_F11, pygame.K_f):
            self.toggle_fullscreen()
            return

        if self.state == "title":
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_z, pygame.K_SPACE):
                self.start_new_game()
        elif self.state == "gameover":
            if self.state_t > 1.2 and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                pygame.K_z, pygame.K_SPACE):
                save_highscore(self.highscore)
                self.state = "title"
                self.state_t = 0.0
                self._clear_groups()
                self.player = None
                self.audio.play_music("title")
        elif self.state == "allclear":
            if self.state_t > 2.0 and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                pygame.K_z, pygame.K_SPACE):
                save_highscore(self.highscore)
                self.state = "title"
                self.state_t = 0.0
                self._clear_groups()
                self.player = None
                self.audio.play_music("title")
        elif self.state in ("play", "boss"):
            if e.key == pygame.K_p:
                self.paused = not self.paused
            elif self.paused:
                return
            elif e.key in (pygame.K_x, pygame.K_k, pygame.K_LSHIFT, pygame.K_RSHIFT):
                if self.player:
                    self.player.start_roll(self)
            elif e.key in (pygame.K_c, pygame.K_l):
                self.use_bomb()

    def quit_game(self) -> None:
        """離開遊戲：先存檔並還原視窗模式再結束主迴圈。

        直接從全螢幕呼叫 pygame.quit() 在 Windows/SDL2 下會觸發存取違規，
        因此結束前務必先切回視窗模式。
        """
        save_highscore(self.highscore)
        self.confirm_quit = False
        if self.fullscreen:
            self.fullscreen = False
            try:
                self.screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
            except pygame.error:
                pass
        self.running = False

    def notify(self, text: str, sub: str = "", duration: float = 1.5) -> None:
        """在畫面中央顯示一則短暫提示（例如炸彈或翻滾已用完）。"""
        fresh = self.notice is None or self.notice[0] != text
        self.notice = (text, sub)
        self.notice_t = duration
        if fresh:
            self.audio.play("menu")

    def use_bomb(self) -> None:
        if not self.player:
            return
        if self.player.bombs <= 0:
            self.notify("NO BOMBS LEFT", "炸彈已用完")
            return
        self.player.bombs -= 1
        self.flash = 0.35
        self.shake = max(self.shake, 0.4)
        self.audio.play("big_explode")
        for b in list(self.enemy_bullets):
            b.kill()
        for en in list(self.enemies):
            en.damage(8, self)
        if self.boss and self.boss.state == "fight":
            self.boss.damage(30, self)
        for _ in range(6):
            self.spawn_explosion((random.uniform(20, S.PLAY_W - 20),
                                  random.uniform(60, S.SCREEN_H - 60)), "big")

    # ==================================================================
    # 更新
    # ==================================================================
    def update(self, dt: float) -> None:
        if self.confirm_quit:
            if self.state != "title":
                self.background.update(dt * 0.15)
            else:
                self.title_bg.update(dt)
            return
        if not self.has_focus and self.state not in ("title",):
            self.background.update(dt * 0.15)
            return
        self.state_t += dt
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt)
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt)
        if self.notice_t > 0:
            self.notice_t = max(0.0, self.notice_t - dt)
            if self.notice_t == 0.0:
                self.notice = None

        if self.state == "title":
            self.title_bg.update(dt)
            self._update_title_planes(dt)
            return

        if self.paused:
            return

        if self.state == "intro":
            self.background.update(dt)
            if self.state_t > 2.6:
                self.state = "play"
                self.state_t = 0.0
            return

        if self.state == "clear":
            self.background.update(dt, 1.6)
            self.effects.update(dt, self)
            if self.player:
                self.player.pos.y -= 60 * dt
                self.player.update(dt, self)
            if self.state_t > 3.4:
                self._advance_stage()
            return

        if self.state == "gameover":
            self.background.update(dt, 0.4)
            self.effects.update(dt, self)
            return

        if self.state == "allclear":
            self.background.update(dt, 1.1)
            self.effects.update(dt, self)
            if self.player:
                self.player.pos.y -= 34 * dt
                if self.player.pos.y < -80:
                    self.player.pos.y = S.SCREEN_H + 60
                self.player.update(dt, self)
            return

        # --- play / boss_alarm / boss ---
        speed_scale = 1.0 if self.state != "boss" else 0.45
        self.background.update(dt, speed_scale)

        if self.state == "play":
            self.stage_time += dt
            self._process_spawns()

        if self.state == "boss_alarm" and self.state_t > 2.2:
            self._spawn_boss()

        self.all_sprites.update(dt, self)
        self.effects.update(dt, self)
        if self.boss:
            self.boss.update(dt, self)
            if self.boss.state == "dying" and self.state_t > 2.6:
                self._stage_clear()

        self._collisions()

        if self.player is None and self.state != "gameover":
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                if self.lives > 0:
                    self.lives -= 1
                    self._spawn_player()
                else:
                    self._game_over()

        if (self.state == "play" and self.pending_i >= len(self.pending)
                and not self.enemies):
            self.state = "boss_alarm"
            self.state_t = 0.0
            self.audio.play("alarm")
            self.audio.play_music("boss")

    def _update_title_planes(self, dt: float) -> None:
        if random.random() < dt * 1.6:
            self.title_planes.append([random.uniform(20, S.PLAY_W - 20), -40.0,
                                      random.uniform(90, 190)])
        for p in self.title_planes:
            p[1] += p[2] * dt
        self.title_planes = [p for p in self.title_planes if p[1] < S.SCREEN_H + 50]

    def _process_spawns(self) -> None:
        while (self.pending_i < len(self.pending)
               and self.pending[self.pending_i]["t"] <= self.stage_time):
            spec = self.pending[self.pending_i]
            self.pending_i += 1
            en = Enemy(self.assets, spec["kind"], (spec["x"], spec["y"]),
                       spec["pattern"], dict(spec["params"]), spec["formation"],
                       hp_scale=self.hp_scale, speed_scale=self.speed_scale)
            self.enemies.add(en)
            self.all_sprites.add(en)

    def _spawn_boss(self) -> None:
        cfg = self.stage_data["boss"]
        hp = int(cfg["hp"] * (1.0 + 0.45 * self.loop_count))
        self.boss = Boss(self.assets, self.stage_index + 1, hp, cfg["score"])
        self.state = "boss"
        self.state_t = 0.0

    def on_boss_defeated(self, boss: Boss) -> None:
        self.add_score(boss.score, boss.rect.center)
        self.spawn_explosion(boss.rect.center, "huge")
        self.audio.play("big_explode")
        self.shake = 1.0
        self.state_t = 0.0

    def _stage_clear(self) -> None:
        if self.boss:
            self.boss = None
        for b in list(self.enemy_bullets):
            b.kill()
        self.state = "clear"
        self.state_t = 0.0
        self.audio.play("clear")
        self.audio.stop_music()
        bonus = 5000 * (self.stage_index + 1)
        self.clear_bonus = bonus + self.lives * 2000
        self.add_score(self.clear_bonus)
        save_highscore(self.highscore)

    def _advance_stage(self) -> None:
        nxt = self.stage_index + 1
        if nxt >= len(STAGES):
            self._all_clear()
            return
        self.start_stage(nxt)

    def _all_clear(self) -> None:
        """全關卡通關：進入結局畫面，不再從第 1 關重跑。"""
        self.allclear_bonus = 50000 + self.lives * 10000
        self.add_score(self.allclear_bonus)
        self.state = "allclear"
        self.state_t = 0.0
        self.audio.stop_music()
        self.audio.play("extend")
        save_highscore(self.highscore)
        for group in (self.enemies, self.enemy_bullets, self.player_bullets,
                      self.powerups):
            for sp in list(group):
                sp.kill()

    def _game_over(self) -> None:
        self.state = "gameover"
        self.state_t = 0.0
        self.audio.stop_music()
        save_highscore(self.highscore)

    # ==================================================================
    # 碰撞
    # ==================================================================
    def _collisions(self) -> None:
        # 玩家子彈 → 敵機（穿透彈不消失，並對每個目標套用命中冷卻）
        hits = pygame.sprite.groupcollide(self.enemies, self.player_bullets, False, False)
        for enemy, bullets in hits.items():
            dmg = 0
            for b in bullets:
                if not b.can_hit(enemy):
                    continue
                dmg += b.damage
                if not b.pierce:
                    b.kill()
            if dmg:
                enemy.damage(dmg, self)

        # 玩家子彈 → 頭目
        if self.boss and self.boss.state == "fight":
            box = self.boss.hitbox
            for b in list(self.player_bullets):
                if box.colliderect(b.rect):
                    if not b.can_hit(self.boss):
                        continue
                    if not b.pierce:
                        b.kill()
                    self.boss.damage(b.damage, self)

        p = self.player
        if p is None:
            return

        # 道具
        for item in pygame.sprite.spritecollide(p, self.powerups, True):
            self._apply_powerup(item.kind)

        if p.invulnerable:
            return

        box = p.hitbox
        for b in list(self.enemy_bullets):
            if box.colliderect(b.rect):
                b.kill()
                self._player_hit()
                return

        for en in list(self.enemies):
            if getattr(en, "surface_ship", False):
                continue          # 水面艦艇位於海面，飛越時不會相撞
            if box.colliderect(en.rect.inflate(-6, -6)):
                en.damage(3, self)
                self._player_hit()
                return

        if self.boss and self.boss.state in ("fight", "enter") and box.colliderect(self.boss.hitbox):
            self._player_hit()

    def _apply_powerup(self, kind: str) -> None:
        p = self.player
        if p is None:
            return
        self.audio.play("powerup")
        if kind == "power":
            p.add_power(self)
            self.add_score(500)
        elif kind == "wing":
            p.add_wingman(self)
            self.add_score(500)
        elif kind == "bomb":
            p.bombs = min(4, p.bombs + 1)
            self.add_score(500)
        elif kind == "roll":
            p.rolls = min(9, p.rolls + 2)
            self.add_score(500)
        elif kind == "laser":
            p.set_weapon(self, S.WEAPON_LASER)
            self.add_score(500)
        elif kind == "vulcan":
            p.set_weapon(self, S.WEAPON_VULCAN)
            self.add_score(500)
        elif kind == "life":
            self.lives += 1
            self.audio.play("extend")

    def _player_hit(self) -> None:
        p = self.player
        if p is None:
            return
        self.spawn_explosion(p.rect.center, "big")
        self.audio.play("death")
        self.shake = 0.5
        p.clear_wingmen(self)
        p.kill()
        self.player = None
        self.respawn_timer = 1.6
        if self.lives <= 0:
            self.respawn_timer = 2.2

    # ==================================================================
    # 繪製
    # ==================================================================
    def draw(self) -> None:
        surf = self.play_surf
        if self.state == "title":
            self._draw_title(surf)
        else:
            self.background.draw(surf)
            # 水面艦艇先畫，讓機群飛越其上方
            for sp in self.enemies:
                if getattr(sp, "surface_ship", False):
                    surf.blit(sp.image, sp.rect)
            for group in (self.powerups, self.enemies, self.wingmen,
                          self.enemy_bullets, self.player_bullets):
                for sp in group:
                    if group is self.enemies and getattr(sp, "surface_ship", False):
                        continue
                    surf.blit(sp.image, sp.rect)
            if self.boss:
                surf.blit(self.boss.image, self.boss.rect)
            if self.player:
                if self.player.invuln <= 0 or int(self.player.invuln * 12) % 2 == 0:
                    surf.blit(self.player.image, self.player.rect)
            self.background.draw_clouds(surf)
            for sp in self.effects:
                surf.blit(sp.image, sp.rect)
            self._draw_overlays(surf)

        if not self.has_focus:
            a = self.assets
            self.hud.draw_banner(surf, 150)
            self.hud.draw_center_text(surf, [
                ("NO KEYBOARD FOCUS", a.font, S.YELLOW),
                ("請點擊遊戲視窗", a.font_cjk, S.WHITE),
                ("以繼續操作", a.font_cjk_small, S.SILVER),
            ])

        if self.confirm_quit:
            a = self.assets
            self.hud.draw_banner(surf, 190)
            self.hud.draw_center_text(surf, [
                ("QUIT GAME?", a.font_big, S.RED),
                ("確定要離開遊戲嗎？", a.font_cjk_small, S.WHITE),
                ("", a.font_tiny, S.WHITE),
                ("Y / ENTER  =  離開", a.font_cjk_small, S.YELLOW),
                ("N / ESC  =  取消", a.font_cjk_small, S.SILVER),
            ])

        self.screen.fill(S.BLACK)
        ox = oy = 0
        if self.shake > 0:
            mag = self.shake * 9
            ox = random.uniform(-mag, mag)
            oy = random.uniform(-mag, mag)
        frame = self.frame
        frame.fill(S.BLACK)
        frame.blit(surf, (ox, oy))
        if self.flash > 0:
            veil = pygame.Surface((S.PLAY_W, S.SCREEN_H), pygame.SRCALPHA)
            veil.fill((255, 255, 255, int(200 * self.flash / 0.35)))
            frame.blit(veil, (0, 0))
        self.hud.draw_panel(frame, self)
        self._present()
        pygame.display.flip()

    # ------------------------------------------------------------------
    def frame_viewport(self) -> pygame.Rect:
        """畫格在實際視窗中的位置與大小（等比縮放後置中）。"""
        sw, sh = self.screen.get_size()
        scale = min(sw / S.SCREEN_W, sh / S.SCREEN_H)
        w = max(1, int(S.SCREEN_W * scale))
        h = max(1, int(S.SCREEN_H * scale))
        return pygame.Rect((sw - w) // 2, (sh - h) // 2, w, h)

    def _present(self) -> None:
        """把固定畫格縮放置中貼到實際視窗，避免全螢幕時偏向左上角。"""
        self.screen.fill(S.BLACK)
        vp = self.frame_viewport()
        if vp.size == (S.SCREEN_W, S.SCREEN_H):
            self.screen.blit(self.frame, vp.topleft)
        else:
            self.screen.blit(pygame.transform.smoothscale(self.frame, vp.size), vp.topleft)

    def toggle_fullscreen(self) -> None:
        """切換全螢幕。

        採用「無邊框視窗鋪滿桌面」而非真正的顯示模式切換：
        SDL2 在 Windows 下切換真全螢幕後，行程結束時會發生存取違規，
        無邊框方式外觀相同、切換更快，也沒有這個問題。
        """
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            size = self._desktop_size()
            self.screen = pygame.display.set_mode(size, pygame.NOFRAME)
            self._reposition_window(0, 0)
        else:
            self.screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
            self._reposition_window(None, None)

    @staticmethod
    def _desktop_size() -> tuple[int, int]:
        try:
            sizes = pygame.display.get_desktop_sizes()
            if sizes:
                return sizes[0]
        except (AttributeError, pygame.error):
            pass
        try:
            import ctypes

            user32 = ctypes.windll.user32
            return (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
        except Exception:  # noqa: BLE001
            info = pygame.display.Info()
            return (info.current_w, info.current_h)

    @staticmethod
    def _reposition_window(x: int | None, y: int | None) -> None:
        """把視窗移到指定位置；None 表示置中於桌面。"""
        try:
            import ctypes

            hwnd = pygame.display.get_wm_info().get("window")
            if not hwnd:
                return
            user32 = ctypes.windll.user32
            if x is None or y is None:
                sw = user32.GetSystemMetrics(0)
                sh = user32.GetSystemMetrics(1)
                w, h = pygame.display.get_surface().get_size()
                x = max(0, (sw - w) // 2)
                y = max(0, (sh - h) // 2)
            user32.SetWindowPos(hwnd, 0, int(x), int(y), 0, 0, 0x0001 | 0x0004)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    def _draw_title(self, surf: pygame.Surface) -> None:
        a = self.assets
        self.title_bg.draw(surf)
        for x, y, _ in self.title_planes:
            surf.blit(a.enemies["scout"], a.enemies["scout"].get_rect(center=(x, y)))
        self.title_bg.draw_clouds(surf)
        self.hud.draw_banner(surf, 90)

        plane = pygame.transform.smoothscale(a.player_frames[0][0], (86, 86))
        surf.blit(plane, plane.get_rect(center=(S.PLAY_W // 2, 150)))

        self.hud.draw_center_text(surf, [
            ("SKY STRIKE", a.font_huge, S.YELLOW),
            ("1 9 4 2", a.font_big, S.WHITE),
        ], y0=212)
        self.hud.draw_center_text(surf, [
            (f"HI-SCORE  {self.highscore:07d}", a.font_small, S.CYAN),
        ], y0=330)

        if self.hud.blink(self.state_t):
            self.hud.draw_center_text(surf, [
                ("PRESS  ENTER  TO  START", a.font_small, S.WHITE)], y0=400)

        lines = [
            "ARROWS / WASD / NUMPAD  ..  MOVE",
            "Z / SPACE  ...............  SHOOT",
            "X  .......................  ROLL / EVADE",
            "C  .......................  BOMB",
            "P / ESC  .................  PAUSE",
            "M  .......................  MUTE",
            "F / F11  .................  FULLSCREEN",
            "Q  .......................  QUIT",
        ]
        y = 462
        for line in lines:
            img = a.font_tiny.render(line, True, S.SILVER)
            surf.blit(img, img.get_rect(center=(S.PLAY_W // 2, y)))
            y += 19
        img = a.font_tiny.render(f"{len(STAGES)} STAGES + BOSS BATTLES", True, S.ORANGE)
        surf.blit(img, img.get_rect(center=(S.PLAY_W // 2, y + 14)))

    def _draw_overlays(self, surf: pygame.Surface) -> None:
        a = self.assets
        if self.state == "intro":
            self.hud.draw_banner(surf, 120)
            stage_no = self.stage_index + 1
            extra = f"  LOOP {self.loop_count + 1}" if self.loop_count else ""
            self.hud.draw_center_text(surf, [
                (f"STAGE {stage_no}{extra}", a.font_big, S.YELLOW),
                (self.stage_data["name"], a.font, S.WHITE),
                (self.stage_data["subtitle"], a.font_cjk_small, S.CYAN),
                ("GET READY!", a.font_small, S.ORANGE if self.hud.blink(self.state_t, 3.0)
                 else S.DARK),
            ])
        elif self.state == "boss_alarm":
            if self.hud.blink(self.state_t, 4.0):
                self.hud.draw_center_text(surf, [
                    ("WARNING", a.font_huge, S.RED),
                    ("巨大敵機接近中", a.font_cjk, S.WHITE),
                ], y0=260)
        elif self.state == "boss" and self.boss:
            self.hud.draw_boss_bar(surf, self.boss)
            name = self.stage_data["boss"]["name"]
            img = a.font_cjk_small.render(name, True, S.SILVER)
            surf.blit(img, img.get_rect(midtop=(S.PLAY_W // 2, 28)))
        elif self.state == "clear":
            self.hud.draw_banner(surf, 110)
            self.hud.draw_center_text(surf, [
                ("STAGE CLEAR!", a.font_big, S.YELLOW),
                (f"BONUS  {getattr(self, 'clear_bonus', 0):,}", a.font_small, S.WHITE),
                (f"SCORE  {self.score:07d}", a.font_small, S.CYAN),
            ])
        elif self.state == "gameover":
            self.hud.draw_banner(surf, 150)
            lines = [
                ("GAME OVER", a.font_big, S.RED),
                (f"SCORE  {self.score:07d}", a.font, S.WHITE),
                (f"HI-SCORE  {self.highscore:07d}", a.font_small, S.CYAN),
                (f"REACHED STAGE {self.stage_index + 1}", a.font_small, S.SILVER),
            ]
            if self.state_t > 1.2 and self.hud.blink(self.state_t):
                lines.append(("PRESS ENTER", a.font_small, S.YELLOW))
            self.hud.draw_center_text(surf, lines)
        elif self.state == "allclear":
            self.hud.draw_banner(surf, 210)
            lines = [
                ("ALL STAGES", a.font_big, S.YELLOW),
                ("CLEAR!", a.font_huge, S.ORANGE),
                ("全 關 卡 通 關", a.font_cjk_small, S.WHITE),
                ("", a.font_tiny, S.WHITE),
                (f"ALL CLEAR BONUS  {getattr(self, 'allclear_bonus', 0):,}",
                 a.font_small, S.GREEN),
                (f"FINAL SCORE  {self.score:07d}", a.font, S.WHITE),
                (f"HI-SCORE  {self.highscore:07d}", a.font_small, S.CYAN),
            ]
            if self.state_t > 2.0 and self.hud.blink(self.state_t):
                lines.append(("PRESS ENTER", a.font_small, S.YELLOW))
            self.hud.draw_center_text(surf, lines)

        if self.notice and self.notice_t > 0:
            text, sub = self.notice
            top = 300
            strip = pygame.Surface((S.PLAY_W, 66 if sub else 42), pygame.SRCALPHA)
            strip.fill((0, 0, 0, 165))
            surf.blit(strip, (0, top - 8))
            lines = [(text, a.font, S.YELLOW)]
            if sub:
                lines.append((sub, a.font_cjk_small, S.WHITE))
            self.hud.draw_center_text(surf, lines, y0=top)

        if self.paused:
            self.hud.draw_banner(surf, 140)
            self.hud.draw_center_text(surf, [
                ("PAUSED", a.font_big, S.WHITE),
                ("P / ESC 繼續", a.font_cjk_small, S.SILVER),
            ])

    # ==================================================================
    def _sync_focus(self, dt: float) -> None:
        """把 has_focus 與作業系統的真實鍵盤焦點同步，並在啟動初期主動搶回前景。

        從主控台 / run.bat 啟動時，SDL 視窗可能一直待在主控台後面而拿不到鍵盤
        焦點。以前 has_focus 固定從 True 開始，導致遊戲照跑、按鍵卻全部沒反應，
        而且連「請點擊視窗」的提示都不會出現。
        """
        if not self.track_os_focus:
            return

        self._key_evt_t = max(0.0, self._key_evt_t - dt)
        real = has_keyboard_focus()
        if real:
            self._unfocus_t = 0.0
            self._focus_grab_t = 0.0
            if not self.has_focus:
                self.has_focus = True
                self.held.clear()
                pygame.mouse.set_visible(False)
            return

        # 尚未取得焦點：啟動後 3 秒內每 0.5 秒主動嘗試搶回前景
        if self._focus_grab_t > 0.0:
            self._focus_grab_t -= dt
            self._focus_grab_cd -= dt
            if self._focus_grab_cd <= 0.0:
                self._focus_grab_cd = 0.5
                focus_window()

        # 還在收到真實按鍵事件時，代表 get_focused() 誤判，不要凍結遊戲
        if self._key_evt_t > 0.0:
            self._unfocus_t = 0.0
            return

        self._unfocus_t += dt
        if self._unfocus_t > 0.3 and self.has_focus:
            self.has_focus = False
            self.held.clear()
            pygame.mouse.set_visible(True)

    # ==================================================================
    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(S.FPS) / 1000.0, 1 / 30)
            for e in pygame.event.get():
                self.handle_event(e)
            self._sync_focus(dt)
            self.update(dt)
            self.draw()
        save_highscore(self.highscore)
        # 保險：確保離開主迴圈時不是全螢幕，避免 pygame.quit() 崩潰
        if self.fullscreen:
            self.fullscreen = False
            try:
                self.screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
            except pygame.error:
                pass
