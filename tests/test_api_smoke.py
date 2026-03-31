import os
import tempfile
import unittest

from backend.app import create_app


class PlatformAPISmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.app = create_app(
            runtime_overrides={
                "testing": True,
                "debug": False,
                "platform_store_path": os.path.join(self.tmpdir.name, "platform_store.db"),
                "prediction_logging_enabled": False,
                "secret_key": "test-secret-key",
                "session_ttl_seconds": 300,
            }
        )
        self.client = self.app.test_client()
        self.teacher_token = self._login("teacher", "teacher-1", "Teacher One")
        self.student_token = self._login("student", "student-1", "Student One")
        self.student_payload = {
            "student_id": "student-1",
            "name": "Student One",
            "grade": "Grade_7",
            "subject": "Mathematics",
            "topic": "Algebra",
            "past_quiz_score_avg": 71.0,
            "accuracy_percentage": 68.0,
            "avg_response_time_sec": 35.0,
            "num_attempts": 2,
            "learning_streak_days": 8,
            "engagement_score": 0.74,
            "hints_used": 1,
            "video_watch_pct": 62.0,
            "time_on_task_min": 28.0,
            "session_count_week": 4,
            "learning_style": "visual",
            "device_type": "tablet",
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_teacher_flow_records_prediction_and_game_results(self):
        prediction = self._predict(self.teacher_token, self.student_payload)

        launch_response = self.client.post(
            "/api/games/launch",
            json={
                "student_profile": self.student_payload,
                "prediction": prediction,
                "game": prediction["game_library"][0],
            },
            headers=self._auth_header(self.teacher_token),
        )
        self.assertEqual(launch_response.status_code, 200)
        session = launch_response.get_json()
        self.assertIn("play_url", session)
        self.assertEqual(session["phase"], "learn")
        self.assertIn("lesson", session)
        self.assertIn("game", session)

        session_state = self.client.get(
            f"/api/games/session/{session['session_id']}",
            headers=self._auth_header(self.teacher_token),
        )
        self.assertEqual(session_state.status_code, 200)
        session = session_state.get_json()
        self.assertEqual(session["phase"], "learn")
        self.assertEqual(len(session["game"]["badge_track"]), 3)

        for expected_badges in range(1, 4):
            learn_response = self.client.post(
                f"/api/games/session/{session['session_id']}/learn",
                json={"selection_id": session["lesson"]["correct_option_id"]},
                headers=self._auth_header(self.teacher_token),
            )
            self.assertEqual(learn_response.status_code, 200)
            session = learn_response.get_json()
            self.assertEqual(len(session["earned_badges"]), expected_badges)

        self.assertEqual(session["phase"], "assessment")
        final_payload = None
        while final_payload is None or not final_payload["completed"]:
            answer_response = self.client.post(
                f"/api/games/session/{session['session_id']}/answer",
                json={
                    "choice_id": session["question"]["choices"][0]["id"],
                },
                headers=self._auth_header(self.teacher_token),
            )
            self.assertEqual(answer_response.status_code, 200)
            final_payload = answer_response.get_json()
            if not final_payload["completed"]:
                session = final_payload["session"]

        self.assertEqual(final_payload["summary"]["badges_earned"][0]["status"], "mastered")
        self.assertEqual(len(final_payload["summary"]["badges_earned"]), 3)

        progress_response = self.client.get(
            f"/api/progress/{self.student_payload['student_id']}",
            headers=self._auth_header(self.teacher_token),
        )
        self.assertEqual(progress_response.status_code, 200)
        progress = progress_response.get_json()
        self.assertEqual(progress["total_predictions"], 1)
        self.assertEqual(progress["total_sessions"], 1)

        dashboard_response = self.client.get("/api/dashboard/teacher", headers=self._auth_header(self.teacher_token))
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.get_json()
        self.assertGreaterEqual(dashboard["total_predictions"], 1)
        self.assertGreaterEqual(dashboard["total_game_sessions"], 1)

    def test_student_cannot_access_another_student_profile(self):
        response = self.client.get("/api/progress/student-2", headers=self._auth_header(self.student_token))
        self.assertEqual(response.status_code, 403)

    def test_missing_token_is_rejected(self):
        response = self.client.post("/api/predict", json=self.student_payload)
        self.assertEqual(response.status_code, 401)

    def _login(self, role: str, user_id: str, display_name: str) -> str:
        response = self.client.post(
            "/api/auth/login",
            json={"role": role, "user_id": user_id, "display_name": display_name},
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()["access_token"]

    def _predict(self, token: str, student_payload: dict) -> dict:
        response = self.client.post(
            "/api/predict",
            json={"student_profile": student_payload},
            headers=self._auth_header(token),
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    @staticmethod
    def _auth_header(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    unittest.main()
