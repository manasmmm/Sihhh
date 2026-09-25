import os

# Data source: "mock", "files", or "model"
DATA_SOURCE = os.environ.get("DATA_SOURCE", "mock")

# Directories
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
MODEL_OUTPUT_DIR = os.path.join(DATA_DIR, "model_output")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
DERIVED_DIR = os.path.join(DATA_DIR, "derived")

# Create directories if they don't exist
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DERIVED_DIR, exist_ok=True)

# Grid constants
LATS = [round(5.0 + i * 0.25, 2) for i in range(101)] # 5.0 to 30.0
LONS = [round(45.0 + i * 0.25, 2) for i in range(241)] # 45.0 to 105.0
DEPTHS_M = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]

MODEL_OUTPUT_VAR = "thetao"
VALIDITY_DAYS = 1
