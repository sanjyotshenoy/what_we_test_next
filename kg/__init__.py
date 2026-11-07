"""The knowledge graphs. Importing this package picks CPU or GPU mode from WWTN_GPU (see kg/backend.py)."""
from kg.backend import activate_from_env

activate_from_env()
