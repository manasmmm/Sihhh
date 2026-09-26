"""Builds a small fake Kaggle OceanEmbed_run folder (same file names, shapes and formats as the
notebook) for testing the in-backend GNN engine without the real 5 GB artifacts."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


def make_fake_run(root, n_days=40, start="2023-06-01", with_y=True, with_z=False, K=3, M=4, seed=0):
    import joblib
    import torch
    from sklearn.ensemble import RandomForestRegressor
    from gnn_engine.model import OceanEmbedGNNOAM
    from model_bridge import get_land_mask

    rng = np.random.default_rng(seed)
    cache = os.path.join(root, "OceanEmbed_run", "cache")
    arts = os.path.join(root, "OceanEmbed_run", "gnn_artifacts")
    ckdir = os.path.join(root, "OceanEmbed_run", "checkpoints")
    for d in (cache, arts, ckdir):
        os.makedirs(d, exist_ok=True)

    times = np.arange(np.datetime64(start), np.datetime64(start) + np.timedelta64(n_days, "D"), dtype="datetime64[D]")
    np.save(os.path.join(cache, "finetune_t.npy"), times)
    X = np.lib.format.open_memmap(os.path.join(cache, "finetune_x.npy"), mode="w+", dtype="float16",
                                  shape=(n_days, 8, 112, 256))
    base = rng.random((1, 7, 112, 256)).astype("float32")
    X[:, :7] = (base + 0.05 * rng.standard_normal((n_days, 7, 112, 256))).astype("float16")
    X[:, 7] = 0
    del X
    land = np.asarray(get_land_mask(), dtype=bool)
    if with_y:
        Y = np.lib.format.open_memmap(os.path.join(cache, "finetune_y.npy"), mode="w+", dtype="float16",
                                      shape=(n_days, 15, 112, 256))
        y = np.linspace(0.9, 0.1, 15, dtype="float32")[None, :, None, None] + np.zeros((n_days, 15, 112, 256), "float32")
        y[:, :, :101, :241][:, :, land] = np.nan
        y[:, 12:, 60, 110] = np.nan          # a shallow column: sea floor above 500 m
        Y[:] = y.astype("float16")
        del Y
    tstats = {"mean": 15.0, "std": 8.0, "min": -1.8, "max": 2.2, "raw_min": 0.6, "raw_max": 32.6, "n": 1}
    json.dump({"stage": "finetune", "n": n_days, "chunks": [[0, n_days]], "done": 1, "target_stats": tstats,
               "input_stats": {}}, open(os.path.join(cache, "finetune_meta.json"), "w"))
    if with_z:
        Z = np.lib.format.open_memmap(os.path.join(cache, "gnn_z.npy"), mode="w+", dtype="float16",
                                      shape=(n_days, 15, 101, 241))
        Z[:] = rng.random((n_days, 15, 101, 241)).astype("float16")
        del Z
        json.dump({"n": n_days, "done_upto": n_days}, open(os.path.join(cache, "gnn_z_meta.json"), "w"))

    json.dump({"labels": (np.arange(15) * K // 15).tolist(), "K": K, "mode": "raw"},
              open(os.path.join(arts, "depth_cluster.json"), "w"))
    json.dump({"n_bins": 52, "bin_labels": (np.arange(52) * M // 52).tolist(), "M": M},
              open(os.path.join(arts, "season_regime.json"), "w"))
    rf = RandomForestRegressor(n_estimators=3, max_depth=6, random_state=seed)
    rf.fit(rng.random((400, 39)), rng.random((400, 15)))
    joblib.dump(rf, os.path.join(arts, "rf_model_0.joblib"))

    torch.manual_seed(seed)
    model = OceanEmbedGNNOAM(15, 128, 32, 32, 4, 2, K, M, 64)
    for p in model.parameters():          # non-trivial edge gates so the attention path is exercised
        if p.dim() == 1 and p.numel() == 4:
            torch.nn.init.normal_(p, std=0.5)
    model.season_labels_lut.copy_(torch.as_tensor(np.arange(52) * M // 52))
    torch.save({"model_state": model.state_dict(), "epoch": 20, "val_loss": 0.01,
                "cfg_model": {"K": K, "M": M}}, os.path.join(ckdir, "gnn_C_full_epoch_20.pt"))
    return times
