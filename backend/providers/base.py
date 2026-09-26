from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import numpy as np
import xarray as xr


class TemperatureProvider(ABC):
    """Every data source implements this. Everything downstream (NetCDF writer,
    derived layers, API) depends only on this interface.

    Dates are 'YYYY-MM-DD' strings throughout the backend."""

    @abstractmethod
    def available_dates(self) -> List[str]:
        """Return list of available dates in YYYY-MM-DD format."""

    @abstractmethod
    def get_temperature(self, day: str) -> xr.Dataset:
        """
        Return a Dataset with variable 'thetao' of shape
        (depth=15, lat=101, lon=241), float32, degree_Celsius,
        NaN over land, coordinates exactly as in Section 3.
        Dataset attrs must include: source ('mock', 'model_output_files' or 'model'),
        model_version, generated_at (ISO 8601 UTC).
        """

    def stamp(self, day: str) -> str:
        """Cheap string that changes whenever the data for `day` changes.
        Used as a cache key for datasets, derived layers and NetCDF exports."""
        return ""

    def date_info(self, day: str) -> Dict[str, Optional[str]]:
        """Cheap per-date metadata: generated_at and model_version."""
        attrs = self.get_temperature(day).attrs
        return {"generated_at": attrs.get("generated_at"), "model_version": attrs.get("model_version")}

    def get_point_series(self, dates: List[str], depth_idx: int, lat_idx: int, lon_idx: int) -> np.ndarray:
        """Values at one cell/depth for several dates. Providers may override
        with a faster path; the default loads each (cached) daily dataset."""
        from provider_facade import get_dataset  # local import: avoid cycle

        out = np.full(len(dates), np.nan, dtype=np.float32)
        for i, d in enumerate(dates):
            try:
                out[i] = get_dataset(d)["thetao"].values[depth_idx, lat_idx, lon_idx]
            except FileNotFoundError:
                pass
        return out
