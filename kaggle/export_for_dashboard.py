# =============================================================================
# 30. Export for the OceanEmbed dashboard  (paste as the LAST cell of OceanEmbed-GNN-OAM-FULL.ipynb)
# =============================================================================
# Before running this cell, run Sections 1-17 (setup, caches, RF/XGBoost stage, cluster tables).
# For EXPORT_PERIOD = "2024" also run Sections 24-26 (2024 cache + its z_col cache).
# Nothing is retrained; the cached steps are skipped automatically.
#
# Writes /kaggle/working/dashboard_export.zip containing:
#   model_output/thetao_YYYY-MM-DD.nc + .json  -> backend/data/model_output/   (DATA_SOURCE=files)
#   validation/validation_metrics.json         -> backend/data/validation/
#   versions.txt                                (library versions used here)
# and, if EXPORT_ARTIFACTS = True, /kaggle/working/dashboard_artifacts.zip with the files the
# backend needs to run the model itself (DATA_SOURCE=model) -> unzip into backend/model_artifacts/
import zipfile

EXPORT_CHECKPOINT = f"{CFG['CHECKPOINT_DIR']}/gnn_C_full_epoch_20.pt"   # the epoch you want to show
EXPORT_VARIANT = "C_full"
EXPORT_PERIOD = "2024"          # "2024" (fine-tune year, needs Sections 24-26) or "2023" (original test year)
EXPORT_START, EXPORT_END = None, None   # e.g. "2024-12-01", "2024-12-31"; None = whole held-out split
EXPORT_STRIDE = 1               # every Nth day (raise to keep the zip small)
EXPORT_MAX_DAYS = 31            # safety cap on the number of daily files
EXPORT_ARTIFACTS = False        # True -> also zip checkpoint + tree models + cluster JSONs + input cache
EXPORT_DIR = "/kaggle/working/dashboard_export"
MODEL_VERSION = "OceanEmbed GNN-OAM C_full epoch 20 + XGBoost stage"

_STANDARD_LATS = np.round(np.arange(101) * 0.25 + 5.0, 2)
_STANDARD_LONS = np.round(np.arange(241) * 0.25 + 45.0, 2)


def _pick_state():
    if EXPORT_PERIOD == "2024":
        if "STATE_2024" not in globals():
            raise RuntimeError("STATE_2024 not found -- run Sections 24-26 first (or set EXPORT_PERIOD = '2023').")
        return STATE_2024, STATE_2024["ends_test"]
    base = globals().get("STATE_ORIGINAL", STATE)
    return base, base["ends_test"]


def _save_day(pred, day, out_dir, meta):
    """Same format as scripts/save_model_output.py in the dashboard repo."""
    ds = xr.Dataset(
        {"thetao": (("time", "depth", "lat", "lon"), pred[None].astype("float32"),
                    {"units": "degree_Celsius", "standard_name": "sea_water_potential_temperature",
                     "long_name": "Reconstructed sea water potential temperature"})},
        coords={"time": [np.datetime64(day, "ns")], "depth": CFG["STANDARD_DEPTHS"].astype("float32"),
                "lat": _STANDARD_LATS, "lon": _STANDARD_LONS},
        attrs={"Conventions": "CF-1.8", "title": "OceanEmbed subsurface temperature reconstruction",
               "model_version": MODEL_VERSION})
    ds.to_netcdf(f"{out_dir}/thetao_{day}.nc", encoding={
        "thetao": {"zlib": True, "complevel": 4, "_FillValue": np.float32(np.nan)},
        "time": {"units": "days since 1970-01-01 00:00:00", "calendar": "standard"}})
    json.dump(meta, open(f"{out_dir}/thetao_{day}.json", "w"), indent=2)


def export_for_dashboard():
    global STATE
    saved_state = STATE
    S, ends = _pick_state()
    STATE = S                                         # reconstruct_day / build_tile_graph read the global STATE
    try:
        if "Zmm" not in STATE:
            STATE["Zmm"] = np.load((z_cache_paths_2024() if EXPORT_PERIOD == "2024" else z_cache_paths())["z"],
                                   mmap_mode="r")
        times = STATE["times"]
        sel = [int(e) for e in ends
               if (EXPORT_START is None or str(times[e]) >= EXPORT_START)
               and (EXPORT_END is None or str(times[e]) <= EXPORT_END)][::EXPORT_STRIDE][:EXPORT_MAX_DAYS]
        if not sel:
            raise RuntimeError("No days selected -- widen EXPORT_START/EXPORT_END.")

        model = build_gnn_model().to(DEVICE)
        model.set_frozen_lookups(STATE["season_labels"])
        ck = load_gnn_checkpoint(EXPORT_CHECKPOINT, model)
        use_skip = EXPORT_VARIANT in ("B_skip", "C_full")
        print(f"Loaded {os.path.basename(EXPORT_CHECKPOINT)} (epoch {ck.get('epoch')}). "
              f"Exporting {len(sel)} day(s): {times[sel[0]]} .. {times[sel[-1]]}")

        shutil.rmtree(EXPORT_DIR, ignore_errors=True)
        out_dir = f"{EXPORT_DIR}/model_output"
        os.makedirs(out_dir); os.makedirs(f"{EXPORT_DIR}/validation")
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        PRED, TRUE = [], []
        for i, e in enumerate(sel, 1):
            predT, _ = reconstruct_day(model, e, use_skip)
            predT[~STATE["ocean3d"]] = np.nan                                  # land + below the sea floor
            trueT = denormalise(np.asarray(STATE["Y"][e, :, :H, :W], dtype="float32"), STATE["tstats"])
            day = str(times[e])[:10]
            _save_day(predT, day, out_dir, {"model_version": MODEL_VERSION, "generated_at": stamp,
                                            "notes": f"{os.path.basename(EXPORT_CHECKPOINT)}, held-out {EXPORT_PERIOD} day"})
            PRED.append(predT); TRUE.append(np.where(np.isfinite(predT), trueT, np.nan))
            print(f"  {i}/{len(sel)} {day}", flush=True)

        m = metrics_per_depth(np.stack(PRED), np.stack(TRUE))
        n = [int((np.isfinite(np.stack(PRED)[:, k]) & np.isfinite(np.stack(TRUE)[:, k])).sum()) for k in range(D)]
        rnd = lambda v: None if not np.isfinite(v) else round(float(v), 4)
        json.dump({
            "status": "final",
            "reference": "GLORYS12 reanalysis (Copernicus), regridded to 0.25 deg / 15 standard depths - held-out days",
            "period": f"{times[sel[0]]} to {times[sel[-1]]}, {len(sel)} day(s) ({EXPORT_PERIOD} held-out split)",
            "model_version": MODEL_VERSION,
            "checkpoint": os.path.basename(EXPORT_CHECKPOINT),
            "metrics": [{"depth_m": int(CFG["STANDARD_DEPTHS"][k]), "rmse_c": rnd(m["rmse"][k]),
                         "bias_c": rnd(m["bias"][k]), "corr": rnd(m["corr"][k]), "n": n[k]} for k in range(D)],
        }, open(f"{EXPORT_DIR}/validation/validation_metrics.json", "w"), indent=2)

        import sklearn
        vers = {"python": sys.version.split()[0], "numpy": np.__version__, "torch": torch.__version__,
                "scikit-learn": sklearn.__version__, "joblib": joblib.__version__}
        try:
            import xgboost
            vers["xgboost"] = xgboost.__version__
        except ImportError:
            pass
        open(f"{EXPORT_DIR}/versions.txt", "w").write("\n".join(f"{k}=={v}" for k, v in vers.items()) + "\n")

        zpath = "/kaggle/working/dashboard_export.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for rootd, _, files in os.walk(EXPORT_DIR):
                for f in files:
                    z.write(os.path.join(rootd, f), os.path.relpath(os.path.join(rootd, f), EXPORT_DIR))
        print(f"\nWrote {zpath} ({os.path.getsize(zpath) / 1e6:.1f} MB). Versions: {vers}")

        if EXPORT_ARTIFACTS:
            stage = "finetune2024" if EXPORT_PERIOD == "2024" else "finetune"
            cp = cache_paths(stage)
            files = [EXPORT_CHECKPOINT, f"{ARTIFACT_DIR}/depth_cluster.json", f"{ARTIFACT_DIR}/season_regime.json",
                     *rf_paths(), cp["x"], cp["t"], cp["meta"], cp["y"], f"{EXPORT_DIR}/versions.txt"]
            apath = "/kaggle/working/dashboard_artifacts.zip"
            with zipfile.ZipFile(apath, "w", zipfile.ZIP_STORED) as z:
                for f in files:
                    if os.path.exists(f):
                        z.write(f, os.path.basename(f))
            print(f"Wrote {apath} ({os.path.getsize(apath) / 1e9:.2f} GB) -> unzip into backend/model_artifacts/")
    finally:
        STATE = saved_state


export_for_dashboard()
