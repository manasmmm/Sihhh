"""
Single access point between the API and the TemperatureProvider.

Adds per-date in-memory caching (keyed by the provider's data stamp, so new or
replaced model output files are picked up automatically) for the thetao
Dataset and its derived layers.
"""
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np
import xarray as xr

import config
from config import LATS, LONS, DEPTHS_M, VALIDITY_DAYS
from providers import get_provider
from data_store import snap_to_grid

_CACHE_SIZE = 8
_lock = threading.Lock()
_ds_cache: "OrderedDict[tuple, xr.Dataset]" = OrderedDict()
_derived_cache: "OrderedDict[tuple, xr.Dataset]" = OrderedDict()


def _cache_get(cache, key):
    with _lock:
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
    return None


def _cache_put(cache, key, value):
    with _lock:
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > _CACHE_SIZE:
            cache.popitem(last=False)


def _key(day: str) -> tuple:
    provider = get_provider()
    return (config.DATA_SOURCE, day, provider.stamp(day))


def valid_upto(day: str) -> str:
    return (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=VALIDITY_DAYS)).strftime("%Y-%m-%d")


def get_dataset(day: str) -> xr.Dataset:
    """thetao Dataset for `day` (cached). Raises FileNotFoundError / ValueError /
    NotImplementedError with a clear message on failure."""
    key = _key(day)
    ds = _cache_get(_ds_cache, key)
    if ds is None:
        ds = get_provider().get_temperature(day)
        _cache_put(_ds_cache, key, ds)
    return ds


def get_derived(day: str) -> xr.Dataset:
    """Derived layers (Section 6) for `day` (cached)."""
    import os
    from derived import compute_derived

    argo_m = os.path.getmtime(config.ARGO_POSITIONS_FILE) if os.path.exists(config.ARGO_POSITIONS_FILE) else 0
    key = _key(day) + (argo_m,)
    out = _cache_get(_derived_cache, key)
    if out is None:
        out = compute_derived(get_dataset(day), day)
        _cache_put(_derived_cache, key, out)
    return out


def resolve_date(date: str) -> str:
    """Existing Explorer behaviour: unknown dates fall back to the first available date."""
    dates = get_provider().available_dates()
    if date in dates:
        return date
    if not dates:
        raise FileNotFoundError("No dates available from the current data source")
    return dates[0]


def _depth_value(depth: int) -> int:
    if depth in DEPTHS_M:
        return depth
    return DEPTHS_M[int(np.argmin(np.abs(np.array(DEPTHS_M) - depth)))]


def get_field_slice_provider(date: str, depth: int) -> np.ndarray:
    ds = get_dataset(resolve_date(date))
    return ds["thetao"].values[DEPTHS_M.index(_depth_value(depth))]


def get_profile_provider(lat: float, lon: float, date: str) -> Dict[str, Any]:
    lat_idx, lon_idx, snapped_lat, snapped_lon, is_land = snap_to_grid(lat, lon)
    if is_land:
        return {"error": "land_cell", "snapped": {"lat": snapped_lat, "lon": snapped_lon}}

    date = resolve_date(date)
    ds = get_dataset(date)
    profile_vals = ds["thetao"].values[:, lat_idx, lon_idx]
    if np.all(np.isnan(profile_vals)):
        return {"error": "land_cell", "snapped": {"lat": snapped_lat, "lon": snapped_lon}}

    temp_list = [round(float(v), 2) if not np.isnan(v) else None for v in profile_vals]
    valid_vals = [v for v in profile_vals if not np.isnan(v)]

    der = get_derived(date)
    derived_vals = {}
    for name in ("d20", "d26", "mld", "front_0m", "front_50m", "front_100m",
                 "subsurface_front_flag", "tchp", "confidence"):
        v = float(der[name].values[lat_idx, lon_idx])
        derived_vals[name] = None if np.isnan(v) else round(v, 4 if name.startswith("front") or name == "confidence" else 2)
    if derived_vals["subsurface_front_flag"] is not None:
        derived_vals["subsurface_front_flag"] = bool(derived_vals["subsurface_front_flag"])
    from derived import confidence_level
    derived_vals["confidence_level"] = confidence_level(derived_vals["confidence"])

    return {
        "requested": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        "date": date,
        "valid_upto": valid_upto(date),
        "depths_m": DEPTHS_M,
        "temperature_c": temp_list,
        "stats": {
            "min": round(float(np.min(valid_vals)), 1) if valid_vals else None,
            "max": round(float(np.max(valid_vals)), 1) if valid_vals else None,
        },
        "derived": derived_vals,
        "front_threshold_c_per_km": config.FRONT_THRESHOLD_C_PER_KM,
    }


def get_timeseries_provider(lat: float, lon: float, depth: int,
                            start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
    lat_idx, lon_idx, snapped_lat, snapped_lon, is_land = snap_to_grid(lat, lon)
    if is_land:
        return {"error": "land_cell", "snapped": {"lat": snapped_lat, "lon": snapped_lon}}

    depth_val = _depth_value(depth)
    provider = get_provider()
    # In-backend model: only days already reconstructed (a series must not trigger one GNN run per day)
    dates = provider.cached_dates() if hasattr(provider, "cached_dates") else provider.available_dates()
    if start:
        dates = [d for d in dates if d >= start]
    if end:
        dates = [d for d in dates if d <= end]
    if not dates:
        raise FileNotFoundError("No dates available in the requested range")

    vals = provider.get_point_series(dates, DEPTHS_M.index(depth_val), lat_idx, lon_idx)
    if np.all(np.isnan(vals)):
        return {"error": "land_cell", "snapped": {"lat": snapped_lat, "lon": snapped_lon}}

    temp_series = [None if np.isnan(v) else round(float(v), 2) for v in vals]
    valid_vals = [v for v in temp_series if v is not None]
    return {
        "requested": {"lat": round(lat, 4), "lon": round(lon, 4), "depth": depth},
        "snapped": {"lat": snapped_lat, "lon": snapped_lon, "depth": depth_val},
        "depth": depth_val,
        "dates": dates,
        "temperature_c": temp_series,
        "stats": {
            "min": round(float(np.min(valid_vals)), 1) if valid_vals else None,
            "median": round(float(np.median(valid_vals)), 1) if valid_vals else None,
            "max": round(float(np.max(valid_vals)), 1) if valid_vals else None,
            "mean": round(float(np.mean(valid_vals)), 2) if valid_vals else None,
        },
    }


def get_metadata_provider() -> Dict[str, Any]:
    provider = get_provider()
    dates = provider.available_dates()
    start_date = dates[0] if dates else None
    end_date = dates[-1] if dates else None

    per_date = {}
    for d in dates:
        info = provider.date_info(d)
        per_date[d] = {"generated_at": info.get("generated_at"), "valid_upto": valid_upto(d),
                       "model_version": info.get("model_version")}

    model_version = per_date[end_date]["model_version"] if dates else None
    source_name = {"mock": "mock", "files": "model_output_files", "model": "model"}.get(config.DATA_SOURCE, "mock")

    invalid = []
    if hasattr(provider, "invalid_files"):
        invalid = provider.invalid_files()
    ready = provider.cached_dates() if hasattr(provider, "cached_dates") else None

    return {
        "domain": {
            "lat_min": float(LATS[0]),
            "lat_max": float(LATS[-1]),
            "lon_min": float(LONS[0]),
            "lon_max": float(LONS[-1]),
            "resolution_deg": config.GRID_STEP_DEG,
        },
        "grid_shape": {"lat": len(LATS), "lon": len(LONS)},
        "depths_m": DEPTHS_M,
        "dates": {
            "start": start_date,
            "end": end_date,
            "count": len(dates),
            "all_dates": dates,
        },
        "per_date": per_date,
        "variable": {
            "name": "thetao",
            "long_name": "Sea water potential temperature",
            "units": "degC",
            "colorbar_range": [0, 32],
        },
        "variables": {
            "thetao": {"units": "degree_Celsius", "long_name": "Sea water potential temperature"},
            **{k: {"units": u, "long_name": ln} for k, (u, ln) in _derived_meta().items()},
        },
        "model_info": {
            "architecture": "OceanEmbed-ViT",
            "resolution": "0.25 deg x 15 depth levels",
            "region": "North Indian Ocean (5N-30N, 45E-105E)",
        },
        "data_source": source_name,
        "model_version": model_version,
        "validity_days": VALIDITY_DAYS,
        "front_threshold_c_per_km": config.FRONT_THRESHOLD_C_PER_KM,
        "derived_display": config.DERIVED_DISPLAY,
        "invalid_model_files": invalid,
        # model mode: days already reconstructed (others are computed on first request)
        "ready_dates": ready,
    }


def _derived_meta():
    from derived import DERIVED_META
    return DERIVED_META


def get_basin_average_provider(depth: int) -> Dict[str, Any]:
    if config.DATA_SOURCE == "mock":
        # Fast path over the precomputed demo store (existing behaviour).
        from data_store import get_basin_average
        return get_basin_average(depth)

    depth_val = _depth_value(depth)
    provider = get_provider()
    # In-backend model: only days already reconstructed (never trigger a GNN run per day here)
    dates = provider.cached_dates() if hasattr(provider, "cached_dates") else provider.available_dates()
    means = [float(np.nanmean(get_dataset(d)["thetao"].values[DEPTHS_M.index(depth_val)])) for d in dates]
    arr = np.array(means) if means else np.array([np.nan])
    return {
        "depth": depth_val,
        "dates": dates,
        "temperature_c": [round(v, 2) for v in means],
        "stats": {
            "min": round(float(np.nanmin(arr)), 1) if means else None,
            "median": round(float(np.nanmedian(arr)), 1) if means else None,
            "max": round(float(np.nanmax(arr)), 1) if means else None,
        },
    }
