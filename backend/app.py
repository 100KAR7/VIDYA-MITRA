import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from backend.auth import AuthManager
from backend.errors import APIError, AuthenticationError
from backend.errors import NotFoundError as APINotFoundError
from backend.game_service import GameService
from backend.platform_store import PlatformStore
from backend.runtime import RuntimeSettings
from backend.validators import (
    ensure_roles,
    ensure_student_access,
    require_json_object,
    validate_answer_payload,
    validate_game_launch_payload,
    validate_login_payload,
    validate_prediction_request,
)
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


def create_app(runtime_overrides: dict | None = None, config_path: str = "config/config.yaml") -> Flask:
    settings = RuntimeSettings.from_env().with_overrides(**(runtime_overrides or {}))
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR),
        static_folder=str(ASSETS_DIR),
        static_url_path="/assets",
    )
    app.config.update(
        ENV=settings.environment,
        DEBUG=settings.debug,
        TESTING=settings.testing,
        SECRET_KEY=settings.secret_key,
        JSON_SORT_KEYS=False,
    )

    cfg = load_config(config_path)
    predictor = Predictor(config_path=config_path)
    game_service = GameService(cfg, settings.session_ttl_seconds, settings.max_live_sessions)
    platform_store = PlatformStore(settings.platform_store_path)
    auth_manager = AuthManager(settings.secret_key)

    app.extensions["runtime_settings"] = settings
    app.extensions["platform_store"] = platform_store
    app.extensions["game_service"] = game_service
    app.extensions["auth_manager"] = auth_manager

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(APIError)
    def handle_api_error(exc: APIError):
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(404)
    def handle_404(_exc):
        if request.path.startswith("/api/"):
            error = APINotFoundError("API route was not found.")
            return jsonify(error.to_dict()), error.status_code
        return "Page not found.", 404

    @app.errorhandler(405)
    def handle_405(_exc):
        error = APIError("HTTP method is not allowed for this endpoint.", status_code=405, code="method_not_allowed")
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        log.exception("Unhandled application error")
        error = APIError("Internal server error.", status_code=500, code="internal_error")
        if app.testing:
            error.details = {"exception": str(exc)}
        return jsonify(error.to_dict()), error.status_code

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/games/<session_id>")
    def game_player(session_id: str):
        return render_template("game.html", session_id=session_id)

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "app": cfg["project"]["name"],
                "version": cfg["project"]["version"],
                "environment": settings.environment,
                "models_ready": _models_ready(cfg),
                "storage_ready": platform_store.healthcheck(),
                "active_game_sessions": game_service.active_session_count(),
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

    @app.post("/api/auth/login")
    def login():
        payload = require_json_object(request.get_json(silent=True))
        credentials = validate_login_payload(payload)
        user = platform_store.login(**credentials)
        return jsonify(
            {
                "user": user,
                "access_token": auth_manager.issue_token(user),
                "expires_in_seconds": settings.auth_token_ttl_seconds,
            }
        )

    @app.post("/api/predict")
    def predict():
        actor = _require_auth(auth_manager, settings.auth_token_ttl_seconds)
        payload = require_json_object(request.get_json(silent=True))
        request_payload = validate_prediction_request(payload, cfg)
        student_profile = request_payload["student_profile"]
        ensure_student_access(actor, student_profile["student_id"])
        result = predictor.predict(student_profile, save=settings.prediction_logging_enabled and not app.testing)
        platform_store.record_prediction(actor, student_profile, result)
        return jsonify(result)

    @app.post("/api/games/launch")
    def launch_game():
        actor = _require_auth(auth_manager, settings.auth_token_ttl_seconds)
        payload = require_json_object(request.get_json(silent=True))
        request_payload = validate_game_launch_payload(payload, cfg)
        ensure_student_access(actor, request_payload["student_profile"]["student_id"])
        return jsonify(
            game_service.launch_session(
                request_payload["student_profile"],
                request_payload["prediction"],
                request_payload["game"],
                actor,
            )
        )

    @app.get("/api/games/session/<session_id>")
    def game_session_state(session_id: str):
        actor = _require_auth(auth_manager, settings.auth_token_ttl_seconds)
        return jsonify(game_service.get_session_state(session_id, actor))

    @app.post("/api/games/session/<session_id>/learn")
    def advance_learning(session_id: str):
        actor = _require_auth(auth_manager, settings.auth_token_ttl_seconds)
        payload = request.get_json(silent=True) or {}
        selection_id = payload.get("selection_id") if isinstance(payload, dict) else None
        return jsonify(game_service.advance_lesson(session_id, actor, selection_id))

    @app.post("/api/games/session/<session_id>/answer")
    def answer_game_session(session_id: str):
        actor = _require_auth(auth_manager, settings.auth_token_ttl_seconds)
        payload = require_json_object(request.get_json(silent=True))
        answer_payload = validate_answer_payload({"session_id": session_id, "choice_id": payload.get("choice_id")})
        result = game_service.submit_answer(answer_payload["session_id"], answer_payload["choice_id"], actor)
        _record_completed_session(game_service, platform_store, answer_payload["session_id"], actor, result)
        return jsonify(result)

    @app.post("/api/games/answer")
    def answer_game():
        actor = _require_auth(auth_manager, settings.auth_token_ttl_seconds)
        payload = require_json_object(request.get_json(silent=True))
        answer_payload = validate_answer_payload(payload)
        result = game_service.submit_answer(answer_payload["session_id"], answer_payload["choice_id"], actor)
        _record_completed_session(game_service, platform_store, answer_payload["session_id"], actor, result)
        return jsonify(result)

    @app.get("/api/progress/<student_id>")
    def student_progress(student_id: str):
        actor = _require_auth(auth_manager, settings.auth_token_ttl_seconds)
        ensure_student_access(actor, student_id)
        return jsonify(platform_store.get_student_progress(student_id))

    @app.get("/api/dashboard/teacher")
    def teacher_dashboard():
        actor = _require_auth(auth_manager, settings.auth_token_ttl_seconds)
        ensure_roles(actor, {"teacher", "admin"})
        return jsonify(platform_store.get_teacher_dashboard())

    return app


def _models_ready(cfg: dict) -> bool:
    required = [
        os.path.join(cfg["paths"]["model_dir"], "xgb_next_topic.pkl"),
        os.path.join(cfg["paths"]["model_dir"], "xgb_recommended_difficulty.pkl"),
        os.path.join(cfg["paths"]["model_dir"], "xgb_success_probability_bin.pkl"),
        os.path.join(cfg["paths"]["model_dir"], "xgb_needs_revision.pkl"),
    ]
    return all(Path(path).exists() for path in required)


def _require_auth(auth_manager: AuthManager, token_ttl_seconds: int) -> dict:
    header = request.headers.get("Authorization", "").strip()
    if not header.startswith("Bearer "):
        raise AuthenticationError("Bearer token is required.")
    token = header.split(" ", 1)[1].strip()
    if not token:
        raise AuthenticationError("Bearer token is required.")
    return auth_manager.verify_token(token, token_ttl_seconds)


def _record_completed_session(game_service: GameService, platform_store: PlatformStore, session_id: str, actor: dict, result: dict) -> None:
    if not result.get("completed"):
        return
    session = game_service.get_session(session_id, actor)
    if session.get("result_recorded"):
        return
    platform_store.record_game_completion(session, result["summary"])
    game_service.mark_result_recorded(session_id)
