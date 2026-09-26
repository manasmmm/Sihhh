"""
OceanEmbed GNN-OAM inference inside the backend (DATA_SOURCE = "model").

A CPU port of the inference path of the Kaggle notebook OceanEmbed-GNN-OAM-FULL.ipynb
(Sections 7, 9, 11, 12, 13 and 20). It reads the artifacts the notebook writes to
/kaggle/working/OceanEmbed_run/ and reconstructs the (15, 101, 241) temperature field
for any day that has a 30-day surface window in the cached inputs.

torch is imported lazily, so the rest of the backend works without it.
"""
from .artifacts import GnnArtifacts, ArtifactsMissing, find_artifacts  # noqa: F401
