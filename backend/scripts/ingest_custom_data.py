"""
Custom Data Ingest Script for OceanEmbed Viewer
===============================================
Use this script to directly feed pre-existing model predictions or NetCDF datasets
into the OceanEmbed Viewer Zarr store without running the synthetic simulation.

Supports:
1. NetCDF files (.nc) with variable 'thetao'
2. NumPy arrays (.npy or .npz) of shape (time, depth, lat, lon)
3. Direct conversion to backend/data/reconstruction.zarr

Usage:
    python scripts/ingest_custom_data.py --netcdf path/to/predictions.nc
    python scripts/ingest_custom_data.py --numpy path/to/array.npy --dates-file dates.txt
"""

import os
import sys
import argparse
import numpy as np
import zarr
import xarray as xr

# Add backend directory to sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from model_bridge import LATS, LONS, DEPTHS_M
from data_store import get_zarr_path


def ingest_from_netcdf(nc_path: str, var_name: str = "thetao"):
    """
    Read NetCDF dataset and save as data/reconstruction.zarr.
    """
    print(f"Reading NetCDF file from: {nc_path}")
    ds = xr.open_dataset(nc_path)

    if var_name not in ds:
        raise ValueError(f"Variable '{var_name}' not found in NetCDF. Available: {list(ds.data_vars)}")

    zarr_path = get_zarr_path()
    os.makedirs(os.path.dirname(zarr_path), exist_ok=True)

    # Standardize dimensions and save to Zarr
    print(f"Writing to Zarr store at: {zarr_path}...")
    ds[[var_name]].to_zarr(zarr_path, mode="w")
    print("Ingestion complete! Restart or refresh the dashboard to see your data.")


def ingest_from_numpy(npy_path: str, dates: list):
    """
    Ingest 4D NumPy array of shape (time, 15, 101, 241) into data/reconstruction.zarr.
    """
    print(f"Loading NumPy array from: {npy_path}")
    data = np.load(npy_path)

    if data.ndim != 4:
        raise ValueError(f"Expected 4D array (time, depth, lat, lon), got shape: {data.shape}")

    num_time, num_depth, num_lat, num_lon = data.shape
    assert num_depth == len(DEPTHS_M), f"Expected {len(DEPTHS_M)} depths, got {num_depth}"
    assert num_lat == len(LATS), f"Expected {len(LATS)} lats, got {num_lat}"
    assert num_lon == len(LONS), f"Expected {len(LONS)} lons, got {num_lon}"

    zarr_path = get_zarr_path()
    root = zarr.open_group(zarr_path, mode="w")
    root.attrs["dates"] = dates
    root.attrs["depths_m"] = DEPTHS_M
    root.attrs["lats"] = [float(x) for x in LATS]
    root.attrs["lons"] = [float(x) for x in LONS]
    root.attrs["variable"] = "thetao"
    root.attrs["units"] = "degC"

    arr = root.create_array(
        "thetao",
        shape=data.shape,
        chunks=(1, 1, num_lat, num_lon),
        dtype="float32",
        fill_value=np.nan,
    )
    arr[:] = data.astype(np.float32)
    print(f"Successfully saved {num_time} time steps to {zarr_path}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest custom model predictions into OceanEmbed Viewer")
    parser.add_argument("--netcdf", help="Path to input NetCDF (.nc) file")
    parser.add_argument("--numpy", help="Path to input NumPy (.npy) file")
    parser.add_argument("--var", default="thetao", help="Variable name in NetCDF file (default: thetao)")
    args = parser.parse_args()

    if args.netcdf:
        ingest_from_netcdf(args.netcdf, var_name=args.var)
    else:
        print("Please provide --netcdf <path> or --numpy <path>. Run with --help for details.")
