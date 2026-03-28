"""
training/trainer.py
PURPOSE : Train one XGBoost model per prediction target.

WHY 4 SEPARATE MODELS?
  Each target has a different number of classes and difficulty.
  Separate models each specialise and perform much better.

DATA SPLIT:
  All data -> Train 70% | Val 10% | Test 20%
  Val is used for early stopping (XGBoost stops adding trees
  when validation score stops improving for 30 rounds).
  Test is held out completely for the honest final score.
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.model_selection import (train_test_split,
                                      RandomizedSearchCV,
                                      StratifiedKFold)
from sklearn.metrics import (accuracy_score, f1_score,
                              classification_report, roc_auc_score)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.logger  import get_logger
from utils.helpers import load_config, save_artifact, load_artifact, save_json

log = get_logger("vidya.trainer")

TARGETS = [
    "next_topic",
    "recommended_difficulty",
    "success_probability_bin",
    "needs_revision",
]


class Trainer:

    def __init__(self, cfg: dict):
        self.cfg       = cfg
        self.xgb_cfg   = cfg["xgboost"]
        self.model_dir = cfg["paths"]["model_dir"]
        self.models    = {}
        self.metrics   = {}
        self.splits    = {}
        os.makedirs(self.model_dir, exist_ok=True)

    def train_all(self, X: pd.DataFrame, targets: dict,
                  tune: bool = False) -> dict:
        log.info(f"Starting training - {len(TARGETS)} targets | X: {X.shape} | tune: {tune}")

        for target in TARGETS:
            y = targets[target]
            log.info(f"\n{'─'*50}\n  Target: {target} ({len(np.unique(y))} classes)\n{'─'*50}")
            model, split = self._train_one(X, y, target, tune)
            self.models[target]  = model
            self.splits[target]  = split
            self.metrics[target] = self._evaluate(model, split, target, y)

        self._save_all()
        return self.metrics

    def _train_one(self, X, y, target, tune):
        cfg_ds = self.cfg["dataset"]

        X_tv, X_test, y_tv, y_test = train_test_split(
            X, y,
            test_size    = cfg_ds["test_size"],
            stratify     = y,
            random_state = cfg_ds["random_seed"],
        )
        val_frac = cfg_ds["val_size"] / (1 - cfg_ds["test_size"])
        X_train, X_val, y_train, y_val = train_test_split(
            X_tv, y_tv,
            test_size    = val_frac,
            stratify     = y_tv,
            random_state = cfg_ds["random_seed"],
        )
        split = dict(X_train=X_train, X_val=X_val, X_test=X_test,
                     y_train=y_train, y_val=y_val, y_test=y_test)

        log.info(f"  Split: train={len(X_train)} | val={len(X_val)} | test={len(X_test)}")

        model = self._build(target, len(np.unique(y)))

        if tune:
            model = self._tune(model, X_train, y_train)

        model = self._fit(model, X_train, y_train, X_val, y_val)
        return model, split

    def _build(self, target: str, n_classes: int):
        c = self.xgb_cfg
        try:
            from xgboost import XGBClassifier
            obj = "multi:softprob" if n_classes > 2 else "binary:logistic"
            return XGBClassifier(
                n_estimators         = c["n_estimators"],
                max_depth            = c["max_depth"],
                learning_rate        = c["learning_rate"],
                subsample            = c["subsample"],
                colsample_bytree     = c["colsample_bytree"],
                gamma                = c["gamma"],
                reg_alpha            = c["reg_alpha"],
                reg_lambda           = c["reg_lambda"],
                min_child_weight     = c["min_child_weight"],
                random_state         = c["random_state"],
                n_jobs               = c["n_jobs"],
                objective            = obj,
                eval_metric          = "mlogloss",
                early_stopping_rounds= c["early_stopping_rounds"],
                verbosity            = 0,
                use_label_encoder    = False,
            )
        except ImportError:
            log.warning("xgboost not installed - using GradientBoostingClassifier fallback")
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(
                n_estimators  = min(c["n_estimators"], 200),
                max_depth     = c["max_depth"],
                learning_rate = c["learning_rate"],
                subsample     = c["subsample"],
                random_state  = c["random_state"],
            )

    def _fit(self, model, X_tr, y_tr, X_val, y_val):
        is_xgb = "XGB" in type(model).__name__
        if is_xgb:
            model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        else:
            model.fit(X_tr, y_tr)
        return model

    def _tune(self, model, X_tr, y_tr):
        log.info("  Hyperparameter tuning (takes a few minutes)...")
        tc   = self.cfg["tuning"]
        grid = tc["param_grid"]

        if "XGB" not in type(model).__name__:
            grid = {k: v for k, v in grid.items()
                    if k in ("n_estimators","max_depth","learning_rate","subsample")}

        cv = StratifiedKFold(
            n_splits=tc["cv_folds"], shuffle=True,
            random_state=self.cfg["dataset"]["random_seed"]
        )
        search = RandomizedSearchCV(
            model, param_distributions=grid,
            n_iter=tc["n_iter"], scoring=tc["scoring"],
            cv=cv, random_state=self.cfg["dataset"]["random_seed"],
            n_jobs=-1, refit=True, verbose=0
        )
        search.fit(X_tr, y_tr)
        log.info(f"  Best CV score: {search.best_score_:.4f}")
        log.info(f"  Best params:   {search.best_params_}")
        return search.best_estimator_

    def _evaluate(self, model, split, target, y_full) -> dict:
        X_te, y_te = split["X_test"], split["y_test"]
        preds      = model.predict(X_te)
        acc        = accuracy_score(y_te, preds)
        f1         = f1_score(y_te, preds, average="weighted", zero_division=0)
        report     = classification_report(y_te, preds, output_dict=True, zero_division=0)

        auc = None
        try:
            proba = model.predict_proba(X_te)
            n_cls = len(np.unique(y_full))
            auc   = (roc_auc_score(y_te, proba[:,1])
                     if n_cls == 2 else
                     roc_auc_score(y_te, proba, multi_class="ovr", average="weighted"))
            auc   = round(float(auc), 4)
        except Exception:
            pass

        log.info(f"  Accuracy={acc:.4f} | F1={f1:.4f}" + (f" | AUC={auc:.4f}" if auc else ""))

        metrics = {
            "target":      target,
            "accuracy":    round(acc, 4),
            "f1_weighted": round(f1,  4),
            "roc_auc":     auc,
            "n_classes":   int(len(np.unique(y_full))),
            "n_test":      len(y_te),
            "classification_report": report,
        }
        if hasattr(model, "feature_importances_"):
            top10 = (pd.Series(model.feature_importances_,
                               index=split["X_test"].columns)
                     .sort_values(ascending=False).head(10).to_dict())
            metrics["top10_features"] = {k: round(float(v), 4)
                                          for k, v in top10.items()}
        return metrics

    def _save_all(self):
        for target, model in self.models.items():
            save_artifact(model, f"{self.model_dir}xgb_{target}.pkl")
            log.info(f"  Saved -> {self.model_dir}xgb_{target}.pkl")
        os.makedirs(self.cfg["paths"]["reports_dir"], exist_ok=True)
        save_json(self.metrics, f"{self.cfg['paths']['reports_dir']}training_metrics.json")

    def load_all(self):
        for target in TARGETS:
            self.models[target] = load_artifact(f"{self.model_dir}xgb_{target}.pkl")
        log.info(f"Loaded {len(self.models)} models.")

    def get_model(self, target: str):
        return self.models.get(target)