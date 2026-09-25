from datetime import datetime
import numpy as np
import xarray as xr
from .base import TemperatureProvider
from config import LATS, LONS, DEPTHS_M
from data_store import get_dates, get_store, is_store_initialized
from model_bridge import get_land_mask

class MockProvider(TemperatureProvider):
    def available_dates(self):
        if is_store_initialized():
            return get_dates()
        return ["2026-09-25"] # fallback

    def get_temperature(self, day: str) -> xr.Dataset:
        land_mask = get_land_mask()
        
        # Try to read from existing zarr store
        if is_store_initialized():
            dates = get_dates()
            if day in dates:
                store = get_store("r")
                time_idx = dates.index(day)
                arr = np.array(store["thetao"][time_idx, :, :, :], dtype=np.float32)
                return self._to_dataset(arr, day)
        
        # Fallback to generating synthetic data if date not in store or store missing
        arr = self._generate_synthetic(day, land_mask)
        return self._to_dataset(arr, day)
        
    def _to_dataset(self, arr: np.ndarray, day: str) -> xr.Dataset:
        ds = xr.Dataset(
            {
                "thetao": (["depth", "lat", "lon"], arr, {
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
        ds.attrs["model_version"] = "mock-v1"
        ds.attrs["generated_at"] = datetime.utcnow().isoformat() + "Z"
        return ds

    def _generate_synthetic(self, day: str, land_mask: np.ndarray) -> np.ndarray:
        # Seed random generator from date
        seed = int(day.replace("-", ""))
        rng = np.random.default_rng(seed)
        
        lat_grid, lon_grid = np.meshgrid(LATS, LONS, indexing='ij')
        
        # SST: 29 at south (lat=5), decreasing northward, plus random
        sst_base = 29.0 - (lat_grid - 5.0) * 0.1
        sst_noise = rng.uniform(-1, 1, size=lat_grid.shape)
        sst = sst_base + sst_noise
        
        # Profile parameters
        t_deep = 7.0
        d_center = rng.uniform(70, 150, size=lat_grid.shape)
        w_width = 50.0
        
        arr = np.zeros((len(DEPTHS_M), len(LATS), len(LONS)), dtype=np.float32)
        for k, z in enumerate(DEPTHS_M):
            arr[k, :, :] = t_deep + (sst - t_deep) * 0.5 * (1.0 - np.tanh((z - d_center) / w_width))
            
        arr[:, land_mask] = np.nan
        return arr
