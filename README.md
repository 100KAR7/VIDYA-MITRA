# VIDYA-MITRA

**Vidya Mitra** is a complete adaptive learning platform with:

- learner-facing frontend (HTML+JS) and Flask API backend
- end-to-end ML pipeline (data, preprocessing, training, inference)
- rank/retention prediction, difficulty estimation, and revision recommendations
- game recommendation engine (adaptive learning sessions)
- persistence layer (SQLite via backend platform store)
- production-ready deployment with `waitress`, logging, env-based settings, and CI smoke tests

---
## Contributors 
- SUSHRUTA KAR(## ML MODEL )
- ARMAN PANDA(## BACKEND )
- RASHMI ANAND (## BACKEND )
- DEBASISH DAS(## FRONTEND)

## 📦 Project Structure

- `app.py` - root starter for API service (runtime settings, waitress fallback)
- `backend/` - domain layer, auth, game service, validators, routes
- `inference/` - `predictor` and game strategy logic
- `preprocessing/` - feature engineering, encoders, artifacts
- `training/` - model training + evaluation and persistence
- `data/` - synthetic dataset generation and schema
- `models/` - saved model + encoder artifacts
- `outputs/` - evaluation plots and reports
- `tests/` - smoke tests for API correctness

---

## 🚀 Quick Start

```powershell
# 1. Create virtual env (strongly recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Bootstrap full pipeline
python main.py --mode all

# 4. Run API server
python app.py
```

Then open `http://127.0.0.1:5000` and `http://127.0.0.1:5000/api/predict` with a JSON payload.

---

## 🧠 Pipeline Modes

- `--mode all` = generate+preprocess+train+evaluate+predict demo
- `--mode train` = data + preprocess + train
- `--mode evaluate` = load model + evaluate metrics & plots
- `--mode predict` = demo inference on preset profiles
- `--mode tune` = hyperparameter search (may require config updates)

### Example

```powershell
python main.py --mode train
python main.py --mode evaluate
python main.py --mode predict
```

---

## 🧪 Tests

```powershell
python -m unittest tests.test_api_smoke
```

---

## 💾 Artifact paths

After training (`main.py --mode all`), these assets should exist:

- `models/encoders/num_imputer.pkl`
- `models/encoders/cat_imputer.pkl`
- `models/encoders/scaler.pkl`
- `models/encoders/ord_encoder.pkl`
- `models/encoders/target_encoders.pkl`
- `models/encoders/freq_maps.pkl`
- `models/encoders/clip_bounds.pkl`
- `models/encoders/feature_cols.pkl`
- `models/saved/xgb_next_topic.pkl`
- `models/saved/xgb_recommended_difficulty.pkl`
- `models/saved/xgb_success_probability_bin.pkl`
- `models/saved/xgb_needs_revision.pkl`

---

## 🐞 Troubleshooting

### FileNotFoundError: models/encoders/num_imputer.pkl

Run:

```powershell
python main.py --mode all
```

If still missing, verify `config/config.yaml` has `paths.encoder_dir: models/encoders/` and folder is writable.

### NameError: os in main.py

Ensure `main.py` imports `os` at top and the first blocks are not duplicated.

### TypeError trainer.train_all unexpected keyword 'tune'

`main.py` now uses `trainer.train_all(X, targets)`.

---

## 📈 Evaluation visuals

During `--mode all` and `--mode evaluate`, chart images are saved under:

- `outputs/plots/confusion_matrix_namedtarget.png`
- `outputs/reports/modeled_performance.png`
- `outputs/reports/training_metrics.json`

> For inline README preview, open these generated images from the file browser or your chosen markdown viewer.

---

## 💬 API Inference Example

POST `http://127.0.0.1:5000/api/predict`

```json
{
  "grade": "Grade_10",
  "subject": "Mathematics",
  "topic": "Algebra",
  "past_quiz_score_avg": 82.3,
  "accuracy_percentage": 77.4,
  "avg_response_time_sec": 26,
  "num_attempts": 2,
  "learning_streak_days": 14,
  "engagement_score": 0.80,
  "hints_used": 2,
  "video_watch_pct": 67,
  "time_on_task_min": 37,
  "session_count_week": 6,
  "learning_style": "visual",
  "device_type": "laptop"
}
```

Response includes:
- `next_recommended_topic`
- `recommended_difficulty`
- `success_probability`
- `needs_revision`
- `recommended_game`
- `confidence_scores`

---

## 🛠️ Environment variables

See `.env.example`; common defaults:

```ini
VIDYA_ENV=development
VIDYA_HOST=0.0.0.0
VIDYA_PORT=5000
VIDYA_DEBUG=True
VIDYA_SECRET_KEY=change-me
VIDYA_WAITRESS_THREADS=4
VIDYA_LOG_LEVEL=INFO
VIDYA_LOG_DIR=logs/
VIDYA_PREDICTION_LOGGING=False
```

---

## 📝 Contribution

1. fork repository
2. create branch `feature/<name>`
3. add tests under `tests/`
4. run `python -m unittest tests.test_api_smoke`
5. open PR with description + reproducer

---

## 🧾 Notes

- Already working with Python 3.10+ and `xgboost` (fallback to `sklearn` when missing)
- `inference/predict.py` requires `models/encoders/*` + `models/saved/*`
- production run: `gunicorn app:app -w 4 -b 0.0.0.0:5000` or via Docker with `waitress`

