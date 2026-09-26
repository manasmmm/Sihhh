"""
Discovery of the Kaggle run artifacts dropped into config.GNN_ARTIFACTS_DIR.

Copy the notebook's /kaggle/working/OceanEmbed_run folder (or just the files below)
anywhere under backend/model_artifacts/. Files are found by name, so the folder
layout does not matter:

  required  <GNN_CHECKPOINT_NAME>            e.g. gnn_C_full_epoch_20.pt
  required  depth_cluster.json, season_regime.json
  required  <stage>_x.npy, <stage>_t.npy, <stage>_meta.json   (stage = finetune and/or finetune2024)
  optional  <stage>_y.npy                    exact GLORYS ocean / sea-floor mask (else the dashboard land mask)
  optional  gnn_z.npy + gnn_z_meta.json      precomputed tree-stage output for the 'finetune' stage
  optional  gnn_z_2024.npy + gnn_z_2024_meta.json
  needed if a day has no precomputed z:  rf_model_*.joblib  (tree stage: XGBoost / random forest)
"""
import glob
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

import config


class ArtifactsMissing(FileNotFoundError):
    """Raised with a message that says exactly which file is missing and where to put it."""


@dataclass
class Stage:
    name: str
    x_path: str
    t_path: str
    meta_path: str
    y_path: Optional[str] = None
    z_path: Optional[str] = None
    z_meta_path: Optional[str] = None


@dataclass
class GnnArtifacts:
    root: str
    checkpoint: str
    depth_cluster: str
    season_regime: str
    tree_models: List[str] = field(default_factory=list)
    stages: Dict[str, Stage] = field(default_factory=dict)

    def signature(self) -> str:
        """Changes when the checkpoint or tree models change (used to invalidate cached outputs)."""
        parts = [self.checkpoint] + self.tree_models
        return "|".join(f"{os.path.basename(p)}:{os.path.getmtime(p):.0f}" for p in parts if os.path.exists(p))


_Z_NAMES = {"finetune": "gnn_z", "finetune2024": "gnn_z_2024"}


def _index_files(root: str) -> Dict[str, List[str]]:
    by_name: Dict[str, List[str]] = {}
    for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        if os.path.isfile(p):
            by_name.setdefault(os.path.basename(p), []).append(p)
    return by_name


def _one(by_name, name) -> Optional[str]:
    hits = by_name.get(name)
    return sorted(hits)[0] if hits else None


def find_artifacts(root: Optional[str] = None, checkpoint_name: Optional[str] = None) -> GnnArtifacts:
    root = root or config.GNN_ARTIFACTS_DIR
    checkpoint_name = checkpoint_name or config.GNN_CHECKPOINT_NAME
    rel = os.path.relpath(root, config.REPO_DIR)
    if not os.path.isdir(root):
        raise ArtifactsMissing(f"GNN artifacts folder not found: {rel}. Copy your Kaggle OceanEmbed_run folder there.")
    by_name = _index_files(root)

    ckpt = _one(by_name, checkpoint_name)
    if ckpt is None:
        found = sorted(n for n in by_name if n.endswith(".pt"))
        raise ArtifactsMissing(
            f"Checkpoint {checkpoint_name} not found under {rel}"
            + (f" (found: {', '.join(found[:6])})" if found else "")
            + ". Copy it from OceanEmbed_run/checkpoints/ or change GNN_CHECKPOINT_NAME in backend/config.py."
        )
    dc, sr = _one(by_name, "depth_cluster.json"), _one(by_name, "season_regime.json")
    if dc is None or sr is None:
        raise ArtifactsMissing(f"depth_cluster.json / season_regime.json not found under {rel} "
                               f"(copy OceanEmbed_run/gnn_artifacts/).")

    trees = sorted(p for n, ps in by_name.items() if n.startswith("rf_model_") and n.endswith(".joblib") for p in ps)

    stages = {}
    for name in config.GNN_CACHE_STAGES:
        x, t, m = (_one(by_name, f"{name}_{s}") for s in ("x.npy", "t.npy", "meta.json"))
        if not (x and t and m):
            continue
        zname = _Z_NAMES.get(name)
        stages[name] = Stage(
            name=name, x_path=x, t_path=t, meta_path=m, y_path=_one(by_name, f"{name}_y.npy"),
            z_path=_one(by_name, f"{zname}.npy") if zname else None,
            z_meta_path=_one(by_name, f"{zname}_meta.json") if zname else None,
        )
    if not stages:
        raise ArtifactsMissing(
            f"No input cache found under {rel}. Copy finetune_x.npy + finetune_t.npy + finetune_meta.json "
            f"(and/or the finetune2024_* files) from OceanEmbed_run/cache/.")
    return GnnArtifacts(root=root, checkpoint=ckpt, depth_cluster=dc, season_regime=sr,
                        tree_models=trees, stages=stages)


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def open_npy(path: str) -> np.ndarray:
    return np.load(path, mmap_mode="r")
