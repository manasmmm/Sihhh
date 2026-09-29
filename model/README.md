# Model files (OceanEmbed GNN-OAM)

These are the raw artifacts from the Kaggle training run, kept as-is for reference and reproducibility.

| File | What it is |
|---|---|
| `gnn-oam-6-layer-FINAL.ipynb` | The Kaggle training notebook: data harmonisation, the RF/XGBoost tree stage, the GNN-OAM model, training loop, and evaluation. |
| `Model-Weights.zip` | Trained weights: the `rf_model_*.joblib` tree-stage models plus `all_models.zip` (GNN-OAM checkpoints across epochs). |
| `Model-Training-and-Tuning.zip` | Small supporting artifacts from the run: cluster/season lookup tables (`depth_cluster.json`, `season_regime.json`), cache metadata, and stats used to reproduce training exactly. |

## Using these with the dashboard

The backend (`DATA_SOURCE=model`) reads a specific set of files by name from `backend/model_artifacts/` — see [`backend/model_artifacts/README.md`](../backend/model_artifacts/README.md) for the exact list and folder layout. To wire these up:

1. Unzip `Model-Weights.zip` and `Model-Training-and-Tuning.zip`.
2. Copy the checkpoint (`gnn_C_full_epoch_*.pt`, from inside `all_models.zip`), the `rf_model_*.joblib` files, `depth_cluster.json`, `season_regime.json`, and the cache files into `backend/model_artifacts/` (any sub-folder layout works; files are found by name).
3. Run `python scripts/run_gnn_inference.py --list` to confirm the backend can see them.

These files are not used automatically — the dashboard's day-by-day output in `backend/data/model_output/` was produced separately via the Kaggle export cell (`kaggle/export_for_dashboard.py`).
