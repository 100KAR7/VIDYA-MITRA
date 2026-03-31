import random
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict

from backend.errors import ConflictError, NotFoundError, ServiceUnavailableError, ValidationError


class GameService:
    def __init__(self, cfg: dict, session_ttl_seconds: int = 1800, max_live_sessions: int = 1000):
        self.cfg = cfg
        self.sessions: dict[str, Dict] = {}
        self.session_ttl_seconds = session_ttl_seconds
        self.max_live_sessions = max_live_sessions
        self.lock = threading.RLock()

    def launch_session(self, student_profile: dict, prediction: dict, game: dict, actor: dict | None = None) -> dict:
        with self.lock:
            self._prune_expired_sessions()
            if len(self.sessions) >= self.max_live_sessions:
                raise ServiceUnavailableError("The game service is at capacity. Please try again shortly.")

            session_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            questions = self._build_questions(student_profile, prediction, game)
            session = {
                "session_id": session_id,
                "student_profile": student_profile,
                "prediction": prediction,
                "game": game,
                "actor": actor or {},
                "questions": questions,
                "current_index": 0,
                "score": 0,
                "max_score": sum(question["points"] for question in questions),
                "answers": [],
                "status": "active",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=self.session_ttl_seconds)).isoformat(),
                "summary": None,
            }
            self.sessions[session_id] = session
            return {
                "session_id": session_id,
                "game": game,
                "progress": self._progress(session),
                "question": self._public_question(session["questions"][0]),
                "summary": None,
            }

    def submit_answer(self, session_id: str, choice_id: str, actor: dict | None = None) -> dict:
        with self.lock:
            session = self._get_active_session(session_id)
            self._authorize_actor(session, actor)

            if session["status"] == "completed":
                raise ConflictError("Game session is already complete.")

            question = session["questions"][session["current_index"]]
            valid_choice_ids = {choice["id"] for choice in question["choices"]}
            if choice_id not in valid_choice_ids:
                raise ValidationError("Choice ID is not valid for the current question.")

            correct = choice_id == question["correct_choice_id"]
            if correct:
                session["score"] += question["points"]

            session["answers"].append(
                {
                    "question_id": question["id"],
                    "choice_id": choice_id,
                    "correct": correct,
                }
            )
            session["current_index"] += 1
            now = datetime.now(timezone.utc)
            session["updated_at"] = now.isoformat()
            session["expires_at"] = (now + timedelta(seconds=self.session_ttl_seconds)).isoformat()

            response = {
                "correct": correct,
                "correct_choice_id": question["correct_choice_id"],
                "explanation": question["explanation"],
                "score": session["score"],
                "progress": self._progress(session),
            }

            if session["current_index"] >= len(session["questions"]):
                session["status"] = "completed"
                session["summary"] = self._build_summary(session)
                response["completed"] = True
                response["summary"] = session["summary"]
                response["question"] = None
            else:
                response["completed"] = False
                response["summary"] = None
                response["question"] = self._public_question(session["questions"][session["current_index"]])

            return response

    def get_session(self, session_id: str) -> dict:
        with self.lock:
            return self._get_active_session(session_id)

    def delete_session(self, session_id: str) -> None:
        with self.lock:
            self.sessions.pop(session_id, None)

    def active_session_count(self) -> int:
        with self.lock:
            self._prune_expired_sessions()
            return len(self.sessions)

    def _build_questions(self, student_profile: dict, prediction: dict, game: dict) -> list[dict]:
        subject = student_profile["subject"]
        current_topic = student_profile["topic"].replace("_", " ")
        target_topic = prediction["next_recommended_topic"].replace("_", " ")
        difficulty = prediction["recommended_difficulty"]
        game_name = game["game_name"]
        same_subject_topics = [
            topic.replace("_", " ")
            for topic in self.cfg["domain"]["topics_by_subject"].get(subject, [])
            if topic.replace("_", " ") not in {current_topic, target_topic}
        ]
        rng = random.Random(f"{student_profile['student_id']}|{game['game_variant_id']}")

        distractors = rng.sample(same_subject_topics, k=min(3, len(same_subject_topics)))
        while len(distractors) < 3:
            distractors.append(f"{target_topic} Extension {len(distractors) + 1}")

        return [
            self._make_question(
                "q1",
                f"In {game_name}, which mission target should stay fixed for this learner?",
                [target_topic, *distractors],
                target_topic,
                f"The learning target should remain {target_topic} even when the game wrapper changes.",
            ),
            self._make_question(
                "q2",
                "What difficulty lane best matches this learner's current plan?",
                [
                    "Easy lane with extra scaffolding",
                    "Medium lane with balanced challenge",
                    "Hard lane with mastery pressure",
                    "Random lane with no adaptation",
                ],
                {
                    "easy": "Easy lane with extra scaffolding",
                    "medium": "Medium lane with balanced challenge",
                    "hard": "Hard lane with mastery pressure",
                }[difficulty],
                "The game should respect the model's recommended difficulty instead of picking a random challenge level.",
            ),
            self._make_question(
                "q3",
                f"Which rule keeps the game aligned while {current_topic} transitions to {target_topic}?",
                [
                    "Swap the theme but keep the target topic and difficulty",
                    "Swap the target topic whenever the child gets bored",
                    "Ignore the learner profile and use one default game",
                    "Use harder questions than the model suggested",
                ],
                "Swap the theme but keep the target topic and difficulty",
                "The system should vary presentation and mechanics, not the educational outcome.",
            ),
            self._make_question(
                "q4",
                f"Which reward loop belongs to {game_name}?",
                [
                    game["reward_loop"],
                    "video ads and unrelated coupons",
                    "random cosmetic unlocks with no learning tie-in",
                    "skip every checkpoint and auto-finish",
                ],
                game["reward_loop"],
                "Rewards should reinforce the designed game mode and learning progression.",
            ),
        ]

    def _make_question(self, question_id: str, prompt: str, choices: list[str], correct_label: str, explanation: str) -> dict:
        labeled_choices = []
        correct_choice_id = None
        for idx, label in enumerate(choices):
            choice_id = f"c{idx + 1}"
            labeled_choices.append({"id": choice_id, "label": label})
            if label == correct_label:
                correct_choice_id = choice_id
        return {
            "id": question_id,
            "prompt": prompt,
            "choices": labeled_choices,
            "correct_choice_id": correct_choice_id,
            "explanation": explanation,
            "points": 25,
        }

    def _public_question(self, question: dict) -> dict:
        return {
            "id": question["id"],
            "prompt": question["prompt"],
            "choices": question["choices"],
        }

    def _progress(self, session: dict) -> dict:
        total = len(session["questions"])
        current = min(session["current_index"] + 1, total)
        return {
            "current_round": current,
            "total_rounds": total,
            "score": session["score"],
            "max_score": session["max_score"],
        }

    def _build_summary(self, session: dict) -> dict:
        score_pct = round(session["score"] / max(session["max_score"], 1) * 100)
        stars = 3 if score_pct >= 85 else (2 if score_pct >= 60 else 1)
        if score_pct >= 85:
            completion_note = "Excellent session. The learner is ready to keep momentum going."
        elif score_pct >= 60:
            completion_note = "Solid session. A little more repetition will strengthen retention."
        else:
            completion_note = "This learner needs another support-focused run before moving on."

        return {
            "score": session["score"],
            "max_score": session["max_score"],
            "score_percent": score_pct,
            "stars": stars,
            "completion_note": completion_note,
            "target_topic": session["prediction"]["next_recommended_topic"],
            "recommended_next_action": session["prediction"]["adaptive_action"],
            "game_name": session["game"]["game_name"],
        }

    def _get_active_session(self, session_id: str) -> dict:
        self._prune_expired_sessions()
        session = self.sessions.get(session_id)
        if session is None:
            raise NotFoundError("Game session was not found or has expired.")
        return session

    def _prune_expired_sessions(self) -> None:
        now = datetime.now(timezone.utc)
        expired_ids = [
            session_id
            for session_id, session in self.sessions.items()
            if datetime.fromisoformat(session["expires_at"]) <= now
        ]
        for session_id in expired_ids:
            self.sessions.pop(session_id, None)

    def _authorize_actor(self, session: dict, actor: dict | None) -> None:
        session_actor = session.get("actor") or {}
        if not session_actor or not actor:
            return
        if actor["role"] in {"teacher", "admin"}:
            return
        if actor["user_id"] != session_actor.get("user_id"):
            raise ConflictError("This session belongs to another learner.")
