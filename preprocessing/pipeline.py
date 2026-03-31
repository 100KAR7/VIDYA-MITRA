import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.helpers import load_artifact
from utils.logger import get_logger

log = get_logger("vidya.preprocessing")

TARGET_COLS = [
    "next_topic",
    "recommended_difficulty",
    "success_probability_bin",
    "needs_revision",
]
DROP_COLS = ["student_id"]


class PreprocessingPipeline:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.cat_feats = cfg["features"]["categorical"]
        self.num_feats = cfg["features"]["numerical"]
        self.enc_dir = cfg["paths"]["encoder_dir"]

        self.num_imputer = None
        self.cat_imputer = None
        self.scaler = None
        self.ord_encoder = None
        self.target_encoders = {}
        self.freq_maps = {}
        self.clip_bounds = {}
        self.feature_cols = []

    def transform(self, data) -> pd.DataFrame:
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = data.copy()

        df = df.drop(columns=TARGET_COLS + DROP_COLS, errors="ignore")

        for column in self.cat_feats + self.num_feats:
            if column not in df.columns:
                df[column] = np.nan

        df = self._transform_impute(df)
        df = self._clip_outliers(df)
        df = self._engineer(df)
        df = self._transform_freq_encode(df)
        df = self._transform_ord_encode(df)
        df = self._transform_scale(df)

        for column in self.feature_cols:
            if column not in df.columns:
                df[column] = 0.0
        return df[self.feature_cols]

    def decode_target(self, target: str, encoded) -> np.ndarray:
        return self.target_encoders[target].inverse_transform(np.asarray(encoded))

    def get_classes(self, target: str) -> list:
        return list(self.target_encoders[target].classes_)

    def load(self) -> None:
        self.num_imputer = load_artifact(f"{self.enc_dir}num_imputer.pkl")
        self.cat_imputer = load_artifact(f"{self.enc_dir}cat_imputer.pkl")
        self.scaler = load_artifact(f"{self.enc_dir}scaler.pkl")
        self.ord_encoder = load_artifact(f"{self.enc_dir}ord_encoder.pkl")
        self.target_encoders = load_artifact(f"{self.enc_dir}target_encoders.pkl")
        self.freq_maps = load_artifact(f"{self.enc_dir}freq_maps.pkl")
        self.clip_bounds = load_artifact(f"{self.enc_dir}clip_bounds.pkl")
        self.feature_cols = load_artifact(f"{self.enc_dir}feature_cols.pkl")
        log.info("Encoders loaded.")

    def _transform_impute(self, frame: pd.DataFrame) -> pd.DataFrame:
        numeric_present = [c for c in self.num_feats if c in frame.columns]
        cat_present = [c for c in self.cat_feats if c in frame.columns]
        if numeric_present and self.num_imputer is not None:
            frame[numeric_present] = self.num_imputer.transform(frame[numeric_present])
        if cat_present and self.cat_imputer is not None:
            frame[cat_present] = self.cat_imputer.transform(frame[cat_present])
        return frame

    def _clip_outliers(self, frame: pd.DataFrame) -> pd.DataFrame:
        for column in [c for c in self.num_feats if c in frame.columns]:
            lo, hi = self.clip_bounds.get(column, (None, None))
            if lo is not None:
                frame[column] = frame[column].clip(lo, hi)
        return frame

    def _engineer(self, frame: pd.DataFrame) -> pd.DataFrame:
        getter = lambda col: frame[col] if col in frame.columns else pd.Series(0, index=frame.index)

        frame["accuracy_x_score"] = (
            getter("accuracy_percentage") * getter("past_quiz_score_avg") / 10000
        ).round(4)
        frame["efficiency_ratio"] = (
            getter("accuracy_percentage") / (getter("avg_response_time_sec") + 1)
        ).round(4)
        frame["struggle_index"] = (
            getter("num_attempts") * (1 - getter("accuracy_percentage") / 100)
        ).round(4)
        frame["hint_dependency"] = (
            getter("hints_used") / (getter("num_attempts") + 1)
        ).round(4)
        frame["engagement_composite"] = (
            0.35 * getter("engagement_score")
            + 0.25 * getter("video_watch_pct") / 100
            + 0.25 * (getter("learning_streak_days") / 60).clip(0, 1)
            + 0.15 * getter("session_count_week") / 21
        ).round(4)
        frame["revision_pressure"] = (
            (100 - getter("accuracy_percentage")) / 100 * 0.5
            + getter("num_attempts") / 15 * 0.3
            + (1 - getter("engagement_score")) * 0.2
        ).clip(0, 1).round(4)
        frame["perf_consistency"] = (
            1 - abs(getter("past_quiz_score_avg") / 100 - getter("accuracy_percentage") / 100)
        ).round(4)
        frame["session_intensity"] = (
            getter("time_on_task_min") / (getter("session_count_week") + 1)
        ).round(4)
        frame["mastery_index"] = (
            0.4 * getter("past_quiz_score_avg") / 100
            + 0.4 * getter("accuracy_percentage") / 100
            + 0.2 * (getter("learning_streak_days") / 60).clip(0, 1)
        ).round(4)
        return frame

    def _transform_freq_encode(self, frame: pd.DataFrame) -> pd.DataFrame:
        for column, freq in self.freq_maps.items():
            if column in frame.columns:
                frame[f"{column}_freq"] = frame[column].map(freq).fillna(0.0)
                frame = frame.drop(columns=[column])
        return frame

    def _transform_ord_encode(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.ord_encoder is None:
            return frame
        remaining = [c for c in self.cat_feats if c in frame.columns and c not in self.freq_maps]
        if remaining:
            frame[remaining] = self.ord_encoder.transform(frame[remaining].astype(str))
        return frame

    def _transform_scale(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.scaler is None:
            return frame
        trained = list(self.scaler.feature_names_in_) if hasattr(self.scaler, "feature_names_in_") else []
        for column in trained:
            if column not in frame.columns:
                frame[column] = 0.0
        if trained:
            frame[trained] = self.scaler.transform(frame[trained])
        return frame
