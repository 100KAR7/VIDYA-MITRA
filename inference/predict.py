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
