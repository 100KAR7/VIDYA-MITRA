import os
import sys
import warnings

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.helpers import load_artifact
from utils.logger import get_logger

log = get_logger("vidya.trainer")

TARGETS = [
    "next_topic",
    "recommended_difficulty",
    "success_probability_bin",
    "needs_revision",
]


class Trainer:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.model_dir = cfg["paths"]["model_dir"]
        self.models = {}

    def load_all(self) -> None:
        for target in TARGETS:
            path = f"{self.model_dir}xgb_{target}.pkl"
            self.models[target] = load_artifact(path)
        log.info("Loaded %s models.", len(self.models))

    def get_model(self, target: str):
        return self.models.get(target)
