"""
OceanEmbedGNNOAM - identical to Section 13 of the notebook (plus the Section 12 scatter ops),
so checkpoints load with load_state_dict(strict=True). Layer sizes are read from the
checkpoint itself, not assumed.
"""
import math
from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# ----------------------------------------------------------------- Section 12
def scatter_add(src, index, n):
    shape = (n,) + tuple(src.shape[1:])
    out = torch.zeros(shape, dtype=src.dtype, device=src.device)
    idx = index.view(-1, *([1] * (src.dim() - 1))).expand_as(src)
    out.scatter_add_(0, idx, src)
    return out


def scatter_softmax(logits, index, n):
    E, Hh = logits.shape
    idx = index.view(-1, 1).expand(E, Hh)
    mx = torch.full((n, Hh), float("-inf"), dtype=logits.dtype, device=logits.device)
    mx.scatter_reduce_(0, idx, logits, reduce="amax", include_self=True)
    mx = torch.nan_to_num(mx, neginf=0.0)
    shifted = (logits - mx.gather(0, idx)).exp()
    denom = torch.zeros((n, Hh), dtype=logits.dtype, device=logits.device).scatter_add_(0, idx, shifted)
    return shifted / denom.gather(0, idx).clamp_min(1e-12)


# ----------------------------------------------------------------- Section 13
class OAMLayer(nn.Module):
    def __init__(self, d_model, attn_dim, heads, use_layernorm=True):
        super().__init__()
        self.h, self.d = heads, attn_dim // heads
        self.bfc = nn.Linear(d_model, attn_dim)
        self.ln = nn.LayerNorm(d_model) if use_layernorm else nn.Identity()
        self.wq = nn.Linear(attn_dim, attn_dim)
        self.wk = nn.Linear(attn_dim, attn_dim)
        self.wv = nn.Linear(attn_dim, attn_dim)
        self.we = nn.Parameter(torch.zeros(heads))
        self.be = nn.Parameter(torch.zeros(heads))
        self.ffc = nn.Linear(attn_dim, d_model)
        self.act = nn.GELU()

    def forward(self, x, edge_index, edge_attr, n_nodes):
        h = self.bfc(self.ln(x))
        q, k, v = self.wq(h), self.wk(h), self.wv(h)
        src, dst = edge_index[0], edge_index[1]
        H, dh = self.h, self.d
        q = q.view(n_nodes, H, dh); k = k.view(n_nodes, H, dh); v = v.view(n_nodes, H, dh)
        e_gate = self.we[None, :] * edge_attr[:, None] + self.be[None, :]
        q_i = q[dst]
        k_j = k[src] + e_gate[:, :, None]
        v_j = v[src] + e_gate[:, :, None]
        logits = ((q_i + e_gate[:, :, None]) * k_j).sum(-1) / math.sqrt(dh)
        alpha = scatter_softmax(logits, dst, n_nodes)
        out = scatter_add(alpha[:, :, None] * v_j, dst, n_nodes)
        return self.ffc(out.reshape(n_nodes, -1))


class DepthEncoding(nn.Module):
    def __init__(self, n_depths, dim):
        super().__init__()
        self.emb = nn.Embedding(n_depths, dim)

    def forward(self, depth_idx):
        return self.emb(depth_idx)


class ClusterSkip(nn.Module):
    def __init__(self, K, M, d_model, hidden):
        super().__init__()
        self.K, self.M = K, M
        self.net = nn.Sequential(nn.Linear(K + M, hidden), nn.GELU(), nn.Linear(hidden, d_model))

    def forward(self, depth_cluster_id, season_bin_id, season_labels_lut):
        season_id = season_labels_lut[season_bin_id]
        c = torch.cat([F.one_hot(depth_cluster_id, self.K).float(),
                       F.one_hot(season_id, self.M).float()], dim=-1)
        return self.net(c)


class OceanEmbedGNNOAM(nn.Module):
    def __init__(self, n_depths, d_model, d_depth, attn_dim, heads, layers, K, M, phi_hidden,
                 time_bins=52, use_layernorm=True):
        super().__init__()
        self.rf_proj = nn.Linear(n_depths, d_model - d_depth)
        self.depth_enc = DepthEncoding(n_depths, d_depth)
        self.layers = nn.ModuleList([OAMLayer(d_model, attn_dim, heads, use_layernorm) for _ in range(layers)])
        self.skip = ClusterSkip(K, M, d_model, phi_hidden)
        self.readout_t = nn.Sequential(nn.Linear(d_model, d_model // 2), nn.ReLU(inplace=True),
                                       nn.Linear(d_model // 2, 1))
        self.readout_s = nn.Sequential(nn.Linear(d_model, d_model // 2), nn.ReLU(inplace=True),
                                       nn.Linear(d_model // 2, 1))
        self.register_buffer("season_labels_lut", torch.zeros(time_bins, dtype=torch.long))

    def forward(self, g, use_skip=True):
        x = torch.cat([self.rf_proj(g["x_rf"]), self.depth_enc(g["depth_idx"])], dim=-1)
        for layer in self.layers:
            x = x + layer(x, g["edge_index"], g["edge_attr"], g["n_nodes"])
        if use_skip:
            x = x + self.skip(g["depth_cluster_id"], g["doy_bin"], self.season_labels_lut)
        return self.readout_t(x).squeeze(-1)


# ------------------------------------------------------------------ loading
def _state_dict(ck) -> Dict[str, torch.Tensor]:
    if isinstance(ck, dict):
        for key in ("model_state", "model_state_dict", "state_dict", "model"):
            if key in ck and isinstance(ck[key], dict):
                return ck[key]
        if all(isinstance(v, torch.Tensor) for v in ck.values()):
            return ck
    raise ValueError("Checkpoint format not recognised (expected a dict with 'model_state').")


def load_model(path: str, season_labels, K: int, M: int) -> Tuple[OceanEmbedGNNOAM, dict]:
    ck = torch.load(path, map_location="cpu", weights_only=False)
    sd = _state_dict(ck)
    sd = {k[len("module."):] if k.startswith("module.") else k: v for k, v in sd.items()}  # DataParallel

    n_depths = sd["rf_proj.weight"].shape[1]
    d_depth = sd["depth_enc.emb.weight"].shape[1]
    d_model = sd["rf_proj.weight"].shape[0] + d_depth
    attn_dim = sd["layers.0.bfc.weight"].shape[0]
    heads = sd["layers.0.we"].shape[0]
    n_layers = len({k.split(".")[1] for k in sd if k.startswith("layers.")})
    phi_hidden = sd["skip.net.0.weight"].shape[0]
    k_plus_m = sd["skip.net.0.weight"].shape[1]
    time_bins = sd["season_labels_lut"].shape[0] if "season_labels_lut" in sd else len(season_labels)
    use_ln = "layers.0.ln.weight" in sd
    if k_plus_m != K + M:
        raise ValueError(f"Checkpoint expects K+M = {k_plus_m} cluster inputs but depth_cluster.json/"
                         f"season_regime.json give K={K}, M={M}. Use the JSON files from the same Kaggle run.")

    model = OceanEmbedGNNOAM(n_depths, d_model, d_depth, attn_dim, heads, n_layers, K, M, phi_hidden,
                             time_bins=time_bins, use_layernorm=use_ln)
    # Notebook order: set_frozen_lookups() then load_state_dict(), so the checkpoint's buffer wins.
    model.season_labels_lut.copy_(torch.as_tensor(season_labels, dtype=torch.long))
    if "season_labels_lut" not in sd:
        sd["season_labels_lut"] = model.season_labels_lut.clone()
    model.load_state_dict(sd, strict=True)
    model.eval()
    info = {"epoch": ck.get("epoch") if isinstance(ck, dict) else None,
            "val_loss": ck.get("val_loss") if isinstance(ck, dict) else None,
            "d_model": d_model, "layers": n_layers, "heads": heads}
    return model, info
