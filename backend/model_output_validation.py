"""
Validation of model output files dropped into MODEL_OUTPUT_DIR (spec Section 4.3).

One implementation shared by ModelOutputFileProvider, /api/v1/model-output/status,
the upload endpoint and scripts/check_model_output.py, so they always agree.
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from config import (
    DEPTHS_M, LATS, LONS, GRID_SHAPE, MODEL_OUTPUT_VAR,
    DEPTH_TOLERANCE_M, GRID_COORD_TOLERANCE_DEG,
    PLAUSIBLE_TEMP_MIN_C, PLAUSIBLE_TEMP_MAX_C,
)

FILE_NAME_RE = re.compile(r"^thetao_(\d{4}-\d{2}-\d{2})\.(nc|npy)$")


@dataclass
class ValidationResult:
    path: str
    date: Optional[str] = None
    format: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[np.ndarray] = None  # (15, 101, 241) float32 when valid

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "file": os.path.basename(self.path),
            "date": self.date,
            "format": self.format,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def parse_file_name(path: str):
    """Return (date, format) from 'thetao_YYYY-MM-DD.nc|npy', or (None, None)."""
    m = FILE_NAME_RE.match(os.path.basename(path))
    if not m:
        return None, None
    return m.group(1), ("netcdf" if m.group(2) == "nc" else "numpy")


def _find_coord(ds, names):
    for n in names:
        if n in ds.variables:
            return ds[n].values
    return None


def validate_file(path: str, land_mask: Optional[np.ndarray] = None) -> ValidationResult:
    """Validate one model output file. Never raises; problems go to .errors.

    land_mask: boolean (101, 241), True on land. Applied when the file has no NaN.
    """
    name = os.path.basename(path)
    day, fmt = parse_file_name(path)
    res = ValidationResult(path=path, date=day, format=fmt)

    if not os.path.exists(path):
        res.errors.append(f"{name}: file not found")
        return res
    if day is None:
        res.errors.append(
            f"{name}: file name must be thetao_YYYY-MM-DD.nc or thetao_YYYY-MM-DD.npy"
        )
        return res

    try:
        if fmt == "netcdf":
            arr = _load_netcdf(path, res)
        else:
            arr = _load_numpy(path, res)
    except Exception as e:  # corrupt file, wrong dtype, ...
        res.errors.append(f"{name}: could not be read ({type(e).__name__}: {e})")
        return res

    if arr is None or res.errors:
        return res

    arr = arr.astype(np.float32, copy=True)

    ocean_vals = arr[~np.isnan(arr)]
    if ocean_vals.size == 0:
        res.errors.append(f"{name}: all values are NaN")
        return res

    vmin, vmax = float(ocean_vals.min()), float(ocean_vals.max())
    if vmin < PLAUSIBLE_TEMP_MIN_C or vmax > PLAUSIBLE_TEMP_MAX_C:
        n_out = int(((ocean_vals < PLAUSIBLE_TEMP_MIN_C) | (ocean_vals > PLAUSIBLE_TEMP_MAX_C)).sum())
        res.warnings.append(
            f"{name}: {n_out} values outside the plausible range "
            f"{PLAUSIBLE_TEMP_MIN_C} to {PLAUSIBLE_TEMP_MAX_C} degC (min {vmin:.2f}, max {vmax:.2f})"
        )

    if not np.isnan(arr).any():
        if land_mask is not None:
            arr[:, land_mask] = np.nan
            res.warnings.append(
                f"{name}: no NaN found (land cells should be NaN); the dashboard land mask was applied"
            )
        else:
            res.warnings.append(f"{name}: no NaN found; land cells should be NaN")

    res.data = arr
    return res


def _check_shape(arr: np.ndarray, name: str, res: ValidationResult) -> Optional[np.ndarray]:
    if arr.ndim == 4 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.shape != GRID_SHAPE:
        res.errors.append(
            f"{name}: shape is {tuple(arr.shape)}, expected {GRID_SHAPE} "
            f"(depth, lat, lon), optionally with a single leading time step"
        )
        return None
    return arr


def _load_numpy(path: str, res: ValidationResult) -> Optional[np.ndarray]:
    arr = np.load(path, allow_pickle=False)
    return _check_shape(np.asarray(arr), os.path.basename(path), res)


def _load_netcdf(path: str, res: ValidationResult) -> Optional[np.ndarray]:
    import xarray as xr

    name = os.path.basename(path)
    with xr.open_dataset(path) as ds:
        if MODEL_OUTPUT_VAR not in ds.data_vars:
            res.errors.append(
                f"{name}: variable '{MODEL_OUTPUT_VAR}' not found (found: {list(ds.data_vars)})"
            )
            return None
        da = ds[MODEL_OUTPUT_VAR]

        # Put dimensions in (time?, depth, lat, lon) order if named sensibly
        dim_alias = {}
        for d in da.dims:
            dl = d.lower()
            if dl in ("depth", "lev", "level", "z", "deptht"):
                dim_alias[d] = "depth"
            elif dl in ("lat", "latitude", "y"):
                dim_alias[d] = "lat"
            elif dl in ("lon", "longitude", "x"):
                dim_alias[d] = "lon"
            elif dl in ("time", "t"):
                dim_alias[d] = "time"
        if {"depth", "lat", "lon"} <= set(dim_alias.values()):
            order = [d for tgt in ("time", "depth", "lat", "lon") for d, a in dim_alias.items() if a == tgt]
            da = da.transpose(*order)

        arr = _check_shape(np.asarray(da.values), name, res)
        if arr is None:
            return None

        depths = _find_coord(ds, ["depth", "lev", "level", "deptht", "z"])
        lats = _find_coord(ds, ["lat", "latitude"])
        lons = _find_coord(ds, ["lon", "longitude"])

    if depths is not None:
        depths = np.asarray(depths, dtype=float)
        if depths.shape != (len(DEPTHS_M),) or not np.allclose(depths, DEPTHS_M, atol=DEPTH_TOLERANCE_M):
            res.errors.append(
                f"{name}: depth values {depths.tolist()} do not match the 15 standard depths {DEPTHS_M} "
                f"(tolerance {DEPTH_TOLERANCE_M} m)"
            )
            return None

    if lats is not None:
        lats = np.asarray(lats, dtype=float)
        if lats.size > 1 and lats[0] > lats[-1]:
            lats = lats[::-1]
            arr = arr[:, ::-1, :]
            res.warnings.append(f"{name}: latitude was descending and has been flipped to ascending")
        if lats.shape != (len(LATS),) or not np.allclose(lats, LATS, atol=GRID_COORD_TOLERANCE_DEG):
            res.errors.append(
                f"{name}: latitude grid {lats[0]:.2f}..{lats[-1]:.2f} ({lats.size} points) does not match "
                f"{LATS[0]}..{LATS[-1]} step 0.25 ({len(LATS)} points)"
            )
            return None

    if lons is not None:
        lons = np.asarray(lons, dtype=float)
        if lons.size and lons.min() < 0:  # -180..180 convention; our domain is all positive anyway
            lons = np.where(lons < 0, lons + 360.0, lons)
        if lons.shape != (len(LONS),) or not np.allclose(lons, LONS, atol=GRID_COORD_TOLERANCE_DEG):
            res.errors.append(
                f"{name}: longitude grid {lons[0]:.2f}..{lons[-1]:.2f} ({lons.size} points) does not match "
                f"{LONS[0]}..{LONS[-1]} step 0.25 ({len(LONS)} points)"
            )
            return None

    return np.ascontiguousarray(arr)
