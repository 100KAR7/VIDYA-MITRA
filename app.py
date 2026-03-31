from backend.app import create_app

app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)
DB_PATH = "database/learning.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn

# Test route — visit this in browser to confirm it works
@app.route("/")
def home():
    return jsonify({"status": "API is running"})

# Get all courses
@app.route("/courses")
def get_courses():
    db = get_db()
    courses = db.execute("SELECT * FROM courses").fetchall()
    return jsonify([dict(c) for c in courses])

if __name__ == "__main__":
    app.run(debug=True)
'''
Run it:
```
python app.py
```

Open your browser and go to `http://localhost:5000` — you should see `{"status": "API is running"}`.

---

## Step 5 — Connect your mobile app

For the mobile front-end you have two beginner-friendly options:

| Option | Best if you... |
|---|---|
| **FlutterFlow** (no-code) | Want to drag and drop UI, no Flutter experience |
| **MIT App Inventor** | Complete beginner, just want it to work |
| **React Native** | Comfortable learning JS alongside Python |

The Flask API you just built works with any of these — they all make HTTP requests to your `localhost` (or a hosted server later).

---

## What you have now
```
learning-app/
├── database/
│   └── learning.db   ← all 11 tables live here
└── app.py            ← your Python API'''
