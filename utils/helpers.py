import json
import os
from datetime import datetime, timezone
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


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_artifact(obj: Any, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    joblib.dump(obj, path)


def load_artifact(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Artifact not found: {path}. "
            "Please run `python main.py --mode train` first to generate preprocessing encoders and models."
        )
    return joblib.load(path)


def now_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
