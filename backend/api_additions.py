"""
New API endpoints (spec Section 7). Existing /api/v1 endpoints in main.py are
unchanged; everything here is additive and uses the same /api/v1 prefix.
"""
import csv
import io
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response

import config
from config import MODEL_OUTPUT_DIR, DEPTHS_M, LATS, LONS
from providers import get_provider
from provider_facade import get_dataset, get_derived, get_metadata_provider, valid_upto

router = APIRouter(prefix="/api/v1")


# --------------------------------------------------------------- helpers
def raise_clear(e: Exception):
    """Map provider/data errors to HTTP errors with a readable message."""
    if isinstance(e, HTTPException):
        raise e
    if isinstance(e, NotImplementedError):
        raise HTTPException(status_code=501, detail=str(e))
    if isinstance(e, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, ValueError):
        raise HTTPException(status_code=422, detail=str(e))
    raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


def _check_date(date: str) -> str:
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid date '{date}', expected YYYY-MM-DD")
    return date


def _require_date(date: str) -> str:
    """Strict: the date must be offered by the current data source."""
    _check_date(date)
    try:
        dates = get_provider().available_dates()
    except Exception as e:
        raise_clear(e)
    if date not in dates:
        if config.DATA_SOURCE == "files":
            msg = f"No model output for {date} in data/model_output/"
            v = getattr(get_provider(), "validation_for", lambda d: None)(date)
            if v and not v["valid"]:
                msg = f"Model output for {date} failed validation: " + "; ".join(v["errors"])
        else:
            msg = f"No data for {date} from data source '{config.DATA_SOURCE}'"
        raise HTTPException(status_code=404, detail=msg)
    return date


def _grid_json(arr: np.ndarray, date: str, units: str, source: str, nd: int, **extra) -> Dict[str, Any]:
    a = np.round(arr.astype(np.float64), nd)
    values = np.where(np.isnan(a), None, a).tolist()
    return {"date": date, "valid_upto": valid_upto(date), "source": source, "units": units,
            "lat": list(LATS), "lon": list(LONS), "values": values, **extra}


# --------------------------------------------------------------- meta
@router.get("/meta", tags=["Metadata"])
def api_meta():
    try:
        return get_metadata_provider()
    except Exception as e:
        raise_clear(e)


@router.get("/field", tags=["Field"])
def api_field(date: str = Query(...), depth: int = Query(0)):
    _require_date(date)
    if depth not in DEPTHS_M:
        raise HTTPException(status_code=422, detail=f"depth must be one of {DEPTHS_M}")
    try:
        ds = get_dataset(date)
    except Exception as e:
        raise_clear(e)
    return _grid_json(ds["thetao"].values[DEPTHS_M.index(depth)], date, "degree_Celsius",
                      ds.attrs.get("source"), 2, depth=depth, variable="thetao",
                      model_version=ds.attrs.get("model_version"))


# ------------------------------------------------------------ derived
def _check_var(var: str):
    from derived import DERIVED_VARS
    if var not in DERIVED_VARS:
        raise HTTPException(status_code=422, detail=f"var must be one of {DERIVED_VARS}")


@router.get("/derived", tags=["Derived"])
def api_derived(date: str = Query(...), var: str = Query(...)):
    _check_var(var)
    _require_date(date)
    try:
        der = get_derived(date)
    except Exception as e:
        raise_clear(e)
    nd = 4 if var.startswith("front") or var == "confidence" else 2
    extra = {"variable": var, "long_name": der[var].attrs.get("long_name"),
             "front_threshold_c_per_km": config.FRONT_THRESHOLD_C_PER_KM}
    if var == "confidence":
        extra["available"] = bool(der.attrs.get("confidence_available"))
        extra["note"] = der.attrs.get("confidence_note")
    return _grid_json(der[var].values, date, der[var].attrs.get("units"), der.attrs.get("source"), nd, **extra)


@router.api_route("/derived.png", methods=["GET", "HEAD"], tags=["Derived"])
def api_derived_png(date: str = Query(...), var: str = Query(...), scale: int = Query(4, ge=1, le=8)):
    from derived_raster import render_derived_png
    _check_var(var)
    _require_date(date)
    try:
        der = get_derived(date)
        png, vmin, vmax = render_derived_png(der[var].values, var, scale=scale)
    except Exception as e:
        raise_clear(e)
    headers = {"Cache-Control": "no-cache", "X-Vmin": str(vmin), "X-Vmax": str(vmax)}
    if var == "confidence":
        headers["X-Available"] = "1" if der.attrs.get("confidence_available") else "0"
    return Response(content=png, media_type="image/png", headers=headers)


@router.get("/derived/legend", tags=["Derived"])
def api_derived_legend(var: str = Query(...)):
    from derived import DERIVED_META
    from derived_raster import colormap_stops
    _check_var(var)
    disp = config.DERIVED_DISPLAY[var]
    return {"var": var, "vmin": disp["vmin"], "vmax": disp["vmax"], "units": DERIVED_META[var][0],
            "long_name": DERIVED_META[var][1], "stops": colormap_stops(var),
            "front_threshold_c_per_km": config.FRONT_THRESHOLD_C_PER_KM,
            "confidence_thresholds": {"high": config.CONF_HIGH_MIN, "medium": config.CONF_MEDIUM_MIN}}


# --------------------------------------------------------------- PFZ
@router.get("/pfz/sectors", tags=["PFZ"])
def api_pfz_sectors():
    from pfz import available_pfz
    avail = available_pfz()
    return {"default": config.PFZ_DEFAULT_SECTOR,
            "bbox_note": "Sector bounding boxes are approximate and used only to zoom the map.",
            "sectors": [{**s, "dates": avail.get(s["code"], [])} for s in config.PFZ_SECTORS]}


@router.get("/pfz", tags=["PFZ"])
def api_pfz(sector: str = Query(...), date: str = Query(...)):
    from pfz import load_pfz, sector_info
    _check_date(date)
    if sector_info(sector) is None:
        raise HTTPException(status_code=422, detail=f"Unknown sector '{sector}'")
    rows, problems = load_pfz(sector, date)
    return {"sector": sector_info(sector)["code"], "date": date, "rows": rows, "problems": problems,
            "message": None if rows else "No PFZ advisory loaded for this sector and date"}


@router.get("/pfz/enriched", tags=["PFZ"])
def api_pfz_enriched(sector: str = Query(...), date: str = Query(...),
                     species: Optional[str] = Query(None), lang: str = Query(config.DEFAULT_LANGUAGE)):
    from pfz import enrich, sector_info
    _check_date(date)
    if sector_info(sector) is None:
        raise HTTPException(status_code=422, detail=f"Unknown sector '{sector}'")
    return enrich(sector, date, species=species or None, lang=lang)


@router.get("/export/pfz.csv", tags=["Export"])
def api_export_pfz_csv(sector: str = Query(...), date: str = Query(...),
                       species: Optional[str] = Query(None), lang: str = Query(config.DEFAULT_LANGUAGE)):
    from pfz import enrich, sector_info
    _check_date(date)
    if sector_info(sector) is None:
        raise HTTPException(status_code=422, detail=f"Unknown sector '{sector}'")
    res = enrich(sector, date, species=species or None, lang=lang)
    if not res["rows"]:
        raise HTTPException(status_code=404, detail=res["message"])
    cols = config.PFZ_COLUMNS + ["grid_cell_lat", "grid_cell_lon", "d20_m", "mld_m", "front_50m",
                                 "subsurface_front", "confidence", "confidence_level"]
    if res.get("species") and res["species"].get("configured"):
        cols += ["gear_depth_from_m", "gear_depth_to_m"]
    cols += [f"thetao_{d}m" for d in DEPTHS_M] + ["summary_text"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in res["rows"]:
        prof = r.get("profile") or [None] * len(DEPTHS_M)
        vals = {**r, **{f"thetao_{d}m": prof[i] for i, d in enumerate(DEPTHS_M)}}
        w.writerow(["" if vals.get(c) is None else vals.get(c) for c in cols])
    fname = f"pfz_enriched_{res['sector']}_{date}.csv"
    return Response(content=buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/species", tags=["PFZ"])
def api_species():
    from pfz import load_species
    sp = load_species()
    return {"species": sp, "any_configured": any(s["configured"] for s in sp),
            "message": None if any(s["configured"] for s in sp) else "Species temperature ranges not configured"}


# -------------------------------------------------------------- i18n
@router.get("/i18n", tags=["i18n"])
def api_languages():
    from summary import available_languages
    return {"default": config.DEFAULT_LANGUAGE, "languages": available_languages()}


@router.get("/i18n/{lang}", tags=["i18n"])
def api_strings(lang: str):
    from summary import load_strings
    if not os.path.exists(os.path.join(config.I18N_DIR, f"{os.path.basename(lang)}.json")):
        raise HTTPException(status_code=404, detail=f"No translation file i18n/{lang}.json")
    return load_strings(os.path.basename(lang))


# -------------------------------------------------------- validation
@router.get("/validation", tags=["Validation"])
def api_validation():
    path = config.VALIDATION_METRICS_FILE
    if not os.path.exists(path):
        return {"status": "missing", "message": "Validation results pending (data/validation/validation_metrics.json not found)",
                "metrics": []}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"validation_metrics.json could not be read: {e}", "metrics": []}
    data.pop("_comment", None)
    if data.get("status") != "final":
        data["message"] = "Validation results pending"
    return data


# ------------------------------------------------------ model output
@router.get("/model-output/status", tags=["Model"])
def api_model_output_status() -> Dict[str, Any]:
    from providers.model_output_provider import ModelOutputFileProvider
    p = ModelOutputFileProvider()
    files = p.scan()
    return {
        "folder": MODEL_OUTPUT_DIR,
        "data_source": config.DATA_SOURCE,
        "active": config.DATA_SOURCE == "files",
        "dates_found": sorted({f["date"] for f in files if f["valid"] and f["date"]}),
        "files": files,
    }


@router.post("/model-output/upload", tags=["Model"])
async def api_model_output_upload(request: Request, filename: str = Query(...),
                                  model_version: Optional[str] = Query(None)):
    """Upload one thetao_YYYY-MM-DD.nc|.npy file as the raw request body.
    It is validated first and only saved to MODEL_OUTPUT_DIR if valid."""
    from model_output_validation import parse_file_name, validate_file
    from model_bridge import get_land_mask

    name = os.path.basename(filename)
    day, fmt = parse_file_name(name)
    if day is None:
        raise HTTPException(status_code=422, detail="File name must be thetao_YYYY-MM-DD.nc or thetao_YYYY-MM-DD.npy")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=422, detail="Empty upload")
    if len(body) > config.UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    tmpdir = tempfile.mkdtemp(prefix="oe_upload_")
    try:
        tmp = os.path.join(tmpdir, name)
        with open(tmp, "wb") as f:
            f.write(body)
        res = validate_file(tmp, land_mask=get_land_mask())
        res.data = None
        result = res.to_dict()
        if not res.valid:
            return JSONResponse(status_code=422, content={"saved": False, **result})
        dest = os.path.join(MODEL_OUTPUT_DIR, name)
        shutil.move(tmp, dest)
        if model_version:
            with open(os.path.join(MODEL_OUTPUT_DIR, f"thetao_{day}.json"), "w", encoding="utf-8") as f:
                json.dump({"model_version": model_version,
                           "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "notes": "uploaded through the dashboard"}, f, indent=2)
        return {"saved": True, "path": dest, **result}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ------------------------------------------------------------ export
@router.get("/export/netcdf", tags=["Export"])
def api_export_netcdf(date: str = Query(..., description="Date formatted as YYYY-MM-DD")):
    """Download CF-1.8 compliant NetCDF (thetao) for a date."""
    from netcdf_writer import generate_netcdf
    _require_date(date)
    try:
        path = generate_netcdf(date)
    except Exception as e:
        raise_clear(e)
    return FileResponse(path=path, filename=f"thetao_{date}.nc", media_type="application/x-netcdf")


@router.get("/export/derived", tags=["Export"])
def api_export_derived(date: str = Query(...)):
    """Download derived layers NetCDF for a date."""
    from netcdf_writer import generate_derived_netcdf
    _require_date(date)
    try:
        path = generate_derived_netcdf(date)
    except Exception as e:
        raise_clear(e)
    return FileResponse(path=path, filename=f"derived_{date}.nc", media_type="application/x-netcdf")
