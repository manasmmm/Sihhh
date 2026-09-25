import numpy as np
import xarray as xr
from .base import TemperatureProvider

class ModelProvider(TemperatureProvider):
    """
    ModelProvider runs the model inside the backend (future).
    
    Contract:
    - Input: a date.
    - Steps (TODO, to be filled by the team):
      1. `load_inputs(day)` -> the 5 harmonised surface inputs on the 0.25 deg daily grid
         (SST, SSS, SSH/SLA, currents U/V, winds U/V)
      2. `preprocess(inputs)`
      3. `run_inference(tensor)` using the trained OceanEmbed-ViT weights at MODEL_WEIGHTS_PATH.
    - Output: numpy.ndarray, float32, shape (15, 101, 241), °C, depth order and grid exactly as
      in Section 3, NaN on land.
      The provider wraps it into the Dataset format of 4.1 with attrs["source"] = "model" and
      attrs["model_version"].
    """

    def available_dates(self):
        raise NotImplementedError("ModelProvider not implemented yet; set DATA_SOURCE=mock or files")

    def get_temperature(self, day: str) -> xr.Dataset:
        raise NotImplementedError("ModelProvider not implemented yet; set DATA_SOURCE=mock or files")
