# OceanEmbed Viewer

**Interactive Subsurface Ocean Temperature Reconstruction Dashboard (North Indian Ocean)**
*Smart India Hackathon (SIH) — Problem Statement SIH26066*
*UI/UX inspired by Copernicus Marine Data Store ("MyOcean" Expert Viewer)*

---

## Overview

**OceanEmbed Viewer** is a high-performance web dashboard that visualizes 3D subsurface ocean potential temperature ($\theta_o$) reconstructed by deep learning (`OceanEmbed-Attn3D-UNet++`) from surface satellite observations.

### Domain & Grid Contract
- **Region**: North Indian Ocean ($5.0^\circ\text{N}$ to $30.0^\circ\text{N}$, $45.0^\circ\text{E}$ to $105.0^\circ\text{E}$)
- **Spatial Resolution**: $0.25^\circ \times 0.25^\circ$ ($101 \text{ lat} \times 241 \text{ lon}$ grid cells)
- **Depth Levels (15, meters)**: `[0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]`
- **Temporal Coverage**: Daily precomputed multi-dimensional Zarr store
- **Land Mask**: Natural Earth $50\text{m}$ high-resolution land-sea mask (land cells rendered as transparent `NaN`, never interpolated)

---

## Quick Start (Two Commands)

### 1. Start the Backend API & Server
```bash
cd oceanembed-viewer/backend
python main.py
```
> The backend runs on `http://localhost:8000`. If `data/reconstruction.zarr` is not yet generated, it automatically precomputes the 120-day baseline on first startup.

### 2. Start the Frontend (Development Mode)
```bash
cd oceanembed-viewer/frontend
npm run dev
```
> The frontend will open at `http://localhost:3000` with hot-reloading and proxying to the backend API.

### Single-Command Production Serving
You can also run the entire stack as a single deployable unit. The prebuilt frontend in `frontend/dist` is served directly by the FastAPI backend:
```bash
cd oceanembed-viewer/backend
python main.py
```
Open **`http://localhost:8000`** in any web browser.

---

## How to Plug in Your Real Trained PyTorch Model

All model interaction is isolated behind a single clean seam in [`backend/model_bridge.py`](file:///oceanembed-viewer/backend/model_bridge.py).

### Step 1: Open `backend/model_bridge.py`
Locate the function `reconstruct_field(date: str) -> np.ndarray`:

```python
def reconstruct_field(date: str) -> np.ndarray:
    """
    Parameters:
        date: 'YYYY-MM-DD'
    Returns:
        float32 numpy array, shape (15, 101, 241), °C, NaN over land.
        Depth axis MUST match DEPTHS_M: index 0 = 0m ... index 14 = 1000m.
    """
    # =========================================================================
    # TODO: replace with real OceanEmbed-Attn3D-UNet++ checkpoint
    # =========================================================================
```

### Step 2: Wire your PyTorch checkpoint
Replace the synthetic physics simulation lines in `reconstruct_field()` with your inference call:

```python
import torch

# Load model checkpoint once at module level
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = OceanEmbedAttn3DUNetPlusPlus.load_from_checkpoint("checkpoints/best_model.ckpt")
model.to(DEVICE)
model.eval()

def reconstruct_field(date: str) -> np.ndarray:
    # 1. Load satellite input features for `date` (SLA, SST, SSS, Wind Stress)
    inputs = load_satellite_tensors(date) # Tensor shape: (1, Channels, 112, 256)
    inputs = inputs.to(DEVICE)

    # 2. Forward pass
    with torch.no_grad():
        output = model(inputs) # Output shape: (1, 15, 112, 256)

    # 3. Crop padded margin back to native grid (15, 101, 241)
    field_3d = output.squeeze(0)[:, :101, :241].cpu().numpy().astype(np.float32)

    # 4. Apply land mask
    land_mask = get_land_mask()
    field_3d[:, land_mask] = np.nan

    return field_3d
```

### Step 3: Re-run Precomputation
Run the batch precompute script over your desired test dates:
```bash
python backend/scripts/precompute.py --start 2023-01-01 --end 2023-04-30 --force
```
Nothing else in the stack needs to change! The entire dashboard (maps, rasters, profiles, timeseries) will instantly reflect the real model output.

---

## Architecture & Project Structure

```
oceanembed-viewer/
├── backend/
│   ├── main.py               # FastAPI REST API & static file mount
│   ├── model_bridge.py       # Single integration seam with reconstruct_field()
│   ├── data_store.py         # Fast Zarr store query helpers & caching
│   ├── raster.py             # Bilinear RGBA PNG raster renderer (turbo colormap)
│   ├── requirements.txt      # Python dependencies
│   ├── scripts/
│   │   └── precompute.py     # Batch populates data/reconstruction.zarr
│   └── data/
│       ├── land_mask.npy     # High-res Natural Earth 50m land-sea mask
│       └── reconstruction.zarr/  # 4D precomputed data store (time, depth, lat, lon)
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Copernicus MyOcean layout & reactive state
│   │   ├── api.ts            # REST client wrappers for /api/v1/*
│   │   ├── types.ts          # TypeScript interfaces
│   │   ├── index.css         # Dark theme & glassmorphism styling
│   │   └── components/
│   │       ├── MapView.tsx         # Leaflet map locked to 5°-30°N, 45°-105°E
│   │       ├── DepthSlider.tsx     # Rail depth slider with 15 discrete stops
│   │       ├── TimeSlider.tsx      # Timeline with play/pause animation & month ticks
│   │       ├── PointCard.tsx       # Floating pinned card with linked live charts
│   │       ├── ProfileChart.tsx    # Inverted-axis depth profile chart (0m at top)
│   │       ├── TimeseriesChart.tsx # Multi-month temperature evolution chart
│   │       ├── Colorbar.tsx        # 0°C to 32°C turbo colormap legend
│   │       └── BasinAverageModal.tsx # Basin-wide spatial mean time series
│   ├── dist/                 # Production compiled static bundle
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## Features Implemented

1. **Copernicus MyOcean Expert Theme**:
   - Near-black `#0a0e14` base background with CartoDB Dark Matter tiles
   - Floating translucent dark cards with backdrop blur (`backdrop-filter: blur(16px)`)
   - Signature cyan/teal accent `#4fd1c5`

2. **Locked North Indian Ocean Viewport**:
   - Panning and zooming restricted strictly to the North Indian Ocean domain ($5^\circ\text{N} - 30^\circ\text{N}$, $45^\circ\text{E} - 105^\circ\text{E}$)
   - High-resolution turbo colormap raster ($964 \times 404$ bilinear upscale) overlay

3. **15-Level Discrete Depth Rail Slider**:
   - Discrete stops from $0\text{m}$ down to $1000\text{m}$ ($0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000\text{m}$)
   - Re-fetches raster and reactively shifts depth reference lines across all open cards

4. **Interactive Timeline & Animation**:
   - Scrubbing across 120 days ($2023\text{-}01\text{-}01$ to $2023\text{-}04\text{-}30$)
   - Play/Pause animation with $4\times, 6\times, 10\times$ speed controls
   - Month boundary indicators ("Jan 2023", "Feb 2023", etc.)

5. **Click-to-Inspect Point Soundings**:
   - Snaps to exact discrete $0.25^\circ$ model grid
   - Chart A: Time series temperature with vertical date reference line and Min/Median/Max summary
   - Chart B: Vertical depth profile with inverted depth axis ($0\text{m}$ at top, $1000\text{m}$ at bottom) and horizontal depth reference line
   - Multiple pins open simultaneously with distinct color coding
   - Live updates: changing global date or depth updates all open cards automatically

6. **Land Mask & Graceful Error Handling**:
   - Real-world Natural Earth $50\text{m}$ coastline mask
   - Clicking land returns HTTP 422 and triggers a friendly toast message without crashing

7. **Stretch Features**:
   - **Basin Average**: Spatial mean time series chart across the entire North Indian Ocean
   - **Ground Truth Validation**: Toggleable Gridded Argo float profile locations
   - **Export**: JSON/Data export button on every pinned card
   - **Live Inference Endpoint**: `POST /api/v1/infer?date=YYYY-MM-DD`
