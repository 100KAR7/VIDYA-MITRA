import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from inference.predict import Predictor
from utils.helpers import load_config
from utils.logger import get_logger

log = get_logger("vidya.web")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"

DEMO_STUDENTS = [
    {
        "student_id": "S100101",
        "name": "Arjun",
        "grade": "Grade_10",
        "subject": "Mathematics",
        "topic": "Algebra",
        "past_quiz_score_avg": 91.0,
        "accuracy_percentage": 88.5,
        "avg_response_time_sec": 18,
        "num_attempts": 1,
        "learning_streak_days": 28,
        "engagement_score": 0.95,
        "hints_used": 0,
        "video_watch_pct": 80,
        "time_on_task_min": 45,
        "session_count_week": 7,
        "learning_style": "visual",
        "device_type": "laptop",
    },
    {
        "student_id": "S100102",
        "name": "Priya",
        "grade": "Grade_6",
        "subject": "Science",
        "topic": "Motion",
        "past_quiz_score_avg": 42.0,
        "accuracy_percentage": 38.0,
        "avg_response_time_sec": 95,
        "num_attempts": 5,
        "learning_streak_days": 2,
        "engagement_score": 0.32,
        "hints_used": 7,
        "video_watch_pct": 20,
        "time_on_task_min": 55,
        "session_count_week": 2,
        "learning_style": "auditory",
        "device_type": "mobile",
    },
    {
        "student_id": "S100103",
        "name": "Riya",
        "grade": "Grade_8",
        "subject": "English",
        "topic": "Grammar",
        "past_quiz_score_avg": 67.0,
        "accuracy_percentage": 63.0,
        "avg_response_time_sec": 42,
        "num_attempts": 3,
        "learning_streak_days": 9,
        "engagement_score": 0.62,
        "hints_used": 3,
        "video_watch_pct": 55,
        "time_on_task_min": 30,
        "session_count_week": 4,
        "learning_style": "reading_writing",
        "device_type": "tablet",
    },
]


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR),
        static_folder=str(ASSETS_DIR),
        static_url_path="/assets",
    )
    cfg = load_config()
    predictor = Predictor()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "app": cfg["project"]["name"],
                "version": cfg["project"]["version"],
                "models_ready": _models_ready(cfg),
            }
        )

    @app.get("/api/options")
    def options():
        return jsonify(
            {
                "grades": cfg["domain"]["grades"],
                "subjects": cfg["domain"]["subjects"],
                "topics_by_subject": cfg["domain"]["topics_by_subject"],
                "learning_styles": cfg["domain"]["learning_styles"],
                "device_types": cfg["domain"]["device_types"],
            }
        )

    @app.get("/api/demo-students")
    def demo_students():
        return jsonify({"students": DEMO_STUDENTS})

    @app.post("/api/predict")
    def predict():
        payload = request.get_json(silent=True) or {}
        if not payload:
            return jsonify({"error": "Request body must be valid JSON."}), 400

        try:
            result = predictor.predict(payload, save=True)
            return jsonify(result)
        except Exception as exc:
            log.exception("Prediction failed")
            return jsonify({"error": str(exc)}), 500

    return app


def _models_ready(cfg: dict) -> bool:
    required = [
        os.path.join(cfg["paths"]["model_dir"], "xgb_next_topic.pkl"),
        os.path.join(cfg["paths"]["model_dir"], "xgb_recommended_difficulty.pkl"),
        os.path.join(cfg["paths"]["model_dir"], "xgb_success_probability_bin.pkl"),
        os.path.join(cfg["paths"]["model_dir"], "xgb_needs_revision.pkl"),
    ]
    return all(Path(path).exists() for path in required)
