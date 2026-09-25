"""
Raster PNG generator for OceanEmbed Viewer
==========================================
Converts a 2D temperature field (101 x 241) into an edge-to-edge RGBA PNG
with Copernicus 'magma' or 'turbo' colormap and transparent land cells (alpha=0),
suitable for Leaflet ImageOverlay.
"""

import io
from typing import Optional, Tuple
import numpy as np
import matplotlib as mpl
from PIL import Image
from scipy.ndimage import distance_transform_edt

# Colormaps: 'magma' is Copernicus MyOcean signature thermal palette
MAGMA_CMAP = mpl.colormaps["magma"]
TURBO_CMAP = mpl.colormaps["turbo"]


def render_temperature_png(
    field_2d: np.ndarray,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    adaptive: bool = False,
    colormap_name: str = "magma",
    scale: int = 4,
) -> Tuple[bytes, float, float]:
    """
    Render 2D temperature grid to PNG bytes.

    Parameters
    ----------
    field_2d : np.ndarray
        Shape (101, 241), float32, with NaN over land.
    vmin : Optional[float]
        Lower temperature bound in °C.
    vmax : Optional[float]
        Upper temperature bound in °C.
    adaptive : bool
        If True, auto-scale contrast for this layer.
    colormap_name : str
        'magma' (Copernicus thermal default) or 'turbo'.
    scale : int
        Bilinear upscale multiplier (default 4 -> 964 x 404).

    Returns
    -------
    Tuple[bytes, float, float]
        Raw PNG image bytes, effective vmin, effective vmax.
    """
    nan_mask = np.isnan(field_2d)

    # If all cells are land or nan, return transparent PNG
    if np.all(nan_mask):
        h, w = field_2d.shape
        img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), 0.0, 32.0

    valid_vals = field_2d[~nan_mask]

    if adaptive:
        eff_vmin = float(np.percentile(valid_vals, 1))
        eff_vmax = float(np.percentile(valid_vals, 99))
        if eff_vmax - eff_vmin < 1.0:
            eff_vmax = eff_vmin + 1.0
    else:
        eff_vmin = float(vmin) if vmin is not None else 0.0
        eff_vmax = float(vmax) if vmax is not None else 32.0

    # Fill NaN cells with nearest ocean neighbor to prevent dark fringing on borders
    if np.any(nan_mask):
        indices = distance_transform_edt(nan_mask, return_distances=False, return_indices=True)
        filled = field_2d[tuple(indices)]
    else:
        filled = field_2d

    # Normalize into [0, 1]
    norm = np.clip((filled - eff_vmin) / (eff_vmax - eff_vmin), 0.0, 1.0)

    # Select colormap (magma = purple->magenta->coral->yellow, matches Copernicus reference)
    cmap = TURBO_CMAP if colormap_name.lower() == "turbo" else MAGMA_CMAP
    rgba = cmap(norm)

    # Convert to uint8
    rgba_uint8 = (rgba * 255.0).astype(np.uint8)

    # Set land cells to fully transparent
    rgba_uint8[nan_mask, 3] = 0

    # Flip vertically: Leaflet ImageOverlay top is lat_max, bottom is lat_min
    rgba_uint8 = np.flipud(rgba_uint8)

    # Create PIL Image
    img = Image.fromarray(rgba_uint8, mode="RGBA")

    # Upscale for smooth visual presentation
    if scale > 1:
        target_w = field_2d.shape[1] * scale
        target_h = field_2d.shape[0] * scale
        img = img.resize((target_w, target_h), resample=Image.Resampling.BILINEAR)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), eff_vmin, eff_vmax
