"""
"Your range": what a normal day looks like for you, like the reference range
on a lab report. It's the middle 80% (10th to 90th percentile) of the days you
actually studied. A value above it is flagged H, below it L.

Pure Python, so it can be tested without Anki.
"""

from __future__ import annotations

MIN_DAYS = 5  # fewer study days than this and there's no range yet


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    pos = (len(sorted_values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def normal_range(values: list[float], min_days: int = MIN_DAYS) -> tuple[float, float] | None:
    """(low, high) from the days with any activity, or None if too few."""
    active = sorted(v for v in values if v > 0)
    if len(active) < min_days:
        return None
    return percentile(active, 0.1), percentile(active, 0.9)


def flag(value: float, rng: tuple[float, float] | None, partial: bool = False) -> str:
    """"H", "L" or "". `partial` is for today's running totals, which are
    only low because the day isn't over, so they're never flagged L."""
    if rng is None:
        return ""
    lo, hi = rng
    if value > hi:
        return "H"
    if value < lo and not partial:
        return "L"
    return ""


def scale(rng: tuple[float, float] | None, factor: float) -> tuple[float, float] | None:
    return None if rng is None else (rng[0] * factor, rng[1] * factor)
