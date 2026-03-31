import json
import os
from datetime import datetime
from typing import Any

import joblib
import numpy as np
import yaml


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def save_json(obj: Any, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, default=_json_default)


def load_artifact(path: str) -> Any:
"""
utils/helpers.py
PURPOSE : Shared utility functions used across every module.

FUNCTIONS:
  load_config()    - reads config/config.yaml → returns dict
  save_json()      - writes dict to .json file
  load_json()      - reads .json file → returns dict
  save_artifact()  - saves any Python object to .pkl (models, encoders)
  load_artifact()  - loads a .pkl file back into Python
  now_slug()       - returns unique timestamp string for filenames
"""

import os
import json
import yaml
import joblib
import numpy as np
from datetime import datetime
from typing import Any


def load_config(path: str = "config/config.yaml") -> dict:
    """Reads the YAML config file and returns it as a Python dict."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def save_json(obj: dict, path: str):
    """Saves a dict to a JSON file. Creates parent folders automatically."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=_json_default)


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _json_default(obj):
    """Handles numpy types that standard json can't serialise."""
    if isinstance(obj, (np.integer,)):  return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, np.ndarray):     return obj.tolist()
    if isinstance(obj, datetime):       return obj.isoformat()
    raise TypeError(f"Not serialisable: {type(obj)}")


def save_artifact(obj: Any, path: str):
    """Saves any Python object (model, scaler, encoder) to a .pkl file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    joblib.dump(obj, path)


def load_artifact(path: str) -> Any:
    """Loads a .pkl file previously saved by save_artifact()."""
    return joblib.load(path)


def now_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _json_default(obj: Any):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    """Returns unique timestamp string e.g. '20260320_143022_456789'."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")
