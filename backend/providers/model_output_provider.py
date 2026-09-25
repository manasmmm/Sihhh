import os
import json
import glob
from datetime import datetime
import numpy as np
import xarray as xr
from .base import TemperatureProvider
from config import MODEL_OUTPUT_DIR, MODEL_OUTPUT_VAR, LATS, LONS, DEPTHS_M
from model_bridge import get_land_mask

class ModelOutputFileProvider(TemperatureProvider):
    def available_dates(self):
        dates = []
        for file in glob.glob(os.path.join(MODEL_OUTPUT_DIR, "thetao_*.nc")) + \
                    glob.glob(os.path.join(MODEL_OUTPUT_DIR, "thetao_*.npy")):
            basename = os.path.basename(file)
            date_str = basename.replace("thetao_", "").replace(".nc", "").replace(".npy", "")
            if date_str not in dates:
                dates.append(date_str)
        return sorted(dates)

    def get_temperature(self, day: str) -> xr.Dataset:
        nc_file = os.path.join(MODEL_OUTPUT_DIR, f"thetao_{day}.nc")
        npy_file = os.path.join(MODEL_OUTPUT_DIR, f"thetao_{day}.npy")
        json_file = os.path.join(MODEL_OUTPUT_DIR, f"thetao_{day}.json")
        
        file_to_load = None
        is_nc = False
        if os.path.exists(nc_file):
            file_to_load = nc_file
            is_nc = True
        elif os.path.exists(npy_file):
            file_to_load = npy_file
        else:
            raise FileNotFoundError(f"No model output for {day} in {MODEL_OUTPUT_DIR}")

        # Metadata sidecar
        model_version = "unknown"
        generated_at = datetime.fromtimestamp(os.path.getmtime(file_to_load)).isoformat() + "Z"
        if os.path.exists(json_file):
            try:
                with open(json_file, "r") as f:
                    meta = json.load(f)
                    model_version = meta.get("model_version", model_version)
                    generated_at = meta.get("generated_at", generated_at)
            except Exception:
                pass

        if is_nc:
            ds = xr.open_dataset(nc_file)
            if MODEL_OUTPUT_VAR not in ds:
                raise ValueError(f"Variable '{MODEL_OUTPUT_VAR}' not found in {nc_file}")
            
            arr = ds[MODEL_OUTPUT_VAR].values
            # Remove single time dimension if present
            if arr.ndim == 4 and arr.shape[0] == 1:
                arr = arr[0]
            
            if arr.shape != (15, 101, 241):
                raise ValueError(f"File {nc_file} has shape {arr.shape}, expected (15, 101, 241)")
            
            lat_vals = ds['lat'].values if 'lat' in ds else ds['latitude'].values
            # Check latitude ascending
            if len(lat_vals) > 1 and lat_vals[0] > lat_vals[-1]:
                # Flip latitude
                arr = arr[:, ::-1, :]
                print(f"Warning: Flipped descending latitude in {nc_file}")

        else:
            arr = np.load(npy_file)
            if arr.shape != (15, 101, 241):
                raise ValueError(f"File {npy_file} has shape {arr.shape}, expected (15, 101, 241)")

        # Validate values range
        if np.nanmin(arr) < -2 or np.nanmax(arr) > 40:
            print(f"Warning: Values in {file_to_load} are outside expected range (-2 to 40)")

        # Validate land mask
        if not np.isnan(arr).any():
            print(f"Warning: No NaNs found in {file_to_load}. Applying default land mask.")
            land_mask = get_land_mask()
            arr[:, land_mask] = np.nan

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
        ds.attrs["source"] = "model_output_files"
        ds.attrs["model_version"] = model_version
        ds.attrs["generated_at"] = generated_at
        
        return ds
