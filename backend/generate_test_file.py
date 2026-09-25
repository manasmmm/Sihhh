
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers.mock_provider import MockProvider
from model_bridge import get_land_mask
from scripts.save_model_output import save_model_output
import xarray as xr

# Use mock provider to generate
provider = MockProvider()
ds = provider.get_temperature('2026-09-25')
arr = ds['thetao'].values

save_model_output(arr, '2026-09-25', out_dir='backend/data/model_output', model_version='TEST-FILE-FROM-MOCK')

