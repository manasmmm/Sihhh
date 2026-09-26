# Put your Kaggle model artifacts here (DATA_SOURCE=model)

Copy files from `/kaggle/working/OceanEmbed_run/` into this folder (any sub-folder layout works; files are found by name):

| File | Needed | From |
|---|---|---|
| `gnn_C_full_epoch_20.pt` | yes | `checkpoints/` |
| `depth_cluster.json`, `season_regime.json` | yes | `gnn_artifacts/` |
| `rf_model_0.joblib`, `rf_model_1.joblib`, `rf_model_2.joblib` (tree / XGBoost stage) | yes | `gnn_artifacts/` |
| `finetune2024_x.npy`, `finetune2024_t.npy`, `finetune2024_meta.json` | for 2024 days | `cache/` |
| `finetune2024_y.npy` | recommended (exact sea-floor mask + validation) | `cache/` |
| `finetune_x.npy`, `finetune_t.npy`, `finetune_meta.json` (+ `finetune_y.npy`, `gnn_z.npy`, `gnn_z_meta.json`) | for 2016-2023 days | `cache/` |

Check with `python scripts/run_gnn_inference.py --list`. Everything in this folder is ignored by git.
