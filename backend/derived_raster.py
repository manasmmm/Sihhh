"""PNG rendering of derived layers for Leaflet ImageOverlay (same conventions
as raster.py: north up, land transparent, edge-to-edge over the domain)."""
import io
from typing import Tuple

import numpy as np
import matplotlib as mpl
from PIL import Image
from scipy.ndimage import distance_transform_edt

import config

FLAG_RGBA = (244, 114, 182, 235)  # pink: subsurface-only front present


def render_derived_png(field: np.ndarray, var: str, scale: int = 4) -> Tuple[bytes, float, float]:
    disp = config.DERIVED_DISPLAY[var]
    vmin, vmax = float(disp["vmin"]), float(disp["vmax"])
    nan_mask = np.isnan(field)
    h, w = field.shape

    if disp["cmap"] == "front_flag":
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[(field == 1) & ~nan_mask] = FLAG_RGBA
        img = Image.fromarray(np.flipud(rgba), mode="RGBA")
        if scale > 1:
            img = img.resize((w * scale, h * scale), resample=Image.Resampling.NEAREST)
    else:
        if nan_mask.all():
            img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
        else:
            filled = field
            if nan_mask.any():
                idx = distance_transform_edt(nan_mask, return_distances=False, return_indices=True)
                filled = field[tuple(idx)]
            norm = np.clip((filled - vmin) / (vmax - vmin), 0.0, 1.0)
            rgba = (mpl.colormaps[disp["cmap"]](norm) * 255).astype(np.uint8)
            rgba[nan_mask, 3] = 0
            img = Image.fromarray(np.flipud(rgba), mode="RGBA")
            if scale > 1:
                img = img.resize((w * scale, h * scale), resample=Image.Resampling.BILINEAR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")  # optimize=True was 8x slower for ~10% smaller files
    return buf.getvalue(), vmin, vmax


def colormap_stops(var: str, n: int = 9):
    """CSS gradient stops for the legend, so the UI matches the PNG exactly."""
    disp = config.DERIVED_DISPLAY[var]
    if disp["cmap"] == "front_flag":
        return ["rgba(0,0,0,0)", "rgba(%d,%d,%d,%.2f)" % (*FLAG_RGBA[:3], FLAG_RGBA[3] / 255)]
    cmap = mpl.colormaps[disp["cmap"]]
    return [mpl.colors.to_hex(cmap(i / (n - 1))) for i in range(n)]
