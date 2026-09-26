"""
INCOIS Potential Fishing Zone advisories (spec Section 5) and their
enrichment with OceanEmbed subsurface information (Section 7).

CSV files: data/pfz/pfz_<SECTOR>_<YYYY-MM-DD>.csv with config.PFZ_COLUMNS.
The PFZ "sea depth" columns are SEA FLOOR depth (bathymetry) and are kept
separate from our temperature depths / warm-layer depth.
"""
import csv
import glob
import json
import os
import re
from typing import Dict, List, Optional, Tuple

import numpy as np

import config
from config import PFZ_DIR, PFZ_COLUMNS, PFZ_SECTORS

_DMS_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*([NSEWnsew])?\s*$")
_FILE_RE = re.compile(r"^pfz_(.+)_(\d{4}-\d{2}-\d{2})\.csv$")


def dms_to_decimal(dms: str) -> float:
    """'15 31 59 N' -> 15.5331 (north and east positive, south and west negative)."""
    m = _DMS_RE.match(str(dms))
    if not m:
        raise ValueError(f"Cannot parse degrees-minutes-seconds value '{dms}' (expected e.g. '15 31 59 N')")
    deg, minutes, seconds, hemi = float(m.group(1)), float(m.group(2)), float(m.group(3)), (m.group(4) or "").upper()
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Minutes and seconds must be below 60 in '{dms}'")
    value = abs(deg) + minutes / 60.0 + seconds / 3600.0
    if deg < 0 or hemi in ("S", "W"):
        value = -value
    return value


# ----------------------------------------------------------------- sectors
def sector_info(code: str) -> Optional[dict]:
    c = str(code).strip().upper().replace(" ", "_")
    for s in PFZ_SECTORS:
        if s["code"] == c or s["name"].upper().replace(" ", "_") == c:
            return s
    return None


def pfz_path(sector: str, date: str) -> str:
    return os.path.join(PFZ_DIR, f"pfz_{sector}_{date}.csv")


def available_pfz() -> Dict[str, List[str]]:
    """sector code -> sorted list of dates with a CSV."""
    out: Dict[str, List[str]] = {}
    for f in glob.glob(os.path.join(PFZ_DIR, "pfz_*.csv")):
        m = _FILE_RE.match(os.path.basename(f))
        if not m:
            continue
        s = sector_info(m.group(1))
        if s:
            out.setdefault(s["code"], []).append(m.group(2))
    return {k: sorted(v) for k, v in out.items()}


# ------------------------------------------------------------------ loader
def _num(v: str) -> Optional[float]:
    v = (v or "").strip()
    if v == "":
        return None
    return float(v)


def load_pfz(sector: str, date: str) -> Tuple[List[dict], List[str]]:
    """Rows of one advisory plus a list of human-readable problems.
    Missing file -> ([], []). Bad rows are skipped and reported."""
    s = sector_info(sector)
    if s is None:
        return [], [f"Unknown sector '{sector}'"]
    path = pfz_path(s["code"], date)
    if not os.path.exists(path):
        return [], []

    rows, problems = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in PFZ_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            return [], [f"{os.path.basename(path)}: missing columns {missing}"]
        for i, r in enumerate(reader, start=2):  # line 1 is the header
            try:
                lat_dec = dms_to_decimal(r["lat_dms"]) if r["lat_dms"].strip() else None
                lon_dec = dms_to_decimal(r["lon_dms"]) if r["lon_dms"].strip() else None
                lat, lon = _num(r["lat"]), _num(r["lon"])
                if lat is None:
                    lat = lat_dec
                if lon is None:
                    lon = lon_dec
                if lat is None or lon is None:
                    raise ValueError("no position (lat/lon or lat_dms/lon_dms required)")
                tol = config.PFZ_DMS_MISMATCH_TOLERANCE_DEG
                if lat_dec is not None and abs(lat - lat_dec) > tol:
                    problems.append(f"line {i}: lat {lat} does not match lat_dms {r['lat_dms']} ({lat_dec:.4f}); using the DMS value")
                    lat = lat_dec
                if lon_dec is not None and abs(lon - lon_dec) > tol:
                    problems.append(f"line {i}: lon {lon} does not match lon_dms {r['lon_dms']} ({lon_dec:.4f}); using the DMS value")
                    lon = lon_dec
                rows.append({
                    "date": r["date"].strip() or date,
                    "sector": s["code"],
                    "landmark": r["landmark"].strip(),
                    "direction": r["direction"].strip().upper(),
                    "bearing_deg": _num(r["bearing_deg"]),
                    "dist_from_km": _num(r["dist_from_km"]),
                    "dist_to_km": _num(r["dist_to_km"]),
                    "sea_depth_from_m": _num(r["sea_depth_from_m"]),
                    "sea_depth_to_m": _num(r["sea_depth_to_m"]),
                    "lat_dms": r["lat_dms"].strip(),
                    "lon_dms": r["lon_dms"].strip(),
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "valid_upto": r["valid_upto"].strip() or None,
                })
            except (ValueError, KeyError) as e:
                problems.append(f"line {i}: skipped ({e})")
    return rows, problems


# ----------------------------------------------------------------- species
def load_species() -> List[dict]:
    if not os.path.exists(config.SPECIES_FILE):
        return []
    try:
        with open(config.SPECIES_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    items = data.get("species", data) if isinstance(data, dict) else data
    out = []
    for s in items:
        if not isinstance(s, dict) or not s.get("name"):
            continue
        out.append({
            "name": s["name"],
            "t_min_c": s.get("t_min_c"),
            "t_max_c": s.get("t_max_c"),
            "source": s.get("source"),
            "configured": s.get("t_min_c") is not None and s.get("t_max_c") is not None,
        })
    return out


# -------------------------------------------------------------- enrichment
def nearest_ocean_cell(lat: float, lon: float, ocean: np.ndarray) -> Optional[Tuple[int, int]]:
    """Nearest grid cell; if it is land, the nearest ocean cell among its 8 neighbours."""
    lats = np.asarray(config.LATS)
    lons = np.asarray(config.LONS)
    i = int(np.argmin(np.abs(lats - lat)))
    j = int(np.argmin(np.abs(lons - lon)))
    if ocean[i, j]:
        return i, j
    best, best_d = None, np.inf
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ii, jj = i + di, j + dj
            if (di or dj) and 0 <= ii < len(lats) and 0 <= jj < len(lons) and ocean[ii, jj]:
                d = (lats[ii] - lat) ** 2 + ((lons[jj] - lon) * np.cos(np.deg2rad(lat))) ** 2
                if d < best_d:
                    best, best_d = (ii, jj), d
    return best


def _f(v, nd=2):
    if v is None:
        return None
    v = float(v)
    return None if np.isnan(v) else round(v, nd)


def enrich(sector: str, date: str, species: Optional[str] = None, lang: str = config.DEFAULT_LANGUAGE) -> dict:
    """Raw PFZ rows + OceanEmbed subsurface fields + summary_text."""
    from derived import confidence_level, gear_depth_range
    from provider_facade import get_dataset, get_derived, valid_upto as product_valid_upto
    from summary import build_summary

    s = sector_info(sector)
    rows, problems = load_pfz(sector, date)
    result = {
        "sector": s["code"] if s else sector,
        "sector_name": s["name"] if s else sector,
        "date": date,
        "rows": [],
        "problems": problems,
        "message": None,
        "oceanembed_available": False,
        "species": None,
        "front_threshold_c_per_km": config.FRONT_THRESHOLD_C_PER_KM,
    }
    if s is None:
        result["message"] = f"Unknown sector '{sector}'"
        return result
    if not rows:
        result["message"] = "No PFZ advisory loaded for this sector and date"
        return result

    sp = None
    if species:
        sp = next((x for x in load_species() if x["name"].lower() == species.lower()), None)
        result["species"] = sp

    ds = der = None
    try:
        ds = get_dataset(date)
        der = get_derived(date)
        result["oceanembed_available"] = True
        result["source"] = ds.attrs.get("source")
        result["model_version"] = ds.attrs.get("model_version")
        result["confidence_note"] = der.attrs.get("confidence_note")
    except (FileNotFoundError, ValueError, NotImplementedError) as e:
        result["message"] = f"OceanEmbed subsurface data not available for {date}: {e}"

    depths = [float(d) for d in config.DEPTHS_M]
    for r in rows:
        out = dict(r)
        out["valid_upto"] = r.get("valid_upto") or product_valid_upto(date)
        extra = {k: None for k in ("d20_m", "mld_m", "front_50m", "subsurface_front", "confidence",
                                   "gear_depth_from_m", "gear_depth_to_m", "profile",
                                   "grid_cell_lat", "grid_cell_lon")}
        extra["confidence_level"] = "not_available"
        if ds is not None:
            T = ds["thetao"].values
            cell = nearest_ocean_cell(r["lat"], r["lon"], ~np.isnan(T[0]))
            if cell is None:
                extra["note"] = "No ocean grid cell near this position"
            else:
                i, j = cell
                prof = T[:, i, j].astype(float)
                conf = _f(der["confidence"].values[i, j], 3)
                ssf = der["subsurface_front_flag"].values[i, j]
                extra.update({
                    "grid_cell_lat": float(config.LATS[i]),
                    "grid_cell_lon": float(config.LONS[j]),
                    "d20_m": _f(der["d20"].values[i, j], 1),
                    "mld_m": _f(der["mld"].values[i, j], 1),
                    "front_50m": _f(der["front_50m"].values[i, j], 4),
                    "subsurface_front": None if np.isnan(ssf) else bool(ssf),
                    "confidence": conf,
                    "confidence_level": confidence_level(conf),
                    "profile": [_f(v) for v in prof],
                })
                if sp and sp["configured"]:
                    g0, g1 = gear_depth_range(prof, depths, sp["t_min_c"], sp["t_max_c"])
                    extra["gear_depth_from_m"], extra["gear_depth_to_m"] = g0, g1
        out.update(extra)
        out["summary_text"] = build_summary(out, lang=lang, species=sp)
        result["rows"].append(out)
    return result
