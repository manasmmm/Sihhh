"""
Data Store for OceanEmbed Viewer
================================
Manages persistent multi-dimensional ocean temperature fields in Zarr format.
Provides fast point queries, vertical profiles, time-series, and 2D spatial slices.
"""

import os
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import zarr

from model_bridge import LATS, LONS, DEPTHS_M, get_land_mask

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ZARR_PATH = os.path.join(DATA_DIR, "reconstruction.zarr")

_STORE_HANDLE: Optional[zarr.Group] = None


def get_zarr_path() -> str:
    """Return path to Zarr reconstruction store."""
    return ZARR_PATH


def is_store_initialized() -> bool:
    """Check if precomputed Zarr store exists on disk."""
    return os.path.exists(ZARR_PATH)


def get_store(mode: str = "r") -> zarr.Group:
    """Get or cache open Zarr store handle."""
    global _STORE_HANDLE
    if mode == "r" and _STORE_HANDLE is not None:
        return _STORE_HANDLE

    if not os.path.exists(ZARR_PATH):
        raise FileNotFoundError(
            f"Zarr store not found at {ZARR_PATH}. Please run scripts/precompute.py first."
        )

    store = zarr.open_group(ZARR_PATH, mode=mode)
    if mode == "r":
        _STORE_HANDLE = store
    return store


def get_dates() -> List[str]:
    """Retrieve list of precomputed dates from Zarr metadata."""
    store = get_store("r")
    return list(store.attrs.get("dates", []))


def get_metadata() -> Dict[str, Any]:
    """Return complete metadata dictionary for frontend initialization."""
    dates = get_dates()
    start_date = dates[0] if dates else "2025-01-01"
    end_date = dates[-1] if dates else "2025-04-30"

    return {
        "domain": {
            "lat_min": float(LATS[0]),
            "lat_max": float(LATS[-1]),
            "lon_min": float(LONS[0]),
            "lon_max": float(LONS[-1]),
            "resolution_deg": 0.25,
        },
        "grid_shape": {
            "lat": len(LATS),
            "lon": len(LONS),
        },
        "depths_m": DEPTHS_M,
        "dates": {
            "start": start_date,
            "end": end_date,
            "count": len(dates),
            "all_dates": dates,
        },
        "variable": {
            "name": "thetao",
            "long_name": "Sea water potential temperature",
            "units": "degC",
            "colorbar_range": [0, 32],
        },
        "model_info": {
            "architecture": "OceanEmbed-GNN-OAM",
            "resolution": "0.25 deg x 15 depth levels",
            "region": "North Indian Ocean (5°N-30°N, 45°E-105°E)",
        },
    }


def snap_to_grid(lat: float, lon: float) -> Tuple[int, int, float, float, bool]:
    """
    Snap arbitrary latitude/longitude to the nearest grid cell.

    Returns
    -------
    Tuple[int, int, float, float, bool]
        lat_idx, lon_idx, snapped_lat, snapped_lon, is_land
    """
    lat_idx = int(np.argmin(np.abs(LATS - lat)))
    lon_idx = int(np.argmin(np.abs(LONS - lon)))

    snapped_lat = float(LATS[lat_idx])
    snapped_lon = float(LONS[lon_idx])

    land_mask = get_land_mask()
    is_land = bool(land_mask[lat_idx, lon_idx])

    return lat_idx, lon_idx, snapped_lat, snapped_lon, is_land


def get_field_slice(date: str, depth: int) -> np.ndarray:
    """
    Retrieve 2D temperature slice for a given date and depth.

    Returns
    -------
    np.ndarray
        Array of shape (101, 241) with NaN over land.
    """
    store = get_store("r")
    dates = get_dates()
    if date not in dates:
        # Fallback to closest available date
        date = dates[0]

    time_idx = dates.index(date)

    if depth not in DEPTHS_M:
        # Snap to closest depth
        depth_idx = int(np.argmin(np.abs(np.array(DEPTHS_M) - depth)))
    else:
        depth_idx = DEPTHS_M.index(depth)

    arr = store["thetao"]
    return np.array(arr[time_idx, depth_idx, :, :], dtype=np.float32)


def get_profile(lat: float, lon: float, date: str) -> Dict[str, Any]:
    """
    Extract vertical temperature profile at the snapped ocean grid cell for date.
    """
    lat_idx, lon_idx, snapped_lat, snapped_lon, is_land = snap_to_grid(lat, lon)

    if is_land:
        return {
            "error": "land_cell",
            "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        }

    store = get_store("r")
    dates = get_dates()
    if date not in dates:
        date = dates[0]
    time_idx = dates.index(date)

    arr = store["thetao"]
    profile_vals = arr[time_idx, :, lat_idx, lon_idx]

    # If all values are NaN, treat as land
    if np.all(np.isnan(profile_vals)):
        return {
            "error": "land_cell",
            "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        }

    temp_list = [round(float(v), 2) if not np.isnan(v) else None for v in profile_vals]
    valid_vals = [v for v in profile_vals if not np.isnan(v)]

    return {
        "requested": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        "date": date,
        "depths_m": DEPTHS_M,
        "temperature_c": temp_list,
        "stats": {
            "min": round(float(np.min(valid_vals)), 1) if valid_vals else None,
            "max": round(float(np.max(valid_vals)), 1) if valid_vals else None,
        },
    }


def get_timeseries(lat: float, lon: float, depth: int) -> Dict[str, Any]:
    """
    Extract full time-series of temperature at the snapped ocean grid cell and depth.
    """
    lat_idx, lon_idx, snapped_lat, snapped_lon, is_land = snap_to_grid(lat, lon)

    if is_land:
        return {
            "error": "land_cell",
            "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        }

    if depth not in DEPTHS_M:
        depth_idx = int(np.argmin(np.abs(np.array(DEPTHS_M) - depth)))
        depth = DEPTHS_M[depth_idx]
    else:
        depth_idx = DEPTHS_M.index(depth)

    store = get_store("r")
    dates = get_dates()
    arr = store["thetao"]

    ts_vals = arr[:, depth_idx, lat_idx, lon_idx]

    if np.all(np.isnan(ts_vals)):
        return {
            "error": "land_cell",
            "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        }

    temp_list = [round(float(v), 2) if not np.isnan(v) else None for v in ts_vals]
    valid_vals = [v for v in ts_vals if not np.isnan(v)]

    return {
        "requested": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        "depth": depth,
        "dates": dates,
        "temperature_c": temp_list,
        "stats": {
            "min": round(float(np.min(valid_vals)), 1) if valid_vals else None,
            "median": round(float(np.median(valid_vals)), 1) if valid_vals else None,
            "max": round(float(np.max(valid_vals)), 1) if valid_vals else None,
        },
    }


def get_basin_average(depth: int) -> Dict[str, Any]:
    """
    Calculate spatial basin-average temperature time series for a given depth.
    """
    if depth not in DEPTHS_M:
        depth_idx = int(np.argmin(np.abs(np.array(DEPTHS_M) - depth)))
        depth = DEPTHS_M[depth_idx]
    else:
        depth_idx = DEPTHS_M.index(depth)

    store = get_store("r")
    dates = get_dates()
    arr = store["thetao"]

    depth_3d = arr[:, depth_idx, :, :] # shape (time, lat, lon)
    basin_means = np.nanmean(depth_3d, axis=(1, 2))

    return {
        "depth": depth,
        "dates": dates,
        "temperature_c": [round(float(v), 2) for v in basin_means],
        "stats": {
            "min": round(float(np.min(basin_means)), 1),
            "median": round(float(np.median(basin_means)), 1),
            "max": round(float(np.max(basin_means)), 1),
        },
    }
