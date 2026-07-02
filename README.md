# VIDYA-MITRA

Vidya Mitra is an adaptive learning platform that combines:

- a learner-facing Flask frontend
- prediction APIs backed by trained ML models
- launchable game sessions with lesson and assessment phases
- role-based access for students, teachers, and admins
- persistent learner progress and teacher analytics

## What Runs The Project

The main product runtime is:

- `app.py` for the Flask web platform

The ML workflow entrypoint is:

- `main.py` for dataset generation, preprocessing, training, evaluation, and prediction demos

The learner UI is served from:

- `frontend/index.html`
- `frontend/game.html`

## Run The Platform

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Run The ML Pipeline

```powershell
python main.py --mode all
python main.py --mode predict
```

## Tests

```powershell
python -m unittest tests.test_api_smoke
```

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

## Deployment

See `DEPLOYMENT.md` for Docker and process-based deployment details.

## Completion Roadmap

See `PROJECT_COMPLETION_PLAN.md` for the 4-step stabilization pattern, what was finished in this pass, and the next high-value improvements.
