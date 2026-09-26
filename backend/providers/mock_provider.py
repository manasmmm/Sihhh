import glob
import os
import re
from typing import List

import numpy as np
import xarray as xr

from .base import TemperatureProvider
from config import LATS, LONS, DEPTHS_M, PFZ_DIR
from data_store import get_dates, get_store, is_store_initialized
from model_bridge import reconstruct_field

MOCK_MODEL_VERSION = "mock-v1"
_PFZ_DATE_RE = re.compile(r"^pfz_.+_(\d{4}-\d{2}-\d{2})\.csv$")


def _pfz_dates() -> List[str]:
    """Dates that have a PFZ advisory CSV. In demo mode these dates are also
    offered so the Fisheries tab always has a temperature field to enrich with."""
    out = set()
    for f in glob.glob(os.path.join(PFZ_DIR, "pfz_*.csv")):
        m = _PFZ_DATE_RE.match(os.path.basename(f))
        if m:
            out.add(m.group(1))
    return sorted(out)


class MockProvider(TemperatureProvider):
    """Demo data. Reuses the existing precomputed Zarr store (the values the
    Explorer always showed). Dates outside the store are generated with the
    same smooth, date-seeded generator used to build the store
    (model_bridge.reconstruct_field), so every mock date looks consistent."""

    def available_dates(self) -> List[str]:
        dates = set(get_dates()) if is_store_initialized() else set()
        dates.update(_pfz_dates())
        return sorted(dates)

    def stamp(self, day: str) -> str:
        if is_store_initialized() and day in get_dates():
            return "zarr:" + str(get_store("r").attrs.get("created_at", ""))
        return "synthetic"

    def date_info(self, day: str):
        return {"generated_at": self._generated_at(day), "model_version": MOCK_MODEL_VERSION}

    def _generated_at(self, day: str) -> str:
        if is_store_initialized() and day in get_dates():
            created = get_store("r").attrs.get("created_at")
            if created:
                return created if created.endswith("Z") else created + "Z"
        return f"{day}T00:00:00Z"

    def get_temperature(self, day: str) -> xr.Dataset:
        if is_store_initialized():
            dates = get_dates()
            if day in dates:
                arr = np.array(get_store("r")["thetao"][dates.index(day), :, :, :], dtype=np.float32)
                return self._to_dataset(arr, day)
        return self._to_dataset(reconstruct_field(day), day)

    def get_point_series(self, dates, depth_idx, lat_idx, lon_idx):
        # Fast path: read one column of the Zarr store instead of whole cubes.
        out = np.full(len(dates), np.nan, dtype=np.float32)
        store_dates = get_dates() if is_store_initialized() else []
        pos = {d: i for i, d in enumerate(store_dates)}
        in_store = [(i, pos[d]) for i, d in enumerate(dates) if d in pos]
        if in_store:
            column = np.asarray(get_store("r")["thetao"][:, depth_idx, lat_idx, lon_idx], dtype=np.float32)
            for i, t in in_store:
                out[i] = column[t]
        for i, d in enumerate(dates):
            if d not in pos:
                out[i] = reconstruct_field(d)[depth_idx, lat_idx, lon_idx]
        return out

    def _to_dataset(self, arr: np.ndarray, day: str) -> xr.Dataset:
        ds = xr.Dataset(
            {
                "thetao": (["depth", "lat", "lon"], arr.astype(np.float32), {
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
        ds.attrs["source"] = "mock"
        ds.attrs["model_version"] = MOCK_MODEL_VERSION
        ds.attrs["generated_at"] = self._generated_at(day)
        return ds
