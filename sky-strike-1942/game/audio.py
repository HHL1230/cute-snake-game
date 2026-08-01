"""程式合成的音效與背景音樂（不需外部素材檔）。

以純 Python 產生 16-bit 單聲道 PCM，再交給 ``pygame.mixer.Sound(buffer=...)``。
"""

from __future__ import annotations

import math
import random
from array import array

import pygame

SAMPLE_RATE = 22050
MAX_AMP = 28000


def _pcm(buf: array, channels: int) -> bytes:
    """依 mixer 實際聲道數輸出 PCM（單聲道資料必要時複製成立體聲）。"""
    if channels <= 1:
        return buf.tobytes()
    out = array("h", bytes(4 * len(buf)))
    out[0::2] = buf
    out[1::2] = buf
    return out.tobytes()


# --------------------------------------------------------------------------
# 基本波形
# --------------------------------------------------------------------------
def _blank(n: int) -> array:
    return array("h", bytes(2 * n))


def _env(i: int, n: int, attack: float, release: float) -> float:
    """簡易 attack / release 包絡（0.0 ~ 1.0）。"""
    a = max(1, int(n * attack))
    r = max(1, int(n * release))
    if i < a:
        return i / a
    if i > n - r:
        return max(0.0, (n - i) / r)
    return 1.0


def _tone(freq0: float, freq1: float, dur: float, vol: float,
          wave: str = "square", attack: float = 0.02, release: float = 0.3) -> array:
    n = max(1, int(SAMPLE_RATE * dur))
    buf = _blank(n)
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = freq0 + (freq1 - freq0) * t
        phase += freq / SAMPLE_RATE
        p = phase % 1.0
        if wave == "square":
            s = 1.0 if p < 0.5 else -1.0
        elif wave == "pulse":
            s = 1.0 if p < 0.25 else -1.0
        elif wave == "saw":
            s = 2.0 * p - 1.0
        elif wave == "tri":
            s = 4.0 * abs(p - 0.5) - 1.0
        else:
            s = math.sin(p * math.tau)
        buf[i] = int(s * vol * MAX_AMP * _env(i, n, attack, release))
    return buf


def _noise(dur: float, vol: float, decay: float = 3.0, low: float = 0.0) -> array:
    n = max(1, int(SAMPLE_RATE * dur))
    buf = _blank(n)
    rnd = random.Random(1234)
    last = 0.0
    for i in range(n):
        raw = rnd.uniform(-1.0, 1.0)
        # 一階低通，讓爆炸聲較低沉
        last = last + (raw - last) * (1.0 - low)
        amp = math.exp(-decay * i / n)
        buf[i] = int(max(-1.0, min(1.0, last)) * vol * MAX_AMP * amp)
    return buf


def _mix(*parts: array) -> array:
    n = max((len(p) for p in parts), default=0)
    out = _blank(n)
    for p in parts:
        for i, v in enumerate(p):
            s = out[i] + v
            out[i] = 32767 if s > 32767 else -32768 if s < -32768 else s
    return out


def _concat(*parts: array) -> array:
    out = array("h")
    for p in parts:
        out.extend(p)
    return out


def _midi_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


# --------------------------------------------------------------------------
# 音效庫
# --------------------------------------------------------------------------
class Audio:
    """統一管理音效與音樂；mixer 不可用時所有呼叫都會安全地忽略。"""

    def __init__(self) -> None:
        init = pygame.mixer.get_init()
        self.enabled = init is not None
        self.channels = 1
        if init:
            global SAMPLE_RATE
            SAMPLE_RATE = init[0]
            self.channels = abs(init[2])
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self._music_cache: dict[str, pygame.mixer.Sound] = {}
        self._music_channel: pygame.mixer.Channel | None = None
        self._current_music: str | None = None
        self.muted = False
        if self.enabled:
            self._build_sounds()
            pygame.mixer.set_num_channels(24)
            self._music_channel = pygame.mixer.Channel(0)

    # -- 建立音效 ------------------------------------------------------
    def _snd(self, buf: array, volume: float = 1.0) -> pygame.mixer.Sound:
        s = pygame.mixer.Sound(buffer=_pcm(buf, self.channels))
        s.set_volume(volume)
        return s

    def _build_sounds(self) -> None:
        self.sounds["shoot"] = self._snd(
            _tone(1050, 640, 0.07, 0.30, "pulse", 0.01, 0.6), 0.28)
        self.sounds["laser"] = self._snd(
            _mix(_tone(1750, 900, 0.12, 0.26, "sine", 0.005, 0.55),
                 _tone(880, 440, 0.12, 0.16, "saw", 0.005, 0.55)), 0.26)
        self.sounds["enemy_shoot"] = self._snd(
            _tone(420, 250, 0.09, 0.25, "square", 0.01, 0.6), 0.22)
        self.sounds["hit"] = self._snd(
            _noise(0.06, 0.35, decay=6.0, low=0.4), 0.35)
        self.sounds["explode"] = self._snd(
            _mix(_noise(0.35, 0.55, decay=4.0, low=0.55),
                 _tone(180, 60, 0.35, 0.25, "tri", 0.01, 0.8)), 0.45)
        self.sounds["big_explode"] = self._snd(
            _mix(_noise(0.95, 0.7, decay=2.4, low=0.72),
                 _tone(140, 40, 0.95, 0.35, "saw", 0.01, 0.9)), 0.6)
        self.sounds["powerup"] = self._snd(
            _concat(_tone(660, 660, 0.06, 0.28, "square", 0.01, 0.3),
                    _tone(880, 880, 0.06, 0.28, "square", 0.01, 0.3),
                    _tone(1320, 1320, 0.12, 0.28, "square", 0.01, 0.5)), 0.4)
        self.sounds["roll"] = self._snd(
            _mix(_noise(0.55, 0.30, decay=1.2, low=0.25),
                 _tone(300, 1200, 0.55, 0.20, "sine", 0.05, 0.5)), 0.35)
        self.sounds["death"] = self._snd(
            _mix(_noise(1.2, 0.6, decay=2.0, low=0.6),
                 _tone(520, 60, 1.2, 0.35, "saw", 0.01, 0.7)), 0.55)
        self.sounds["extend"] = self._snd(
            _concat(_tone(784, 784, 0.09, 0.3, "square", 0.01, 0.2),
                    _tone(988, 988, 0.09, 0.3, "square", 0.01, 0.2),
                    _tone(1175, 1175, 0.09, 0.3, "square", 0.01, 0.2),
                    _tone(1568, 1568, 0.22, 0.3, "square", 0.01, 0.5)), 0.45)
        self.sounds["menu"] = self._snd(
            _tone(880, 880, 0.05, 0.25, "square", 0.01, 0.4), 0.3)
        self.sounds["start"] = self._snd(
            _concat(_tone(523, 523, 0.10, 0.3, "pulse", 0.01, 0.3),
                    _tone(659, 659, 0.10, 0.3, "pulse", 0.01, 0.3),
                    _tone(1047, 1047, 0.26, 0.3, "pulse", 0.01, 0.5)), 0.45)
        self.sounds["alarm"] = self._snd(
            _concat(_tone(500, 900, 0.28, 0.30, "square", 0.02, 0.2),
                    _tone(500, 900, 0.28, 0.30, "square", 0.02, 0.4)), 0.4)
        self.sounds["clear"] = self._snd(
            _concat(_tone(523, 523, 0.13, 0.3, "tri", 0.01, 0.2),
                    _tone(659, 659, 0.13, 0.3, "tri", 0.01, 0.2),
                    _tone(784, 784, 0.13, 0.3, "tri", 0.01, 0.2),
                    _tone(1047, 1047, 0.40, 0.3, "tri", 0.01, 0.5)), 0.5)

    def play(self, name: str) -> None:
        if not self.enabled or self.muted:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            snd.play()

    # -- 背景音樂 ------------------------------------------------------
    def _render_music(self, key: str) -> pygame.mixer.Sound:
        spec = MUSIC[key]
        bpm = spec["bpm"]
        beat = 60.0 / bpm
        total_beats = spec["beats"]
        n = int(SAMPLE_RATE * beat * total_beats)
        master = _blank(n)

        def stamp(buf: array, at_beat: float) -> None:
            start = int(SAMPLE_RATE * beat * at_beat)
            for i, v in enumerate(buf):
                j = start + i
                if 0 <= j < n:
                    s = master[j] + v
                    master[j] = 32767 if s > 32767 else -32768 if s < -32768 else s

        for track in spec["tracks"]:
            wave = track["wave"]
            vol = track["vol"]
            step = track.get("step", 1.0)
            length = track.get("length", 0.9)
            for idx, note in enumerate(track["notes"]):
                if note is None:
                    continue
                at = idx * step
                if at >= total_beats:
                    break
                if note == "x":  # 打擊樂
                    stamp(_noise(beat * step * length, vol, decay=8.0, low=0.5), at)
                elif note == "b":  # 大鼓
                    stamp(_tone(150, 45, beat * step * length, vol, "sine", 0.01, 0.6), at)
                else:
                    f = _midi_freq(int(note))
                    stamp(_tone(f, f, beat * step * length, vol, wave, 0.02, 0.35), at)

        snd = pygame.mixer.Sound(buffer=_pcm(master, self.channels))
        snd.set_volume(0.34)
        return snd

    def play_music(self, key: str) -> None:
        if not self.enabled or self._music_channel is None:
            return
        if self._current_music == key and self._music_channel.get_busy():
            return
        self._current_music = key
        if self.muted:
            self._music_channel.stop()
            return
        if key not in self._music_cache:
            self._music_cache[key] = self._render_music(key)
        self._music_channel.play(self._music_cache[key], loops=-1)

    def stop_music(self) -> None:
        self._current_music = None
        if self._music_channel is not None:
            self._music_channel.stop()

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        if self._music_channel is not None:
            if self.muted:
                self._music_channel.stop()
            elif self._current_music:
                key, self._current_music = self._current_music, None
                self.play_music(key)
        return self.muted


# --------------------------------------------------------------------------
# 音樂資料（八分音符為單位的簡易 chiptune）
# --------------------------------------------------------------------------
def _rep(seq: list, times: int) -> list:
    out: list = []
    for _ in range(times):
        out.extend(seq)
    return out


_DRUM = _rep(["b", None, "x", None, "b", "b", "x", None], 8)

MUSIC: dict[str, dict] = {
    "title": {
        "bpm": 112, "beats": 32,
        "tracks": [
            {"wave": "pulse", "vol": 0.20, "step": 0.5, "length": 0.85,
             "notes": _rep([69, 72, 76, 72, 77, 76, 72, 69,
                            67, 71, 74, 71, 76, 74, 71, 67], 4)},
            {"wave": "tri", "vol": 0.26, "step": 1.0, "length": 0.9,
             "notes": _rep([45, 45, 52, 45, 43, 43, 50, 43], 4)},
        ],
    },
    "stage1": {
        "bpm": 132, "beats": 32,
        "tracks": [
            {"wave": "square", "vol": 0.17, "step": 0.5, "length": 0.8,
             "notes": _rep([64, 67, 71, 74, 71, 67, 64, 67,
                            62, 65, 69, 72, 69, 65, 62, 65], 4)},
            {"wave": "tri", "vol": 0.28, "step": 0.5, "length": 0.6,
             "notes": _rep([40, 40, 47, 40, 38, 38, 45, 38], 8)},
            {"wave": "noise", "vol": 0.14, "step": 0.5, "length": 0.35,
             "notes": _DRUM},
        ],
    },
    "stage2": {
        "bpm": 140, "beats": 32,
        "tracks": [
            {"wave": "pulse", "vol": 0.17, "step": 0.5, "length": 0.8,
             "notes": _rep([69, 76, 74, 72, 74, 72, 69, 67,
                            67, 74, 72, 71, 72, 71, 67, 64], 4)},
            {"wave": "saw", "vol": 0.22, "step": 0.5, "length": 0.6,
             "notes": _rep([45, 45, 45, 52, 43, 43, 43, 50], 8)},
            {"wave": "noise", "vol": 0.14, "step": 0.5, "length": 0.35,
             "notes": _DRUM},
        ],
    },
    "stage3": {
        "bpm": 146, "beats": 32,
        "tracks": [
            {"wave": "square", "vol": 0.17, "step": 0.5, "length": 0.75,
             "notes": _rep([72, 71, 69, 71, 72, 74, 76, 74,
                            67, 69, 71, 69, 67, 65, 64, 65], 4)},
            {"wave": "tri", "vol": 0.26, "step": 0.5, "length": 0.55,
             "notes": _rep([36, 36, 43, 36, 41, 41, 48, 41], 8)},
            {"wave": "noise", "vol": 0.15, "step": 0.5, "length": 0.35,
             "notes": _DRUM},
        ],
    },
    "stage4": {
        "bpm": 152, "beats": 32,
        "tracks": [
            {"wave": "pulse", "vol": 0.18, "step": 0.5, "length": 0.7,
             "notes": _rep([76, 75, 76, 71, 74, 72, 69, 72,
                            74, 72, 71, 69, 67, 69, 71, 74], 4)},
            {"wave": "saw", "vol": 0.24, "step": 0.5, "length": 0.5,
             "notes": _rep([38, 38, 38, 38, 37, 37, 36, 36], 8)},
            {"wave": "noise", "vol": 0.16, "step": 0.5, "length": 0.35,
             "notes": _DRUM},
        ],
    },
    "stage5": {
        "bpm": 158, "beats": 32,
        "tracks": [
            {"wave": "square", "vol": 0.18, "step": 0.5, "length": 0.7,
             "notes": _rep([71, 74, 76, 79, 78, 76, 74, 71,
                            69, 72, 74, 77, 76, 74, 72, 69], 4)},
            {"wave": "saw", "vol": 0.25, "step": 0.5, "length": 0.5,
             "notes": _rep([35, 35, 42, 35, 33, 33, 40, 33], 8)},
            {"wave": "noise", "vol": 0.16, "step": 0.5, "length": 0.35,
             "notes": _DRUM},
        ],
    },
    "stage6": {
        "bpm": 164, "beats": 32,
        "tracks": [
            {"wave": "pulse", "vol": 0.18, "step": 0.5, "length": 0.65,
             "notes": _rep([68, 71, 73, 68, 76, 73, 71, 68,
                            66, 69, 71, 66, 74, 71, 69, 66], 4)},
            {"wave": "saw", "vol": 0.26, "step": 0.25, "length": 0.4,
             "notes": _rep([32, 32, 39, 32, 32, 39, 32, 44], 16)},
            {"wave": "noise", "vol": 0.17, "step": 0.5, "length": 0.32,
             "notes": _DRUM},
        ],
    },
    "stage7": {
        "bpm": 172, "beats": 32,
        "tracks": [
            {"wave": "square", "vol": 0.19, "step": 0.25, "length": 0.6,
             "notes": _rep([76, 79, 81, 79, 76, 74, 72, 74,
                            77, 81, 84, 81, 77, 76, 74, 72], 8)},
            {"wave": "saw", "vol": 0.27, "step": 0.5, "length": 0.45,
             "notes": _rep([33, 33, 33, 40, 31, 31, 31, 38], 8)},
            {"wave": "tri", "vol": 0.20, "step": 1.0, "length": 0.9,
             "notes": _rep([57, 60, 64, 60, 55, 59, 62, 59], 4)},
            {"wave": "noise", "vol": 0.17, "step": 0.25, "length": 0.30,
             "notes": _rep(["b", "x", "x", "x"], 32)},
        ],
    },
    "boss": {
        "bpm": 160, "beats": 32,
        "tracks": [
            {"wave": "square", "vol": 0.19, "step": 0.25, "length": 0.7,
             "notes": _rep([64, 64, 65, 64, 63, 64, 65, 67,
                            64, 64, 65, 64, 70, 69, 67, 65], 8)},
            {"wave": "saw", "vol": 0.26, "step": 0.5, "length": 0.5,
             "notes": _rep([36, 36, 37, 36, 35, 35, 36, 37], 8)},
            {"wave": "noise", "vol": 0.17, "step": 0.25, "length": 0.3,
             "notes": _rep(["b", "x", "x", "x"], 32)},
        ],
    },
}
