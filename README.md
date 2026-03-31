# VIDYA-MITRA

Vidya Mitra is now structured as a complete MVP that combines:

- a frontend learner dashboard,
- a backend prediction API,
- and the trained ML recommendation models already stored in `models/`.

## What the MVP does

The system takes a learner profile and predicts:

- the next recommended topic,
- the recommended difficulty,
- the success probability band,
- whether revision is needed.

Then it adds a game-personalization layer so each child can receive a fresh game variant while the course outcome stays aligned.

## Run the MVP

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the app:

```bash
python app.py
```

3. Open the local URL shown by Flask in your browser.

## Main paths

- `app.py` starts the MVP.
- `backend/app.py` serves the backend API and the frontend.
- `frontend/index.html` is the learner-facing UI.
- `frontend/assets/app.js` connects the form to the backend.
- `inference/predict.py` loads the trained models and returns predictions.
- `inference/game_selector.py` creates a unique game wrapper for the same learning target.
