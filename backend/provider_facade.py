import numpy as np
import xarray as xr
from typing import Dict, Any, Tuple
from providers import get_provider
from config import LATS, LONS, DEPTHS_M
from data_store import snap_to_grid

def get_field_slice_provider(date: str, depth: int) -> np.ndarray:
    provider = get_provider()
    dates = provider.available_dates()
    if date not in dates:
        if not dates:
            raise ValueError("No dates available")
        date = dates[0]
        
    ds = provider.get_temperature(date)
    # Get the nearest depth
    if depth not in DEPTHS_M:
        depth_idx = int(np.argmin(np.abs(np.array(DEPTHS_M) - depth)))
        depth_val = DEPTHS_M[depth_idx]
    else:
        depth_val = depth
        
    arr = ds["thetao"].sel(depth=depth_val).values
    return arr

def get_profile_provider(lat: float, lon: float, date: str) -> Dict[str, Any]:
    lat_idx, lon_idx, snapped_lat, snapped_lon, is_land = snap_to_grid(lat, lon)
    if is_land:
        return {
            "error": "land_cell",
            "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        }
        
    provider = get_provider()
    dates = provider.available_dates()
    if date not in dates:
        if not dates:
            raise ValueError("No dates available")
        date = dates[0]
        
    ds = provider.get_temperature(date)
    profile_vals = ds["thetao"].sel(lat=snapped_lat, lon=snapped_lon, method="nearest").values
    
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

def get_timeseries_provider(lat: float, lon: float, depth: int) -> Dict[str, Any]:
    lat_idx, lon_idx, snapped_lat, snapped_lon, is_land = snap_to_grid(lat, lon)
    if is_land:
        return {
            "error": "land_cell",
            "snapped": {"lat": snapped_lat, "lon": snapped_lon},
        }
        
    if depth not in DEPTHS_M:
        depth_idx = int(np.argmin(np.abs(np.array(DEPTHS_M) - depth)))
        depth_val = DEPTHS_M[depth_idx]
    else:
        depth_val = depth
        
    provider = get_provider()
    dates = provider.available_dates()
    if not dates:
        raise ValueError("No dates available")
        
    # We load each dataset and extract the point
    temp_series = []
    
    # Check land on the first date
    ds_first = provider.get_temperature(dates[0])
    first_val = ds_first["thetao"].sel(depth=depth_val, lat=snapped_lat, lon=snapped_lon, method="nearest").values
    if np.isnan(first_val) and len(dates) > 0: # Check if first is nan, maybe land
        # if the whole profile is nan, it's land
        profile = ds_first["thetao"].sel(lat=snapped_lat, lon=snapped_lon, method="nearest").values
        if np.all(np.isnan(profile)):
            return {
                "error": "land_cell",
                "snapped": {"lat": snapped_lat, "lon": snapped_lon},
            }

    for d in dates:
        ds = provider.get_temperature(d)
        val = ds["thetao"].sel(depth=depth_val, lat=snapped_lat, lon=snapped_lon, method="nearest").values
        if np.isnan(val):
            temp_series.append(None)
        else:
            temp_series.append(round(float(val), 2))
            
    valid_vals = [v for v in temp_series if v is not None]
            
    return {
        "requested": {"lat": round(lat, 4), "lon": round(lon, 4), "depth": depth},
        "snapped": {"lat": snapped_lat, "lon": snapped_lon, "depth": depth_val},
        "dates": dates,
        "temperature_c": temp_series,
        "stats": {
            "min": round(float(np.min(valid_vals)), 1) if valid_vals else None,
            "max": round(float(np.max(valid_vals)), 1) if valid_vals else None,
            "mean": round(float(np.mean(valid_vals)), 2) if valid_vals else None,
        },
    }
    
def get_metadata_provider() -> Dict[str, Any]:
    provider = get_provider()
    dates = provider.available_dates()
    start_date = dates[0] if dates else "2026-09-25"
    end_date = dates[-1] if dates else "2026-09-25"
    
    model_version = "mock-v1"
    data_source = provider.__class__.__name__
    
    if dates:
        ds = provider.get_temperature(dates[-1])
        model_version = ds.attrs.get("model_version", model_version)
        data_source = ds.attrs.get("source", "mock")

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
            "architecture": "OceanEmbed-ViT",
            "resolution": "0.25 deg x 15 depth levels",
            "region": "North Indian Ocean (5AN-30AN, 45AE-105AE)",
        },
        "data_source": data_source,
        "model_version": model_version,
    }

def get_basin_average_provider(depth: int) -> Dict[str, Any]:
    # Placeholder for basin average, not strictly required for Phase 1 except to not break.
    # Keep it simple or use data_store's implementation if needed.
    from data_store import get_basin_average
    return get_basin_average(depth)
