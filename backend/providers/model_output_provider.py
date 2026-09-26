"""
ModelOutputFileProvider (DATA_SOURCE = "files") - the main integration path.

The team runs the model outside the backend and drops one file per day into
MODEL_OUTPUT_DIR:  thetao_YYYY-MM-DD.nc (preferred) or thetao_YYYY-MM-DD.npy,
plus an optional thetao_YYYY-MM-DD.json sidecar with model_version/generated_at.

The folder is rescanned on every call (cheap: file names + mtimes), so new files
appear without restarting the server. Validation results are cached per file
modification time.
"""
import glob
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import xarray as xr

from .base import TemperatureProvider
from config import MODEL_OUTPUT_DIR, LATS, LONS, DEPTHS_M
from model_bridge import get_land_mask
from model_output_validation import ValidationResult, parse_file_name, validate_file

log = logging.getLogger("oceanembed.files")

_LOCK = threading.Lock()
_VALIDATION_CACHE: Dict[str, Tuple[float, ValidationResult]] = {}


def _validated(path: str) -> ValidationResult:
    """Validate a file once per modification time."""
    mtime = os.path.getmtime(path)
    with _LOCK:
        hit = _VALIDATION_CACHE.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
    res = validate_file(path, land_mask=get_land_mask())
    for w in res.warnings:
        log.warning(w)
    for e in res.errors:
        log.error(e)
    with _LOCK:
        _VALIDATION_CACHE[path] = (mtime, res)
    return res


def _read_sidecar(day: str, data_path: str) -> dict:
    json_file = os.path.join(MODEL_OUTPUT_DIR, f"thetao_{day}.json")
    meta = {
        "model_version": "unknown",
        "generated_at": datetime.fromtimestamp(os.path.getmtime(data_path), tz=timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": None,
    }
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                side = json.load(f)
            for k in ("model_version", "generated_at", "notes"):
                if side.get(k):
                    meta[k] = side[k]
        except Exception as e:
            log.warning(f"thetao_{day}.json could not be read: {e}")
    return meta


class ModelOutputFileProvider(TemperatureProvider):

    # ------------------------------------------------------------------ scan
    def _files_by_date(self) -> Dict[str, str]:
        """date -> preferred file path (.nc wins over .npy)."""
        found: Dict[str, str] = {}
        for path in sorted(glob.glob(os.path.join(MODEL_OUTPUT_DIR, "thetao_*.*"))):
            day, fmt = parse_file_name(path)
            if day is None:
                continue
            if day not in found or fmt == "netcdf":
                found[day] = path
        return found

    def scan(self) -> List[dict]:
        """Every candidate file in the folder with its validation status."""
        out = []
        for path in sorted(glob.glob(os.path.join(MODEL_OUTPUT_DIR, "thetao_*"))):
            if path.endswith(".json"):
                continue
            res = _validated(path)
            info = res.to_dict()
            if res.date:
                info["model_version"] = _read_sidecar(res.date, path)["model_version"]
            out.append(info)
        return out

    def invalid_files(self) -> List[dict]:
        return [f for f in self.scan() if not f["valid"]]

    # ------------------------------------------------------------ interface
    def available_dates(self) -> List[str]:
        return sorted(d for d, p in self._files_by_date().items() if _validated(p).valid)

    def _path_for(self, day: str) -> str:
        path = self._files_by_date().get(day)
        if path is None:
            raise FileNotFoundError(f"No model output for {day} in data/model_output/")
        return path

    def stamp(self, day: str) -> str:
        try:
            path = self._path_for(day)
        except FileNotFoundError:
            return "missing"
        side = os.path.join(MODEL_OUTPUT_DIR, f"thetao_{day}.json")
        side_m = os.path.getmtime(side) if os.path.exists(side) else 0
        return f"{os.path.basename(path)}:{os.path.getmtime(path)}:{side_m}"

    def date_info(self, day: str):
        meta = _read_sidecar(day, self._path_for(day))
        return {"generated_at": meta["generated_at"], "model_version": meta["model_version"]}

    def validation_for(self, day: str) -> Optional[dict]:
        path = self._files_by_date().get(day)
        return _validated(path).to_dict() if path else None

    def get_temperature(self, day: str) -> xr.Dataset:
        path = self._path_for(day)
        res = _validated(path)
        if not res.valid:
            raise ValueError("; ".join(res.errors))
        meta = _read_sidecar(day, path)

        ds = xr.Dataset(
            {
                "thetao": (["depth", "lat", "lon"], res.data.copy(), {
                    "units": "degree_Celsius",
                    "standard_name": "sea_water_potential_temperature",
                })
            },
            coords={
                "depth": ("depth", DEPTHS_M, {"units": "m", "positive": "down", "axis": "Z"}),
                "lat": ("lat", LATS, {"units": "degrees_north", "axis": "Y"}),
                "lon": ("lon", LONS, {"units": "degrees_east", "axis": "X"}),
            }
        )
        ds.attrs["source"] = "model_output_files"
        ds.attrs["model_version"] = meta["model_version"]
        ds.attrs["generated_at"] = meta["generated_at"]
        ds.attrs["validation_warnings"] = "; ".join(res.warnings)
        return ds
