import hashlib
import random
from typing import Dict

GAME_POOLS = {
    "revision": [
        ("Concept Rescue", "repair_mission"),
        ("Memory Builder", "card_match"),
        ("Mistake Detective", "spot_and_fix"),
        ("Skill Repair Lab", "guided_puzzle"),
        ("Checkpoint Coach", "micro_quiz"),
    ],
    "practice": [
        ("Quest Trail", "level_path"),
        ("Puzzle Forge", "logic_puzzle"),
        ("Skill Sprint", "timed_challenge"),
        ("Adventure Grid", "tile_strategy"),
        ("Challenge Studio", "creative_builder"),
    ],
    "mastery": [
        ("Champion Arena", "boss_battle"),
        ("Mission Atlas", "strategy_map"),
        ("Elite Lab", "simulation_run"),
        ("Victory Circuit", "combo_challenge"),
        ("Discovery Tower", "multi_stage_quest"),
    ],
}

THEMES_BY_SUBJECT = {
    "Mathematics": ["Treasure", "Space", "Robot", "Temple", "City"],
    "Science": ["Lab", "Space", "Eco", "Inventor", "Galaxy"],
    "English": ["Story", "Library", "Mystery", "Kingdom", "Studio"],
    "History": ["Timeline", "Museum", "Empire", "Archive", "Voyage"],
    "Geography": ["Explorer", "Atlas", "Expedition", "Planet", "Compass"],
    "Computer_Science": ["Code", "Cyber", "Robot", "Network", "Pixel"],
    "Hindi": ["Kahani", "Sahitya", "Kala", "Pathshala", "Manch"],
    "General_Knowledge": ["Quiz", "World", "Newsroom", "Explorer", "Summit"],
}

STYLE_FLAVORS = {
    "visual": ["map-based", "color-led", "icon-guided"],
    "auditory": ["rhythm-led", "voice-cue", "sound-prompted"],
    "reading_writing": ["story-card", "notebook", "text-clue"],
    "kinesthetic": ["drag-and-drop", "tap-to-build", "movement-led"],
}

DEVICE_MODES = {
    "mobile": "short touch rounds",
    "tablet": "interactive gesture rounds",
    "laptop": "extended keyboard-mouse rounds",
    "desktop": "full precision challenge rounds",
}

OUTCOME_VERBS = {
    "easy": "build confidence in",
    "medium": "practise",
    "hard": "master",
}

SESSION_LENGTHS = {
    "revision": "8-10 min",
    "practice": "12-15 min",
    "mastery": "15-18 min",
}

REWARD_LOOPS = {
    "revision": "repair stars and hint boosts",
    "practice": "streak gems and combo badges",
    "mastery": "boss keys and mastery crowns",
}


class GameVariantRecommender:
    def recommend(self, profile: Dict, outcome: Dict) -> Dict:
        current_topic = str(profile.get("topic", "General_Topic"))
        subject = str(profile.get("subject", "General_Knowledge"))
        next_topic = str(outcome.get("next_topic", current_topic))
        difficulty = str(outcome.get("recommended_difficulty", "medium"))
        success_band = str(outcome.get("success_probability_bin", "medium"))
        needs_revision = bool(outcome.get("needs_revision", False))
        learning_style = str(profile.get("learning_style", "visual"))
        device_type = str(profile.get("device_type", "mobile"))

        mode = self._select_mode(difficulty, success_band, needs_revision)
        rng = random.Random(self._seed(profile, outcome))

        theme = rng.choice(THEMES_BY_SUBJECT.get(subject, THEMES_BY_SUBJECT["General_Knowledge"]))
        title_base, game_type = rng.choice(GAME_POOLS[mode])
        flavor = rng.choice(STYLE_FLAVORS.get(learning_style, STYLE_FLAVORS["visual"]))
        variant_id = self._variant_id(profile, outcome)
        title = f"{theme} {title_base}"
        subject_label = subject.replace("_", " ").lower()
        topic_label = next_topic.replace("_", " ")
        article = "an" if difficulty[:1].lower() in "aeiou" else "a"

        return {
            "game_variant_id": variant_id,
            "game_name": title,
            "game_type": game_type,
            "game_mode": mode,
            "theme": theme,
            "interaction_style": flavor,
            "learning_objective": (
                f"{OUTCOME_VERBS.get(difficulty, 'practise')} {topic_label} "
                f"through {article} {difficulty} {subject_label} game."
            ),
            "adaptation_reason": (
                f"Outcome stays focused on {topic_label} while gameplay shifts "
                f"to a {flavor} experience suited for {DEVICE_MODES.get(device_type, 'guided rounds')}."
            ),
            "course_outcome": {
                "current_topic": current_topic,
                "target_topic": next_topic,
                "recommended_difficulty": difficulty,
                "success_probability_label": success_band,
                "needs_revision": needs_revision,
            },
            "content_rules": [
                "Keep the same target topic and curriculum objective.",
                "Change only the game skin, mechanics, and presentation style.",
                "Match question difficulty to the predicted learner level.",
            ],
            "session_length": SESSION_LENGTHS[mode],
            "reward_loop": REWARD_LOOPS[mode],
            "headline": f"{topic_label} mission for {difficulty.upper()} readiness",
        }

    def build_game_library(self, profile: Dict, outcome: Dict, count: int = 4) -> list[Dict]:
        subject = str(profile.get("subject", "General_Knowledge"))
        next_topic = str(outcome.get("next_topic", profile.get("topic", "General_Topic")))
        difficulty = str(outcome.get("recommended_difficulty", "medium"))
        success_band = str(outcome.get("success_probability_bin", "medium"))
        needs_revision = bool(outcome.get("needs_revision", False))
        learning_style = str(profile.get("learning_style", "visual"))

        mode = self._select_mode(difficulty, success_band, needs_revision)
        theme_pool = THEMES_BY_SUBJECT.get(subject, THEMES_BY_SUBJECT["General_Knowledge"])
        style_pool = STYLE_FLAVORS.get(learning_style, STYLE_FLAVORS["visual"])
        topic_label = next_topic.replace("_", " ")
        seed = self._seed(profile, outcome)
        theme_offset = seed % len(theme_pool)
        style_offset = seed % len(style_pool)

        cards = []
        for index in range(min(count, len(GAME_POOLS[mode]))):
            title_base, game_type = GAME_POOLS[mode][index]
            theme = theme_pool[(theme_offset + index) % len(theme_pool)]
            interaction_style = style_pool[(style_offset + index) % len(style_pool)]
            game_name = f"{theme} {title_base}"
            cards.append(
                {
                    "slot": index + 1,
                    "status": "Primary" if index == 0 else "Alternative",
                    "game_variant_id": f"{self._variant_id(profile, outcome)}-{index + 1}",
                    "game_name": game_name,
                    "game_type": game_type,
                    "game_mode": mode,
                    "theme": theme,
                    "interaction_style": interaction_style,
                    "learning_target": topic_label,
                    "session_length": SESSION_LENGTHS[mode],
                    "reward_loop": REWARD_LOOPS[mode],
                    "progression_arc": self._progression_arc(mode, difficulty),
                    "launch_label": f"Launch {game_name}",
                }
            )
        return cards

    def _progression_arc(self, mode: str, difficulty: str) -> str:
        if mode == "revision":
            return f"Warm-up -> repair -> confidence rebuild ({difficulty})"
        if mode == "mastery":
            return f"Challenge lane -> boss round -> mastery unlock ({difficulty})"
        return f"Guided practice -> combo streak -> checkpoint clear ({difficulty})"

    def _select_mode(self, difficulty: str, success_band: str, needs_revision: bool) -> str:
        if needs_revision:
            return "revision"
        if difficulty == "hard" or success_band == "high":
            return "mastery"
        return "practice"

    def _seed(self, profile: Dict, outcome: Dict) -> int:
        payload = "|".join([
            str(profile.get("student_id", "")),
            str(profile.get("grade", "")),
            str(profile.get("subject", "")),
            str(profile.get("topic", "")),
            str(profile.get("learning_style", "")),
            str(profile.get("device_type", "")),
            str(outcome.get("next_topic", "")),
            str(outcome.get("recommended_difficulty", "")),
            str(outcome.get("success_probability_bin", "")),
            str(outcome.get("needs_revision", "")),
        ])
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def _variant_id(self, profile: Dict, outcome: Dict) -> str:
        payload = "|".join([
            str(profile.get("student_id", "")),
            str(profile.get("subject", "")),
            str(profile.get("topic", "")),
            str(outcome.get("next_topic", "")),
            str(outcome.get("recommended_difficulty", "")),
        ])
        return f"gv-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:10]}"
