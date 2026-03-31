import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.helpers import load_artifact, save_artifact, save_json
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
        self.xgb_cfg = cfg["xgboost"]
        self.model_dir = cfg["paths"]["model_dir"]
        self.models = {}
        self.metrics = {}
        self.splits = {}
        os.makedirs(self.model_dir, exist_ok=True)

    def train_all(self, X: pd.DataFrame, targets: dict) -> dict:
        for target in TARGETS:
            y = targets[target]
            model, split = self._train_one(X, y)
            self.models[target] = model
            self.splits[target] = split
            self.metrics[target] = self._evaluate(model, split, target, y)
        self._save_all()
        return self.metrics

    def _train_one(self, X, y):
        cfg_ds = self.cfg["dataset"]
        X_tv, X_test, y_tv, y_test = train_test_split(
            X,
            y,
            test_size=cfg_ds["test_size"],
            stratify=y,
            random_state=cfg_ds["random_seed"],
        )
        val_frac = cfg_ds["val_size"] / (1 - cfg_ds["test_size"])
        X_train, X_val, y_train, y_val = train_test_split(
            X_tv,
            y_tv,
            test_size=val_frac,
            stratify=y_tv,
            random_state=cfg_ds["random_seed"],
        )
        split = dict(X_train=X_train, X_val=X_val, X_test=X_test, y_train=y_train, y_val=y_val, y_test=y_test)

        model = self._build(len(np.unique(y)))
        model = self._fit(model, X_train, y_train, X_val, y_val)
        return model, split

    def _build(self, n_classes: int):
        try:
            from xgboost import XGBClassifier

            params = dict(
                n_estimators=self.xgb_cfg["n_estimators"],
                max_depth=self.xgb_cfg["max_depth"],
                learning_rate=self.xgb_cfg["learning_rate"],
                subsample=self.xgb_cfg["subsample"],
                colsample_bytree=self.xgb_cfg["colsample_bytree"],
                gamma=self.xgb_cfg["gamma"],
                reg_alpha=self.xgb_cfg["reg_alpha"],
                reg_lambda=self.xgb_cfg["reg_lambda"],
                min_child_weight=self.xgb_cfg["min_child_weight"],
                random_state=self.xgb_cfg["random_state"],
                n_jobs=self.xgb_cfg["n_jobs"],
                objective="multi:softprob" if n_classes > 2 else "binary:logistic",
                eval_metric="mlogloss" if n_classes > 2 else "logloss",
                early_stopping_rounds=self.xgb_cfg["early_stopping_rounds"],
                verbosity=0,
            )
            if n_classes > 2:
                params["num_class"] = n_classes
            return XGBClassifier(**params)
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier

            return GradientBoostingClassifier(
                n_estimators=min(self.xgb_cfg["n_estimators"], 200),
                learning_rate=self.xgb_cfg["learning_rate"],
                random_state=self.xgb_cfg["random_state"],
            )

    def _fit(self, model, X_train, y_train, X_val, y_val):
        if hasattr(model, "predict_proba") and "XGB" in type(model).__name__:
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        else:
            model.fit(X_train, y_train)
        return model

    def _evaluate(self, model, split, target, y_full) -> dict:
        X_test, y_test = split["X_test"], split["y_test"]
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds, average="weighted", zero_division=0)
        report = classification_report(y_test, preds, output_dict=True, zero_division=0)
        auc = None
        try:
            proba = model.predict_proba(X_test)
            n_classes = len(np.unique(y_full))
            auc = (
                roc_auc_score(y_test, proba[:, 1])
                if n_classes == 2
                else roc_auc_score(y_test, proba, multi_class="ovr", average="weighted")
            )
            auc = round(float(auc), 4)
        except Exception:
            pass
        return {
            "target": target,
            "accuracy": round(acc, 4),
            "f1_weighted": round(f1, 4),
            "roc_auc": auc,
            "classification_report": report,
        }

    def _save_all(self) -> None:
        for target, model in self.models.items():
            save_artifact(model, f"{self.model_dir}xgb_{target}.pkl")
        save_json(self.metrics, f"{self.cfg['paths']['reports_dir']}training_metrics.json")

    def load_all(self) -> None:
        for target in TARGETS:
            self.models[target] = load_artifact(f"{self.model_dir}xgb_{target}.pkl")
        log.info("Loaded %s models.", len(self.models))

    def get_model(self, target: str):
        return self.models.get(target)
