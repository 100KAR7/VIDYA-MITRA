# Deployment Guide for Vidya Mitra

Vidya Mitra is deployed as a Python web app. The primary runtime is `app.py`, which boots the Flask platform and serves the learner-facing UI from `frontend/`.

## Local Run

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Health Check

Use the built-in health endpoint after startup:

```text
GET /api/health
```

It reports environment, model readiness, storage readiness, and active game session count.

## Docker

Build and run the container from the repository root:

```bash
docker build -t vidya-mitra .
docker run -p 8080:8080 vidya-mitra
```

The container starts `waitress` with:

```text
app:app
```

## Procfile Platforms

The Procfile uses the same Flask entrypoint:

```text
web: waitress-serve --host=0.0.0.0 --port=$PORT app:app
```

This matches Railway, Render, and other process-based Python deployments.

## Environment Variables

Supported runtime variables are defined in `.env.example`.

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

## Optional Vite Preview

The root `package.json` is only for an optional React developer preview. It is not the production UI and does not replace the Flask-served platform.

```powershell
npm install
npm run dev
```

Use it only when you want a quick frontend health panel while the Flask API is running on port `5000`.
