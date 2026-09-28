"""
Central configuration for the OceanEmbed backend.

Every tunable value (paths, grid, thresholds, physical constants, data-source
switch) lives here. Do not scatter magic numbers in other modules.
"""
import os

# =============================================================================
# Data source switch: "mock", "files" or "model" (env var DATA_SOURCE overrides)
# =============================================================================
DATA_SOURCE = os.environ.get("DATA_SOURCE", "mock").strip().lower()

# =============================================================================
# Directories
# =============================================================================
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, "data")
MODEL_OUTPUT_DIR = os.environ.get("MODEL_OUTPUT_DIR", os.path.join(DATA_DIR, "model_output"))
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
DERIVED_DIR = os.path.join(DATA_DIR, "derived")
PFZ_DIR = os.path.join(DATA_DIR, "pfz")
ARGO_DIR = os.path.join(DATA_DIR, "argo")
VALIDATION_DIR = os.path.join(DATA_DIR, "validation")
CLIMATOLOGY_DIR = os.path.join(DATA_DIR, "climatology")

ARGO_POSITIONS_FILE = os.path.join(ARGO_DIR, "argo_positions.csv")
VALIDATION_METRICS_FILE = os.path.join(VALIDATION_DIR, "validation_metrics.json")
SPECIES_FILE = os.path.join(REPO_DIR, "config", "species.json")
I18N_DIR = os.path.join(REPO_DIR, "i18n")

for _d in (MODEL_OUTPUT_DIR, OUTPUT_DIR, DERIVED_DIR, PFZ_DIR, ARGO_DIR, VALIDATION_DIR):
    os.makedirs(_d, exist_ok=True)

# =============================================================================
# Grid definition (Section 3 of the spec)
# =============================================================================
LAT_MIN, LAT_MAX = 5.0, 30.0
LON_MIN, LON_MAX = 45.0, 105.0
GRID_STEP_DEG = 0.25
LATS = [round(LAT_MIN + i * GRID_STEP_DEG, 2) for i in range(101)]  # 5.0 .. 30.0
LONS = [round(LON_MIN + i * GRID_STEP_DEG, 2) for i in range(241)]  # 45.0 .. 105.0
DEPTHS_M = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]
GRID_SHAPE = (len(DEPTHS_M), len(LATS), len(LONS))  # (15, 101, 241)

MODEL_OUTPUT_VAR = "thetao"
VALIDITY_DAYS = 1

# =============================================================================
# Model output file validation (Section 4.3)
# =============================================================================
DEPTH_TOLERANCE_M = 0.5
GRID_COORD_TOLERANCE_DEG = 0.01
PLAUSIBLE_TEMP_MIN_C = -2.0
PLAUSIBLE_TEMP_MAX_C = 40.0
MODEL_OUTPUT_RESCAN_SECONDS = 30  # folder is also rescanned on every /meta call
UPLOAD_MAX_BYTES = 200 * 1024 * 1024

# =============================================================================
# In-backend model: OceanEmbed GNN-OAM (DATA_SOURCE = "model")
# Drop the Kaggle run folder (OceanEmbed_run/...) anywhere under GNN_ARTIFACTS_DIR.
# Values below mirror CFG in OceanEmbed-GNN-OAM-FULL.ipynb (Sections 2 and 2b);
# keep them identical to the run that produced the checkpoint.
# =============================================================================
GNN_ARTIFACTS_DIR = os.environ.get("GNN_ARTIFACTS_DIR", os.path.join(BACKEND_DIR, "model_artifacts"))
GNN_CHECKPOINT_NAME = os.environ.get("GNN_CHECKPOINT_NAME", "gnn_C_full_epoch_28.pt")
GNN_VARIANT = "C_full"                        # A_base / B_skip / C_full
GNN_USE_SKIP = GNN_VARIANT in ("B_skip", "C_full")
GNN_MODEL_VERSION = os.environ.get(
    "GNN_MODEL_VERSION", "OceanEmbed GNN-OAM C_full epoch 28 + XGBoost stage")
GNN_CACHE_STAGES = ["finetune", "finetune2024"]   # <stage>_x.npy / _t.npy / _meta.json input caches
GNN_OUTPUT_CACHE_DIR = os.path.join(DATA_DIR, "gnn_output")   # reconstructed days are stored here once computed
GNN_T_WINDOW = 30
GNN_TILE_SIZE = 12
GNN_HALO = 2
GNN_SIM_THRESHOLD = 0.9
GNN_SIM_MAX_PARTNERS = 4
GNN_SIM_DEPTH_PAIRING = "all"
GNN_EVAL_BATCH_TILES = 12
GNN_TRAIN_YEARS = list(range(2016, 2022))     # notebook split (used only to label validation periods)
GNN_VAL_YEARS = [2022]
GNN_TEST_YEARS = [2023]
os.makedirs(GNN_ARTIFACTS_DIR, exist_ok=True)

MODEL_WEIGHTS_PATH = os.path.join(GNN_ARTIFACTS_DIR, GNN_CHECKPOINT_NAME)

# =============================================================================
# Derived layers (Section 6)
# =============================================================================
D20_ISOTHERM_C = 20.0
D26_ISOTHERM_C = 26.0

MLD_REF_DEPTH_M = 10
MLD_DELTA_T_C = 0.2

KM_PER_DEG_LAT = 110.57
KM_PER_DEG_LON_EQUATOR = 111.32
FRONT_DEPTHS_M = [0, 50, 100]
# Starting value, to be tuned by the team. Shown in the UI legend.
FRONT_THRESHOLD_C_PER_KM = 0.02

SEAWATER_DENSITY_KG_M3 = 1025.0
SEAWATER_CP_J_KG_K = 4000.0
TCHP_J_M2_TO_KJ_CM2 = 1e7

EARTH_RADIUS_KM = 6371.0
CONF_WINDOW_DAYS = 10
CONF_LENGTH_KM = 300.0
CONF_HIGH_MIN = 0.6
CONF_MEDIUM_MIN = 0.3

GEAR_DEPTH_STEP_M = 1.0  # resolution used when interpolating gear-depth ranges

# Colour ranges for derived map layers (display only)
DERIVED_DISPLAY = {
    "d20": {"vmin": 40, "vmax": 200, "cmap": "viridis_r", "units": "m"},
    "d26": {"vmin": 0, "vmax": 120, "cmap": "viridis_r", "units": "m"},
    "mld": {"vmin": 0, "vmax": 100, "cmap": "viridis_r", "units": "m"},
    "front_0m": {"vmin": 0, "vmax": 0.05, "cmap": "inferno", "units": "degC/km"},
    "front_50m": {"vmin": 0, "vmax": 0.05, "cmap": "inferno", "units": "degC/km"},
    "front_100m": {"vmin": 0, "vmax": 0.05, "cmap": "inferno", "units": "degC/km"},
    "subsurface_front_flag": {"vmin": 0, "vmax": 1, "cmap": "front_flag", "units": "1"},
    "tchp": {"vmin": 0, "vmax": 150, "cmap": "magma", "units": "kJ/cm2"},
    "confidence": {"vmin": 0, "vmax": 1, "cmap": "RdYlGn", "units": "1"},
}

# =============================================================================
# PFZ (Section 5)
# =============================================================================
PFZ_COLUMNS = [
    "date", "sector", "landmark", "direction", "bearing_deg",
    "dist_from_km", "dist_to_km", "sea_depth_from_m", "sea_depth_to_m",
    "lat_dms", "lon_dms", "lat", "lon", "valid_upto",
]
PFZ_DMS_MISMATCH_TOLERANCE_DEG = 0.001
KM_PER_NAUTICAL_MILE = 1.852
M_PER_FATHOM = 1.8288

# Approximate bounding boxes [lat_min, lon_min, lat_max, lon_max] used only to
# zoom the map. These are APPROXIMATE and not official INCOIS sector limits.
PFZ_SECTORS = [
    {"code": "GUJARAT", "name": "Gujarat", "bbox": [20.0, 66.0, 24.8, 73.0]},
    {"code": "MAHARASHTRA", "name": "Maharashtra", "bbox": [15.6, 70.0, 20.3, 73.6]},
    {"code": "GOA", "name": "Goa", "bbox": [14.7, 72.5, 15.9, 74.2]},
    {"code": "KARNATAKA", "name": "Karnataka", "bbox": [12.6, 72.5, 14.9, 75.0]},
    {"code": "KERALA", "name": "Kerala", "bbox": [8.2, 73.5, 12.8, 77.2]},
    {"code": "LAKSHADWEEP", "name": "Lakshadweep", "bbox": [8.0, 71.0, 12.5, 74.5]},
    {"code": "SOUTH_TAMIL_NADU", "name": "South Tamil Nadu", "bbox": [7.8, 76.5, 10.5, 80.5]},
    {"code": "NORTH_TAMIL_NADU", "name": "North Tamil Nadu", "bbox": [10.5, 79.5, 13.6, 82.0]},
    {"code": "SOUTH_ANDHRA_PRADESH", "name": "South Andhra Pradesh", "bbox": [13.6, 79.8, 16.2, 83.0]},
    {"code": "NORTH_ANDHRA_PRADESH", "name": "North Andhra Pradesh", "bbox": [16.2, 81.5, 19.2, 85.5]},
    {"code": "ODISHA", "name": "Odisha", "bbox": [19.0, 84.5, 21.8, 88.0]},
    {"code": "WEST_BENGAL", "name": "West Bengal", "bbox": [20.8, 86.8, 22.4, 89.2]},
    {"code": "ANDAMAN", "name": "Andaman", "bbox": [10.5, 91.5, 14.0, 94.5]},
    {"code": "NICOBAR", "name": "Nicobar", "bbox": [6.0, 92.0, 9.5, 94.5]},
]
PFZ_DEFAULT_SECTOR = "GOA"

# =============================================================================
# i18n (Section 8.5)
# =============================================================================
DEFAULT_LANGUAGE = "en"
FISHERMAN_MESSAGE_MAX_CHARS = 320
