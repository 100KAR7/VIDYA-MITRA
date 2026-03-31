"""
data/generate_data.py
PURPOSE : Build a synthetic student dataset for training.

WHY SYNTHETIC DATA?
  No real data yet. Synthetic data lets us build and test the full
  pipeline. When real data is available, replace data/raw/students.csv
  with the same column names — nothing else changes.

WHAT ONE ROW REPRESENTS:
  One student at the end of one study session on one topic.

TARGETS CREATED (columns the model predicts):
  next_topic               - which topic to do next
  recommended_difficulty   - easy / medium / hard
  success_probability_bin  - low / medium / high
  needs_revision           - 0 or 1

RUN STANDALONE:
  python data/generate_data.py
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.logger  import get_logger
from utils.helpers import load_config, save_json

log = get_logger("vidya.data_gen")

# Topic curriculum graph — key=current topic, value=what comes next
TOPIC_GRAPH = {
    "Fractions":         ["Algebra",          "Number_Theory"],
    "Algebra":           ["Geometry",         "Statistics"],
    "Geometry":          ["Trigonometry",      "Statistics"],
    "Statistics":        ["Calculus",          "Algebra"],
    "Trigonometry":      ["Calculus",          "Geometry"],
    "Calculus":          ["Statistics",        "Number_Theory"],
    "Number_Theory":     ["Algebra",           "Statistics"],
    "Motion":            ["Electricity",       "Light_Optics"],
    "Electricity":       ["Chemical_Reactions","Light_Optics"],
    "Chemical_Reactions":["Cells_Biology",     "Periodic_Table"],
    "Cells_Biology":     ["Ecosystems",        "Periodic_Table"],
    "Light_Optics":      ["Electricity",       "Chemical_Reactions"],
    "Ecosystems":        ["Cells_Biology",     "Chemical_Reactions"],
    "Periodic_Table":    ["Chemical_Reactions","Electricity"],
    "Grammar":           ["Comprehension",     "Vocabulary"],
    "Comprehension":     ["Essay_Writing",     "Literature"],
    "Vocabulary":        ["Grammar",           "Essay_Writing"],
    "Essay_Writing":     ["Literature",        "Poetry"],
    "Poetry":            ["Literature",        "Comprehension"],
    "Literature":        ["Essay_Writing",     "Comprehension"],
    "Ancient_India":     ["Medieval_Period",   "Freedom_Movement"],
    "Medieval_Period":   ["Freedom_Movement",  "World_Wars"],
    "Freedom_Movement":  ["Post_Independence", "World_Wars"],
    "World_Wars":        ["Post_Independence", "Freedom_Movement"],
    "Post_Independence": ["Freedom_Movement",  "World_Wars"],
    "Physical_Geography":["Climate",           "Resources"],
    "Climate":           ["Resources",         "Population"],
    "Resources":         ["Population",        "Maps_Cartography"],
    "Population":        ["Maps_Cartography",  "Climate"],
    "Maps_Cartography":  ["Physical_Geography","Resources"],
    "Python_Basics":     ["Data_Structures",   "Algorithms"],
    "Algorithms":        ["Data_Structures",   "Networking"],
    "Data_Structures":   ["Algorithms",        "Databases"],
    "Networking":        ["Databases",         "Web_Development"],
    "Databases":         ["Web_Development",   "Networking"],
    "Web_Development":   ["Networking",        "Databases"],
    "Vyakaran":          ["Kavita",            "Gadya"],
    "Kavita":            ["Gadya",             "Patra_Lekhan"],
    "Gadya":             ["Kavita",            "Patra_Lekhan"],
    "Patra_Lekhan":      ["Vyakaran",          "Gadya"],
    "Current_Affairs":   ["Sports",            "Science_Tech"],
    "Sports":            ["Current_Affairs",   "Awards"],
    "Science_Tech":      ["Current_Affairs",   "Awards"],
    "Awards":            ["Science_Tech",      "Sports"],
}


class StudentDataGenerator:

    def __init__(self, cfg: dict):
        self.cfg    = cfg
        self.domain = cfg["domain"]
        self.rng    = np.random.default_rng(cfg["dataset"]["random_seed"])

    def generate(self, n: int = None) -> pd.DataFrame:
        n = n or self.cfg["dataset"]["n_samples"]
        log.info(f"Generating {n} student records ...")
        rows = [self._make_row() for _ in range(n)]
        df   = pd.DataFrame(rows)
        df   = self._attach_targets(df)
        df   = self._inject_missingness(df, rate=0.025)
        log.info(f"Done: {df.shape[0]} rows x {df.shape[1]} cols | "
                 f"null cells: {df.isnull().sum().sum()}")
        return df

    def _make_row(self) -> dict:
        grade   = self.rng.choice(self.domain["grades"])
        subject = self.rng.choice(self.domain["subjects"])
        topic   = self.rng.choice(self._get_topics(subject))
        g_num   = int(grade.split("_")[1])

        base_score    = float(np.clip(40 + g_num * 3.5 + self.rng.normal(0, 12), 0, 100))
        accuracy      = float(np.clip(base_score / 100 * 0.92 + self.rng.normal(0, 0.07), 0.05, 1.0))
        response_time = float(np.clip(130 - g_num * 6 + self.rng.normal(0, 18), 5, 180))
        streak        = int(np.clip(self.rng.exponential(scale=8), 0, 60))
        attempts      = int(np.clip(1 + int((1 - accuracy) * 5) + self.rng.integers(0, 3), 1, 15))
        hints         = int(np.clip(int((1 - accuracy) * 4) + self.rng.integers(0, 3), 0, 10))
        vid_pct       = float(np.clip(accuracy * 75 + self.rng.normal(0, 12), 0, 100))
        eng           = float(np.clip(
            0.35 * accuracy + 0.25 * (streak / 60) +
            0.25 * (vid_pct / 100) + 0.15 * (1 - hints / 10) +
            self.rng.normal(0, 0.04), 0.0, 1.0
        ))
        time_min  = float(np.clip(10 + attempts * 5 + self.rng.normal(0, 6), 5, 90))
        sess_week = int(np.clip(int(streak / 7 * 3) + self.rng.integers(1, 4), 1, 21))

        return {
            "student_id":            f"S{self.rng.integers(100_000, 999_999)}",
            "grade":                 grade,
            "subject":               subject,
            "topic":                 topic,
            "learning_style":        self.rng.choice(self.domain["learning_styles"]),
            "device_type":           self.rng.choice(self.domain["device_types"]),
            "past_quiz_score_avg":   round(base_score, 2),
            "accuracy_percentage":   round(accuracy * 100, 2),
            "avg_response_time_sec": round(response_time, 1),
            "num_attempts":          attempts,
            "learning_streak_days":  streak,
            "engagement_score":      round(eng, 4),
            "hints_used":            hints,
            "video_watch_pct":       round(vid_pct, 2),
            "time_on_task_min":      round(time_min, 1),
            "session_count_week":    sess_week,
        }

    def _attach_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["next_topic"] = df["topic"].apply(
            lambda t: self.rng.choice(TOPIC_GRAPH.get(t, [t]))
        )
        df["recommended_difficulty"]  = df.apply(self._difficulty_rule, axis=1)
        df["success_probability_bin"] = df.apply(self._success_rule,    axis=1)
        df["needs_revision"]          = df.apply(self._revision_rule,   axis=1)
        return df

    def _difficulty_rule(self, r) -> str:
        mastery = (
            0.45 * (r["past_quiz_score_avg"] / 100) +
            0.35 * (r["accuracy_percentage"] / 100) +
            0.20 * min(r["learning_streak_days"] / 60, 1.0)
        ) + self.rng.normal(0, 0.04)
        if mastery >= 0.72: return "hard"
        if mastery >= 0.44: return "medium"
        return "easy"

    def _success_rule(self, r) -> str:
        p = (
            0.40 * (r["accuracy_percentage"] / 100) +
            0.35 * (r["past_quiz_score_avg"]  / 100) +
            0.25 * r["engagement_score"]
        ) + self.rng.normal(0, 0.04)
        if p >= 0.72: return "high"
        if p >= 0.44: return "medium"
        return "low"

    def _revision_rule(self, r) -> int:
        flags = sum([
            r["accuracy_percentage"]   < 55,
            r["past_quiz_score_avg"]   < 50,
            r["num_attempts"]          >= 4,
            r["hints_used"]            >= 4,
            r["avg_response_time_sec"] > 85,
            r["engagement_score"]      < 0.40,
        ])
        noise = int(self.rng.integers(0, 2))
        return int((flags + noise) >= 3)

    def _get_topics(self, subject: str) -> list:
        return self.cfg["domain"]["topics_by_subject"].get(subject, ["General_Topic"])

    def _inject_missingness(self, df: pd.DataFrame, rate: float) -> pd.DataFrame:
        skip = {"student_id", "next_topic", "recommended_difficulty",
                "success_probability_bin", "needs_revision"}
        for col in df.columns:
            if col not in skip:
                mask = self.rng.random(len(df)) < rate
                df.loc[mask, col] = np.nan
        return df


def export_schema(df: pd.DataFrame, path: str):
    schema = {
        "rows": len(df),
        "columns": {
            col: {
                "dtype":    str(df[col].dtype),
                "null_pct": round(df[col].isnull().mean() * 100, 2),
                "examples": [str(v) for v in df[col].dropna().unique()[:5].tolist()]
            }
            for col in df.columns
        }
    }
    save_json(schema, path)
    log.info(f"Schema saved -> {path}")


if __name__ == "__main__":
    cfg = load_config()
    gen = StudentDataGenerator(cfg)
    df  = gen.generate()
    os.makedirs("data/raw",    exist_ok=True)
    os.makedirs("data/schemas",exist_ok=True)
    df.to_csv(cfg["paths"]["raw_data"], index=False)
    export_schema(df, cfg["paths"]["schema"])
    print(f"Shape: {df.shape}")
    for t in ["recommended_difficulty", "success_probability_bin", "needs_revision"]:
        print(f"  {t}: {df[t].value_counts().to_dict()}")