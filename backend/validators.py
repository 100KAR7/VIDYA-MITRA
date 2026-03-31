from typing import Any

from backend.errors import AuthorizationError, ValidationError
from utils.helpers import now_slug

LOGIN_ROLES = {"student", "teacher", "admin"}
NUMERIC_RULES = {
    "past_quiz_score_avg": (float, 0, 100),
    "accuracy_percentage": (float, 0, 100),
    "avg_response_time_sec": (float, 1, 300),
    "num_attempts": (int, 1, 50),
    "learning_streak_days": (int, 0, 365),
    "engagement_score": (float, 0, 1),
    "hints_used": (int, 0, 50),
    "video_watch_pct": (float, 0, 100),
    "time_on_task_min": (float, 1, 240),
    "session_count_week": (int, 1, 60),
}


def require_json_object(payload: Any, *, message: str = "Request body must be a JSON object.") -> dict:
    if not isinstance(payload, dict) or not payload:
        raise ValidationError(message)
    return payload


def validate_login_payload(payload: dict) -> dict:
    payload = require_json_object(payload)
    role = _required_string(payload, "role").lower()
    if role not in LOGIN_ROLES:
        raise ValidationError("Role must be student, teacher, or admin.")
    return {
        "role": role,
        "user_id": _required_string(payload, "user_id"),
        "display_name": _required_string(payload, "display_name"),
    }


def validate_student_profile(payload: dict, cfg: dict) -> dict:
    payload = require_json_object(payload, message="Learner profile must be a JSON object.")
    domain = cfg["domain"]
    subject = _enum_string(payload, "subject", domain["subjects"])
    cleaned = {
        "student_id": str(payload.get("student_id") or f"S-{now_slug()}").strip(),
        "name": str(payload.get("name") or "Learner").strip(),
        "grade": _enum_string(payload, "grade", domain["grades"]),
        "subject": subject,
        "topic": _enum_string(payload, "topic", domain["topics_by_subject"].get(subject, [])),
        "learning_style": _enum_string(payload, "learning_style", domain["learning_styles"]),
        "device_type": _enum_string(payload, "device_type", domain["device_types"]),
    }
    if not cleaned["student_id"]:
        raise ValidationError("Student ID is required.")

    for field, (caster, minimum, maximum) in NUMERIC_RULES.items():
        cleaned[field] = _coerce_numeric(payload.get(field), field, caster, minimum, maximum)
    return cleaned


def validate_prediction_request(payload: dict, cfg: dict) -> dict:
    payload = require_json_object(payload)
    student_profile = payload.get("student_profile", payload)
    return {"student_profile": validate_student_profile(student_profile, cfg)}


def validate_game_launch_payload(payload: dict, cfg: dict) -> dict:
    payload = require_json_object(payload)
    student_profile = validate_student_profile(payload.get("student_profile"), cfg)
    prediction = validate_prediction_snapshot(payload.get("prediction"))
    game = validate_game_card(payload.get("game"))
    return {
        "student_profile": student_profile,
        "prediction": prediction,
        "game": game,
    }


def validate_answer_payload(payload: dict) -> dict:
    payload = require_json_object(payload)
    return {
        "session_id": _required_string(payload, "session_id"),
        "choice_id": _required_string(payload, "choice_id"),
    }


def validate_prediction_snapshot(prediction: dict) -> dict:
    prediction = require_json_object(prediction, message="Prediction payload must be a JSON object.")
    difficulty = _enum_string(prediction, "recommended_difficulty", ["easy", "medium", "hard"])
    return {
        **prediction,
        "next_recommended_topic": _required_string(prediction, "next_recommended_topic"),
        "recommended_difficulty": difficulty,
        "adaptive_action": _required_string(prediction, "adaptive_action"),
    }


def validate_game_card(game: dict) -> dict:
    game = require_json_object(game, message="Game payload must be a JSON object.")
    required_fields = [
        "game_name",
        "game_variant_id",
        "game_type",
        "game_mode",
        "theme",
        "interaction_style",
        "learning_target",
        "reward_loop",
    ]
    cleaned = {field: _required_string(game, field) for field in required_fields}
    cleaned.update({key: value for key, value in game.items() if key not in cleaned})
    return cleaned


def ensure_student_access(actor: dict, student_id: str) -> None:
    if actor["role"] == "student" and actor["user_id"] != student_id:
        raise AuthorizationError("Students can only access their own learner record.")


def ensure_roles(actor: dict, allowed_roles: set[str]) -> None:
    if actor["role"] not in allowed_roles:
        raise AuthorizationError("You do not have permission to access this resource.")


def _required_string(payload: dict, field: str) -> str:
    value = str(payload.get(field, "")).strip()
    if not value:
        raise ValidationError(f"{field} is required.")
    return value


def _enum_string(payload: dict, field: str, allowed: list[str]) -> str:
    value = _required_string(payload, field)
    if value not in allowed:
        raise ValidationError(f"{field} must be one of: {', '.join(allowed)}.")
    return value


def _coerce_numeric(value: Any, field: str, caster: type, minimum: float, maximum: float) -> int | float:
    if value in (None, ""):
        raise ValidationError(f"{field} is required.")
    try:
        parsed = caster(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be a valid {caster.__name__}.") from exc
    if parsed < minimum or parsed > maximum:
        raise ValidationError(f"{field} must be between {minimum} and {maximum}.")
    return parsed
