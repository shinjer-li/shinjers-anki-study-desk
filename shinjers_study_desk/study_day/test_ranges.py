"""
Tests for ranges.py (pure Python, no Anki needed). Run:
    python test_ranges.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ranges as r  # noqa: E402


def approx(a, b):
    return abs(a - b) < 1e-9


def test_normal_range():
    # Too few active days -> no range; zero days don't count as active.
    assert r.normal_range([10, 20, 30, 40]) is None
    assert r.normal_range([0, 0, 0, 10, 20, 30, 40]) is None
    assert r.normal_range([]) is None
    assert r.normal_range([1, 2, 3], min_days=3) is not None
    # 10th..90th percentile of the active days, interpolated, order-independent.
    lo, hi = r.normal_range([0, 50, 10, 0, 30, 20, 40, 0])
    assert approx(lo, 14) and approx(hi, 46), (lo, hi)
    lo, hi = r.normal_range(list(range(1, 12)))  # 1..11
    assert approx(lo, 2) and approx(hi, 10), (lo, hi)
    lo, hi = r.normal_range([7] * 6)
    assert lo == hi == 7
    print("normal_range ok")


def test_flag():
    rng = (10.0, 20.0)
    assert r.flag(25, rng) == "H"
    assert r.flag(5, rng) == "L"
    assert r.flag(15, rng) == ""
    assert r.flag(10, rng) == "" and r.flag(20, rng) == ""  # bounds are normal
    assert r.flag(5, rng, partial=True) == ""  # today's total is still growing
    assert r.flag(25, rng, partial=True) == "H"
    assert r.flag(1000, None) == ""
    print("flag ok")


def test_scale():
    assert r.scale(None, 2) is None
    assert r.scale((10.0, 20.0), 0.5) == (5.0, 10.0)
    assert r.scale((10.0, 20.0), 1) == (10.0, 20.0)
    print("scale ok")


if __name__ == "__main__":
    test_normal_range()
    test_flag()
    test_scale()
    print("ALL OK")
