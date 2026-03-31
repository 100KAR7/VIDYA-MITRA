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
            lessons = self._build_lessons(student_profile, prediction, game)
            questions = self._build_questions(student_profile, prediction, game)
            session = {
                "session_id": session_id,
                "student_profile": student_profile,
                "prediction": prediction,
                "game": game,
                "actor": actor or {},
                "lesson_cards": lessons,
                "lesson_index": 0,
                "lesson_history": [],
                "questions": questions,
                "current_index": 0,
                "score": 0,
                "max_score": sum(question["points"] for question in questions),
                "answers": [],
                "phase": "learn",
                "status": "active",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "phase_started_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=self.session_ttl_seconds)).isoformat(),
                "summary": None,
                "result_recorded": False,
                "earned_badges": [],
            }
            self.sessions[session_id] = session
            return self._public_session(session)

    def get_session(self, session_id: str, actor: dict | None = None) -> dict:
        with self.lock:
            session = self._get_active_session(session_id)
            self._authorize_actor(session, actor)
            return session

    def get_session_state(self, session_id: str, actor: dict | None = None) -> dict:
        with self.lock:
            session = self._get_active_session(session_id)
            self._authorize_actor(session, actor)
            return self._public_session(session)

    def advance_lesson(self, session_id: str, actor: dict | None = None, selection_id: str | None = None) -> dict:
        with self.lock:
            session = self._get_active_session(session_id)
            self._authorize_actor(session, actor)

            if session["status"] == "completed":
                raise ConflictError("This game session is already complete.")
            if session["phase"] != "learn":
                raise ConflictError("Learning missions are already complete. Start the final test.")

            lesson = session["lesson_cards"][session["lesson_index"]]
            option_ids = {option["id"] for option in lesson["mechanic_options"]}
            if selection_id and selection_id not in option_ids:
                raise ValidationError("Selection is not valid for the current lesson mechanic.")

            mechanic_success = bool(selection_id and selection_id == lesson["correct_option_id"])
            earned_badge = {
                **lesson["reward_badge"],
                "status": "mastered" if mechanic_success else "cleared",
                "earned_at": datetime.now(timezone.utc).isoformat(),
            }
            session["earned_badges"].append(earned_badge)
            session["lesson_history"].append(
                {
                    "lesson_id": lesson["id"],
                    "selected_option_id": selection_id,
                    "success": mechanic_success,
                    "badge_id": earned_badge["id"],
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            session["lesson_index"] += 1
            self._touch(session, phase_reset=session["lesson_index"] >= len(session["lesson_cards"]))

            if session["lesson_index"] >= len(session["lesson_cards"]):
                session["phase"] = "assessment"
                session["phase_started_at"] = datetime.now(timezone.utc).isoformat()
                return {
                    **self._public_session(session),
                    "badge_awarded": earned_badge,
                    "mechanic_success": mechanic_success,
                    "transition_note": "Learning complete. The final test is now unlocked.",
                }

            return {
                **self._public_session(session),
                "badge_awarded": earned_badge,
                "mechanic_success": mechanic_success,
                "transition_note": "Lesson complete. The next learning mechanic is ready.",
            }

    def submit_answer(self, session_id: str, choice_id: str, actor: dict | None = None) -> dict:
        with self.lock:
            session = self._get_active_session(session_id)
            self._authorize_actor(session, actor)

            if session["status"] == "completed":
                raise ConflictError("Game session is already complete.")
            if session["phase"] != "assessment":
                raise ConflictError("Finish the learning missions before starting the final test.")

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
            self._touch(session)

            response = {
                "correct": correct,
                "correct_choice_id": question["correct_choice_id"],
                "explanation": question["explanation"],
                "score": session["score"],
                "progress": self._progress(session),
            }

            if session["current_index"] >= len(session["questions"]):
                session["status"] = "completed"
                session["phase"] = "completed"
                session["summary"] = self._build_summary(session)
                response["completed"] = True
                response["summary"] = session["summary"]
                response["question"] = None
                response["session"] = self._public_session(session)
            else:
                response["completed"] = False
                response["summary"] = None
                response["question"] = self._public_question(session["questions"][session["current_index"]])
                response["session"] = self._public_session(session)

            return response

    def mark_result_recorded(self, session_id: str) -> None:
        with self.lock:
            session = self._get_active_session(session_id)
            session["result_recorded"] = True

    def active_session_count(self) -> int:
        with self.lock:
            self._prune_expired_sessions()
            return len(self.sessions)

    def _build_lessons(self, student_profile: dict, prediction: dict, game: dict) -> list[dict]:
        current_topic = student_profile["topic"].replace("_", " ")
        target_topic = prediction["next_recommended_topic"].replace("_", " ")
        difficulty = prediction["recommended_difficulty"]
        scene_pack = game.get("scene_pack", {})
        mechanic_lineup = game.get("mechanic_lineup", ["choice_path", "pattern_stack", "signal_scan"])
        badge_track = game.get("badge_track", [])
        lesson_seconds = int(game.get("timer_profile", {}).get("lesson_seconds", 50))

        return [
            self._make_lesson(
                lesson_id=f"lesson-{index + 1}",
                lesson_number=index + 1,
                current_topic=current_topic,
                target_topic=target_topic,
                difficulty=difficulty,
                game=game,
                scene_pack=scene_pack,
                mechanic_type=mechanic_lineup[index],
                reward_badge=badge_track[index],
                timer_seconds=lesson_seconds + index * 3,
            )
            for index in range(min(3, len(mechanic_lineup), len(badge_track)))
        ]

    def _make_lesson(
        self,
        lesson_id: str,
        lesson_number: int,
        current_topic: str,
        target_topic: str,
        difficulty: str,
        game: dict,
        scene_pack: dict,
        mechanic_type: str,
        reward_badge: dict,
        timer_seconds: int,
    ) -> dict:
        title = f"{game['game_name']}: {self._mechanic_title(mechanic_type)}"
        subtitle = f"{scene_pack.get('world_name', game['theme'])} · Lesson {lesson_number}"
        coach_line = (
            f"{scene_pack.get('mentor_title', 'Mission guide')} is helping the learner move from {current_topic} into {target_topic}."
        )
        focus_points = [
            f"Keep the target fixed on {target_topic}.",
            f"Use the {difficulty} lane to match the learner model.",
            f"Let the theme change while the curriculum outcome stays stable.",
        ]
        example = game.get("narrative_hook", f"Clear this mechanic to unlock the final {target_topic} test.")
        mechanic = self._mechanic_content(mechanic_type, current_topic, target_topic, difficulty, game, scene_pack)
        return {
            "id": lesson_id,
            "title": title,
            "subtitle": subtitle,
            "coach_line": coach_line,
            "focus_points": focus_points,
            "example": example,
            "action_label": "Bank Badge And Continue" if lesson_number < 3 else "Unlock Final Test",
            "scene_title": mechanic["scene_title"],
            "scene_tokens": scene_pack.get("visual_tokens", []),
            "mechanic_type": mechanic_type,
            "mechanic_prompt": mechanic["prompt"],
            "mechanic_options": mechanic["options"],
            "correct_option_id": mechanic["correct_option_id"],
            "success_message": mechanic["success_message"],
            "retry_message": mechanic["retry_message"],
            "reward_badge": reward_badge,
            "timer_seconds": timer_seconds,
        }

    def _mechanic_content(
        self,
        mechanic_type: str,
        current_topic: str,
        target_topic: str,
        difficulty: str,
        game: dict,
        scene_pack: dict,
    ) -> dict:
        if mechanic_type == "choice_path":
            return {
                "scene_title": f"{scene_pack.get('world_name', game['theme'])} route console",
                "prompt": f"Pick the route that keeps the mission focused on {target_topic}.",
                "options": [
                    {
                        "id": "route-focus",
                        "label": f"Target route: {target_topic}",
                        "description": f"Lock the path on {target_topic} and keep {difficulty} challenge balance.",
                    },
                    {
                        "id": "route-repeat",
                        "label": f"Repeat only {current_topic}",
                        "description": "Stay in the old topic and never advance the learner.",
                    },
                    {
                        "id": "route-random",
                        "label": "Random topic switch",
                        "description": "Break curriculum alignment with a new but unrelated challenge.",
                    },
                ],
                "correct_option_id": "route-focus",
                "success_message": f"Correct route. The game world changes, but {target_topic} stays locked in.",
                "retry_message": f"That route changes the learning outcome. Re-center on {target_topic}.",
            }

        if mechanic_type == "pattern_stack":
            return {
                "scene_title": f"{scene_pack.get('mentor_title', 'Mentor')} pattern bench",
                "prompt": f"Choose the pattern stack that best builds toward {target_topic}.",
                "options": [
                    {
                        "id": "stack-balanced",
                        "label": f"Bridge {current_topic} -> practice -> {target_topic}",
                        "description": "A guided pattern flow that builds confidence and transfer.",
                    },
                    {
                        "id": "stack-rush",
                        "label": "Skip practice and jump to the boss",
                        "description": "Too abrupt for a stable adaptive progression.",
                    },
                    {
                        "id": "stack-static",
                        "label": "Use one unchanged pattern forever",
                        "description": "No fresh game feel and no adaptive pacing.",
                    },
                ],
                "correct_option_id": "stack-balanced",
                "success_message": "Pattern locked. The learner gets a fresh mechanic and a stable knowledge bridge.",
                "retry_message": "That stack weakens the practice arc. Choose the bridge that supports progression.",
            }

        if mechanic_type == "build_combo":
            return {
                "scene_title": f"{game['theme']} combo forge",
                "prompt": f"Assemble the best mechanic combo for a {difficulty} path toward {target_topic}.",
                "options": [
                    {
                        "id": "combo-adaptive",
                        "label": f"Theme skin + {difficulty} lane + {target_topic} goal",
                        "description": "This combo keeps the learning target fixed while changing the play style.",
                    },
                    {
                        "id": "combo-cosmetic",
                        "label": "Skins only, no learning adjustment",
                        "description": "Looks fun but ignores the model recommendation.",
                    },
                    {
                        "id": "combo-chaos",
                        "label": "Random goal + random difficulty + random rewards",
                        "description": "Too noisy to serve the learner outcome.",
                    },
                ],
                "correct_option_id": "combo-adaptive",
                "success_message": "Combo built. The mechanics now support the right learning target and difficulty.",
                "retry_message": "That combo breaks adaptation. Keep the goal and difficulty anchored to the model.",
            }

        return {
            "scene_title": f"{scene_pack.get('world_name', game['theme'])} signal board",
            "prompt": f"Scan the board and lock the strongest signal for {target_topic}.",
            "options": [
                {
                    "id": "signal-target",
                    "label": f"{target_topic} beacon",
                    "description": "The signal that matches the target topic and current mission objective.",
                },
                {
                    "id": "signal-noise",
                    "label": "Theme-only beacon",
                    "description": "Looks exciting but does not represent the learning target.",
                },
                {
                    "id": "signal-detour",
                    "label": "Difficulty spike beacon",
                    "description": "Adds pressure without respecting the current learner path.",
                },
            ],
            "correct_option_id": "signal-target",
            "success_message": "Signal locked. The student can now enter the test with the right topic target.",
            "retry_message": "That signal is noise. Lock the beacon that points to the actual topic goal.",
        }

    def _build_questions(self, student_profile: dict, prediction: dict, game: dict) -> list[dict]:
        subject = student_profile["subject"]
        current_topic = student_profile["topic"].replace("_", " ")
        target_topic = prediction["next_recommended_topic"].replace("_", " ")
        difficulty = prediction["recommended_difficulty"]
        game_name = game["game_name"]
        test_seconds = int(game.get("timer_profile", {}).get("test_seconds", 35))
        same_subject_topics = [
            topic.replace("_", " ")
            for topic in self.cfg["domain"]["topics_by_subject"].get(subject, [])
            if topic.replace("_", " ") not in {current_topic, target_topic}
        ]

        while len(same_subject_topics) < 3:
            same_subject_topics.append(f"{target_topic} Extension {len(same_subject_topics) + 1}")

        distractors = same_subject_topics[:3]
        return [
            self._make_question(
                "q1",
                f"Which topic is the real learning target inside {game_name}?",
                [target_topic, *distractors],
                target_topic,
                f"The learning target stays on {target_topic} even though the game presentation changes.",
                test_seconds,
            ),
            self._make_question(
                "q2",
                "Which rule keeps the game aligned with the model recommendation?",
                [
                    "Keep the same target topic and difficulty while changing only the game wrapper",
                    "Change the topic whenever the learner asks for a new game",
                    "Ignore the model and pick a random challenge level",
                    "Use the same exact visuals for every learner",
                ],
                "Keep the same target topic and difficulty while changing only the game wrapper",
                "A fresh game should change presentation, not the curriculum outcome.",
                test_seconds,
            ),
            self._make_question(
                "q3",
                "Which challenge lane matches this learner's plan?",
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
                "The final test should confirm that the learner stays in the model-selected difficulty lane.",
                test_seconds,
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
                "Rewards should reinforce the gameplay and learning progression together.",
                test_seconds,
            ),
        ]

    def _make_question(
        self,
        question_id: str,
        prompt: str,
        choices: list[str],
        correct_label: str,
        explanation: str,
        timer_seconds: int,
    ) -> dict:
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
            "timer_seconds": timer_seconds,
            "arena_title": "Final mastery check",
        }

    def _public_session(self, session: dict) -> dict:
        lesson = None
        question = None
        if session["phase"] == "learn" and session["lesson_index"] < len(session["lesson_cards"]):
            lesson = self._public_lesson(session["lesson_cards"][session["lesson_index"]])
        if session["phase"] == "assessment" and session["current_index"] < len(session["questions"]):
            question = self._public_question(session["questions"][session["current_index"]])

        return {
            "session_id": session["session_id"],
            "play_url": f"/games/{session['session_id']}",
            "status": session["status"],
            "phase": session["phase"],
            "game": session["game"],
            "learner": {
                "student_id": session["student_profile"]["student_id"],
                "name": session["student_profile"].get("name", "Learner"),
                "grade": session["student_profile"]["grade"],
            },
            "lesson": lesson,
            "question": question,
            "summary": session["summary"],
            "earned_badges": session["earned_badges"],
            "progress": self._progress(session),
        }

    def _public_lesson(self, lesson: dict) -> dict:
        return {
            "id": lesson["id"],
            "title": lesson["title"],
            "subtitle": lesson["subtitle"],
            "coach_line": lesson["coach_line"],
            "focus_points": lesson["focus_points"],
            "example": lesson["example"],
            "action_label": lesson["action_label"],
            "scene_title": lesson["scene_title"],
            "scene_tokens": lesson["scene_tokens"],
            "mechanic_type": lesson["mechanic_type"],
            "mechanic_prompt": lesson["mechanic_prompt"],
            "mechanic_options": lesson["mechanic_options"],
            "correct_option_id": lesson["correct_option_id"],
            "success_message": lesson["success_message"],
            "retry_message": lesson["retry_message"],
            "reward_badge": lesson["reward_badge"],
            "timer_seconds": lesson["timer_seconds"],
        }

    def _public_question(self, question: dict) -> dict:
        return {
            "id": question["id"],
            "prompt": question["prompt"],
            "choices": question["choices"],
            "timer_seconds": question["timer_seconds"],
            "arena_title": question["arena_title"],
        }

    def _progress(self, session: dict) -> dict:
        lesson_total = len(session["lesson_cards"])
        question_total = len(session["questions"])
        current_lesson = min(session["lesson_index"] + 1, lesson_total) if session["phase"] == "learn" else lesson_total
        current_round = 0
        if session["phase"] == "assessment":
            current_round = min(session["current_index"] + 1, question_total)
        elif session["phase"] == "completed":
            current_round = question_total

        return {
            "phase": session["phase"],
            "lessons_completed": min(session["lesson_index"], lesson_total),
            "total_lessons": lesson_total,
            "current_lesson": current_lesson,
            "current_round": current_round,
            "total_rounds": question_total,
            "score": session["score"],
            "max_score": session["max_score"],
            "badges_earned": len(session["earned_badges"]),
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
            "lessons_completed": len(session["lesson_history"]),
            "total_lessons": len(session["lesson_cards"]),
            "test_title": "Final learning check",
            "badges_earned": session["earned_badges"],
        }

    def _mechanic_title(self, mechanic_type: str) -> str:
        return {
            "choice_path": "Route Pick",
            "pattern_stack": "Pattern Stack",
            "signal_scan": "Signal Scan",
            "build_combo": "Build Combo",
        }.get(mechanic_type, mechanic_type.replace("_", " ").title())

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

    def _touch(self, session: dict, phase_reset: bool = False) -> None:
        now = datetime.now(timezone.utc)
        session["updated_at"] = now.isoformat()
        if phase_reset:
            session["phase_started_at"] = now.isoformat()
        session["expires_at"] = (now + timedelta(seconds=self.session_ttl_seconds)).isoformat()
