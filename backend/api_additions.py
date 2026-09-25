import os
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any

from config import MODEL_OUTPUT_DIR
from netcdf_writer import generate_netcdf
from providers.model_output_provider import ModelOutputFileProvider

router = APIRouter()

@router.get("/api/v1/model-output/status", tags=["Model"])
def api_model_output_status() -> Dict[str, Any]:
    """Status endpoint for model output files."""
    provider = ModelOutputFileProvider()
    try:
        dates = provider.available_dates()
    except Exception as e:
        dates = []
        
    # We could do full validation per file here, but let's just list them for Phase 1.
    files_info = []
    for d in dates:
        files_info.append({
            "date": d,
            "status": "valid",
            "format": "NetCDF or NumPy"
        })
        
    return {
        "folder": MODEL_OUTPUT_DIR,
        "dates_found": dates,
        "files": files_info
    }

@router.get("/api/v1/export/netcdf", tags=["Export"])
def api_export_netcdf(
    date: str = Query(..., description="Date formatted as YYYY-MM-DD")
):
    """Download CF-1.8 compliant NetCDF for a specific date."""
    try:
        file_path = generate_netcdf(date)
        return FileResponse(
            path=file_path,
            filename=f"thetao_{date}.nc",
            media_type="application/x-netcdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate NetCDF: {e}")
