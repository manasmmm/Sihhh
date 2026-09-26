"""
Check a model output file before dropping it into backend/data/model_output/.

    python scripts/check_model_output.py backend/data/model_output/thetao_2026-09-25.nc

Runs exactly the same validation as the dashboard backend and prints "OK"
(plus any warnings) or the list of problems. Exit code 0 = valid, 1 = invalid.
"""
import argparse
import os
import sys

BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BACKEND_DIR)

from model_output_validation import validate_file  # noqa: E402
from model_bridge import get_land_mask  # noqa: E402


def check_file(path: str) -> bool:
    res = validate_file(path, land_mask=get_land_mask())
    print(f"Checking {path} ...")
    for w in res.warnings:
        print(f"  warning: {w}")
    if res.valid:
        print("OK")
        return True
    print("Problems found:")
    for e in res.errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check model output file validity.")
    parser.add_argument("files", nargs="+", help="Path(s) to thetao_YYYY-MM-DD.nc or .npy")
    args = parser.parse_args()
    ok = all([check_file(f) for f in args.files])
    sys.exit(0 if ok else 1)
