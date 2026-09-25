"""
Precompute Script for OceanEmbed Viewer
=======================================
Precomputes daily 3D subsurface ocean temperature fields using the model bridge
and writes them to data/reconstruction.zarr.

Usage:
    python scripts/precompute.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--force]
"""

import os
import sys
import argparse
import shutil
from datetime import datetime, timedelta
import numpy as np
import zarr

# Add backend directory to sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from model_bridge import reconstruct_field, LATS, LONS, DEPTHS_M
from data_store import get_zarr_path


def generate_date_range(start_date: str, end_date: str) -> list:
    """Generate list of ISO date strings from start_date to end_date inclusive."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    curr = start
    while curr <= end:
        dates.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return dates


def precompute_dataset(
    start_date: str = "2025-01-01",
    end_date: str = "2025-04-30",
    force: bool = False,
):
    """
    Generate and save precomputed Zarr dataset.
    """
    zarr_path = get_zarr_path()
    os.makedirs(os.path.dirname(zarr_path), exist_ok=True)

    if os.path.exists(zarr_path):
        if not force:
            print(f"Zarr store already exists at {zarr_path}.")
            print("Use --force to overwrite. Exiting.")
            return
        print(f"Overwriting existing Zarr store at {zarr_path}...")
        shutil.rmtree(zarr_path, ignore_errors=True)

    dates = generate_date_range(start_date, end_date)
    num_dates = len(dates)
    num_depths = len(DEPTHS_M)
    num_lats = len(LATS)
    num_lons = len(LONS)

    print("=" * 60)
    print("OceanEmbed Viewer - Precomputing Reconstruction Store")
    print(f"Date Range: {start_date} to {end_date} ({num_dates} days)")
    print(f"Grid: {num_lats} lats x {num_lons} lons x {num_depths} depth levels")
    print(f"Target Zarr store: {zarr_path}")
    print("=" * 60)

    # Initialize Zarr Group
    root = zarr.open_group(zarr_path, mode="w")

    # Store domain metadata as attributes
    root.attrs["dates"] = dates
    root.attrs["depths_m"] = DEPTHS_M
    root.attrs["lats"] = [float(x) for x in LATS]
    root.attrs["lons"] = [float(x) for x in LONS]
    root.attrs["variable"] = "thetao"
    root.attrs["units"] = "degC"
    root.attrs["created_at"] = datetime.utcnow().isoformat()

    # Create 4D array: (time, depth, lat, lon)
    # Chunks: 1 time step, 1 depth level, full spatial slice (101, 241) for optimal 2D rendering speed
    thetao_arr = root.create_array(
        "thetao",
        shape=(num_dates, num_depths, num_lats, num_lons),
        chunks=(1, 1, num_lats, num_lons),
        dtype="float32",
        fill_value=np.nan,
    )

    t0 = datetime.now()
    for idx, d_str in enumerate(dates):
        field_3d = reconstruct_field(d_str) # shape: (15, 101, 241)
        thetao_arr[idx] = field_3d

        if (idx + 1) % 15 == 0 or (idx + 1) == num_dates:
            pct = ((idx + 1) / num_dates) * 100
            elapsed = (datetime.now() - t0).total_seconds()
            print(f"[{idx + 1:3d}/{num_dates}] ({pct:5.1f}%) Processed date: {d_str} (Elapsed: {elapsed:.1f}s)")

    print("-" * 60)
    print("Precomputation complete!")
    print(f"Final store shape: {thetao_arr.shape}")
    print(f"Store size on disk: {os.path.getsize(zarr_path) if os.path.isfile(zarr_path) else 'directory store'}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Precompute OceanEmbed reconstruction store")
    parser.add_argument("--start", default="2025-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-04-30", help="End date (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing store")
    args = parser.parse_args()

    precompute_dataset(start_date=args.start, end_date=args.end, force=args.force)
