"""
ModelProvider (DATA_SOURCE = "model") - runs the OceanEmbed GNN-OAM model inside the backend.

Uses the artifacts of the Kaggle notebook OceanEmbed-GNN-OAM-FULL.ipynb copied into
backend/model_artifacts/ (checkpoint gnn_C_full_epoch_20.pt, the tree-stage models
rf_model_*.joblib, depth_cluster.json, season_regime.json and the cached, normalised
surface inputs finetune*_x/_t/_meta). See backend/gnn_engine/.

Contract (unchanged from the spec):
- Input: a date. Output: float32 (15, 101, 241) degC, depth order 0..1000 m,
  lat 5->30, lon 45->105, NaN on land. Wrapped into the standard Dataset with
  attrs["source"] = "model".

Each reconstructed day is written once to data/gnn_output/thetao_<date>.nc (same
format as scripts/save_model_output.py) and served from there afterwards. The cache
is invalidated automatically when the checkpoint or tree models change.
"""
import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np
import xarray as xr

from .base import TemperatureProvider
import config
from config import LATS, LONS, DEPTHS_M, GRID_SHAPE

NOT_IMPLEMENTED_MSG = "ModelProvider not implemented yet; set DATA_SOURCE=mock or DATA_SOURCE=files"
_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _day_lock(day: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(day, threading.Lock())


def _cache_paths(day: str):
    base = os.path.join(config.GNN_OUTPUT_CACHE_DIR, f"thetao_{day}")
    return base + ".nc", base + ".json"


class ModelProvider(TemperatureProvider):

    def _engine(self):
        from gnn_engine.engine import get_engine
        return get_engine()

    # ---------------------------------------------------------- interface
    def available_dates(self) -> List[str]:
        return self._engine().available_dates()

    def cached_dates(self) -> List[str]:
        """Days already reconstructed with the current checkpoint (cheap; used by time series)."""
        sig = self._engine().art.signature()
        out = []
        for d in self.available_dates():
            nc, js = _cache_paths(d)
            if os.path.exists(nc) and os.path.exists(js):
                try:
                    with open(js, encoding="utf-8") as f:
                        if json.load(f).get("signature") == sig:
                            out.append(d)
                except Exception:
                    pass
        return out

    def stamp(self, day: str) -> str:
        return "gnn:" + self._engine().art.signature()

    def date_info(self, day: str):
        nc, js = _cache_paths(day)
        gen = None
        if os.path.exists(js):
            try:
                with open(js, encoding="utf-8") as f:
                    gen = json.load(f).get("generated_at")
            except Exception:
                pass
        return {"generated_at": gen, "model_version": config.GNN_MODEL_VERSION}

    def get_temperature(self, day: str) -> xr.Dataset:
        eng = self._engine()
        sig = eng.art.signature()
        nc, js = _cache_paths(day)
        with _day_lock(day):
            arr, meta = self._read_cache(nc, js, sig)
            if arr is None:
                arr = eng.reconstruct(day)
                if arr.shape != GRID_SHAPE:
                    raise ValueError(f"GNN reconstruction returned shape {arr.shape}, expected {GRID_SHAPE}")
                meta = self._write_cache(arr, day, nc, js, sig, eng)
        return self._to_dataset(arr, meta)

    def get_point_series(self, dates, depth_idx, lat_idx, lon_idx):
        # Only days that are already reconstructed: a time series must never trigger
        # thousands of GNN runs. Run scripts/run_gnn_inference.py to fill a period.
        done = set(self.cached_dates())
        out = np.full(len(dates), np.nan, dtype=np.float32)
        for i, d in enumerate(dates):
            if d in done:
                out[i] = self.get_temperature(d)["thetao"].values[depth_idx, lat_idx, lon_idx]
        return out

    # ------------------------------------------------------------- cache
    @staticmethod
    def _read_cache(nc, js, sig):
        if not (os.path.exists(nc) and os.path.exists(js)):
            return None, None
        try:
            with open(js, encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("signature") != sig:
                return None, None
            with xr.open_dataset(nc) as ds:
                arr = np.asarray(ds["thetao"].values, dtype=np.float32)
            return (arr[0] if arr.ndim == 4 else arr), meta
        except Exception:
            return None, None

    @staticmethod
    def _write_cache(arr, day, nc, js, sig, eng):
        os.makedirs(config.GNN_OUTPUT_CACHE_DIR, exist_ok=True)
        info = eng.model_info
        meta = {
            "model_version": config.GNN_MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "checkpoint": os.path.basename(eng.art.checkpoint),
            "checkpoint_epoch": info.get("epoch"),
            "tree_models": [os.path.basename(p) for p in eng.art.tree_models],
            "ocean_mask": eng.mask_source,
            "signature": sig,
        }
        ds = xr.Dataset(
            {"thetao": (("time", "depth", "lat", "lon"), arr[None].astype(np.float32),
                        {"units": "degree_Celsius", "standard_name": "sea_water_potential_temperature",
                         "long_name": "Reconstructed sea water potential temperature"})},
            coords={"time": [np.datetime64(day, "ns")], "depth": DEPTHS_M, "lat": LATS, "lon": LONS},
            attrs={"Conventions": "CF-1.8", "model_version": config.GNN_MODEL_VERSION},
        )
        tmp = nc + ".tmp"
        ds.to_netcdf(tmp, engine="netcdf4", encoding={
            "thetao": {"zlib": True, "complevel": 4, "_FillValue": np.float32(np.nan)},
            "time": {"units": "days since 1970-01-01 00:00:00", "calendar": "standard"}})
        os.replace(tmp, nc)
        with open(js, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return meta

    @staticmethod
    def _to_dataset(arr, meta) -> xr.Dataset:
        ds = xr.Dataset(
            {"thetao": (["depth", "lat", "lon"], arr.astype(np.float32), {
                "units": "degree_Celsius", "standard_name": "sea_water_potential_temperature"})},
            coords={
                "depth": ("depth", DEPTHS_M, {"units": "m", "positive": "down", "axis": "Z"}),
                "lat": ("lat", LATS, {"units": "degrees_north", "axis": "Y"}),
                "lon": ("lon", LONS, {"units": "degrees_east", "axis": "X"}),
            },
        )
        ds.attrs["source"] = "model"
        ds.attrs["model_version"] = meta.get("model_version", config.GNN_MODEL_VERSION)
        ds.attrs["generated_at"] = meta.get("generated_at")
        return ds
