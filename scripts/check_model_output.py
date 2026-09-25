import os
import sys
import argparse
import numpy as np
import xarray as xr

# Grid constants
LATS = [round(5.0 + i * 0.25, 2) for i in range(101)]
LONS = [round(45.0 + i * 0.25, 2) for i in range(241)]
DEPTHS_M = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]

def check_file(file_path: str):
    problems = []
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
        
    print(f"Checking {file_path}...")
    
    if file_path.endswith('.nc'):
        try:
            ds = xr.open_dataset(file_path)
        except Exception as e:
            print(f"Error opening NetCDF: {e}")
            return
            
        var_name = "thetao"
        if var_name not in ds:
            problems.append(f"Variable '{var_name}' not found in NetCDF.")
            return
            
        arr = ds[var_name].values
        if arr.ndim == 4 and arr.shape[0] == 1:
            arr = arr[0]
            
        if arr.shape != (15, 101, 241):
            problems.append(f"Shape is {arr.shape}, expected (15, 101, 241) after removing time dimension.")
            
        # Check depths
        if 'depth' in ds:
            depths = ds['depth'].values
            if not np.allclose(depths, DEPTHS_M, atol=0.5):
                problems.append(f"Depths do not match standard depths. Got {depths}")
                
        # Check lat/lon
        if 'lat' in ds and 'lon' in ds:
            lat_vals = ds['lat'].values
            lon_vals = ds['lon'].values
            if len(lat_vals) > 1 and lat_vals[0] > lat_vals[-1]:
                print("Note: Latitude is descending. The backend will automatically flip it, but ascending is preferred.")
            
            # Simple check for lon range
            if lon_vals[0] >= 0 and lon_vals[-1] <= 360:
                pass # Accept 0-360
            if not (np.isclose(lon_vals[0], LONS[0], atol=0.1) and np.isclose(lon_vals[-1], LONS[-1], atol=0.1)):
                problems.append(f"Longitude range {lon_vals[0]} to {lon_vals[-1]} does not match expected {LONS[0]} to {LONS[-1]}.")
                
    elif file_path.endswith('.npy'):
        try:
            arr = np.load(file_path)
        except Exception as e:
            print(f"Error loading NumPy array: {e}")
            return
            
        if arr.shape != (15, 101, 241):
            problems.append(f"Shape is {arr.shape}, expected (15, 101, 241).")
    else:
        print("Error: Unsupported file format. Use .nc or .npy")
        return
        
    # Check values
    min_val = np.nanmin(arr)
    max_val = np.nanmax(arr)
    
    if min_val < -2 or max_val > 40:
        print(f"Warning: Values range from {min_val:.2f} to {max_val:.2f}, outside expected -2 to 40.")
        
    if not np.isnan(arr).any():
        print("Warning: No NaNs found. Ensure land cells are set to NaN.")
        
    if not problems:
        print("OK")
    else:
        print("Problems found:")
        for p in problems:
            print(f" - {p}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check model output file validity.")
    parser.add_argument("file", help="Path to .nc or .npy file")
    args = parser.parse_args()
    check_file(args.file)
