import config
from .base import TemperatureProvider
from .mock_provider import MockProvider
from .model_output_provider import ModelOutputFileProvider
from .model_provider import ModelProvider, NOT_IMPLEMENTED_MSG

_PROVIDERS = {
    "mock": MockProvider,
    "files": ModelOutputFileProvider,
    "model": ModelProvider,
}
_INSTANCES = {}


def get_provider() -> TemperatureProvider:
    """Provider selected by config.DATA_SOURCE (read at call time so tests can switch it)."""
    key = config.DATA_SOURCE if config.DATA_SOURCE in _PROVIDERS else "mock"
    if key not in _INSTANCES:
        _INSTANCES[key] = _PROVIDERS[key]()
    return _INSTANCES[key]
