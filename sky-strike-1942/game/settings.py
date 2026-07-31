"""全域設定常數。"""

from __future__ import annotations

# --- 視窗 ---
SCREEN_W = 480
SCREEN_H = 720
FPS = 60
TITLE = "Sky Strike 1942"

# --- 遊戲區域（右側保留 HUD 欄）---
HUD_W = 120
PLAY_W = SCREEN_W - HUD_W
PLAY_RECT = (0, 0, PLAY_W, SCREEN_H)

# --- 玩家 ---
PLAYER_SPEED = 260.0          # px / 秒
PLAYER_START_LIVES = 3
PLAYER_START_LOOPS = 3        # 每條命的翻滾迴避次數
PLAYER_RESPAWN_INVULN = 2.5   # 復活無敵秒數
PLAYER_LOOP_TIME = 0.9        # 翻滾持續秒數（期間無敵）
PLAYER_FIRE_COOLDOWN = 0.14
PLAYER_HITBOX = (10, 10)      # 判定框比外觀小，較好操作

# --- 子彈 ---
PLAYER_BULLET_SPEED = 620.0
ENEMY_BULLET_SPEED = 210.0

# --- 火力等級 ---
MAX_POWER = 4

# --- 分數 ---
EXTEND_SCORE = 30000          # 每達此分數加一命

# --- 顏色 ---
WHITE = (245, 245, 245)
BLACK = (10, 10, 14)
GREY = (120, 128, 140)
DARK = (28, 30, 38)
RED = (222, 66, 58)
DEEP_RED = (150, 32, 30)
ORANGE = (245, 150, 46)
YELLOW = (250, 216, 84)
GREEN = (86, 190, 96)
CYAN = (110, 214, 224)
BLUE = (70, 118, 208)
NAVY = (34, 52, 104)
SILVER = (196, 202, 212)
STEEL = (128, 140, 158)
BROWN = (138, 104, 66)
SAND = (216, 190, 138)
PURPLE = (150, 96, 200)

HIGHSCORE_FILE = "highscore.txt"
