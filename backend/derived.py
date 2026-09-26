"""
Derived ocean layers (spec Section 6).

Pure NumPy functions. Each works on a whole field T of shape (n_depth, ...) so
the same code handles one profile (n_depth,) and the full grid
(n_depth, lat, lon). Scalar convenience wrappers are provided for tests and the
per-point API.
"""
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import xarray as xr

import config

# d20/d26 status flags
ISO_OK = 0
ISO_ABSENT = 1        # surface already colder than the isotherm
ISO_NOT_REACHED = 2   # temperature never drops below the isotherm above the deepest level


# =============================================================================
# 6.1 Isotherm depth
# =============================================================================
def isotherm_depth_field(T: np.ndarray, depths: Sequence[float], t_iso: float) -> Tuple[np.ndarray, np.ndarray]:
    """Depth where T first crosses t_iso going down, linearly interpolated.

    T: (n_depth, ...). Returns (depth, flag), both shaped T.shape[1:].
    depth is NaN when the isotherm is absent (surface < t_iso), not reached
    above the deepest level, or the column is land.
    """
    T = np.asarray(T, dtype=np.float64)
    z = np.asarray(depths, dtype=np.float64).reshape((-1,) + (1,) * (T.ndim - 1))
    with np.errstate(invalid="ignore"):
        cross = (T[:-1] >= t_iso) & (T[1:] < t_iso)  # (n-1, ...)
    has = cross.any(axis=0)
    k = np.argmax(cross, axis=0)

    t0 = np.take_along_axis(T[:-1], k[None], axis=0)[0]
    t1 = np.take_along_axis(T[1:], k[None], axis=0)[0]
    z0 = np.take_along_axis(np.broadcast_to(z[:-1], T[:-1].shape), k[None], axis=0)[0]
    z1 = np.take_along_axis(np.broadcast_to(z[1:], T[1:].shape), k[None], axis=0)[0]
    with np.errstate(invalid="ignore", divide="ignore"):
        d = z0 + (t0 - t_iso) / (t0 - t1) * (z1 - z0)

    surface = T[0]
    with np.errstate(invalid="ignore"):
        absent = surface < t_iso
    flag = np.full(T.shape[1:], ISO_OK, dtype=np.int8)
    flag[absent] = ISO_ABSENT
    flag[~has & ~absent & ~np.isnan(surface)] = ISO_NOT_REACHED

    d = np.where(has & ~absent, d, np.nan)
    return d, flag


def isotherm_depth(profile: Sequence[float], depths: Sequence[float], t_iso: float) -> float:
    d, _ = isotherm_depth_field(np.asarray(profile, dtype=float), depths, t_iso)
    return float(d)


# =============================================================================
# 6.2 Mixed-layer depth (temperature criterion)
# =============================================================================
def mld_field(T: np.ndarray, depths: Sequence[float],
              ref_depth: float = config.MLD_REF_DEPTH_M,
              delta_t: float = config.MLD_DELTA_T_C) -> np.ndarray:
    """Depth where T first falls to T(ref_depth) - delta_t, interpolated between
    levels below ref_depth. NaN if never reached above the deepest level."""
    T = np.asarray(T, dtype=np.float64)
    depths = list(depths)
    r = depths.index(ref_depth)
    sub = T[r:]
    z = np.asarray(depths[r:], dtype=np.float64).reshape((-1,) + (1,) * (T.ndim - 1))
    target = sub[0] - delta_t
    with np.errstate(invalid="ignore"):
        cross = (sub[:-1] > target) & (sub[1:] <= target)
    has = cross.any(axis=0)
    k = np.argmax(cross, axis=0)
    t0 = np.take_along_axis(sub[:-1], k[None], axis=0)[0]
    t1 = np.take_along_axis(sub[1:], k[None], axis=0)[0]
    z0 = np.take_along_axis(np.broadcast_to(z[:-1], sub[:-1].shape), k[None], axis=0)[0]
    z1 = np.take_along_axis(np.broadcast_to(z[1:], sub[1:].shape), k[None], axis=0)[0]
    with np.errstate(invalid="ignore", divide="ignore"):
        d = z0 + (t0 - target) / (t0 - t1) * (z1 - z0)
    return np.where(has, d, np.nan)


def mixed_layer_depth(profile: Sequence[float], depths: Sequence[float], **kw) -> float:
    return float(mld_field(np.asarray(profile, dtype=float), depths, **kw))


# =============================================================================
# 6.3 Horizontal fronts
# =============================================================================
def front_strength(field2d: np.ndarray, lats: Sequence[float],
                   step_deg: float = config.GRID_STEP_DEG) -> np.ndarray:
    """Horizontal gradient magnitude in degC/km on a regular lat/lon grid.
    Central differences; NaN next to land (NaN neighbours propagate)."""
    f = np.asarray(field2d, dtype=np.float64)
    dy_km = step_deg * config.KM_PER_DEG_LAT
    dx_km = step_deg * config.KM_PER_DEG_LON_EQUATOR * np.cos(np.deg2rad(np.asarray(lats, dtype=float)))
    g_lat, g_lon = np.gradient(f)  # per grid step
    return np.sqrt((g_lat / dy_km) ** 2 + (g_lon / dx_km[:, None]) ** 2)


def subsurface_front_flag(front_50m: np.ndarray, front_0m: np.ndarray,
                          threshold: float = config.FRONT_THRESHOLD_C_PER_KM) -> np.ndarray:
    """1 where a front exists at 50 m but not at the surface, 0 otherwise, NaN on land."""
    with np.errstate(invalid="ignore"):
        flag = ((front_50m >= threshold) & (front_0m < threshold)).astype(np.float32)
    flag[np.isnan(front_50m) | np.isnan(front_0m)] = np.nan
    return flag


# =============================================================================
# 6.4 Tropical Cyclone Heat Potential
# =============================================================================
def tchp_field(T: np.ndarray, depths: Sequence[float], d26: Optional[np.ndarray] = None,
               rho: float = config.SEAWATER_DENSITY_KG_M3,
               cp: float = config.SEAWATER_CP_J_KG_K) -> np.ndarray:
    """rho * cp * integral_0^D26 (T - 26) dz in kJ/cm2 (trapezoidal on the
    levels plus the partial layer down to D26). 0 where the surface < 26 degC,
    NaN on land or where 26 degC is not reached above the deepest level."""
    T = np.asarray(T, dtype=np.float64)
    if d26 is None:
        d26, flag26 = isotherm_depth_field(T, depths, config.D26_ISOTHERM_C)
    else:
        _, flag26 = isotherm_depth_field(T, depths, config.D26_ISOTHERM_C)
    z = np.asarray(depths, dtype=np.float64).reshape((-1,) + (1,) * (T.ndim - 1))
    e = T - config.D26_ISOTHERM_C
    z0, z1 = z[:-1], z[1:]
    e0, e1 = e[:-1], e[1:]
    D = np.where(np.isnan(d26), -1.0, d26)[None]
    with np.errstate(invalid="ignore"):
        full = z1 <= D
        partial = (z0 < D) & (D < z1)
    area = np.where(full, 0.5 * (e0 + e1) * (z1 - z0), 0.0)
    area += np.where(partial, 0.5 * e0 * (D - z0), 0.0)
    total = np.nansum(area, axis=0) * rho * cp / config.TCHP_J_M2_TO_KJ_CM2

    total = np.where(flag26 == ISO_ABSENT, 0.0, total)
    total = np.where(flag26 == ISO_NOT_REACHED, np.nan, total)
    total = np.where(np.isnan(T[0]), np.nan, total)
    return total


def tchp(profile: Sequence[float], depths: Sequence[float]) -> float:
    return float(tchp_field(np.asarray(profile, dtype=float), depths))


# =============================================================================
# 6.5 Confidence index (data-density, NOT a statistical error estimate)
# =============================================================================
def load_argo_positions(path: str = config.ARGO_POSITIONS_FILE) -> Optional[List[dict]]:
    """Rows of date, lat, lon, platform_id. None if the file is missing."""
    if not os.path.exists(path):
        return None
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "date": r["date"].strip(),
                    "lat": float(r["lat"]),
                    "lon": float(r["lon"]),
                    "platform_id": r.get("platform_id", "").strip(),
                })
            except (KeyError, ValueError):
                continue
    return rows


def argo_in_window(rows: List[dict], day: str, window_days: int = config.CONF_WINDOW_DAYS) -> List[dict]:
    d = datetime.strptime(day, "%Y-%m-%d")
    lo, hi = d - timedelta(days=window_days), d + timedelta(days=window_days)
    out = []
    for r in rows:
        try:
            rd = datetime.strptime(r["date"], "%Y-%m-%d")
        except ValueError:
            continue
        if lo <= rd <= hi:
            out.append(r)
    return out


def great_circle_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.deg2rad(lat1), np.deg2rad(lat2)
    dphi = p2 - p1
    dlmb = np.deg2rad(lon2) - np.deg2rad(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * config.EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def confidence_field(lats, lons, points: List[dict],
                     length_km: float = config.CONF_LENGTH_KM) -> Optional[np.ndarray]:
    """exp(-d / L) with d the distance to the nearest ARGO profile. None if no points."""
    if not points:
        return None
    lat_g, lon_g = np.meshgrid(np.asarray(lats, float), np.asarray(lons, float), indexing="ij")
    dmin = np.full(lat_g.shape, np.inf)
    for p in points:
        dmin = np.minimum(dmin, great_circle_km(lat_g, lon_g, p["lat"], p["lon"]))
    return np.exp(-dmin / length_km)


def confidence_level(value: Optional[float]) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "not_available"
    if value >= config.CONF_HIGH_MIN:
        return "high"
    if value >= config.CONF_MEDIUM_MIN:
        return "medium"
    return "low"


# =============================================================================
# 6.6 Gear depth by species
# =============================================================================
def gear_depth_range(profile: Sequence[float], depths: Sequence[float],
                     t_min: Optional[float], t_max: Optional[float],
                     step_m: float = config.GEAR_DEPTH_STEP_M) -> Tuple[Optional[float], Optional[float]]:
    """(from, to) depth range where the interpolated profile lies within
    [t_min, t_max]. (None, None) if not configured or never in range."""
    if t_min is None or t_max is None:
        return None, None
    p = np.asarray(profile, dtype=float)
    z = np.asarray(depths, dtype=float)
    ok = ~np.isnan(p)
    if ok.sum() < 2:
        return None, None
    zz = np.arange(z[ok][0], z[ok][-1] + step_m / 2, step_m)
    tt = np.interp(zz, z[ok], p[ok])
    inside = (tt >= t_min) & (tt <= t_max)
    if not inside.any():
        return None, None
    return float(zz[inside][0]), float(zz[inside][-1])


# =============================================================================
# Full derived dataset for one day
# =============================================================================
DERIVED_META = {
    "d20": ("m", "Depth of the 20 degC isotherm (warm-layer depth, thermocline proxy)"),
    "d26": ("m", "Depth of the 26 degC isotherm"),
    "mld": ("m", f"Mixed-layer depth (T({config.MLD_REF_DEPTH_M} m) - {config.MLD_DELTA_T_C} degC criterion)"),
    "front_0m": ("degC km-1", "Horizontal temperature gradient magnitude at 0 m"),
    "front_50m": ("degC km-1", "Horizontal temperature gradient magnitude at 50 m"),
    "front_100m": ("degC km-1", "Horizontal temperature gradient magnitude at 100 m"),
    "subsurface_front_flag": ("1", "Front at 50 m not visible at the surface (1 = yes, 0 = no)"),
    "tchp": ("kJ cm-2", "Tropical cyclone heat potential (integral of T-26 degC down to D26)"),
    "confidence": ("1", "Indicative data-density index exp(-d/L) from distance to nearest ARGO profile; "
                        "NOT a statistical error estimate"),
}
DERIVED_VARS = list(DERIVED_META.keys())


def compute_derived(ds: xr.Dataset, day: str, argo_rows: Optional[List[dict]] = "load") -> xr.Dataset:
    """All Section 6 layers on the (lat, lon) grid of ds."""
    T = ds["thetao"].values.astype(np.float64)
    depths = [float(v) for v in ds["depth"].values]
    lats = ds["lat"].values
    lons = ds["lon"].values
    land = np.isnan(T[0])

    d20, d20_flag = isotherm_depth_field(T, depths, config.D20_ISOTHERM_C)
    d26, d26_flag = isotherm_depth_field(T, depths, config.D26_ISOTHERM_C)
    mld = mld_field(T, depths)

    fronts = {}
    for zf in config.FRONT_DEPTHS_M:
        fronts[f"front_{zf}m"] = front_strength(T[depths.index(zf)], lats)
    ssf = subsurface_front_flag(fronts["front_50m"], fronts["front_0m"])
    tc = tchp_field(T, depths, d26)

    if argo_rows == "load":
        argo_rows = load_argo_positions()
    if argo_rows is None:
        conf, conf_note = None, "ARGO positions file not provided"
    else:
        pts = argo_in_window(argo_rows, day)
        conf = confidence_field(lats, lons, pts)
        conf_note = (f"{len(pts)} ARGO profiles within +/-{config.CONF_WINDOW_DAYS} days"
                     if conf is not None else f"No ARGO profiles within +/-{config.CONF_WINDOW_DAYS} days")
    if conf is None:
        conf = np.full(land.shape, np.nan)
    conf = np.where(land, np.nan, conf)

    layers = {"d20": d20, "d26": d26, "mld": mld, **fronts,
              "subsurface_front_flag": ssf, "tchp": tc, "confidence": conf}
    data_vars = {}
    for name, arr in layers.items():
        units, long_name = DERIVED_META[name]
        a = np.asarray(arr, dtype=np.float32)
        a[land] = np.nan
        attrs = {"units": units, "long_name": long_name}
        if name.startswith("front") or name == "subsurface_front_flag":
            attrs["front_threshold_degC_per_km"] = config.FRONT_THRESHOLD_C_PER_KM
        data_vars[name] = (("lat", "lon"), a, attrs)
    data_vars["d20_flag"] = (("lat", "lon"), d20_flag, {
        "long_name": "D20 status: 0 ok, 1 surface colder than 20 degC, 2 not reached above deepest level"})
    data_vars["d26_flag"] = (("lat", "lon"), d26_flag, {
        "long_name": "D26 status: 0 ok, 1 surface colder than 26 degC, 2 not reached above deepest level"})

    out = xr.Dataset(data_vars, coords={
        "lat": ("lat", lats, {"units": "degrees_north", "axis": "Y"}),
        "lon": ("lon", lons, {"units": "degrees_east", "axis": "X"}),
    })
    out.attrs.update({k: v for k, v in ds.attrs.items() if isinstance(v, (str, int, float))})
    out.attrs["confidence_available"] = int(not np.all(np.isnan(conf)))
    out.attrs["confidence_note"] = conf_note
    return out


def point_derived(profile: Sequence[float], depths: Sequence[float]) -> Dict[str, Optional[float]]:
    """Profile-only derived values at one cell (fronts/confidence need the grid)."""
    def clean(v):
        return None if v is None or np.isnan(v) else round(float(v), 2)
    return {
        "d20": clean(isotherm_depth(profile, depths, config.D20_ISOTHERM_C)),
        "d26": clean(isotherm_depth(profile, depths, config.D26_ISOTHERM_C)),
        "mld": clean(mixed_layer_depth(profile, depths)),
        "tchp": clean(tchp(profile, depths)),
    }
