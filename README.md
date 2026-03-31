# VIDYA-MITRA

Vidya Mitra is an adaptive learning platform that combines:

- a learner-facing frontend
- a Flask API backend
- trained ML recommendation models
- a game center with launchable learning sessions
- role-based access for students, teachers, and admins
- persistent learner progress and teacher analytics

## Production Features

- bearer-token authentication for protected API routes
- request validation and consistent API error responses
- SQLite-backed persistence instead of in-memory JSON state
- game session TTL and capacity limits
- production-safe startup with `waitress`
- rotating log files and environment-based runtime settings
- smoke tests for login, prediction, gameplay, progress, and dashboard flows

## Run

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Environment

Copy the values you need from `.env.example` into your runtime environment.

- `VIDYA_ENV`
- `VIDYA_HOST`
- `VIDYA_PORT`
- `VIDYA_DEBUG`
- `VIDYA_SECRET_KEY`
- `VIDYA_PLATFORM_STORE`
- `VIDYA_AUTH_TOKEN_TTL_SECONDS`
- `VIDYA_SESSION_TTL_SECONDS`
- `VIDYA_MAX_LIVE_SESSIONS`
- `VIDYA_SAVE_PREDICTIONS`
- `VIDYA_WAITRESS_THREADS`
- `VIDYA_LOG_LEVEL`
- `VIDYA_LOG_DIR`

## Tests

```powershell
python -m unittest tests.test_api_smoke
```

## Main Paths

- `app.py`
- `backend/app.py`
- `backend/auth.py`
- `backend/errors.py`
- `backend/game_service.py`
- `backend/platform_store.py`
- `backend/runtime.py`
- `backend/validators.py`
- `frontend/index.html`
- `frontend/assets/app.js`
- `frontend/assets/styles.css`
- `inference/predict.py`
- `inference/game_selector.py`
