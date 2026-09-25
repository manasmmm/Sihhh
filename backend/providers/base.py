from abc import ABC, abstractmethod
from typing import List
import xarray as xr

class TemperatureProvider(ABC):
    @abstractmethod
    def available_dates(self) -> List[str]:
        """Return list of available dates in YYYY-MM-DD format."""
        pass

    @abstractmethod
    def get_temperature(self, day: str) -> xr.Dataset:
        """
        Return a Dataset with variable 'thetao' of shape
        (depth=15, lat=101, lon=241), float32, degree_Celsius,
        NaN over land, coordinates exactly as in Section 3.
        Dataset attrs must include: source ('mock', 'model_output_files' or 'model'),
        model_version, generated_at (ISO 8601 UTC).
        """
        pass
