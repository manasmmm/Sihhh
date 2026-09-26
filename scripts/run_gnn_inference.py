"""
Batch-run the OceanEmbed GNN-OAM model inside the backend for a date range.

    python scripts/run_gnn_inference.py --list
    python scripts/run_gnn_inference.py --start 2023-06-01 --end 2023-06-30
    python scripts/run_gnn_inference.py --start 2023-01-01 --end 2023-12-31 --stride 7 --validation

Uses the artifacts in backend/model_artifacts/ (see backend/gnn_engine/artifacts.py).
Each day is stored in backend/data/gnn_output/ and then served instantly by the
dashboard with DATA_SOURCE=model.

--export-files  also copies each day to backend/data/model_output/ (for DATA_SOURCE=files)
--validation    compares every reconstructed day with the GLORYS target cache (<stage>_y.npy)
                and writes backend/data/validation/validation_metrics.json (status "final").
                Use held-out days (2023 = notebook test year, or 2024) for honest numbers.
"""
import argparse
import json
import os
import shutil
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "backend"))
os.environ.setdefault("DATA_SOURCE", "model")

import config  # noqa: E402
from gnn_engine.engine import get_engine  # noqa: E402
from providers.model_provider import ModelProvider, _cache_paths  # noqa: E402


def metrics_per_depth(P, T):
    rows = []
    for k, dz in enumerate(config.DEPTHS_M):
        p, t = P[:, k].ravel(), T[:, k].ravel()
        v = np.isfinite(p) & np.isfinite(t)
        if v.sum() < 2:
            rows.append({"depth_m": dz, "rmse_c": None, "bias_c": None, "corr": None, "n": int(v.sum())})
            continue
        d = p[v] - t[v]
        corr = float(np.corrcoef(p[v], t[v])[0, 1]) if np.std(p[v]) > 1e-8 and np.std(t[v]) > 1e-8 else None
        rows.append({"depth_m": dz, "rmse_c": round(float(np.sqrt(np.mean(d ** 2))), 4),
                     "bias_c": round(float(np.mean(d)), 4), "corr": None if corr is None else round(corr, 4),
                     "n": int(v.sum())})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--stride", type=int, default=1, help="use every Nth day")
    ap.add_argument("--list", action="store_true", help="show which dates can be reconstructed and exit")
    ap.add_argument("--export-files", action="store_true")
    ap.add_argument("--validation", action="store_true")
    args = ap.parse_args()

    eng = get_engine()
    dates = eng.available_dates()
    print(f"Artifacts: {os.path.relpath(eng.art.root, REPO)}")
    print(f"  checkpoint : {os.path.basename(eng.art.checkpoint)}")
    print(f"  tree stage : {', '.join(os.path.basename(p) for p in eng.art.tree_models) or 'none (precomputed gnn_z only)'}")
    print(f"  caches     : {', '.join(eng.art.stages)} | ocean mask from {eng.mask_source}")
    print(f"  K={eng.K} depth clusters, M={eng.M} season regimes, {len(eng.origins)} tiles/day")
    if not dates:
        sys.exit("No reconstructable dates found.")
    print(f"  {len(dates)} dates: {dates[0]} .. {dates[-1]}")
    if args.list:
        return

    sel = [d for d in dates if (not args.start or d >= args.start) and (not args.end or d <= args.end)]
    sel = sel[::max(args.stride, 1)]
    if not sel:
        sys.exit("No available dates in the requested range.")
    info = eng.model_info
    print(f"Model: epoch {info.get('epoch')}, d_model {info['d_model']}, {info['layers']} OAM layers, "
          f"{info['heads']} heads. Reconstructing {len(sel)} day(s) ...")

    provider = ModelProvider()
    P, T, used = [], [], []
    t0 = time.time()
    for i, d in enumerate(sel, 1):
        arr = provider.get_temperature(d)["thetao"].values
        if args.export_files:
            nc, js = _cache_paths(d)
            shutil.copy(nc, os.path.join(config.MODEL_OUTPUT_DIR, os.path.basename(nc)))
            shutil.copy(js, os.path.join(config.MODEL_OUTPUT_DIR, os.path.basename(js)))
        if args.validation:
            t = eng.truth(d)
            if t is not None:
                P.append(arr); T.append(t); used.append(d)
        el = time.time() - t0
        print(f"  [{i}/{len(sel)}] {d}  ({el / i:.1f}s/day, ~{(len(sel) - i) * el / i / 60:.1f} min left)", flush=True)

    if args.validation:
        if not used:
            print("No GLORYS target cache (<stage>_y.npy) for these days -> validation file not written.")
            return
        splits = sorted({eng.split_of(d) for d in used})
        if "train" in splits:
            print("WARNING: some days are from the training years; metrics on them are optimistic.")
        out = {
            "status": "final",
            "reference": "GLORYS12 reanalysis (Copernicus), regridded to 0.25 deg / 15 standard depths - the model's training target",
            "period": f"{used[0]} to {used[-1]}, {len(used)} day(s), split: {'/'.join(splits)}",
            "model_version": config.GNN_MODEL_VERSION,
            "checkpoint": os.path.basename(eng.art.checkpoint),
            "metrics": metrics_per_depth(np.stack(P), np.stack(T)),
        }
        with open(config.VALIDATION_METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"Wrote {os.path.relpath(config.VALIDATION_METRICS_FILE, REPO)}")
        for m in out["metrics"]:
            print(f"  {m['depth_m']:>5} m  RMSE {m['rmse_c']}  bias {m['bias_c']}  corr {m['corr']}")


if __name__ == "__main__":
    main()
