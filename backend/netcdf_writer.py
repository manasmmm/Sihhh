import os
from datetime import datetime, timedelta
import xarray as xr
from config import OUTPUT_DIR, VALIDITY_DAYS
from providers import get_provider

def generate_netcdf(date: str) -> str:
    """
    Generate CF-1.8 compliant NetCDF for a given date.
    Returns path to the saved file.
    """
    file_path = os.path.join(OUTPUT_DIR, f"thetao_{date}.nc")
    
    provider = get_provider()
    ds = provider.get_temperature(date)
    
    source = ds.attrs.get("source", "unknown")
    model_version = ds.attrs.get("model_version", "unknown")
    generated_at = ds.attrs.get("generated_at", datetime.utcnow().isoformat() + "Z")
    
    valid_upto = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=VALIDITY_DAYS)).strftime("%Y-%m-%d")
    
    # Format Dataset for CF-1.8
    # Add time dimension
    ds = ds.expand_dims({"time": [1]})
    # Time variable needs CF units
    ds["time"].attrs = {
        "units": f"days since {date} 00:00:00",
        "axis": "T",
    }
    
    # Global attributes
    ds.attrs = {
        "title": "OceanEmbed subsurface temperature reconstruction",
        "institution": "Team Crisis Workers, SIH 2026",
        "source": source,
        "model_version": model_version,
        "generated_at": generated_at,
        "valid_upto": valid_upto,
        "geospatial_lat_min": float(ds.lat.min()),
        "geospatial_lat_max": float(ds.lat.max()),
        "geospatial_lon_min": float(ds.lon.min()),
        "geospatial_lon_max": float(ds.lon.max()),
        "history": f"{datetime.utcnow().isoformat()}Z: Created via OceanEmbed backend",
        "Conventions": "CF-1.8"
    }

    # Use _FillValue instead of just keeping NaNs
    encoding = {
        "thetao": {
            "_FillValue": float("nan"),
            "zlib": True,
            "complevel": 4
        }
    }
    
    # Write to disk
    ds.to_netcdf(file_path, encoding=encoding, engine="netcdf4")
    return file_path
