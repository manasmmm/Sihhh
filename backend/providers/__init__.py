from config import DATA_SOURCE
from .base import TemperatureProvider
from .mock_provider import MockProvider
from .model_output_provider import ModelOutputFileProvider
from .model_provider import ModelProvider

def get_provider() -> TemperatureProvider:
    if DATA_SOURCE == "files":
        return ModelOutputFileProvider()
    elif DATA_SOURCE == "model":
        return ModelProvider()
    else:
        return MockProvider()
