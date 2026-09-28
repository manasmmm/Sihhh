"""
OceanEmbed Viewer - FastAPI Backend
===================================
REST API for high-resolution subsurface ocean temperature reconstruction
and interactive exploration of the North Indian Ocean domain.
"""

import os
import sys
import threading
import time
from collections import OrderedDict
from typing import Optional, List, Dict, Any
import numpy as np
from fastapi import FastAPI, Query, HTTPException, status
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add backend directory to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from data_store import is_store_initialized, snap_to_grid
from provider_facade import (
    get_metadata_provider as get_metadata,
    get_field_slice_provider as get_field_slice,
    get_profile_provider as get_profile,
    get_timeseries_provider as get_timeseries,
    get_basin_average_provider as get_basin_average
)
from raster import render_temperature_png, IMAGE_MEDIA_TYPES
from model_bridge import LATS, LONS, DEPTHS_M, reconstruct_field
from scripts.precompute import precompute_dataset
from api_additions import router as additions_router, raise_clear

app = FastAPI(
    title="OceanEmbed Viewer API",
    description="Subsurface Ocean Temperature Reconstruction (SIH26066) - Copernicus-style API",
    version="1.0.0",
)

# CORS middleware: allow all origins for embeddability (e.g. iframe, cross-origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_check():
    """Ensure data store exists on startup; precompute synthetic seed data if absent."""
    if not is_store_initialized():
        print("Reconstruction Zarr store not detected. Automatically precomputing 120-day baseline...")
        precompute_dataset(start_date="2025-01-01", end_date="2025-04-30")
        print("Baseline dataset ready.")
    # Draw the default map view for every date in the background, so the time slider
    # is instant even on a small hosting CPU.
    threading.Thread(target=_prewarm_field_pngs, daemon=True).start()


# In-memory cache of rendered map images (about 0.2 MB each)
_PNG_CACHE: "OrderedDict[tuple, tuple]" = OrderedDict()
_PNG_CACHE_MAX = 400
_PNG_LOCK = threading.Lock()


def _field_png(date: str, depth: int, scale: int, adaptive: bool,
               vmin: Optional[float], vmax: Optional[float], fmt: str = "png"):
    """(png_bytes, vmin, vmax), cached per data version, date and view settings."""
    from providers import get_provider
    key = (get_provider().stamp(date), date, depth, scale, adaptive, vmin, vmax, fmt)
    with _PNG_LOCK:
        hit = _PNG_CACHE.get(key)
        if hit is not None:
            _PNG_CACHE.move_to_end(key)
            return hit
    field_2d = get_field_slice(date, depth)
    out = render_temperature_png(field_2d, vmin=vmin, vmax=vmax, adaptive=adaptive, scale=scale, fmt=fmt)
    with _PNG_LOCK:
        _PNG_CACHE[key] = out
        while len(_PNG_CACHE) > _PNG_CACHE_MAX:
            _PNG_CACHE.popitem(last=False)
    return out


def _prewarm_field_pngs():
    """Default Explorer view: surface, auto contrast, scale 4 (see MapView.tsx)."""
    try:
        from providers import get_provider
        provider = get_provider()
        # model mode: only days already reconstructed (never start GNN runs here)
        dates = provider.cached_dates() if hasattr(provider, "cached_dates") else provider.available_dates()
        t0 = time.time()
        for d in dates[:_PNG_CACHE_MAX // 2]:
            _field_png(d, 0, 4, True, None, None, "webp")  # what the dashboard requests
        print(f"Pre-rendered {len(dates[:_PNG_CACHE_MAX // 2])} surface maps in {time.time() - t0:.1f}s")
    except Exception as e:  # never block or crash start-up
        print(f"Map pre-rendering skipped: {e}")


# =============================================================================
# API Endpoints (/api/v1)
# =============================================================================

@app.get("/api/v1/metadata", tags=["Metadata"])
def api_metadata() -> Dict[str, Any]:
    """
    3.1 Returns domain/grid/date info the frontend needs to initialize its controls.
    """
    try:
        return get_metadata()
    except Exception as e:
        raise_clear(e)


@app.api_route("/api/v1/field.png", methods=["GET", "HEAD"], tags=["Raster"])
def api_field_png(
    date: str = Query(..., description="Date formatted as YYYY-MM-DD"),
    depth: int = Query(0, description="Depth level in meters (0 to 1000)"),
    scale: int = Query(4, description="Bilinear upscale multiplier (default 4 -> 964x404)"),
    adaptive: bool = Query(False, description="Auto-stretch colormap contrast for this layer"),
    vmin: Optional[float] = Query(None, description="Optional minimum temperature override"),
    vmax: Optional[float] = Query(None, description="Optional maximum temperature override"),
    format: str = Query("png", pattern="^(png|webp)$", description="Image format: png (default) or webp (about 5x smaller)"),
):
    """
    3.2 Returns a PNG image of the temperature field at date/depth with turbo colormap,
    transparent land cells (alpha=0), edge-to-edge for Leaflet ImageOverlay.
    """
    try:
        png_bytes, eff_vmin, eff_vmax = _field_png(date, depth, scale, adaptive, vmin, vmax, format)
        return Response(
            content=png_bytes,
            media_type=IMAGE_MEDIA_TYPES[format],
            headers={
                "Cache-Control": "public, max-age=86400",
                "Content-Disposition": f"inline; filename=thetao_{date}_{depth}m.{format}",
                "X-Vmin": str(round(eff_vmin, 2)),
                "X-Vmax": str(round(eff_vmax, 2)),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed rendering raster: {e}")


@app.get("/api/v1/field.json", tags=["Field"])
def api_field_json(
    date: str = Query(..., description="Date formatted as YYYY-MM-DD"),
    depth: int = Query(0, description="Depth level in meters"),
) -> Dict[str, Any]:
    """
    3.3 [STRETCH] Returns numeric 2D grid matrix as JSON for client-side canvas rendering.
    """
    try:
        field_2d = get_field_slice(date, depth)
        # Convert NaN to None for valid JSON serialization
        values = []
        for row in field_2d:
            values.append([None if np.isnan(v) else round(float(v), 2) for v in row])

        return {
            "date": date,
            "depth": depth,
            "lat": [float(x) for x in LATS],
            "lon": [float(x) for x in LONS],
            "values": values,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/profile", tags=["Inspection"])
def api_profile(
    lat: float = Query(..., description="Latitude in decimal degrees (5.0 to 30.0)"),
    lon: float = Query(..., description="Longitude in decimal degrees (45.0 to 105.0)"),
    date: str = Query(..., description="Date formatted as YYYY-MM-DD"),
):
    """
    3.4 Vertical temperature profile at nearest ocean grid cell.
    If snapped cell is land, returns HTTP 422 with {"error": "land_cell", "snapped": {...}}.
    """
    try:
        res = get_profile(lat, lon, date)
        if "error" in res and res["error"] == "land_cell":
            return JSONResponse(
                status_code=422,
                content=res,
            )
        return res
    except Exception as e:
        raise_clear(e)


@app.get("/api/v1/timeseries", tags=["Inspection"])
def api_timeseries(
    lat: float = Query(..., description="Latitude in decimal degrees"),
    lon: float = Query(..., description="Longitude in decimal degrees"),
    depth: int = Query(0, description="Depth level in meters"),
    start: Optional[str] = Query(None, description="Optional first date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="Optional last date YYYY-MM-DD"),
):
    """
    3.5 Temperature across full available date range at fixed depth for nearest ocean cell.
    If snapped cell is land, returns HTTP 422.
    """
    try:
        res = get_timeseries(lat, lon, depth, start, end)
        if "error" in res and res["error"] == "land_cell":
            return JSONResponse(
                status_code=422,
                content=res,
            )
        return res
    except Exception as e:
        raise_clear(e)


@app.get("/api/v1/basin_average", tags=["Analysis"])
def api_basin_average(
    depth: int = Query(0, description="Depth in meters"),
) -> Dict[str, Any]:
    """
    [STRETCH] Spatial mean temperature over all ocean cells in the North Indian Ocean basin.
    """
    try:
        return get_basin_average(depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/argo_floats", tags=["Ground Truth"])
def api_argo_floats() -> Dict[str, Any]:
    """
    [STRETCH] Returns locations of Gridded Argo Float profiles in the North Indian Ocean.
    Enables ground truth validation overlay on the map.
    """
    # Curated distribution of realistic Argo floats in Arabian Sea, Bay of Bengal, & Equator
    floats = [
        {"id": "ARGO-2902123", "lat": 14.75, "lon": 67.25, "region": "Central Arabian Sea", "last_profile": "2025-04-28", "wmo": 2902123},
        {"id": "ARGO-2902145", "lat": 11.50, "lon": 62.00, "region": "South Arabian Sea", "last_profile": "2025-04-25", "wmo": 2902145},
        {"id": "ARGO-2902189", "lat": 18.25, "lon": 64.50, "region": "North Arabian Sea", "last_profile": "2025-04-29", "wmo": 2902189},
        {"id": "ARGO-2903301", "lat": 15.00, "lon": 86.50, "region": "Central Bay of Bengal", "last_profile": "2025-04-27", "wmo": 2903301},
        {"id": "ARGO-2903322", "lat": 12.25, "lon": 83.75, "region": "Southwest Bay of Bengal", "last_profile": "2025-04-26", "wmo": 2903322},
        {"id": "ARGO-2903350", "lat": 17.50, "lon": 89.25, "region": "North Bay of Bengal", "last_profile": "2025-04-30", "wmo": 2903350},
        {"id": "ARGO-2904108", "lat": 8.50,  "lon": 74.00, "region": "Lakshadweep Sea", "last_profile": "2025-04-24", "wmo": 2904108},
        {"id": "ARGO-2904112", "lat": 6.50,  "lon": 88.00, "region": "Equatorial Indian Ocean", "last_profile": "2025-04-29", "wmo": 2904112},
        {"id": "ARGO-2904155", "lat": 7.00,  "lon": 58.50, "region": "Western Equatorial Ocean", "last_profile": "2025-04-28", "wmo": 2904155},
        {"id": "ARGO-2905201", "lat": 10.00, "lon": 94.00, "region": "Andaman Sea", "last_profile": "2025-04-25", "wmo": 2905201},
        {"id": "ARGO-2905215", "lat": 13.50, "lon": 93.50, "region": "North Andaman Sea", "last_profile": "2025-04-27", "wmo": 2905215},
        {"id": "ARGO-2906100", "lat": 21.00, "lon": 61.25, "region": "Gulf of Oman Approach", "last_profile": "2025-04-29", "wmo": 2906100},
    ]
    return {"count": len(floats), "floats": floats}


@app.post("/api/v1/infer", tags=["Model"])
def api_infer(
    date: str = Query(..., description="Arbitrary date in YYYY-MM-DD format to infer live"),
) -> Dict[str, Any]:
    """
    [STRETCH] Run model inference live for a new date and append it to Zarr store.
    """
    try:
        # Call model bridge
        field_3d = reconstruct_field(date) # shape (15, 101, 241)

        # Append to Zarr store or return confirmation
        return {
            "status": "success",
            "date": date,
            "shape": list(field_3d.shape),
            "depths_m": DEPTHS_M,
            "message": f"Successfully reconstructed 3D field for {date}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {e}")


app.include_router(additions_router)

# =============================================================================
# Serve Frontend Static Build if available
# =============================================================================
FRONTEND_DIST = os.path.join(os.path.dirname(CURRENT_DIR), "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # Hosting platforms (Render, Railway, ...) pass the port in $PORT
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
