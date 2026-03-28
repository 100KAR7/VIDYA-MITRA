"""
training/evaluate.py
PURPOSE : Generate evaluation reports and plots after training.

OUTPUTS CREATED:
  outputs/plots/cm_<target>.png          - Confusion matrix
  outputs/plots/feat_imp_<target>.png    - Feature importance chart
  outputs/plots/metrics_dashboard.png   - All 4 models side by side
  outputs/reports/evaluation_summary.json
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (confusion_matrix, accuracy_score,
                              f1_score, classification_report)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.logger  import get_logger
from utils.helpers import load_config, save_json

log = get_logger("vidya.evaluator")

TARGETS = [
    "next_topic",
    "recommended_difficulty",
    "success_probability_bin",
    "needs_revision",
]


class Evaluator:

    def __init__(self, cfg: dict, pipeline):
        self.cfg      = cfg
        self.pipeline = pipeline
        self.plot_dir = cfg["paths"]["plots_dir"]
        self.rep_dir  = cfg["paths"]["reports_dir"]
        os.makedirs(self.plot_dir, exist_ok=True)
        os.makedirs(self.rep_dir,  exist_ok=True)

    def evaluate_all(self, trainer, X: pd.DataFrame, targets: dict):
        summary = []

        for target in TARGETS:
            model = trainer.get_model(target)
            if model is None:
                log.warning(f"No model for {target} - skipping")
                continue

            y       = targets.get(target)
            classes = self.pipeline.get_classes(target)
            split   = trainer.splits.get(target, {})
            X_te    = split.get("X_test", X)
            y_te    = split.get("y_test", y if y is not None else [])

            if y_te is None or len(y_te) == 0:
                continue

            preds = model.predict(X_te)
            acc   = accuracy_score(y_te, preds)
            f1    = f1_score(y_te, preds, average="weighted", zero_division=0)

            print(f"\n{'='*55}")
            print(f"  {target}")
            print(f"  Accuracy : {acc:.4f}  |  F1 (weighted): {f1:.4f}")
            print(f"{'─'*55}")
            print(classification_report(y_te, preds, target_names=classes, zero_division=0))

            if len(classes) <= 10:
                self._plot_confusion_matrix(target, y_te, preds, classes)
            self._plot_feature_importance(model, X_te, target)

            summary.append({
                "target":      target,
                "accuracy":    round(acc, 4),
                "f1_weighted": round(f1,  4),
                "n_classes":   len(classes),
            })

        if summary:
            self._plot_dashboard(summary)
            save_json({"summary": summary}, f"{self.rep_dir}evaluation_summary.json")
            self._print_leaderboard(summary)
        return summary

    def _plot_confusion_matrix(self, target, y_true, y_pred, classes):
        cm  = confusion_matrix(y_true, y_pred)
        n   = len(classes)
        fig, ax = plt.subplots(figsize=(max(5, n * 1.3), max(4, n)))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                    xticklabels=classes, yticklabels=classes,
                    linewidths=0.5, linecolor="white", ax=ax)
        ax.set_title(f"Confusion Matrix - {target}", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        plt.xticks(rotation=30, ha="right", fontsize=9)
        plt.yticks(rotation=0,  fontsize=9)
        plt.tight_layout()
        path = f"{self.plot_dir}cm_{target}.png"
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        log.info(f"  Saved: {path}")

    def _plot_feature_importance(self, model, X_te, target):
        if not hasattr(model, "feature_importances_"):
            return
        imp = (pd.Series(model.feature_importances_, index=X_te.columns)
               .sort_values(ascending=True).tail(20))
        fig, ax = plt.subplots(figsize=(10, 7))
        colors  = plt.cm.RdYlGn(np.linspace(0.25, 0.85, len(imp)))
        imp.plot(kind="barh", ax=ax, color=colors, edgecolor="black", linewidth=0.3)
        ax.set_title(f"Feature Importance - {target}", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("XGBoost Importance Score")
        ax.grid(axis="x", alpha=0.3, linestyle="--")
        ax.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()
        path = f"{self.plot_dir}feat_imp_{target}.png"
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()

    def _plot_dashboard(self, summary: list):
        labels = [s["target"].replace("_", "\n") for s in summary]
        accs   = [s["accuracy"]    for s in summary]
        f1s    = [s["f1_weighted"] for s in summary]
        x, w   = np.arange(len(labels)), 0.35

        fig, ax = plt.subplots(figsize=(13, 6))
        b1 = ax.bar(x - w/2, accs, w, label="Accuracy",    color="#2196F3", alpha=0.88)
        b2 = ax.bar(x + w/2, f1s,  w, label="F1 Weighted", color="#4CAF50", alpha=0.88)
        for bar in list(b1) + list(b2):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.005,
                    f"{bar.get_height():.3f}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylim(0, 1.12)
        ax.legend(fontsize=10)
        ax.set_title("Vidya-Mitra - XGBoost Model Performance",
                     fontsize=13, fontweight="bold", pad=12)
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()
        path = f"{self.plot_dir}metrics_dashboard.png"
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        log.info(f"  Dashboard saved: {path}")

    def _print_leaderboard(self, summary):
        print(f"\n{'='*55}")
        print(f"  MODEL LEADERBOARD")
        print(f"{'='*55}")
        print(f"  {'Target':<35} {'Acc':>8} {'F1':>8}")
        print(f"  {'─'*35} {'─'*8} {'─'*8}")
        for s in sorted(summary, key=lambda x: x["f1_weighted"], reverse=True):
            print(f"  {s['target']:<35} {s['accuracy']:>8.4f} {s['f1_weighted']:>8.4f}")
        print(f"{'='*55}\n")