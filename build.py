"""
Package each add-on folder into dist/<name>.ankiaddon (double-click to install).

    python addons/build.py              # all add-ons
    python addons/build.py shinjers_study_desk
"""

import fnmatch
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
SKIP_DIRS = {"__pycache__", "dist"}
SKIP_FILES = ["test_*.py", "*.pyc", "history-*.json", "*.tmp", "meta.json", ".*"]


def addons() -> list[str]:
    return sorted(
        d for d in os.listdir(HERE)
        if os.path.isfile(os.path.join(HERE, d, "manifest.json"))
    )


def build(name: str) -> str:
    src = os.path.join(HERE, name)
    out = os.path.join(DIST, f"{name}.ankiaddon")
    os.makedirs(DIST, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for f in sorted(files):
                if any(fnmatch.fnmatch(f, p) for p in SKIP_FILES):
                    continue
                path = os.path.join(root, f)
                z.write(path, os.path.relpath(path, src))
    return out


if __name__ == "__main__":
    for name in sys.argv[1:] or addons():
        out = build(name)
        with zipfile.ZipFile(out) as z:
            print(f"{os.path.relpath(out, HERE)}: {', '.join(z.namelist())}")
