"""小工具函式。"""

from __future__ import annotations

import math
import os
from pathlib import Path

from . import settings


def clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def angle_to_vector(degrees: float) -> tuple[float, float]:
    """0 度朝下（螢幕正下方），順時針為正。"""
    rad = math.radians(degrees)
    return math.sin(rad), math.cos(rad)


def vector_to(src: tuple[float, float], dst: tuple[float, float]) -> tuple[float, float]:
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    dist = math.hypot(dx, dy) or 1.0
    return dx / dist, dy / dist


def _highscore_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home()) / "SkyStrike1942"
    base.mkdir(parents=True, exist_ok=True)
    return base / settings.HIGHSCORE_FILE


def load_highscore() -> int:
    try:
        return int(_highscore_path().read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def save_highscore(score: int) -> None:
    try:
        _highscore_path().write_text(str(int(score)), encoding="utf-8")
    except OSError:
        pass
