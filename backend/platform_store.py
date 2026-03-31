import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from utils.helpers import utc_now_iso


class PlatformStore:
    def __init__(self, path: str = "outputs/platform_store.db"):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def login(self, role: str, user_id: str, display_name: str) -> dict:
        timestamp = utc_now_iso()
        user = {
            "user_id": user_id,
            "display_name": display_name,
            "role": role,
            "last_login": timestamp,
        }
        with self.lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, display_name, role, last_login, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    role = excluded.role,
                    last_login = excluded.last_login,
                    updated_at = excluded.updated_at
                """,
                (user_id, display_name, role, timestamp, timestamp, timestamp),
            )
        return user

    def record_prediction(self, actor: dict | None, student_profile: dict, prediction: dict) -> None:
        with self.lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO prediction_events (
                    timestamp,
                    actor_json,
                    student_id,
                    student_profile_json,
                    prediction_json,
                    next_recommended_topic,
                    recommended_difficulty,
                    success_probability_label,
                    needs_revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    utc_now_iso(),
                    json.dumps(actor or {}),
                    student_profile.get("student_id"),
                    json.dumps(student_profile),
                    json.dumps(prediction),
                    prediction["next_recommended_topic"],
                    prediction["recommended_difficulty"],
                    prediction["success_probability_label"],
                    int(bool(prediction["needs_revision"])),
                ),
            )

    def record_game_completion(self, session: dict, summary: dict) -> None:
        with self.lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO game_results (
                    timestamp,
                    actor_json,
                    student_id,
                    student_profile_json,
                    game_name,
                    game_variant_id,
                    summary_json,
                    score_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    utc_now_iso(),
                    json.dumps(session.get("actor") or {}),
                    session["student_profile"].get("student_id"),
                    json.dumps(session["student_profile"]),
                    session["game"]["game_name"],
                    session["game"]["game_variant_id"],
                    json.dumps(summary),
                    float(summary.get("score_percent", 0)),
                ),
            )

    def get_student_progress(self, student_id: str) -> dict:
        with self.lock, self._connect() as conn:
            prediction_rows = conn.execute(
                """
                SELECT prediction_json
                FROM prediction_events
                WHERE student_id = ?
                ORDER BY id DESC
                """,
                (student_id,),
            ).fetchall()
            game_rows = conn.execute(
                """
                SELECT timestamp, actor_json, student_id, student_profile_json, game_name, game_variant_id, summary_json
                FROM game_results
                WHERE student_id = ?
                ORDER BY id DESC
                LIMIT 5
                """,
                (student_id,),
            ).fetchall()
            total_sessions = conn.execute(
                "SELECT COUNT(*) AS count FROM game_results WHERE student_id = ?",
                (student_id,),
            ).fetchone()["count"]
            average_score = conn.execute(
                "SELECT COALESCE(ROUND(AVG(score_percent), 1), 0.0) AS avg_score FROM game_results WHERE student_id = ?",
                (student_id,),
            ).fetchone()["avg_score"]

        latest_prediction = json.loads(prediction_rows[0]["prediction_json"]) if prediction_rows else None
        return {
            "student_id": student_id,
            "total_predictions": len(prediction_rows),
            "total_sessions": int(total_sessions or 0),
            "average_score_percent": float(average_score or 0.0),
            "latest_prediction": latest_prediction,
            "recent_games": [self._deserialize_game_row(row) for row in game_rows],
        }

    def get_teacher_dashboard(self) -> dict:
        with self.lock, self._connect() as conn:
            prediction_totals = conn.execute(
                """
                SELECT
                    COUNT(DISTINCT student_id) AS total_learners,
                    COUNT(*) AS total_predictions,
                    COALESCE(SUM(needs_revision), 0) AS revision_alerts
                FROM prediction_events
                """
            ).fetchone()
            session_totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_game_sessions,
                    COALESCE(ROUND(AVG(score_percent), 1), 0.0) AS average_score_percent
                FROM game_results
                """
            ).fetchone()
            activity_rows = conn.execute(
                """
                SELECT timestamp, actor_json, student_id, student_profile_json, game_name, game_variant_id, summary_json
                FROM game_results
                ORDER BY id DESC
                LIMIT 8
                """
            ).fetchall()

        return {
            "total_learners": int(prediction_totals["total_learners"] or 0),
            "total_predictions": int(prediction_totals["total_predictions"] or 0),
            "total_game_sessions": int(session_totals["total_game_sessions"] or 0),
            "average_score_percent": float(session_totals["average_score_percent"] or 0.0),
            "revision_alerts": int(prediction_totals["revision_alerts"] or 0),
            "recent_activity": [self._deserialize_game_row(row) for row in activity_rows],
        }

    def healthcheck(self) -> bool:
        try:
            with self.lock, self._connect() as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def _initialize(self) -> None:
        with self.lock, self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    last_login TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS prediction_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    actor_json TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    student_profile_json TEXT NOT NULL,
                    prediction_json TEXT NOT NULL,
                    next_recommended_topic TEXT NOT NULL,
                    recommended_difficulty TEXT NOT NULL,
                    success_probability_label TEXT NOT NULL,
                    needs_revision INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS game_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    actor_json TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    student_profile_json TEXT NOT NULL,
                    game_name TEXT NOT NULL,
                    game_variant_id TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    score_percent REAL NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_prediction_events_student
                    ON prediction_events(student_id, id DESC);

                CREATE INDEX IF NOT EXISTS idx_game_results_student
                    ON game_results(student_id, id DESC);
                """
            )
        self._maybe_migrate_legacy_json()

    def _maybe_migrate_legacy_json(self) -> None:
        legacy_path = self.path.with_suffix(".json")
        if not legacy_path.exists():
            return

        with self.lock, self._connect() as conn:
            row_count = conn.execute("SELECT COUNT(*) AS count FROM prediction_events").fetchone()["count"]
            if row_count:
                return

            with legacy_path.open("r", encoding="utf-8") as handle:
                legacy_state = json.load(handle)

            for user in legacy_state.get("users", {}).values():
                timestamp = user.get("last_login") or utc_now_iso()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO users (user_id, display_name, role, last_login, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user["user_id"],
                        user.get("display_name", user["user_id"]),
                        user.get("role", "student"),
                        timestamp,
                        timestamp,
                        timestamp,
                    ),
                )

            for event in legacy_state.get("prediction_events", []):
                prediction = event.get("prediction", {})
                conn.execute(
                    """
                    INSERT INTO prediction_events (
                        timestamp,
                        actor_json,
                        student_id,
                        student_profile_json,
                        prediction_json,
                        next_recommended_topic,
                        recommended_difficulty,
                        success_probability_label,
                        needs_revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.get("timestamp", utc_now_iso()),
                        json.dumps(event.get("actor", {})),
                        event.get("student_id"),
                        json.dumps(event.get("student_profile", {})),
                        json.dumps(prediction),
                        prediction.get("next_recommended_topic") or prediction.get("next_topic", "Unknown"),
                        prediction.get("recommended_difficulty", "medium"),
                        prediction.get("success_probability_label", "medium"),
                        int(bool(prediction.get("needs_revision", False))),
                    ),
                )

            for result in legacy_state.get("game_results", []):
                summary = result.get("summary", {})
                conn.execute(
                    """
                    INSERT INTO game_results (
                        timestamp,
                        actor_json,
                        student_id,
                        student_profile_json,
                        game_name,
                        game_variant_id,
                        summary_json,
                        score_percent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.get("timestamp", utc_now_iso()),
                        json.dumps(result.get("actor", {})),
                        result.get("student_id"),
                        json.dumps(result.get("student_profile", {})),
                        result.get("game_name", "Unknown Game"),
                        result.get("game_variant_id", "legacy"),
                        json.dumps(summary),
                        float(summary.get("score_percent", 0)),
                    ),
                )

    def _deserialize_game_row(self, row: sqlite3.Row) -> dict:
        return {
            "timestamp": row["timestamp"],
            "actor": json.loads(row["actor_json"]),
            "student_id": row["student_id"],
            "student_profile": json.loads(row["student_profile_json"]),
            "game_name": row["game_name"],
            "game_variant_id": row["game_variant_id"],
            "summary": json.loads(row["summary_json"]),
        }

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
