import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder, RobustScaler

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.helpers import load_artifact, save_artifact
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

        os.makedirs(self.enc_dir, exist_ok=True)

    def fit_transform(self, df: pd.DataFrame) -> dict:
        df = df.copy()
        raw_targets = df[TARGET_COLS].copy()
        X = df.drop(columns=TARGET_COLS + DROP_COLS, errors="ignore")

        for column in self.cat_feats + self.num_feats:
            if column not in X.columns:
                X[column] = np.nan

        X = self._fit_impute(X)
        X = self._clip_outliers(X, fit=True)
        X = self._engineer(X)
        X = self._fit_freq_encode(X)
        X = self._fit_ord_encode(X)
        X = self._fit_scale(X)

        encoded_targets = {}
        for column in TARGET_COLS:
            encoder = LabelEncoder()
            encoded_targets[column] = encoder.fit_transform(raw_targets[column].astype(str))
            self.target_encoders[column] = encoder

        self.feature_cols = list(X.columns)
        self._save()
        return {"X": X, "targets": encoded_targets, "feature_cols": self.feature_cols}

    def transform(self, data) -> pd.DataFrame:
        df = pd.DataFrame([data]) if isinstance(data, dict) else data.copy()
        df = df.drop(columns=TARGET_COLS + DROP_COLS, errors="ignore")

        for column in self.cat_feats + self.num_feats:
            if column not in df.columns:
                df[column] = np.nan

        df = self._transform_impute(df)
        df = self._clip_outliers(df, fit=False)
        df = self._engineer(df)
        df = self._transform_freq_encode(df)
        df = self._transform_ord_encode(df)
        df = self._transform_scale(df)

        for column in self.feature_cols:
            if column not in df.columns:
                df[column] = 0.0
        return df[self.feature_cols]

    def decode_target(self, target: str, encoded):
        return self.target_encoders[target].inverse_transform(np.asarray(encoded))

    def get_classes(self, target: str) -> list:
        return list(self.target_encoders[target].classes_)

    def _fit_impute(self, frame: pd.DataFrame) -> pd.DataFrame:
        present_num = [c for c in self.num_feats if c in frame.columns]
        present_cat = [c for c in self.cat_feats if c in frame.columns]
        self.num_imputer = SimpleImputer(strategy="median")
        self.cat_imputer = SimpleImputer(strategy="most_frequent")
        if present_num:
            frame[present_num] = self.num_imputer.fit_transform(frame[present_num])
        if present_cat:
            frame[present_cat] = self.cat_imputer.fit_transform(frame[present_cat])
        return frame

    def _transform_impute(self, frame: pd.DataFrame) -> pd.DataFrame:
        present_num = [c for c in self.num_feats if c in frame.columns]
        present_cat = [c for c in self.cat_feats if c in frame.columns]
        if present_num and self.num_imputer is not None:
            frame[present_num] = self.num_imputer.transform(frame[present_num])
        if present_cat and self.cat_imputer is not None:
            frame[present_cat] = self.cat_imputer.transform(frame[present_cat])
        return frame

    def _clip_outliers(self, frame: pd.DataFrame, fit: bool) -> pd.DataFrame:
        present_num = [c for c in self.num_feats if c in frame.columns]
        if fit:
            for column in present_num:
                lo, hi = frame[column].quantile([0.01, 0.99])
                self.clip_bounds[column] = (lo, hi)
        for column in present_num:
            lo, hi = self.clip_bounds.get(column, (None, None))
            if lo is not None:
                frame[column] = frame[column].clip(lo, hi)
        return frame

    def _engineer(self, frame: pd.DataFrame) -> pd.DataFrame:
        getter = lambda column: frame[column] if column in frame.columns else pd.Series(0, index=frame.index)
        frame["accuracy_x_score"] = (getter("accuracy_percentage") * getter("past_quiz_score_avg") / 10000).round(4)
        frame["efficiency_ratio"] = (getter("accuracy_percentage") / (getter("avg_response_time_sec") + 1)).round(4)
        frame["struggle_index"] = (getter("num_attempts") * (1 - getter("accuracy_percentage") / 100)).round(4)
        frame["hint_dependency"] = (getter("hints_used") / (getter("num_attempts") + 1)).round(4)
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
        frame["perf_consistency"] = (1 - abs(getter("past_quiz_score_avg") / 100 - getter("accuracy_percentage") / 100)).round(4)
        frame["session_intensity"] = (getter("time_on_task_min") / (getter("session_count_week") + 1)).round(4)
        frame["mastery_index"] = (
            0.4 * getter("past_quiz_score_avg") / 100
            + 0.4 * getter("accuracy_percentage") / 100
            + 0.2 * (getter("learning_streak_days") / 60).clip(0, 1)
        ).round(4)
        return frame

    def _fit_freq_encode(self, frame: pd.DataFrame) -> pd.DataFrame:
        high_card = [c for c in self.cat_feats if c in frame.columns and frame[c].nunique() > 15]
        for column in high_card:
            freq = frame[column].value_counts(normalize=True).to_dict()
            self.freq_maps[column] = freq
            frame[f"{column}_freq"] = frame[column].map(freq).fillna(0.0)
            frame = frame.drop(columns=[column])
        return frame

    def _transform_freq_encode(self, frame: pd.DataFrame) -> pd.DataFrame:
        for column, freq in self.freq_maps.items():
            if column in frame.columns:
                frame[f"{column}_freq"] = frame[column].map(freq).fillna(0.0)
                frame = frame.drop(columns=[column])
        return frame

    def _fit_ord_encode(self, frame: pd.DataFrame) -> pd.DataFrame:
        remaining = [c for c in self.cat_feats if c in frame.columns and c not in self.freq_maps]
        self.ord_encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        if remaining:
            frame[remaining] = self.ord_encoder.fit_transform(frame[remaining].astype(str))
        return frame

    def _transform_ord_encode(self, frame: pd.DataFrame) -> pd.DataFrame:
        remaining = [c for c in self.cat_feats if c in frame.columns and c not in self.freq_maps]
        if remaining and self.ord_encoder is not None:
            frame[remaining] = self.ord_encoder.transform(frame[remaining].astype(str))
        return frame

    def _fit_scale(self, frame: pd.DataFrame) -> pd.DataFrame:
        numeric_cols = frame.select_dtypes(include=np.number).columns.tolist()
        self.scaler = RobustScaler()
        frame[numeric_cols] = self.scaler.fit_transform(frame[numeric_cols])
        return frame

    def _transform_scale(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.scaler is None:
            return frame
        trained = list(self.scaler.feature_names_in_) if hasattr(self.scaler, "feature_names_in_") else frame.select_dtypes(include=np.number).columns.tolist()
        for column in trained:
            if column not in frame.columns:
                frame[column] = 0.0
        frame[trained] = self.scaler.transform(frame[trained])
        return frame

    def _save(self) -> None:
        save_artifact(self.num_imputer, f"{self.enc_dir}num_imputer.pkl")
        save_artifact(self.cat_imputer, f"{self.enc_dir}cat_imputer.pkl")
        save_artifact(self.scaler, f"{self.enc_dir}scaler.pkl")
        save_artifact(self.ord_encoder, f"{self.enc_dir}ord_encoder.pkl")
        save_artifact(self.target_encoders, f"{self.enc_dir}target_encoders.pkl")
        save_artifact(self.freq_maps, f"{self.enc_dir}freq_maps.pkl")
        save_artifact(self.clip_bounds, f"{self.enc_dir}clip_bounds.pkl")
        save_artifact(self.feature_cols, f"{self.enc_dir}feature_cols.pkl")

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
