# OceanEmbed — Team Crisis Workers

**Smart India Hackathon 2026 · Problem Statement SIH26066**

*OceanEmbed: Satellite Embedding-Based Deep Learning Framework for Reconstruction of Subsurface Ocean Temperature from Surface Satellite Observations*

| | |
|---|---|
| **Theme** | Disaster Management |
| **Organization** | Ministry of Earth Sciences (MoES) |
| **Category** | Software |
| **Team** | Crisis Workers |

**Links:** [Live prototype](https://oceanembed-4z4g.onrender.com/) · [Demo video](https://www.youtube.com/watch?v=DaPUYD2coU8) · [Data](https://drive.google.com/drive/folders/1DK8M_-ag9nDpAFU06-tXmQKexKEJ3FSv)

---

## The problem

**Fishermen are fishing blind.** A fisherman heading into the Arabian Sea today gets advice based only on what satellites see at the surface. But fish, cyclones and marine heatwaves are shaped by the temperature *below* it.

- **The ocean is a black box.** Real depth measurements come from ARGO floats, which are scattered thousands of kilometres apart and report roughly every 10 days. Large parts of the Arabian Sea and Bay of Bengal go weeks without a fresh profile.
- **Moored buoys (OMNI, RAMA) are accurate but fixed.** They cover only a few points and are costly to multiply.
- **Current advisories stop at the surface.** INCOIS Potential Fishing Zone (PFZ) advisories use surface SST and chlorophyll: they tell fishermen *where* to go, never *how deep*.
- **The data isn't usable by the people who need it.** Subsurface products arrive as NetCDF files and research portals meant for oceanographers.

## Our solution

OceanEmbed uses the surface data India's satellites already capture every day (sea temperature, salinity, sea level, currents and winds) to reconstruct a full temperature profile down to 1000 m for **every point** of the North Indian Ocean, **every day**, including the gaps no float ever visits. It serves the result through a dashboard anyone can read.

## Technical approach

**Pipeline**

1. **Harmonise** 5 surface inputs (SST · SSS · SSH/SLA · currents u/v · winds u/v) onto a common 0.25°, daily grid covering 5–30°N, 45–105°E. No subsurface data is used as input.
2. **XGBoost stage:** summarise each location's recent 30-day surface history into a compact temporal embedding, `z_col`.
3. **Build the 3-D graph:** every (latitude, longitude, depth) cell is a node, combining `z_col` with a learned depth encoding.
4. **Combine three adjacency sources:** 26-connected spatial/vertical neighbours, long-range surface-correlation links, and self-connections.
5. **Edge-aware OAM attention** (6 stacked layers, 4 heads) refines node representations using both node and edge information.
6. **Cluster-conditioning skip connection** gives each node its depth regime and seasonal regime after the attention stack.
7. **Readout** reconstructs temperature at 15 depths (0–1000 m) and predicts auxiliary salinity for the physics-guided loss.
8. **Train on GLORYS12** reanalysis; evaluate on held-out days and against independent INCOIS gridded ARGO fields.

**Physics-guided loss.** Besides the data term, the loss penalises errors in temperature and salinity and in the resulting **seawater density** (TEOS-10 equation of state), so reconstructions stay physically consistent rather than just pattern-matched.

**Spatio-temporal clustering.** Instead of fixed depth bands or a monsoon calendar, the data decides. Correlation graphs across depths and across the seasons are clustered spectrally, and the number of groups is chosen automatically (eigengap). These depth and season regimes feed back into the encoder, so one model adapts across the whole basin and the whole year.

**Why a GNN?** Following *3-D Ocean Temperature Prediction via Graph Neural Network With Optimized Attention Mechanisms* (IEEE, 2024), we model the ocean as a network with edge-aware attention, which captures long-range connections that CNNs and ViTs miss. In our own benchmarks of 3D U-Net++, ViT and GNN:
- **ViT** struggled (about 2 °C RMSE, inflated in the thermocline).
- **U-Net++** was competitive but carried a −0.26 °C bias.
- **GNN** gave near-zero overall bias and roughly halved upper-ocean error, and its explicit graph structure makes predictions easier to interpret. It became our final model.

**Lightweight:** 98,130 trainable parameters.

## Results

Evaluation on **31 held-out days (December 2024)** against GLORYS12 reanalysis, with the fine-tuned GNN checkpoint (`model/gnn-oam-6-layer-FINAL.ipynb`, Section 28):

| Overall RMSE | Overall correlation | Overall bias |
|---|---|---|
| **1.03 °C** | **0.990** | **−0.04 °C** |

| Depth (m) | 0 | 10 | 20 | 50 | 75 | 100 | 125 | 150 | 200 | 300 | 500 | 1000 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RMSE (°C) | 0.51 | 0.52 | 0.53 | 1.04 | 1.57 | 1.77 | 1.73 | 1.39 | 1.14 | 0.87 | 0.68 | 0.64 |
| Correlation | 0.95 | 0.94 | 0.92 | 0.79 | 0.76 | 0.71 | 0.64 | 0.70 | 0.76 | 0.81 | 0.84 | 0.78 |

Error is lowest in the upper 20 m (about 0.5 °C) and in the deep ocean, and highest around the thermocline (75–150 m), where temperature changes fastest with depth.

An additional check against independent **INCOIS gridded ARGO** fields (12 months of 2024; Section 31b of the notebook) gives a mean RMSE of 1.23 °C across depths. 2024 was also used for fine-tuning, so this is a sanity check rather than a strict out-of-sample test; a fully independent test needs 2025 surface inputs.

## Impact

**Fisheries departments and fishermen's cooperatives.** OceanEmbed derives the thermocline depth (D20, the 20 °C isotherm), the standard proxy for where warm-water species such as tuna and mackerel concentrate. It doesn't replace PFZ: each PFZ zone is enriched with subsurface fields through a lightweight API, leaving PFZ's own pipeline untouched.

**Disaster management.** INCOIS's SAMUDRA issues storm-surge and high-wave alerts but has no subsurface heat-content layer for cyclone intensity. We compute daily, basin-wide **tropical cyclone heat potential (TCHP)** and **26 °C isotherm depth (D26)** from the reconstructed profiles. These flag pre-conditioning zones for rapid intensification, particularly in the Bay of Bengal.

**Marine heatwaves (planned).** Applying Hobday-style 90th-percentile thresholds to the reconstructed depth profiles would detect subsurface warming that surface-only SST misses. This needs a multi-year climatology and is the next extension.

## The prototype

A two-tab web dashboard: [oceanembed-4z4g.onrender.com](https://oceanembed-4z4g.onrender.com/).

**Explorer**
- Map of the North Indian Ocean at 0.25° with a depth rail (15 levels, 0–1000 m) and a day-by-day timeline with play/pause.
- Click any ocean point for its temperature time series and vertical profile, with warm-layer depth (D20) and mixed-layer depth marked.
- Derived layers: warm-layer depth, mixed-layer depth, and temperature fronts at 0, 50 and 100 m.
- Five background maps, ARGO float positions, and the basin-wide average temperature.
- Download any day as CF-compliant NetCDF: the temperature field, or the derived layers (including TCHP and D26).

**Fisheries Advisory**
- INCOIS-format PFZ advisories for 14 coastal sectors, each zone enriched with warm-layer depth, mixed-layer depth and subsurface-front information.
- A ready-to-send fisherman message in English or Hindi.
- Advisory table with unit toggles (km / nautical miles, metres / fathoms) and CSV export.

## Feasibility

- **Technical:** only open surface products go in, regridded to one daily 0.25° grid; every location and depth is a node in one 3-D graph.
- **Economic:** no new satellites, sensors or cruises. Every input is an open product already produced daily.
- **Operational:** derived layers (D20, TCHP, D26) come straight from the profiles and plug in alongside existing PFZ and SAMUDRA services. The model is retrained on fresh reanalysis/ARGO data at regular intervals, and output is compared with new floats as they report so drift shows up early.

## Data sources

| Variable | Source |
|---|---|
| Sea surface temperature | GHRSST Level 4 MUR 0.25° Global Foundation SST Analysis (v4.2) |
| Sea surface salinity | SMAP L3 (NASA) |
| Sea surface height | DUACS altimetry |
| Surface currents (u, v) | OSCAR v2.0 |
| Surface winds (u, v) | ERA5 10 m winds / ASCAT |
| Training target (subsurface temperature) | GLORYS12V1 (Copernicus Marine) |
| Independent validation | INCOIS Live Access Server (gridded ARGO) |

## References

1. *3-D Ocean Temperature Prediction via Graph Neural Network With Optimized Attention Mechanisms*, IEEE Geoscience, 2024.
2. Feng et al., 2026. DSVIT. *Deep Sea Research Part II*, 10.1016/j.dsr2.2025.105589.
3. *Adaptive Spatiotemporal Clustering Framework for 3D OST Reconstruction*, arXiv 2605.00860, 2026.
4. *North Atlantic Explainable DL framework*, Int'l J. Digital Earth, 2026, 10.1080/17538947.2026.2632430.
5. isQG method: Wang et al. 2013, *J. Phys. Oceanogr.*; Liu et al. 2017, *JGR Oceans*.
6. *Attention-enhanced 3D-U-Net++ with transfer learning*, ESSD, 2026.

## Tech stack

| | |
|---|---|
| **Model** | PyTorch (GNN-OAM) + XGBoost stage |
| **Backend** | FastAPI, xarray / netCDF4, NumPy |
| **Frontend** | React + TypeScript, Vite, Tailwind CSS, Leaflet, Recharts |

## Repository structure

```
model/              Training notebook and trained model weights
backend/            FastAPI server: data providers, derived layers, PFZ enrichment
  gnn_engine/        In-backend GNN-OAM inference (optional)
frontend/           React + TypeScript dashboard
kaggle/             Export script: Kaggle model output -> dashboard
scripts/            Checks, batch inference and tests
i18n/               English / Hindi translations
docs/SETUP.md       Detailed setup, model wiring and API reference
```

## Running locally

```bash
cd backend
python main.py
```

Open `http://localhost:8000`; the backend also serves the built frontend. See [`docs/SETUP.md`](docs/SETUP.md) for data-source modes and connecting the trained model.
