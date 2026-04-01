"""
main.py  —  Master entry point

COMMANDS:
  python main.py --mode all        run everything (USE THIS FIRST TIME)
  python main.py --mode train      generate data + preprocess + train
  python main.py --mode evaluate   load saved models + plots + metrics
  python main.py --mode predict    run predictions on 5 demo students
  python main.py --mode tune       train with hyperparameter search (slow)
"""

import os
import sys
import argparse
import warnings
warnings.filterwarnings("ignore")

import pandas as pd

from utils.logger           import get_logger
from utils.helpers          import load_config
from data.generate_data     import StudentDataGenerator, export_schema
from preprocessing.pipeline import PreprocessingPipeline
from training.trainer       import Trainer
from training.evaluate      import Evaluator
from inference.predict      import Predictor

log = get_logger("vidya.main")

DEMO_STUDENTS = [
    {
        "_name": "Arjun - Top Scorer",
        "grade": "Grade_10", "subject": "Mathematics", "topic": "Algebra",
        "past_quiz_score_avg": 91.0, "accuracy_percentage": 88.5,
        "avg_response_time_sec": 18, "num_attempts": 1,
        "learning_streak_days": 28,  "engagement_score": 0.95,
        "hints_used": 0, "video_watch_pct": 80, "time_on_task_min": 45,
        "session_count_week": 7, "learning_style": "visual", "device_type": "laptop",
    },
    {
        "_name": "Priya - Struggling",
        "grade": "Grade_6", "subject": "Science", "topic": "Motion",
        "past_quiz_score_avg": 42.0, "accuracy_percentage": 38.0,
        "avg_response_time_sec": 95, "num_attempts": 5,
        "learning_streak_days": 2,   "engagement_score": 0.32,
        "hints_used": 7, "video_watch_pct": 20, "time_on_task_min": 55,
        "session_count_week": 2, "learning_style": "auditory", "device_type": "mobile",
    },
    {
        "_name": "Riya - Average",
        "grade": "Grade_8", "subject": "English", "topic": "Grammar",
        "past_quiz_score_avg": 67.0, "accuracy_percentage": 63.0,
        "avg_response_time_sec": 42, "num_attempts": 3,
        "learning_streak_days": 9,   "engagement_score": 0.62,
        "hints_used": 3, "video_watch_pct": 55, "time_on_task_min": 30,
        "session_count_week": 4, "learning_style": "reading_writing", "device_type": "tablet",
    },
    {
        "_name": "Dev - Consistent Learner",
        "grade": "Grade_12", "subject": "Computer_Science", "topic": "Algorithms",
        "past_quiz_score_avg": 85.0, "accuracy_percentage": 80.0,
        "avg_response_time_sec": 12, "num_attempts": 1,
        "learning_streak_days": 45,  "engagement_score": 0.88,
        "hints_used": 1, "video_watch_pct": 65, "time_on_task_min": 25,
        "session_count_week": 10, "learning_style": "kinesthetic", "device_type": "desktop",
    },
    {
        "_name": "Meera - Re-engaging",
        "grade": "Grade_9", "subject": "History", "topic": "Freedom_Movement",
        "past_quiz_score_avg": 55.0, "accuracy_percentage": 58.0,
        "avg_response_time_sec": 60, "num_attempts": 4,
        "learning_streak_days": 6,   "engagement_score": 0.55,
        "hints_used": 4, "video_watch_pct": 45, "time_on_task_min": 40,
        "session_count_week": 3, "learning_style": "visual", "device_type": "mobile",
    },
]


def step_generate(cfg) -> pd.DataFrame:
    print("\n" + "─"*55)
    print("  STEP 1 / 4  Generating Dataset")
    print("─"*55)
    for d in ["data/raw", "data/schemas", "data/processed"]:
        os.makedirs(d, exist_ok=True)
    gen = StudentDataGenerator(cfg)
    df  = gen.generate()
    df.to_csv(cfg["paths"]["raw_data"], index=False)
    export_schema(df, cfg["paths"]["schema"])
    print(f"  OK  {len(df):,} records -> {cfg['paths']['raw_data']}")
    return df


def step_preprocess(cfg, df: pd.DataFrame):
    print("\n" + "─"*55)
    print("  STEP 2 / 4  Preprocessing")
    print("─"*55)
    pipe   = PreprocessingPipeline(cfg)
    result = pipe.fit_transform(df)
    X, targets = result["X"], result["targets"]
    X.to_csv(cfg["paths"]["processed_data"], index=False)
    print(f"  OK  {df.shape[1]} -> {X.shape[1]} columns")
    print(f"  OK  Encoders -> {cfg['paths']['encoder_dir']}")
    return pipe, X, targets


def step_train(cfg, pipe, X: pd.DataFrame, targets: dict):
    print("\n" + "─"*55)
    print("  STEP 3 / 4  Training")
    print("─"*55)
    trainer = Trainer(cfg)
    metrics = trainer.train_all(X, targets)
    print(f"\n  Results:")
    print(f"  {'Target':<35} {'Acc':>8} {'F1':>8}")
    print(f"  {'─'*35} {'─'*8} {'─'*8}")
    for t, m in metrics.items():
        print(f"  {t:<35} {m['accuracy']:>8.4f} {m['f1_weighted']:>8.4f}")
    return trainer


def step_evaluate(cfg, trainer, pipe, X, targets):
    print("\n" + "─"*55)
    print("  STEP 4 / 4  Evaluation")
    print("─"*55)
    ev = Evaluator(cfg, pipe)
    ev.evaluate_all(trainer, X, targets)
    print(f"  OK  Plots   -> {cfg['paths']['plots_dir']}")
    print(f"  OK  Reports -> {cfg['paths']['reports_dir']}")


def step_predict():
    print("\n" + "─"*55)
    print("  INFERENCE DEMO  5 Student Profiles")
    print("─"*55)
    predictor = Predictor()

    for student in DEMO_STUDENTS:
        name = student.pop("_name")
        print(f"\n  {'='*50}")
        print(f"  {name}")
        print(f"  {student['grade']} | {student['subject']} | {student['topic']}")
        print(f"  Score={student['past_quiz_score_avg']} | "
              f"Acc={student['accuracy_percentage']}% | "
              f"Streak={student['learning_streak_days']}d")
        print(f"  {'─'*50}")

        r = predictor.predict(student, save=True)
        print(f"  Next Topic          : {r['next_recommended_topic']}")
        print(f"  Difficulty          : {r['recommended_difficulty'].upper()}")
        print(f"  Success Probability : {r['success_probability']:.1%} [{r['success_probability_label']}]")
        print(f"  Needs Revision      : {'YES' if r['needs_revision'] else 'NO'} [{r['revision_urgency']} urgency]")
        print(f"  Action              : {r['adaptive_action']}")
        student["_name"] = name


def main():
    parser = argparse.ArgumentParser(description="Vidya-Mitra ML Pipeline")
    parser.add_argument(
        "--mode",
        choices=["all", "train", "evaluate", "predict", "tune"],
        default="all",
    )
    args = parser.parse_args()

    for d in ["logs", "models/saved", "models/encoders",
              "outputs/plots", "outputs/reports", "outputs/predictions"]:
        os.makedirs(d, exist_ok=True)

    cfg = load_config()

    print(f"\n{'='*55}")
    print(f"  VIDYA-MITRA ADAPTIVE LEARNING ML")
    print(f"  Mode: {args.mode.upper()}")
    print(f"{'='*55}")

    df = pipe = X = targets = trainer = None

    if args.mode in ("all", "train", "tune"):
        df               = step_generate(cfg)
        pipe, X, targets = step_preprocess(cfg, df)
        trainer          = step_train(cfg, pipe, X, targets)

    if args.mode in ("all", "evaluate"):
        if trainer is None:
            trainer = Trainer(cfg)
            trainer.load_all()
        if pipe is None:
            pipe = PreprocessingPipeline(cfg)
            pipe.load()
        if X is None:
            X       = pd.read_csv(cfg["paths"]["processed_data"])
            targets = {}
        step_evaluate(cfg, trainer, pipe, X, targets)

    if args.mode in ("all", "predict"):
        step_predict()

    print(f"\n{'='*55}")
    print(f"  Done! Check outputs/ and models/ for results.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()