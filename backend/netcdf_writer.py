"""
CF-1.8 NetCDF export (spec Section 4.4).

data/output/thetao_YYYY-MM-DD.nc   - thetao(time, depth, lat, lon)
data/derived/derived_YYYY-MM-DD.nc - derived layers (lat, lon)

Files are created on first request and then served from disk. They are
regenerated when the provider, model version or input data changed (tracked
through the global attribute `input_stamp`).
"""
import os
from datetime import datetime, timezone

import numpy as np
import xarray as xr

import config
from provider_facade import get_dataset, get_derived, valid_upto, _key

TIME_UNITS = "days since 1970-01-01 00:00:00"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp(date: str) -> str:
    return "|".join(str(p) for p in _key(date))


def _cached(path: str, stamp: str) -> bool:
    if not os.path.exists(path):
        return False
    try:
        with xr.open_dataset(path) as ds:
            return ds.attrs.get("input_stamp") == stamp
    except Exception:
        return False


def _global_attrs(src: xr.Dataset, date: str, stamp: str, title: str) -> dict:
    return {
        "Conventions": "CF-1.8",
        "title": title,
        "institution": "Team Crisis Workers, SIH 2026",
        "source": src.attrs.get("source", "unknown"),
        "model_version": src.attrs.get("model_version", "unknown"),
        "generated_at": src.attrs.get("generated_at", _now_iso()),
        "valid_upto": valid_upto(date),
        "product_date": date,
        "geospatial_lat_min": float(config.LAT_MIN),
        "geospatial_lat_max": float(config.LAT_MAX),
        "geospatial_lon_min": float(config.LON_MIN),
        "geospatial_lon_max": float(config.LON_MAX),
        "history": f"{_now_iso()}: created by the OceanEmbed dashboard backend",
        "input_stamp": stamp,
    }


def _coords(date: str, with_depth: bool) -> dict:
    coords = {
        "time": ("time", np.array([np.datetime64(date, "ns")]),
                 {"standard_name": "time", "axis": "T"}),
        "lat": ("lat", np.asarray(config.LATS, dtype=np.float32),
                {"standard_name": "latitude", "units": "degrees_north", "axis": "Y"}),
        "lon": ("lon", np.asarray(config.LONS, dtype=np.float32),
                {"standard_name": "longitude", "units": "degrees_east", "axis": "X"}),
    }
    if with_depth:
        coords["depth"] = ("depth", np.asarray(config.DEPTHS_M, dtype=np.float32),
                           {"standard_name": "depth", "units": "m", "positive": "down", "axis": "Z"})
    return coords


def _write(ds: xr.Dataset, path: str, var_names):
    enc = {v: {"_FillValue": np.float32(np.nan), "zlib": True, "complevel": 4, "dtype": "float32"} for v in var_names}
    enc["time"] = {"units": TIME_UNITS, "calendar": "standard", "dtype": "float64"}
    for c in ("lat", "lon", "depth"):
        if c in ds.coords:
            enc[c] = {"_FillValue": None}
    tmp = path + ".tmp"
    ds.to_netcdf(tmp, encoding=enc, engine="netcdf4")
    os.replace(tmp, path)


def generate_netcdf(date: str) -> str:
    """Write (or reuse) data/output/thetao_<date>.nc. Returns the file path."""
    path = os.path.join(config.OUTPUT_DIR, f"thetao_{date}.nc")
    stamp = _stamp(date)
    if _cached(path, stamp):
        return path

    src = get_dataset(date)
    arr = src["thetao"].values.astype(np.float32)[None]  # (1, 15, 101, 241)
    ds = xr.Dataset(
        {"thetao": (("time", "depth", "lat", "lon"), arr, {
            "units": "degree_Celsius",
            "standard_name": "sea_water_potential_temperature",
            "long_name": "Reconstructed sea water potential temperature",
        })},
        coords=_coords(date, with_depth=True),
        attrs=_global_attrs(src, date, stamp, "OceanEmbed subsurface temperature reconstruction"),
    )
    _write(ds, path, ["thetao"])
    return path


def generate_derived_netcdf(date: str) -> str:
    """Write (or reuse) data/derived/derived_<date>.nc. Returns the file path."""
    path = os.path.join(config.DERIVED_DIR, f"derived_{date}.nc")
    stamp = _stamp(date)
    if _cached(path, stamp):
        return path

    src = get_dataset(date)
    der = get_derived(date)
    data_vars = {}
    names = []
    for name in der.data_vars:
        if name.endswith("_flag") and name != "subsurface_front_flag":
            continue  # internal status flags
        a = der[name].values.astype(np.float32)[None]
        data_vars[name] = (("time", "lat", "lon"), a, dict(der[name].attrs))
        names.append(name)
    attrs = _global_attrs(src, date, stamp, "OceanEmbed derived subsurface ocean layers")
    attrs["confidence_note"] = der.attrs.get("confidence_note", "")
    attrs["front_threshold_degC_per_km"] = config.FRONT_THRESHOLD_C_PER_KM
    ds = xr.Dataset(data_vars, coords=_coords(date, with_depth=False), attrs=attrs)
    _write(ds, path, names)
    return path
