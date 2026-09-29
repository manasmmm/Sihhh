# Setup and operations reference

Detailed instructions that don't belong in the project's top-level `README.md`. See that file first for the project overview.

## Data source modes

`DATA_SOURCE` (env var, default `mock`):

- **`mock`** — bundled synthetic demo data. Amber "DEMO DATA" badge.
- **`files`** — reads daily model output files from `backend/data/model_output/`. Green "MODEL OUTPUT" badge. **Recommended for demos.**
- **`model`** — runs the trained model live inside the backend on each request. Green "MODEL: ..." badge.

```bash
# PowerShell
$env:DATA_SOURCE="files"; python backend/main.py
```

## Connecting model output (recommended path — no backend code changes)

1. Run the model wherever you normally do (notebook, Colab, script). For each day, build one array of shape `(15, 101, 241)` in °C — depths 0…1000 m, lat 5→30 ascending, lon 45→105 ascending, `NaN` on land. Patch-based models must assemble all ocean cells into the full grid first.
2. Save it with `save_model_output(pred, "YYYY-MM-DD", out_dir="backend/data/model_output", model_version="...")` from `scripts/save_model_output.py` (copy the function into your notebook).
3. Check it: `python scripts/check_model_output.py backend/data/model_output/thetao_YYYY-MM-DD.nc`
4. Start the backend with `DATA_SOURCE=files`.

New files appear in the dashboard within 30 seconds, no restart needed. Invalid files are rejected and listed in a banner in the header. Derived layers, NetCDF exports, the PFZ table and fisherman messages are computed automatically from whatever file is dropped in. The Explorer also has an "Upload model output" button that runs the same validation.

## Connecting the Kaggle GNN-OAM model directly

Two ways, using checkpoint `gnn_C_full_epoch_28.pt` (in `model/Model-Weights.zip`) plus the tree-stage models `rf_model_*.joblib`:

**A. Export on Kaggle, then drop the files in** (small download, no ML libraries needed locally)
1. Paste `kaggle/export_for_dashboard.py` as the last cell of the training notebook. Run the setup/cache-building sections first, then the export cell.
2. Download the exported zip and unzip it into `backend/data/` (`model_output/` and `validation/` land in place).
3. Start the backend with `DATA_SOURCE=files`.

**B. Run the model inside the backend** (any cached day, computed on demand)
1. `pip install torch --index-url https://download.pytorch.org/whl/cpu`. If the tree models are XGBoost, also install the matching `xgboost` version.
2. Copy the files listed in `backend/model_artifacts/README.md` into `backend/model_artifacts/`.
3. Check the setup: `python scripts/run_gnn_inference.py --list`
4. Optionally precompute a period and write real validation metrics: `python scripts/run_gnn_inference.py --start YYYY-MM-DD --end YYYY-MM-DD --validation`
5. Start the backend with `DATA_SOURCE=model`.

A day takes a few seconds on CPU the first time and is then served from `backend/data/gnn_output/`. The checkpoint name and model label are set in `backend/config.py` (`GNN_CHECKPOINT_NAME`, `GNN_MODEL_VERSION`).

## Data files the team maintains

| File | What to put in it |
|---|---|
| `backend/data/validation/validation_metrics.json` | Real per-depth RMSE/bias/corr/n from an evaluation script, with `"status": "final"`. |
| `config/species.json` | `t_min_c`/`t_max_c` from literature (CMFRI/FAO), with a citation in `source`. A species stays hidden in the UI while its values are `null`. |
| `backend/data/pfz/pfz_<SECTOR>_<YYYY-MM-DD>.csv` | Rows copied from the INCOIS PFZ page (see the existing Goa file for the column format). `lat`/`lon` can be left empty; they're computed from the DMS columns. |
| `backend/data/argo/argo_positions.csv` | `date,lat,lon,platform_id` for real ARGO profiles, used by the confidence layer (profiles within ±10 days of the product date). |
| `i18n/<lang>.json` | Copy `en.json` to add a coastal language. `hi.json` is a draft that should be reviewed by a native speaker. |

All thresholds and constants (front threshold, MLD criterion, confidence length scale, sector boxes, etc.) live in `backend/config.py`.

## API endpoints (all under `/api/v1`)

`meta`, `field`, `field.png`, `derived`, `derived.png`, `derived/legend`, `profile`, `timeseries`, `basin_average`, `argo_floats`, `pfz/sectors`, `pfz`, `pfz/enriched`, `species`, `i18n`, `validation`, `model-output/status`, `model-output/upload`, `export/netcdf`, `export/derived`, `export/pfz.csv`.

## Tests

```bash
python -m unittest discover -s scripts/tests -v
```
