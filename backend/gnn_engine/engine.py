"""
Full-basin reconstruction for one day - port of notebook Sections 7, 9, 11 and 20.

Pipeline per day e (e = index of the day in a cached input stage):
  1. z_col: the tree stage (XGBoost / random forest, rf_model_*.joblib) maps 39 window
     statistics of the 30-day, 7-channel surface history to a 15-vector per ocean column.
     Taken from the notebook's precomputed gnn_z cache when available, otherwise
     predicted here with the average of all tree models (as the notebook does for
     validation/test/2024 days).
  2. Exhaustive overlapping 12x12 tiles -> ITTSG graph per tile (Section 11).
  3. GNN-OAM forward pass, weighted stitching of tile cores (Section 20).
  4. De-normalise with the cache's target_stats -> degC; NaN on land / below the sea floor.
"""
import logging
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

import config
from .artifacts import ArtifactsMissing, GnnArtifacts, find_artifacts, load_json, open_npy

log = logging.getLogger("oceanembed.gnn")

N_SURF = 7
RF_FEATURE_GROUPS = ("cur", "mean", "std", "slope", "d7")
N_RF_FEATS = len(RF_FEATURE_GROUPS) * N_SURF + 4          # 39

_NBR26 = np.array([(dr, dc, dz) for dr in (-1, 0, 1) for dc in (-1, 0, 1) for dz in (-1, 0, 1)
                   if not (dr == 0 and dc == 0 and dz == 0)], dtype="int64")


# --------------------------------------------------------------- helpers
def denormalise(z, s):
    return (z * (s["max"] - s["min"] + 1e-8) + s["min"]) * s["std"] + s["mean"]


def valid_window_ends(times, window):
    t = np.asarray(times).astype("datetime64[D]")
    ok = np.zeros(len(t), dtype=bool)
    need = np.timedelta64(window - 1, "D")
    for e in range(window - 1, len(t)):
        ok[e] = (t[e] - t[e - window + 1]) == need
    return ok


def season_bin_of(doy, n_bins):
    return np.minimum(((np.asarray(doy) - 1) * n_bins) // 366, n_bins - 1).astype("int64")


def window_stats(Xw, T):
    n = Xw.shape[0] - T + 1
    cs = np.zeros((Xw.shape[0] + 1,) + Xw.shape[1:], dtype="float64")
    cs2 = np.zeros_like(cs)
    np.cumsum(Xw, axis=0, dtype="float64", out=cs[1:])
    np.cumsum(np.square(Xw, dtype="float64"), axis=0, out=cs2[1:])
    mean = (cs[T:T + n] - cs[:n]) / T
    var = np.maximum((cs2[T:T + n] - cs2[:n]) / T - mean ** 2, 0.0)
    ws = np.arange(T, dtype="float64") - (T - 1) / 2.0
    ws = ws / np.sum(ws ** 2)
    slope = np.zeros((n,) + Xw.shape[1:], dtype="float64")
    for tau in range(T):
        slope += ws[tau] * Xw[tau:tau + n]
    cur = Xw[T - 1:T - 1 + n]
    d7 = cur - Xw[T - 1 - 7:T - 1 - 7 + n]
    return {"cur": cur.astype("float32"), "mean": mean.astype("float32"), "std": np.sqrt(var).astype("float32"),
            "slope": (slope * (T - 1)).astype("float32"), "d7": d7.astype("float32")}


def _pcc_matrix(feat):
    f = feat - feat.mean(axis=1, keepdims=True)
    s = np.sqrt(np.maximum((f * f).sum(axis=1, keepdims=True), 1e-12))
    fn = f / s
    pcc = np.clip(fn @ fn.T, -1.0, 1.0)
    np.fill_diagonal(pcc, 1.0)
    return pcc


def _tree_predict(model, F):
    """Works for sklearn forests, XGBRegressor / MultiOutputRegressor(XGB...) and raw xgboost Boosters."""
    if type(model).__name__ == "Booster":
        import xgboost as xgb
        return np.asarray(model.predict(xgb.DMatrix(F)))
    return np.asarray(model.predict(F))


# --------------------------------------------------------------- engine
class GnnEngine:
    def __init__(self, artifacts: Optional[GnnArtifacts] = None):
        self.art = artifacts or find_artifacts()
        self._lock = threading.Lock()
        self._model = None
        self._model_info: Dict = {}
        self._trees = None
        self._stages: Dict[str, dict] = {}
        self._day_index: Dict[str, Tuple[str, int]] = {}

        dc = load_json(self.art.depth_cluster)
        sr = load_json(self.art.season_regime)
        self.depth_cluster = np.array(dc["labels"], dtype="int64")
        self.K = int(dc["K"])
        self.season_labels = np.array(sr["bin_labels"], dtype="int64")
        self.M = int(sr["M"])
        self.time_bins = int(sr.get("n_bins", len(self.season_labels)))

        self.T = config.GNN_T_WINDOW
        self.TILE, self.HALO = config.GNN_TILE_SIZE, config.GNN_HALO
        self.CORE = self.TILE - 2 * self.HALO
        self.D, self.H, self.W = config.GRID_SHAPE
        lat = np.asarray(config.LATS, dtype="float64")
        lon = np.asarray(config.LONS, dtype="float64")
        self.lat_norm = ((lat - config.LAT_MIN) / (config.LAT_MAX - config.LAT_MIN)).astype("float32")
        self.lon_norm = ((lon - config.LON_MIN) / (config.LON_MAX - config.LON_MIN)).astype("float32")

        self._open_stages()
        self._build_masks()
        self._build_tiles()

    # ------------------------------------------------------------ inputs
    def _open_stages(self):
        # 2024 stage first so a date present in both uses the dedicated 2016-2023 stage
        for name in sorted(self.art.stages, key=lambda n: n != "finetune2024"):
            st = self.art.stages[name]
            meta = load_json(st.meta_path)
            times = np.load(st.t_path).astype("datetime64[D]")
            X = open_npy(st.x_path)
            if X.shape[0] != len(times):
                raise ArtifactsMissing(f"{os.path.basename(st.x_path)} has {X.shape[0]} days but "
                                       f"{os.path.basename(st.t_path)} has {len(times)}; copy matching files.")
            if meta.get("done") is not None and meta.get("chunks") and meta["done"] != len(meta["chunks"]):
                raise ArtifactsMissing(f"{os.path.basename(st.meta_path)}: cache build was incomplete on Kaggle.")
            ok_end = valid_window_ends(times, self.T)
            doy = (times - times.astype("datetime64[Y]").astype("datetime64[D]")).astype(int) + 1  # day of year
            z = zdone = None
            if st.z_path and st.z_meta_path:
                zmeta = load_json(st.z_meta_path)
                if zmeta.get("n") == len(times):
                    z = open_npy(st.z_path)
                    zdone = int(zmeta.get("done_upto", 0))
            self._stages[name] = dict(times=times, X=X, meta=meta, ok_end=ok_end, doy=doy,
                                      tstats=meta["target_stats"], z=z, zdone=zdone,
                                      Y=open_npy(st.y_path) if st.y_path else None)
            for e in np.flatnonzero(ok_end):
                self._day_index[str(times[e])] = (name, int(e))

    def _build_masks(self):
        """Static 3-D ocean mask as in Section 7 (7 probe days of the GLORYS target cache)."""
        m3 = None
        for st in self._stages.values():
            Y = st["Y"]
            if Y is None:
                continue
            N = Y.shape[0]
            m3 = np.ones((self.D, self.H, self.W), dtype=bool)
            for i in np.unique(np.linspace(0, N - 1, min(7, N)).astype(int)):
                m3 &= np.isfinite(np.asarray(Y[i, :, :self.H, :self.W], dtype="float32"))
            break
        if m3 is None or not m3.any():
            from model_bridge import get_land_mask
            log.warning("No *_y.npy target cache found: using the dashboard land mask as the ocean mask.")
            ocean2d = ~np.asarray(get_land_mask(), dtype=bool)
            m3 = np.repeat(ocean2d[None], self.D, axis=0)
            self.mask_source = "dashboard land mask (no GLORYS target cache provided)"
        else:
            self.mask_source = "GLORYS target cache"
        self.ocean3d = m3
        self.col_ocean = m3.any(axis=0)
        self.col_r, self.col_c = np.nonzero(self.col_ocean)

    def _tile_core_mask(self, r0, c0):
        TILE, HALO, H, W = self.TILE, self.HALO, self.H, self.W
        m = np.ones((TILE, TILE), dtype=bool)
        if r0 > 0:
            m[:HALO, :] = False
        if r0 + TILE < H:
            m[TILE - HALO:, :] = False
        if c0 > 0:
            m[:, :HALO] = False
        if c0 + TILE < W:
            m[:, TILE - HALO:] = False
        return m

    def _build_tiles(self):
        H, W, TILE, CORE = self.H, self.W, self.TILE, self.CORE
        rows = list(range(0, H - TILE + 1, CORE))
        if rows[-1] != H - TILE:
            rows.append(H - TILE)
        cols = list(range(0, W - TILE + 1, CORE))
        if cols[-1] != W - TILE:
            cols.append(W - TILE)
        origins = [(r0, c0) for r0 in rows for c0 in cols
                   if (self.col_ocean[r0:r0 + TILE, c0:c0 + TILE] & self._tile_core_mask(r0, c0)).any()]
        self.origins = np.array(origins, dtype="int64")

    # ------------------------------------------------------------- public
    def available_dates(self) -> List[str]:
        can_predict_z = bool(self.art.tree_models)
        out = []
        for d, (name, e) in self._day_index.items():
            st = self._stages[name]
            if can_predict_z or (st["z"] is not None and e < st["zdone"]):
                out.append(d)
        return sorted(out)

    def model(self):
        if self._model is None:
            from .model import load_model
            self._model, self._model_info = load_model(self.art.checkpoint, self.season_labels, self.K, self.M)
        return self._model

    @property
    def model_info(self) -> dict:
        self.model()
        return self._model_info

    def trees(self):
        if self._trees is None:
            if not self.art.tree_models:
                raise ArtifactsMissing("No rf_model_*.joblib (tree stage) found; needed for days without a "
                                       "precomputed gnn_z cache. Copy OceanEmbed_run/gnn_artifacts/rf_model_*.joblib.")
            import joblib
            trees = []
            for p in self.art.tree_models:
                try:
                    m = joblib.load(p)
                except ModuleNotFoundError as e:
                    raise ArtifactsMissing(
                        f"{os.path.basename(p)} needs the '{e.name}' package. Install the same version that "
                        f"was used on Kaggle (pip install {e.name}).") from e
                except Exception as e:
                    raise ArtifactsMissing(
                        f"{os.path.basename(p)} could not be loaded ({type(e).__name__}: {e}). Install the same "
                        f"scikit-learn / xgboost versions as on Kaggle.") from e
                nf = getattr(m, "n_features_in_", None)
                if nf is not None and nf != N_RF_FEATS:
                    raise ArtifactsMissing(f"{os.path.basename(p)} expects {nf} features, but the notebook's "
                                           f"tree stage uses {N_RF_FEATS}.")
                trees.append(m)
            self._trees = trees
        return self._trees

    # ----------------------------------------------------------- z_col
    def z_col(self, name: str, e: int) -> np.ndarray:
        st = self._stages[name]
        if st["z"] is not None and e < st["zdone"]:
            return np.asarray(st["z"][e], dtype="float32")              # (D, H, W), exactly the notebook's cache
        T, H, W = self.T, self.H, self.W
        Xw = np.asarray(st["X"][e - T + 1:e + 1, :N_SURF, :H, :W], dtype="float32")
        s = window_stats(Xw, T)
        rr, cc = self.col_r, self.col_c
        parts = [s[g][:, :, rr, cc] for g in RF_FEATURE_GROUPS]
        Fm = np.concatenate(parts, axis=1).transpose(0, 2, 1)[0]         # (m, 35)
        static = np.stack([self.lat_norm[rr], self.lon_norm[cc]], axis=-1)
        ang = 2.0 * np.pi * float(st["doy"][e]) / 366.0
        tfe = np.broadcast_to(np.array([np.sin(ang), np.cos(ang)], dtype="float32"), (len(rr), 2))
        F = np.concatenate([Fm, static, tfe], axis=-1).astype("float32")
        p = np.mean([_tree_predict(m, F).reshape(len(rr), self.D) for m in self.trees()], axis=0)
        z = np.zeros((self.D, H, W), dtype="float32")
        z[:, rr, cc] = p.T
        return z.astype("float16").astype("float32")                     # same fp16 round-trip as the notebook

    # ------------------------------------------------------------ graph
    def _build_graph(self, Xwin, z, doy, tiles):
        D, TILE = self.D, self.TILE
        xs, di, ri, ci, dbins, dcids, batch_ids, ei_list, ea_list = ([] for _ in range(9))
        node_off = 0
        bin_ = int(season_bin_of(np.array([doy]), self.time_bins)[0])
        for bi, (r0, c0) in enumerate(tiles):
            rr = np.arange(r0, r0 + TILE); cc = np.arange(c0, c0 + TILE)
            lr, lc = np.nonzero(self.col_ocean[r0:r0 + TILE, c0:c0 + TILE])
            m = len(lr)
            if m == 0:
                continue
            gr, gc = rr[lr], cc[lc]
            col_id = np.arange(m)
            zc = z[:, gr, gc].T                                            # (m, D)
            xs.append(np.repeat(zc, D, axis=0))
            di.append(np.tile(np.arange(D), m))
            ri.append(np.repeat(gr, D)); ci.append(np.repeat(gc, D))
            dbins.append(np.full(m * D, bin_, dtype="int64"))
            dcids.append(np.tile(self.depth_cluster, m))
            batch_ids.append(np.full(m * D, bi, dtype="int64"))

            Xw = Xwin[:, :, gr, gc]                                        # (T, C, m)
            pcc_col = _pcc_matrix(Xw.transpose(2, 1, 0).reshape(m, -1))

            node_id_of = -np.ones((TILE, TILE, D), dtype="int64")
            node_id_of[lr, lc, :] = (col_id[:, None] * D + np.arange(D)[None, :]) + node_off

            src_n, dst_n, col_n_s = [], [], []
            for dr, dc, dz in _NBR26:
                r2, c2 = lr + dr, lc + dc
                inb = (r2 >= 0) & (r2 < TILE) & (c2 >= 0) & (c2 < TILE)
                if not inb.any():
                    continue
                r2v, c2v, colv = r2[inb], c2[inb], col_id[inb]
                for k in range(D):
                    k2 = k + dz
                    if not (0 <= k2 < D):
                        continue
                    nb_id = node_id_of[r2v, c2v, k2]
                    ok = nb_id >= 0
                    if not ok.any():
                        continue
                    src_n.append((colv[ok] * D + k) + node_off)
                    dst_n.append(nb_id[ok])
                    col_n_s.append(colv[ok])
            if src_n:
                src_n = np.concatenate(src_n); dst_n = np.concatenate(dst_n)
                col_s = np.concatenate(col_n_s)
                col_d = (dst_n - node_off) // D
                ei_list.append(np.stack([src_n, dst_n]))
                ea_list.append(np.maximum(1.0 + pcc_col[col_s, col_d], 1.0).astype("float32"))

            pcc_thresh = pcc_col.copy()
            np.fill_diagonal(pcc_thresh, -2.0)
            if config.GNN_SIM_MAX_PARTNERS is not None and m > 1:
                k = min(config.GNN_SIM_MAX_PARTNERS, m - 1)
                part = np.argpartition(-pcc_thresh, kth=k - 1, axis=1)[:, :k]
                keep = np.zeros_like(pcc_thresh, dtype=bool)
                keep[np.repeat(np.arange(m), k), part.reshape(-1)] = True
                pcc_thresh = np.where(keep, pcc_thresh, -2.0)
            ii, jj = np.nonzero(pcc_thresh >= config.GNN_SIM_THRESHOLD)
            if ii.size:
                vals = pcc_col[ii, jj].astype("float32")
                if config.GNN_SIM_DEPTH_PAIRING == "all":
                    k1 = np.repeat(np.arange(D), D); k2 = np.tile(np.arange(D), D)
                    src_s = ((ii[:, None] * D + k1[None, :]) + node_off).reshape(-1)
                    dst_s = ((jj[:, None] * D + k2[None, :]) + node_off).reshape(-1)
                    ea_s = np.repeat(vals, D * D)
                else:
                    src_s = ((ii[:, None] * D + np.arange(D)[None, :]) + node_off).reshape(-1)
                    dst_s = ((jj[:, None] * D + np.arange(D)[None, :]) + node_off).reshape(-1)
                    ea_s = np.repeat(vals, D)
                ei_list.append(np.stack([src_s, dst_s])); ea_list.append(ea_s.astype("float32"))

            allnodes = np.arange(m * D) + node_off
            ei_list.append(np.stack([allnodes, allnodes]))
            ea_list.append(np.full(m * D, 2.0, dtype="float32"))
            node_off += m * D

        if node_off == 0:
            return None
        import torch
        return {
            "x_rf": torch.from_numpy(np.concatenate(xs, axis=0).astype("float32")),
            "depth_idx": torch.from_numpy(np.concatenate(di)),
            "row": np.concatenate(ri), "col": np.concatenate(ci),
            "doy_bin": torch.from_numpy(np.concatenate(dbins)),
            "depth_cluster_id": torch.from_numpy(np.concatenate(dcids)),
            "edge_index": torch.from_numpy(np.concatenate(ei_list, axis=1)),
            "edge_attr": torch.from_numpy(np.concatenate(ea_list)),
            "batch": np.concatenate(batch_ids),
            "n_nodes": node_off,
        }

    def truth(self, day: str) -> Optional[np.ndarray]:
        """GLORYS target for `day` in degC (from <stage>_y.npy), or None if that cache was not copied."""
        if day not in self._day_index:
            return None
        name, e = self._day_index[day]
        st = self._stages[name]
        if st["Y"] is None:
            return None
        y = np.asarray(st["Y"][e, :, :self.H, :self.W], dtype="float32")
        return denormalise(y, st["tstats"]).astype("float32")

    def split_of(self, day: str) -> str:
        """Which notebook split a day belonged to (years as configured in the notebook)."""
        y = int(day[:4])
        if y in config.GNN_TRAIN_YEARS:
            return "train"
        if y in config.GNN_VAL_YEARS:
            return "val"
        return "test" if y in config.GNN_TEST_YEARS else "2024" if y == 2024 else "other"

    # ------------------------------------------------------- reconstruct
    def reconstruct(self, day: str) -> np.ndarray:
        """(15, 101, 241) float32 degC, NaN on land / below the sea floor."""
        import torch

        if day not in self._day_index:
            raise FileNotFoundError(f"No cached surface inputs with a full {self.T}-day window for {day}")
        name, e = self._day_index[day]
        st = self._stages[name]
        t0 = time.time()
        with self._lock:
            model = self.model()
            z = self.z_col(name, e)
            Xwin = np.asarray(st["X"][e - self.T + 1:e + 1, :N_SURF, :self.H, :self.W], dtype="float32")
            doy = int(st["doy"][e])
            D, H, W = self.D, self.H, self.W
            accum = np.zeros((D, H, W), dtype="float64")
            wsum = np.zeros((D, H, W), dtype="float64")
            bt = config.GNN_EVAL_BATCH_TILES
            with torch.no_grad():
                for i0 in range(0, len(self.origins), bt):
                    tiles = [(int(r), int(c)) for r, c in self.origins[i0:i0 + bt]]
                    g = self._build_graph(Xwin, z, doy, tiles)
                    if g is None:
                        continue
                    t_hat = model(g, use_skip=config.GNN_USE_SKIP).float().numpy()
                    Tdeg = denormalise(t_hat, st["tstats"])
                    row, col, depth, bvec = g["row"], g["col"], g["depth_idx"].numpy(), g["batch"]
                    for bi, (r0, c0) in enumerate(tiles):
                        msk = bvec == bi
                        if not msk.any():
                            continue
                        wt = np.where(self._tile_core_mask(r0, c0), 1.0, 1e-3).astype("float32")
                        w = wt[row[msk] - r0, col[msk] - c0]
                        np.add.at(accum, (depth[msk], row[msk], col[msk]), Tdeg[msk] * w)
                        np.add.at(wsum, (depth[msk], row[msk], col[msk]), w)
        pred = np.where(wsum > 0, accum / np.maximum(wsum, 1e-12), np.nan).astype("float32")
        pred[~self.ocean3d] = np.nan
        log.info(f"GNN reconstruction for {day} ({name}[{e}]) took {time.time() - t0:.1f}s")
        return pred


_ENGINE: Optional[GnnEngine] = None
_ENGINE_SIG: Optional[str] = None
_ENGINE_LOCK = threading.Lock()


def get_engine() -> GnnEngine:
    """Shared engine; rebuilt automatically when new artifacts are dropped in."""
    global _ENGINE, _ENGINE_SIG
    with _ENGINE_LOCK:
        art = find_artifacts()
        sig = art.signature() + "|" + "|".join(sorted(art.stages))
        if _ENGINE is None or sig != _ENGINE_SIG:
            _ENGINE = GnnEngine(art)
            _ENGINE_SIG = sig
        return _ENGINE
