import os
import sys
import warnings
from datetime import datetime
from typing import List, Union

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from inference.game_selector import GameVariantRecommender
from preprocessing.pipeline import PreprocessingPipeline
from training.trainer import TARGETS, Trainer
from utils.helpers import load_config, now_slug, save_json
from utils.logger import get_logger

log = get_logger("vidya.predictor")

ADAPTIVE_ACTIONS = {
    ("easy", True, "low"): "Immediate revision needed. Revisit the foundations before moving on.",
    ("easy", True, "medium"): "Do a short revision pass and then continue.",
    ("easy", False, "high"): "Strong signal to level up soon.",
    ("easy", False, "medium"): "Build confidence with a few more guided rounds.",
    ("medium", True, "low"): "Pause and reinforce weak areas before new content.",
    ("medium", True, "medium"): "Run targeted revision on the tricky concepts first.",
    ("medium", False, "high"): "Good momentum. This learner is ready for a challenge.",
    ("medium", False, "medium"): "Stay at medium and keep practising.",
    ("hard", True, "low"): "Reduce intensity, revise, and rebuild confidence.",
    ("hard", True, "medium"): "Keep the goal high but add support and revision.",
    ("hard", False, "high"): "Excellent mastery signal. Push with a richer game.",
    ("hard", False, "medium"): "Keep the challenge high and monitor consistency.",
}

DEFAULTS = {
    "hints_used": 0,
    "video_watch_pct": 50.0,
    "time_on_task_min": 30.0,
    "session_count_week": 5,
    "learning_style": "visual",
    "device_type": "mobile",
"""
inference/predict.py
PURPOSE : Load trained models and predict for real students.

USAGE:
  from inference.predict import Predictor

  p = Predictor()
  result = p.predict({
      "grade": "Grade_8",
      "subject": "Mathematics",
      "topic": "Algebra",
      "past_quiz_score_avg": 72.0,
      "accuracy_percentage": 68.5,
      "avg_response_time_sec": 35.0,
      "num_attempts": 2,
      "learning_streak_days": 7,
      "engagement_score": 0.70,
  })

  print(result["recommended_difficulty"])   # "medium"
  print(result["needs_revision"])           # False
  print(result["adaptive_action"])          # "📈 Good progress..."
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Union, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.logger  import get_logger
from utils.helpers import load_config, save_json, now_slug
from preprocessing.pipeline import PreprocessingPipeline
from training.trainer       import Trainer, TARGETS

log = get_logger("vidya.predictor")

# Human-readable advice based on (difficulty, needs_revision, success_bin)
ADAPTIVE_ACTIONS = {
    ("easy",   True,  "low"):    "⚠️  Immediate revision needed - revisit fundamentals.",
    ("easy",   True,  "medium"): "📝  Quick revision before moving to the next topic.",
    ("easy",   False, "high"):   "🚀  Great job! Ready to level up to medium difficulty.",
    ("easy",   False, "medium"): "📈  Solid foundation. Keep practising.",
    ("medium", True,  "low"):    "🔄  Stop and revise. Topic needs more consolidation.",
    ("medium", True,  "medium"): "📖  Brief revision on weak areas before continuing.",
    ("medium", False, "high"):   "⭐  Excellent! Try hard difficulty now.",
    ("medium", False, "medium"): "📈  Good progress. Keep practising at medium.",
    ("hard",   True,  "low"):    "⬇️  Step back to medium difficulty and revise.",
    ("hard",   True,  "medium"): "🔁  Targeted revision on specific weak spots.",
    ("hard",   False, "high"):   "🏆  Outstanding! You are mastering this topic!",
    ("hard",   False, "medium"): "💪  Solid at hard level. Keep pushing!",
}

# Default values for optional input fields
DEFAULTS = {
    "hints_used":        0,
    "video_watch_pct":   50.0,
    "time_on_task_min":  30.0,
    "session_count_week":5,
    "learning_style":    "visual",
    "device_type":       "mobile",
}


class Predictor:
    VERSION = "1.0.0"

    def __init__(self, config_path: str = "config/config.yaml"):
        self.cfg = load_config(config_path)
        self.pipeline = PreprocessingPipeline(self.cfg)
        self.trainer = Trainer(self.cfg)
        self.game_recommender = GameVariantRecommender()
        self._ready = False

    def predict(self, student: Union[dict, pd.DataFrame], save: bool = True) -> dict:
        self._load()
        data = self._validate(student)
        matrix = self.pipeline.transform(data)

        raw_preds = {}
        confidences = {}
        for target in TARGETS:
            model = self.trainer.get_model(target)
            encoded = model.predict(matrix)[0]
            label = self.pipeline.decode_target(target, [encoded])[0]
            raw_preds[target] = label

            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(matrix)[0]
                classes = self.pipeline.get_classes(target)
                confidences[target] = {cls: round(float(p), 4) for cls, p in zip(classes, proba)}

    VERSION = "1.0.0"

    def __init__(self, config_path: str = "config/config.yaml"):
        self.cfg      = load_config(config_path)
        self.pipeline = PreprocessingPipeline(self.cfg)
        self.trainer  = Trainer(self.cfg)
        self._ready   = False

    def _load(self):
        if not self._ready:
            self.pipeline.load()
            self.trainer.load_all()
            self._ready = True
            log.info("Predictor ready.")

    def predict(self, student: Union[dict, pd.DataFrame],
                save: bool = True) -> dict:
        self._load()
        data = self._validate(student)
        X    = self.pipeline.transform(data)
        X    = self._align(X)

        raw_preds   = {}
        confidences = {}
        for target in TARGETS:
            model = self.trainer.get_model(target)
            if model is None:
                continue
            enc   = model.predict(X)[0]
            label = self.pipeline.decode_target(target, [enc])[0]
            raw_preds[target] = label

            if hasattr(model, "predict_proba"):
                proba   = model.predict_proba(X)[0]
                classes = self.pipeline.get_classes(target)
                confidences[target] = {
                    c: round(float(p), 4) for c, p in zip(classes, proba)
                }

        result = self._build_response(raw_preds, confidences, data)

        if save:
            output_dir = self.cfg["paths"]["predictions_dir"]
            os.makedirs(output_dir, exist_ok=True)
            save_json(result, f"{output_dir}pred_{now_slug()}.json")

        return result

    def predict_batch(self, students: List[dict], save: bool = False) -> List[dict]:
        return [self.predict(student, save=save) for student in students]

    def _build_response(self, raw_preds: dict, confidences: dict, profile: dict) -> dict:
        difficulty = raw_preds.get("recommended_difficulty", "medium")
        success_band = raw_preds.get("success_probability_bin", "medium")
        needs_revision = str(raw_preds.get("needs_revision", "0")) in ("1", "True", "1.0")
        next_topic = raw_preds.get("next_topic", profile.get("topic", "Unknown"))

        success_conf = confidences.get("success_probability_bin", {})
        weighted_success = (
            success_conf.get("high", 0.0) * 1.0
            + success_conf.get("medium", 0.0) * 0.5
            + success_conf.get("low", 0.0) * 0.0
        )

        revision_conf = confidences.get("needs_revision", {})
        revision_probability = revision_conf.get("1", revision_conf.get("True", 0.0))
        urgency = "high" if revision_probability > 0.7 else ("low" if revision_probability > 0.35 else "none")

        action = ADAPTIVE_ACTIONS.get(
            (difficulty, needs_revision, success_band),
            f"Continue practising {profile.get('topic', 'this topic')} at {difficulty} level.",
        )

        game_recommendation = self.game_recommender.recommend(
            profile,
            {
                "next_topic": next_topic,
                "recommended_difficulty": difficulty,
                "success_probability_bin": success_band,
                "needs_revision": needs_revision,
            },
        )

        return {
            "next_recommended_topic": next_topic,
            "recommended_difficulty": difficulty,
            "success_probability": round(float(weighted_success), 4),
            "success_probability_label": success_band,
            "needs_revision": needs_revision,
            "revision_urgency": urgency,
            "adaptive_action": action,
            "recommended_game": game_recommendation,
            "confidence_scores": confidences,
            "student_input": {key: value for key, value in profile.items() if key != "student_id"},
            "metadata": {
                "model_version": self.VERSION,
                "timestamp": datetime.now().isoformat(),
            },
        }

    def _load(self) -> None:
        if self._ready:
            return
        self.pipeline.load()
        self.trainer.load_all()
        self._ready = True
        log.info("Predictor ready.")

    def _validate(self, data: Union[dict, pd.DataFrame]) -> dict:
        if isinstance(data, pd.DataFrame):
            data = data.iloc[0].to_dict()

        payload = dict(data)
        for key, value in DEFAULTS.items():
            payload.setdefault(key, value)

        payload.setdefault("student_id", f"S-{now_slug()}")
        payload["past_quiz_score_avg"] = float(np.clip(payload.get("past_quiz_score_avg", 50), 0, 100))
        payload["accuracy_percentage"] = float(np.clip(payload.get("accuracy_percentage", 50), 0, 100))
        payload["avg_response_time_sec"] = float(np.clip(payload.get("avg_response_time_sec", 30), 1, 300))
        payload["num_attempts"] = int(max(1, payload.get("num_attempts", 1)))
        payload["learning_streak_days"] = int(max(0, payload.get("learning_streak_days", 0)))
        payload["engagement_score"] = float(np.clip(payload.get("engagement_score", 0.5), 0, 1))
        payload["video_watch_pct"] = float(np.clip(payload.get("video_watch_pct", 50), 0, 100))
        payload["time_on_task_min"] = float(np.clip(payload.get("time_on_task_min", 30), 1, 180))
        payload["session_count_week"] = int(np.clip(payload.get("session_count_week", 5), 1, 50))
        payload["hints_used"] = int(max(0, payload.get("hints_used", 0)))
        return payload
            out_dir = self.cfg["paths"]["predictions_dir"]
            os.makedirs(out_dir, exist_ok=True)
            save_json(result, f"{out_dir}pred_{now_slug()}.json")

        return result

    def predict_batch(self, students: List[dict], save: bool = True) -> List[dict]:
        self._load()
        validated = [self._validate(s) for s in students]
        df_batch  = pd.DataFrame(validated)
        X_batch   = self.pipeline.transform(df_batch)

        results = []
        for i, data in enumerate(validated):
            X_row = self._align(X_batch.iloc[[i]])
            raw_preds   = {}
            confidences = {}
            for target in TARGETS:
                model = self.trainer.get_model(target)
                if model is None:
                    continue
                enc   = model.predict(X_row)[0]
                label = self.pipeline.decode_target(target, [enc])[0]
                raw_preds[target] = label
                if hasattr(model, "predict_proba"):
                    proba   = model.predict_proba(X_row)[0]
                    classes = self.pipeline.get_classes(target)
                    confidences[target] = {
                        c: round(float(p), 4) for c, p in zip(classes, proba)
                    }
            results.append(self._build_response(raw_preds, confidences, data))

        if save:
            out_dir = self.cfg["paths"]["predictions_dir"]
            os.makedirs(out_dir, exist_ok=True)
            save_json({"batch_size": len(results), "predictions": results},
                      f"{out_dir}batch_{now_slug()}.json")
        return results

    def _build_response(self, raw_preds, confidences, profile) -> dict:
        diff       = raw_preds.get("recommended_difficulty",    "medium")
        sbin       = raw_preds.get("success_probability_bin",   "medium")
        needs_rev  = str(raw_preds.get("needs_revision", "0")) in ("1","True","1.0")
        next_topic = raw_preds.get("next_topic", "Unknown")

        sc = confidences.get("success_probability_bin", {})
        wp = sc.get("high",0)*1.0 + sc.get("medium",0)*0.5 + sc.get("low",0)*0.0

        rc       = confidences.get("needs_revision", {})
        rev_prob = rc.get("1", rc.get("True", 0.0))
        urgency  = "high" if rev_prob > 0.70 else ("low" if rev_prob > 0.35 else "none")

        action = ADAPTIVE_ACTIONS.get(
            (diff, needs_rev, sbin),
            f"📚 Continue practising {profile.get('topic','this topic')} at {diff} level."
        )

        return {
            "next_recommended_topic":    next_topic,
            "recommended_difficulty":    diff,
            "success_probability":       round(float(wp), 4),
            "success_probability_label": sbin,
            "needs_revision":            needs_rev,
            "revision_urgency":          urgency,
            "adaptive_action":           action,
            "confidence_scores":         confidences,
            "student_input":             {k: v for k, v in profile.items()
                                          if k != "student_id"},
            "metadata": {
                "model_version": self.VERSION,
                "timestamp":     datetime.now().isoformat(),
            }
        }

    def _validate(self, data: Union[dict, pd.DataFrame]) -> dict:
        if isinstance(data, pd.DataFrame):
            data = data.iloc[0].to_dict()
        data = dict(data)
        for k, v in DEFAULTS.items():
            data.setdefault(k, v)
        data["past_quiz_score_avg"]   = float(np.clip(data.get("past_quiz_score_avg",   50), 0, 100))
        data["accuracy_percentage"]   = float(np.clip(data.get("accuracy_percentage",   50), 0, 100))
        data["avg_response_time_sec"] = float(np.clip(data.get("avg_response_time_sec", 30), 1, 300))
        data["num_attempts"]          = int(max(1, data.get("num_attempts", 1)))
        data["learning_streak_days"]  = int(max(0, data.get("learning_streak_days", 0)))
        data["engagement_score"]      = float(np.clip(data.get("engagement_score", 0.5), 0, 1))
        data["video_watch_pct"]       = float(np.clip(data.get("video_watch_pct",   50), 0, 100))
        data["time_on_task_min"]      = float(np.clip(data.get("time_on_task_min",  30), 1, 180))
        data["session_count_week"]    = int(np.clip(data.get("session_count_week",   5), 1,  50))
        data["hints_used"]            = int(max(0, data.get("hints_used", 0)))
        return data

    def _align(self, X: pd.DataFrame) -> pd.DataFrame:
        for col in self.pipeline.feature_cols:
            if col not in X.columns:
                X[col] = 0.0
        return X[self.pipeline.feature_cols]
