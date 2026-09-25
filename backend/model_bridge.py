"""
Model Bridge for OceanEmbed-ViT
==========================================
Integration boundary for the subsurface ocean temperature reconstruction model.
The frontend and data pipeline call `reconstruct_field(date: str)` to get full 3D temperature fields.
"""

import os
import hashlib
from datetime import datetime
import numpy as np
from scipy.ndimage import gaussian_filter

# Fixed reference epoch for continuous day indexing. Using a continuous day
# count (instead of day-of-year, which resets every Jan 1) keeps multi-year
# variability from exactly repeating year over year.
_EPOCH = datetime(2000, 1, 1)

# Domain constants (Section 1 of spec)
LATS = np.round(np.arange(5.0, 30.0 + 1e-6, 0.25), 2)   # 101 values, ascending: 5.0 to 30.0
LONS = np.round(np.arange(45.0, 105.0 + 1e-6, 0.25), 2) # 241 values, ascending: 45.0 to 105.0
DEPTHS_M = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000] # 15 levels

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LAND_MASK_FILE = os.path.join(DATA_DIR, "land_mask.npy")

# Cache land mask
_LAND_MASK = None

def get_land_mask() -> np.ndarray:
    """Load or fallback land mask for the North Indian Ocean domain (101 x 241)."""
    global _LAND_MASK
    if _LAND_MASK is not None:
        return _LAND_MASK
    
    if os.path.exists(LAND_MASK_FILE):
        _LAND_MASK = np.load(LAND_MASK_FILE)
        return _LAND_MASK
    
    # Fallback geometric mask if file not present
    lon_grid, lat_grid = np.meshgrid(LONS, LATS)
    mask = np.zeros_like(lat_grid, dtype=bool)
    # India triangular landmass
    mask |= (lat_grid >= 8.2) & (lat_grid <= 30.0) & (lon_grid >= 68.0) & (lon_grid <= 89.0) & (
        lat_grid > 8.2 + (lon_grid - 77.5) * 1.5
    ) & (lat_grid > 8.2 - (lon_grid - 77.5) * 1.5)
    # Arabian peninsula
    mask |= (lat_grid >= 12.0) & (lat_grid <= 30.0) & (lon_grid >= 45.0) & (lon_grid <= 60.0) & ~(
        (lat_grid >= 22.0) & (lon_grid >= 56.0) & (lon_grid <= 60.0) # Gulf of Oman opening
    )
    # Sri Lanka
    mask |= (lat_grid >= 6.0) & (lat_grid <= 9.8) & (lon_grid >= 79.6) & (lon_grid <= 81.8)
    # Southeast Asia (Myanmar/Thailand/Malay Peninsula)
    mask |= (lat_grid >= 5.0) & (lat_grid <= 30.0) & (lon_grid >= 99.0)
    _LAND_MASK = mask
    return _LAND_MASK


def _date_seed(date: str, salt: str) -> int:
    """Deterministic 32-bit seed derived from a date string, so the same date
    always reproduces the same noise (stable across re-precomputation) while
    different dates/salts get uncorrelated draws."""
    digest = hashlib.sha256(f"{date}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16)


def _smooth_field_noise(seed: int, shape: tuple, sigma: float = 1.6) -> np.ndarray:
    """Spatially-correlated unit-variance noise field (mesoscale turbulence
    texture) instead of flat white noise, so it reads as ocean-like rather
    than pixel static."""
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal(shape)
    smoothed = gaussian_filter(raw, sigma=sigma, mode="wrap")
    std = smoothed.std()
    return smoothed / std if std > 1e-9 else smoothed


def _pseudo_random_series(t: float, seed: int, n_components: int, period_range: tuple, amp_scale: float) -> float:
    """Sum of a few sinusoids with randomized (but fixed-seed) incommensurate
    periods/phases. Unlike a single clean sine wave, this does not line up
    into an obviously repeating signal over the dataset's time span, which
    keeps timeseries/profile charts from reading as a textbook periodic
    anomaly while remaining fully deterministic for a given date."""
    rng = np.random.default_rng(seed)
    periods = rng.uniform(period_range[0], period_range[1], size=n_components)
    phases = rng.uniform(0, 2 * np.pi, size=n_components)
    weights = rng.uniform(0.4, 1.0, size=n_components)
    weights /= weights.sum()
    value = 0.0
    for period, phase, weight in zip(periods, phases, weights):
        value += weight * np.sin(2 * np.pi * t / period + phase)
    return float(value) * amp_scale


def reconstruct_field(date: str) -> np.ndarray:
    """
    Reconstruct 3D sea water potential temperature (thetao) field for a single date.

    Parameters
    ----------
    date : str
        Date string in 'YYYY-MM-DD' format.

    Returns
    -------
    np.ndarray
        float32 array, shape (15, 101, 241), unit °C, NaN over land.
        Order of depth axis matches DEPTHS_M (index 0 = 0m ... index 14 = 1000m).
    """
    # =========================================================================
    # TODO: replace with real OceanEmbed-ViT checkpoint
    #
    # When wiring your trained model:
    # 1. Load your satellite input features for `date` (e.g., SLA, SST, SSS, Wind Stress).
    # 2. Run forward pass through `OceanEmbed-ViT` PyTorch model:
    #       with torch.no_grad():
    #           pred_tensor = model(input_tensor) # shape: (1, 15, 101, 241)
    # 3. Apply land mask (pred_tensor[..., land_mask] = np.nan).
    # 4. Return as float32 numpy array of shape (15, 101, 241).
    # =========================================================================

    dt = datetime.strptime(date, "%Y-%m-%d")
    day_of_year = dt.timetuple().tm_yday
    # Continuous day index (does not reset at year boundaries), used for the
    # drift and irregular-variability terms below.
    t_cont = (dt - _EPOCH).days

    # 2D coordinates
    lon_grid, lat_grid = np.meshgrid(LONS, LATS) # shape (101, 241)
    land_mask = get_land_mask()

    # Base sea surface temperature (SST):
    # Warmest near equator / Bay of Bengal (~29.5 - 30.5°C), decaying slightly northward and westward
    # Seasonal warming cycle in spring (March - May)
    seasonal_phase = (day_of_year - 40) / 365.25 * 2.0 * np.pi
    seasonal_amp = 1.2 * np.sin(seasonal_phase)
    # Interannual modulation (ENSO-like variability): same calendar day in
    # different years is no longer identical, since this term tracks a
    # continuous, non-resetting clock with incommensurate periods.
    seasonal_amp *= 1.0 + 0.15 * _pseudo_random_series(
        t_cont, seed=1009, n_components=3, period_range=(400, 1100), amp_scale=1.0
    )

    # Synoptic-scale variability: irregular multi-week fluctuations layered
    # on top of the smooth seasonal cycle so timeseries/profile charts don't
    # read as a single clean repeating sine wave.
    synoptic_noise = _pseudo_random_series(
        t_cont, seed=4211, n_components=6, period_range=(10, 140), amp_scale=0.5
    )

    # Base surface temperature field (26°C - 30.5°C)
    sst_base = (
        29.2
        + seasonal_amp
        + synoptic_noise
        - 0.12 * (lat_grid - 5.0)
        + 0.6 * np.sin((lon_grid - 70.0) * np.pi / 40.0)
    )

    # Mesoscale eddy field (dynamic eddies with westward drift: ~0.1 deg/day).
    # Drift uses the continuous day index so it keeps advancing across year
    # boundaries instead of jumping back to 0 every Jan 1.
    drift = (t_cont * 0.12) % (2 * np.pi)
    eddy_1 = 1.1 * np.sin(0.4 * lat_grid + 0.3 * lon_grid - drift) * np.cos(0.25 * lon_grid)
    eddy_2 = 0.8 * np.sin(0.6 * lat_grid - 0.5 * (lon_grid + drift))
    eddy_3 = 0.6 * np.cos(0.8 * (lat_grid - 12.0)) * np.sin(0.7 * (lon_grid - 82.0))
    eddy_field = eddy_1 + eddy_2 + eddy_3

    # Reproducible small-scale turbulence texture, unique per day. Strongest
    # near the surface and faded out with depth in the loop below, so it
    # breaks up the perfectly smooth/periodic spatial pattern without
    # overriding the overall decrease-with-depth trend.
    turbulence = _smooth_field_noise(_date_seed(date, "turb"), lat_grid.shape, sigma=1.6) * 0.45

    sst = sst_base + eddy_field
    # Clip realistic SST range
    sst = np.clip(sst, 24.5, 31.8)

    # Deep water temperature at 1000m: ~5.5°C to 7.0°C
    deep_temp = 5.8 + 0.04 * (lat_grid - 5.0) + 0.2 * np.sin(lon_grid * np.pi / 30.0)

    # Thermocline decay across 15 depth levels
    field_3d = np.zeros((len(DEPTHS_M), len(LATS), len(LONS)), dtype=np.float32)

    for d_idx, depth in enumerate(DEPTHS_M):
        if depth == 0:
            layer = sst.copy()
        elif depth <= 30:
            # Upper mixed layer: very little decay (~0.1 - 0.3°C)
            layer = sst - (depth / 30.0) * 0.35 + 0.15 * eddy_field
        elif depth <= 200:
            # Main thermocline: steep exponential/sigmoidal drop
            alpha = (depth - 30.0) / 170.0
            decay_factor = 1.0 / (1.0 + np.exp((depth - 90.0) / 35.0))
            # Temperature decays from ~28°C at 30m towards ~14°C at 200m
            layer = deep_temp + (sst - 0.35 - deep_temp) * (0.35 + 0.65 * decay_factor)
            # Eddies penetrate deepest in thermocline (eddy baroclinic signature)
            layer += eddy_field * (1.2 * decay_factor)
        else:
            # Deep ocean (>200m down to 1000m): slow gradual asymptotic approach to deep_temp
            # 200m ~ 13-15°C, 500m ~ 9-11°C, 1000m ~ 5.5-7°C
            ratio = (depth - 200.0) / 800.0
            layer = deep_temp + (14.0 - deep_temp) * np.exp(-1.8 * ratio)
            # Weak eddy decay at depth
            layer += 0.25 * np.exp(-2.0 * ratio) * eddy_field

        # Add the turbulence texture, fading out with depth so the profile
        # still mostly decreases with depth overall.
        layer = layer + turbulence * np.exp(-depth / 300.0) * 0.5

        # Mask land cells with NaN
        layer[land_mask] = np.nan
        field_3d[d_idx] = layer.astype(np.float32)

    return field_3d


if __name__ == "__main__":
    test_field = reconstruct_field("2025-01-15")
    print(f"Reconstructed field shape: {test_field.shape}")
    print(f"Surface ocean temp min: {np.nanmin(test_field[0]):.2f}°C, max: {np.nanmax(test_field[0]):.2f}°C, mean: {np.nanmean(test_field[0]):.2f}°C")
    print(f"1000m ocean temp min: {np.nanmin(test_field[-1]):.2f}°C, max: {np.nanmax(test_field[-1]):.2f}°C, mean: {np.nanmean(test_field[-1]):.2f}°C")
    print(f"NaN (land) cells count per level: {np.isnan(test_field[0]).sum()}")
