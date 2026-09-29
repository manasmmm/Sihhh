# OceanEmbed — Team Crisis Workers

**Smart India Hackathon 2026 — Problem Statement SIH26066**
*Reconstructing subsurface ocean temperature from surface satellite data, for the North Indian Ocean*

---

## The problem

Satellites give us a detailed, daily picture of the ocean **surface**: temperature, height, currents, winds. What they cannot see is what lies **below** — and that hidden layer is exactly what drives the things that matter most for India's coast:

- **Fisheries** — fish concentrate around subsurface temperature fronts and the thermocline, not just surface warmth.
- **Cyclone intensification** — a storm draws its strength from the heat stored in the upper few hundred metres of the ocean, not the surface alone.
- **The monsoon** — subsurface heat content shapes how much moisture the ocean gives up to the atmosphere.

Measuring this directly needs ARGO floats and research ships, which are sparse and slow. INCOIS's own Potential Fishing Zone (PFZ) advisories, for instance, are built from surface data alone, because that's what satellites provide every day.

**OceanEmbed reconstructs the missing layer** — full-depth ocean temperature, every day, across the entire North Indian Ocean — from the surface data we already collect for free.

## Our approach

```
7 daily surface satellite channels (30-day history)
        │   SST · SSS · SSH/SLA · currents (u, v) · winds (u, v)
        ▼
Tree-stage embedding (Random Forest / XGBoost)
        │   window statistics (mean, std, trend, day-7 lag) → a per-column "z_col" feature
        ▼
GNN-OAM — a graph neural network with attention-based message passing
        │   the ocean is treated as a 3-D graph of (lat, lon, depth) nodes;
        │   6 attention layers reason across neighbouring columns and depths
        │   trained with a physics-guided loss (temperature + salinity + density consistency)
        ▼
Full-depth reconstruction: 15 standard depths (0–1000 m), 0.25° grid, daily
        ▼
Derived ocean layers            Fisheries enrichment
  · warm-layer / mixed-layer      · adds subsurface structure to
    depth                           INCOIS PFZ advisories
  · subsurface temperature        · per-zone summary + fisherman
    fronts (incl. ones invisible    message, in English and Hindi
    to satellites)
  · cyclone heat potential
```

The model (`GNN-OAM`, `model/gnn-oam-6-layer-FINAL.ipynb`) was trained on GLORYS12 reanalysis as the ground-truth target, using 2016–2023 data for training/validation/test and fine-tuned separately on more recent held-out days — so its accuracy is measured on days it never saw during training, not just on the training period.

**What makes this more than "just another interpolation":**
1. **Physically grounded**, not just statistically fitted — the training loss enforces consistency between the reconstructed temperature, salinity, and the resulting water density (via the TEOS-10 equation of state), so the output respects real ocean physics, not just pattern-matching.
2. **Reveals structure invisible to satellites** — subsurface-only fronts (a temperature boundary at 50 m with no surface signature at all) are exactly the kind of feature a surface-only product like today's PFZ advisory cannot see, by definition.
3. **Built to plug into what INCOIS already runs** — the dashboard doesn't replace the PFZ advisory, it reads the same advisory format and adds a subsurface layer on top of it.

## The prototype

A two-tab web dashboard serving the model's output.

### Explorer

- Interactive map of the North Indian Ocean (5°N–30°N, 45°E–105°E) at 0.25° resolution, with a depth rail (0–1000 m, 15 levels) and a day-by-day timeline with play/pause animation.
- Click any ocean point for its full temperature history and vertical profile, with the warm-layer depth and mixed-layer depth marked.
- Layer switch to view derived ocean structure instead of raw temperature: warm-layer depth, mixed-layer depth, and horizontal temperature fronts at 0 m, 50 m and 100 m.
- Toggle between five background maps (satellite, NASA Blue Marble, ocean bathymetry, and more), overlay ARGO float positions, and view the basin-wide average temperature over time.
- Download any day as a CF-compliant NetCDF file — either the raw temperature field or the full set of derived layers (including cyclone heat potential).

### Fisheries Advisory

- Reads INCOIS-format PFZ advisory data for 14 coastal sectors and adds, per fishing zone: warm-layer depth, mixed-layer depth, whether a subsurface-only front is present, and (where species data is configured) a suggested gear depth.
- One-click, ready-to-send fisherman advisory message, generated in English or Hindi.
- Full advisory table with unit toggles (km/nautical miles, metres/fathoms) and CSV export.

### Under the hood

- The dashboard reads model output through a clean provider interface (`backend/providers/`) — swap in new daily files, or run the model live inside the backend, without touching the API or the frontend.
- Every derived quantity (fronts, thermocline depth, cyclone heat potential, etc.) is computed server-side from the model's raw temperature field, so it stays consistent across the map, the point-inspection charts, the fisheries table and the NetCDF exports.

## Tech stack

| | |
|---|---|
| **Model** | PyTorch — GNN-OAM (graph attention network) + scikit-learn/XGBoost tree stage |
| **Backend** | FastAPI, xarray/netCDF4, NumPy, Matplotlib (map rendering) |
| **Frontend** | React + TypeScript, Vite, Tailwind CSS, Leaflet (map), Recharts (charts) |
| **Data** | GLORYS12 reanalysis (training target), satellite SST/SSS/SSH/currents/winds (model inputs) |

## Project structure

```
backend/            FastAPI server: data providers, derived-layer computation, PFZ enrichment
  gnn_engine/        In-backend GNN-OAM inference (optional; runs the model live)
  providers/         mock / file-based / live-model data sources behind one interface
frontend/           React + TypeScript dashboard (Explorer + Fisheries Advisory tabs)
model/              Kaggle training notebook and trained model weights
kaggle/             Script to export model output from Kaggle straight into the dashboard
scripts/            Setup, validation, and test utilities
i18n/               English / Hindi translation files
config/             Species and other tunable configuration
```

## Running it

```bash
cd backend
python main.py
```
Open `http://localhost:8000` — the backend also serves the built frontend.

By default it runs on bundled demo data (`DATA_SOURCE=mock`). To serve real model output, set `DATA_SOURCE=files` (reads daily files from `backend/data/model_output/`) or `DATA_SOURCE=model` (runs the model live — see `backend/model_artifacts/README.md` and `model/README.md` for how to wire up the trained weights).

```bash
python -m unittest discover -s scripts/tests -v
```

For data-source modes, connecting the trained model, and the full API reference, see [`docs/SETUP.md`](docs/SETUP.md).

## Team

**Crisis Workers** — Smart India Hackathon 2026, Problem Statement SIH26066 (set by INCOIS).
