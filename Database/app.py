"""Legacy SQLite example API kept as a small reference app."""

from pathlib import Path
import sqlite3

from flask import Flask, jsonify

app = Flask(__name__)
DB_PATH = Path(__file__).resolve().parent / "database" / "learning.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def home():
    return jsonify({"status": "API is running", "database": str(DB_PATH)})


@app.get("/courses")
def get_courses():
    with get_db() as db:
        courses = db.execute("SELECT * FROM courses").fetchall()
    return jsonify([dict(course) for course in courses])


if __name__ == "__main__":
    app.run(debug=True)
