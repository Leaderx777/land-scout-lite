# Ensure repo root is on sys.path so "import land_scout" works even if pytest rootdir shifts.
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
