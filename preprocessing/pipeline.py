import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.helpers import load_artifact
from utils.logger import get_logger
"""
preprocessing/pipeline.py
PURPOSE : Transform raw CSV data into a clean numeric matrix for XGBoost.

STEPS:
  1. Imputation    - fill NaN with median (numbers) or mode (categories)
  2. Clip Outliers - clamp to 1st-99th percentile range
  3. Feature Eng.  - create 9 derived features from combinations
  4. Freq Encode   - replace high-cardinality topic column with frequency values
  5. Ordinal Encode- convert grade/subject/etc to integers
  6. Scale         - RobustScaler on all numeric columns
  7. Label Encode  - convert target strings to 0,1,2... integers

All fitted transformers are saved to models/encoders/ so inference
uses the EXACT same encoding as training.
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import OrdinalEncoder, LabelEncoder, RobustScaler
from sklearn.impute        import SimpleImputer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.logger  import get_logger
from utils.helpers import load_config, save_artifact, load_artifact

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


    def __init__(self, cfg: dict):
        self.cfg       = cfg
        self.cat_feats = cfg["features"]["categorical"]
        self.num_feats = cfg["features"]["numerical"]
        self.enc_dir   = cfg["paths"]["encoder_dir"]

        self.num_imputer     = None
        self.cat_imputer     = None
        self.scaler          = None
        self.ord_encoder     = None
        self.target_encoders = {}
        self.freq_maps       = {}
        self.clip_bounds     = {}
        self.feature_cols    = []

        os.makedirs(self.enc_dir, exist_ok=True)

    # ── FIT + TRANSFORM (call once on training data) ──────────
    def fit_transform(self, df: pd.DataFrame) -> dict:
        log.info(f"fit_transform: input {df.shape}")
        df = df.copy()

        raw_targets = df[TARGET_COLS].copy()
        X = df.drop(columns=TARGET_COLS + DROP_COLS, errors="ignore")

        for c in self.cat_feats + self.num_feats:
            if c not in X.columns:
                X[c] = np.nan

        X = self._fit_impute(X)
        log.info(f"  After impute  - nulls: {X.isnull().sum().sum()}")

        X = self._clip_outliers(X, fit=True)
        log.info(f"  Outliers clipped (p1-p99)")

        X = self._engineer(X)
        log.info(f"  After feature eng - columns: {X.shape[1]}")

        X = self._fit_freq_encode(X)
        X = self._fit_ord_encode(X)
        X = self._fit_scale(X)

        encoded_targets = {}
        for col in TARGET_COLS:
            le  = LabelEncoder()
            arr = le.fit_transform(raw_targets[col].astype(str))
            encoded_targets[col]      = arr
            self.target_encoders[col] = le
            log.info(f"  Target '{col}' -> {len(le.classes_)} classes: {list(le.classes_)}")

        self.feature_cols = list(X.columns)
        self._save()
        log.info(f"fit_transform done - X: {X.shape}")
        return {
            "X":            X,
            "targets":      encoded_targets,
            "feature_cols": self.feature_cols,
        }

    # ── TRANSFORM (call at inference time after load()) ───────
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
        for c in self.cat_feats + self.num_feats:
            if c not in df.columns:
                df[c] = np.nan

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
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0.0
        df = df[self.feature_cols]
        return df

    # ── STEP 1: IMPUTATION ────────────────────────────────────
    def _fit_impute(self, X):
        pn = [c for c in self.num_feats if c in X.columns]
        pc = [c for c in self.cat_feats if c in X.columns]
        if pn:
            self.num_imputer = SimpleImputer(strategy="median")
            X[pn] = self.num_imputer.fit_transform(X[pn])
        if pc:
            self.cat_imputer = SimpleImputer(strategy="most_frequent")
            X[pc] = self.cat_imputer.fit_transform(X[pc])
        return X

    def _transform_impute(self, X):
        pn = [c for c in self.num_feats if c in X.columns]
        pc = [c for c in self.cat_feats if c in X.columns]
        if pn and self.num_imputer: X[pn] = self.num_imputer.transform(X[pn])
        if pc and self.cat_imputer: X[pc] = self.cat_imputer.transform(X[pc])
        return X

    # ── STEP 2: OUTLIER CLIPPING ──────────────────────────────
    def _clip_outliers(self, X, fit: bool):
        pn = [c for c in self.num_feats if c in X.columns]
        if fit:
            for col in pn:
                lo, hi = X[col].quantile([0.01, 0.99])
                self.clip_bounds[col] = (lo, hi)
        for col in pn:
            lo, hi = self.clip_bounds.get(col, (None, None))
            if lo is not None:
                X[col] = X[col].clip(lo, hi)
        return X

    # ── STEP 3: FEATURE ENGINEERING ──────────────────────────
    def _engineer(self, X) -> pd.DataFrame:
        g = lambda c: X[c] if c in X.columns else pd.Series(0, index=X.index)

        X["accuracy_x_score"]     = (g("accuracy_percentage") * g("past_quiz_score_avg") / 10000).round(4)
        X["efficiency_ratio"]     = (g("accuracy_percentage") / (g("avg_response_time_sec") + 1)).round(4)
        X["struggle_index"]       = (g("num_attempts") * (1 - g("accuracy_percentage") / 100)).round(4)
        X["hint_dependency"]      = (g("hints_used") / (g("num_attempts") + 1)).round(4)
        X["engagement_composite"] = (
            0.35 * g("engagement_score") +
            0.25 * g("video_watch_pct") / 100 +
            0.25 * (g("learning_streak_days") / 60).clip(0, 1) +
            0.15 * g("session_count_week") / 21
        ).round(4)
        X["revision_pressure"]    = (
            (100 - g("accuracy_percentage")) / 100 * 0.5 +
            g("num_attempts") / 15 * 0.3 +
            (1 - g("engagement_score")) * 0.2
        ).clip(0, 1).round(4)
        X["perf_consistency"]     = (
            1 - abs(g("past_quiz_score_avg") / 100 - g("accuracy_percentage") / 100)
        ).round(4)
        X["session_intensity"]    = (g("time_on_task_min") / (g("session_count_week") + 1)).round(4)
        X["mastery_index"]        = (
            0.4 * g("past_quiz_score_avg") / 100 +
            0.4 * g("accuracy_percentage") / 100 +
            0.2 * (g("learning_streak_days") / 60).clip(0, 1)
        ).round(4)
        return X

    # ── STEP 4a: FREQUENCY ENCODING ──────────────────────────
    def _fit_freq_encode(self, X):
        high_card = [c for c in self.cat_feats
                     if c in X.columns and X[c].nunique() > 15]
        for col in high_card:
            freq = X[col].value_counts(normalize=True).to_dict()
            self.freq_maps[col] = freq
            X[col + "_freq"] = X[col].map(freq).fillna(0.0)
            X = X.drop(columns=[col])
        return X

    def _transform_freq_encode(self, X):
        for col, freq in self.freq_maps.items():
            if col in X.columns:
                X[col + "_freq"] = X[col].map(freq).fillna(0.0)
                X = X.drop(columns=[col])
        return X

    # ── STEP 4b: ORDINAL ENCODING ─────────────────────────────
    def _fit_ord_encode(self, X):
        remaining = [c for c in self.cat_feats
                     if c in X.columns and c not in self.freq_maps]
        if not remaining:
            return X
        self.ord_encoder = OrdinalEncoder(
            handle_unknown="use_encoded_value", unknown_value=-1
        )
        X[remaining] = self.ord_encoder.fit_transform(X[remaining].astype(str))
        return X

    def _transform_ord_encode(self, X):
        if self.ord_encoder is None:
            return X
        remaining = [c for c in self.cat_feats
                     if c in X.columns and c not in self.freq_maps]
        if remaining:
            X[remaining] = self.ord_encoder.transform(X[remaining].astype(str))
        return X

    # ── STEP 5: SCALING ───────────────────────────────────────
    def _fit_scale(self, X):
        num_cols = X.select_dtypes(include=np.number).columns.tolist()
        self.scaler = RobustScaler()
        X[num_cols] = self.scaler.fit_transform(X[num_cols])
        return X

    def _transform_scale(self, X):
        if self.scaler is None:
            return X
        trained = (list(self.scaler.feature_names_in_)
                   if hasattr(self.scaler, "feature_names_in_") else
                   X.select_dtypes(include=np.number).columns.tolist())
        for c in trained:
            if c not in X.columns:
                X[c] = 0.0
        X[trained] = self.scaler.transform(X[trained])
        return X

    # ── TARGET HELPERS ────────────────────────────────────────
    def decode_target(self, target: str, encoded) -> np.ndarray:
        return self.target_encoders[target].inverse_transform(np.asarray(encoded))

    def get_classes(self, target: str) -> list:
        return list(self.target_encoders[target].classes_)

    # ── SAVE / LOAD ───────────────────────────────────────────
    def _save(self):
        save_artifact(self.num_imputer,     f"{self.enc_dir}num_imputer.pkl")
        save_artifact(self.cat_imputer,     f"{self.enc_dir}cat_imputer.pkl")
        save_artifact(self.scaler,          f"{self.enc_dir}scaler.pkl")
        save_artifact(self.ord_encoder,     f"{self.enc_dir}ord_encoder.pkl")
        save_artifact(self.target_encoders, f"{self.enc_dir}target_encoders.pkl")
        save_artifact(self.freq_maps,       f"{self.enc_dir}freq_maps.pkl")
        save_artifact(self.clip_bounds,     f"{self.enc_dir}clip_bounds.pkl")
        save_artifact(self.feature_cols,    f"{self.enc_dir}feature_cols.pkl")
        log.info(f"Encoders saved -> {self.enc_dir}")

    def load(self):
        self.num_imputer     = load_artifact(f"{self.enc_dir}num_imputer.pkl")
        self.cat_imputer     = load_artifact(f"{self.enc_dir}cat_imputer.pkl")
        self.scaler          = load_artifact(f"{self.enc_dir}scaler.pkl")
        self.ord_encoder     = load_artifact(f"{self.enc_dir}ord_encoder.pkl")
        self.target_encoders = load_artifact(f"{self.enc_dir}target_encoders.pkl")
        self.freq_maps       = load_artifact(f"{self.enc_dir}freq_maps.pkl")
        self.clip_bounds     = load_artifact(f"{self.enc_dir}clip_bounds.pkl")
        self.feature_cols    = load_artifact(f"{self.enc_dir}feature_cols.pkl")
        log.info("Encoders loaded.")
