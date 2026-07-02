from datetime import datetime, timedelta, timezone

from inference.game_selector import (
    BADGE_TRACKS,
    DEVICE_MODES,
    DIFFICULTY_METER,
    GAME_POOLS,
    MECHANIC_LINEUPS,
    OUTCOME_VERBS,
    REWARD_LOOPS,
    SCENE_PACKS_BY_SUBJECT,
    SESSION_LENGTHS,
    STYLE_FLAVORS,
    THEMES_BY_SUBJECT,
    TIMER_PROFILES,
)
from utils.helpers import now_slug, utc_now_iso

OFFLINE_PACK_TTL_DAYS = 30


def build_offline_pack(cfg: dict, actor: dict, progress: dict, mastery_snapshot: dict | None = None) -> dict:
    downloaded_at = utc_now_iso()
    return {
        "pack_id": f"pack-{actor['user_id']}-{now_slug()}",
        "pack_version": f"{cfg['project']['version']}-{now_slug()}",
        "student": {
            "user_id": actor["user_id"],
            "display_name": actor.get("display_name", actor["user_id"]),
            "role": actor["role"],
        },
        "catalog": {
            "grades": cfg["domain"]["grades"],
            "subjects": cfg["domain"]["subjects"],
            "topics_by_subject": cfg["domain"]["topics_by_subject"],
            "learning_styles": cfg["domain"]["learning_styles"],
            "device_types": cfg["domain"]["device_types"],
        },
        "game_templates": {
            "game_pools": GAME_POOLS,
            "themes_by_subject": THEMES_BY_SUBJECT,
            "style_flavors": STYLE_FLAVORS,
            "device_modes": DEVICE_MODES,
            "outcome_verbs": OUTCOME_VERBS,
            "session_lengths": SESSION_LENGTHS,
            "reward_loops": REWARD_LOOPS,
            "scene_packs_by_subject": SCENE_PACKS_BY_SUBJECT,
            "mechanic_lineups": MECHANIC_LINEUPS,
            "badge_tracks": BADGE_TRACKS,
            "timer_profiles": TIMER_PROFILES,
            "difficulty_meter": DIFFICULTY_METER,
        },
        "rules_config": {
            "success_probability_thresholds": {"high": 0.78, "medium": 0.55},
            "revision_thresholds": {"high": 45, "medium": 60},
            "difficulty_thresholds": {"easy": 55, "hard": 82},
            "mastery_threshold": 80,
            "review_mastery_threshold": 70,
            "recent_session_window": 5,
            "max_recent_games": 5,
        },
        "baseline_progress": {
            "progress": progress,
            "mastery_snapshot": mastery_snapshot or default_mastery_snapshot(actor["user_id"]),
        },
        "offline_access_expires_at": (datetime.now(timezone.utc) + timedelta(days=OFFLINE_PACK_TTL_DAYS)).isoformat(),
        "downloaded_at": downloaded_at,
    }


def default_mastery_snapshot(student_id: str) -> dict:
    return {
        "student_id": student_id,
        "topics": {},
        "updated_at": utc_now_iso(),
    }
