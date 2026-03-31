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

SCENE_PACKS_BY_SUBJECT = {
    "Mathematics": {
        "palette": "mathematics",
        "world_name": "Arc Grid Harbor",
        "mentor_title": "Puzzle Navigator",
        "visual_tokens": ["Angle gates", "Grid rails", "Number lanterns"],
    },
    "Science": {
        "palette": "science",
        "world_name": "Discovery Lab Orbit",
        "mentor_title": "Lab Captain",
        "visual_tokens": ["Energy coils", "Test domes", "Signal scanners"],
    },
    "English": {
        "palette": "english",
        "world_name": "Story Bloom Library",
        "mentor_title": "Narrative Keeper",
        "visual_tokens": ["Story pages", "Word lanterns", "Clue shelves"],
    },
    "History": {
        "palette": "history",
        "world_name": "Chronicle Vault",
        "mentor_title": "Timeline Guide",
        "visual_tokens": ["Archive seals", "Era banners", "Artifact cases"],
    },
    "Geography": {
        "palette": "geography",
        "world_name": "Atlas Ridge",
        "mentor_title": "Expedition Scout",
        "visual_tokens": ["Compass towers", "Map rivers", "Terrain markers"],
    },
    "Computer_Science": {
        "palette": "computer_science",
        "world_name": "Code Circuit Hub",
        "mentor_title": "System Architect",
        "visual_tokens": ["Logic nodes", "Packet beams", "Pixel panels"],
    },
    "Hindi": {
        "palette": "hindi",
        "world_name": "Sahitya Courtyard",
        "mentor_title": "Bhasha Mentor",
        "visual_tokens": ["Script scrolls", "Poetry lamps", "Letter arches"],
    },
    "General_Knowledge": {
        "palette": "general_knowledge",
        "world_name": "World Pulse Arena",
        "mentor_title": "Quest Host",
        "visual_tokens": ["Signal globes", "Topic towers", "News banners"],
    },
}

MECHANIC_LINEUPS = {
    "repair_mission": ["signal_scan", "choice_path", "pattern_stack"],
    "card_match": ["pattern_stack", "signal_scan", "choice_path"],
    "spot_and_fix": ["signal_scan", "build_combo", "choice_path"],
    "guided_puzzle": ["choice_path", "pattern_stack", "build_combo"],
    "micro_quiz": ["choice_path", "signal_scan", "pattern_stack"],
    "level_path": ["choice_path", "pattern_stack", "signal_scan"],
    "logic_puzzle": ["pattern_stack", "build_combo", "choice_path"],
    "timed_challenge": ["signal_scan", "choice_path", "pattern_stack"],
    "tile_strategy": ["build_combo", "choice_path", "pattern_stack"],
    "creative_builder": ["build_combo", "signal_scan", "choice_path"],
    "boss_battle": ["choice_path", "build_combo", "signal_scan"],
    "strategy_map": ["choice_path", "pattern_stack", "build_combo"],
    "simulation_run": ["signal_scan", "build_combo", "pattern_stack"],
    "combo_challenge": ["pattern_stack", "choice_path", "signal_scan"],
    "multi_stage_quest": ["choice_path", "build_combo", "pattern_stack"],
}

BADGE_TRACKS = {
    "revision": [
        {"id": "repair-spark", "label": "Repair Spark", "description": "Completed the warm-up restore mission."},
        {"id": "focus-shield", "label": "Focus Shield", "description": "Stayed with the correct target topic."},
        {"id": "rebuild-star", "label": "Rebuild Star", "description": "Reached the final test with stronger confidence."},
    ],
    "practice": [
        {"id": "path-finder", "label": "Path Finder", "description": "Picked the right practice route."},
        {"id": "combo-crafter", "label": "Combo Crafter", "description": "Built a stable learning sequence."},
        {"id": "checkpoint-pro", "label": "Checkpoint Pro", "description": "Unlocked the assessment gate."},
    ],
    "mastery": [
        {"id": "elite-scout", "label": "Elite Scout", "description": "Entered the challenge lane with control."},
        {"id": "boss-ready", "label": "Boss Ready", "description": "Completed the high-pressure skill mechanic."},
        {"id": "crown-core", "label": "Crown Core", "description": "Reached the final mastery test."},
    ],
}

TIMER_PROFILES = {
    "revision": {"lesson_seconds": 45, "test_seconds": 30},
    "practice": {"lesson_seconds": 55, "test_seconds": 35},
    "mastery": {"lesson_seconds": 65, "test_seconds": 40},
}

DIFFICULTY_METER = {
    "easy": "Guided support lane",
    "medium": "Balanced practice lane",
    "hard": "High-pressure mastery lane",
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
        scene_pack = self._scene_pack(subject, theme)
        mechanic_lineup = MECHANIC_LINEUPS.get(game_type, ["choice_path", "pattern_stack", "signal_scan"])

        return {
            "game_variant_id": variant_id,
            "game_name": title,
            "game_type": game_type,
            "game_mode": mode,
            "theme": theme,
            "interaction_style": flavor,
            "learning_target": topic_label,
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
            "scene_pack": scene_pack,
            "mechanic_lineup": mechanic_lineup,
            "badge_track": BADGE_TRACKS[mode],
            "timer_profile": TIMER_PROFILES[mode],
            "difficulty_meter": DIFFICULTY_METER[difficulty],
            "boss_stage": f"{theme} Final Gate",
            "narrative_hook": (
                f"Enter {scene_pack['world_name']} and clear three mechanics before the final {topic_label} test."
            ),
        }

    def build_game_library(self, profile: Dict, outcome: Dict, count: int = 4) -> list[Dict]:
        subject = str(profile.get("subject", "General_Knowledge"))
        next_topic = str(outcome.get("next_topic", profile.get("topic", "General_Topic")))
        difficulty = str(outcome.get("recommended_difficulty", "medium"))
        success_band = str(outcome.get("success_probability_bin", "medium"))
        needs_revision = bool(outcome.get("needs_revision", False))
        learning_style = str(profile.get("learning_style", "visual"))
        device_type = str(profile.get("device_type", "mobile"))

        mode = self._select_mode(difficulty, success_band, needs_revision)
        theme_pool = THEMES_BY_SUBJECT.get(subject, THEMES_BY_SUBJECT["General_Knowledge"])
        style_pool = STYLE_FLAVORS.get(learning_style, STYLE_FLAVORS["visual"])
        topic_label = next_topic.replace("_", " ")
        subject_label = subject.replace("_", " ").lower()
        article = "an" if difficulty[:1].lower() in "aeiou" else "a"
        seed = self._seed(profile, outcome)
        theme_offset = seed % len(theme_pool)
        style_offset = seed % len(style_pool)

        cards = []
        for index in range(min(count, len(GAME_POOLS[mode]))):
            title_base, game_type = GAME_POOLS[mode][index]
            theme = theme_pool[(theme_offset + index) % len(theme_pool)]
            interaction_style = style_pool[(style_offset + index) % len(style_pool)]
            game_name = f"{theme} {title_base}"
            mechanic_lineup = MECHANIC_LINEUPS.get(game_type, ["choice_path", "pattern_stack", "signal_scan"])
            scene_pack = self._scene_pack(subject, theme)
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
                    "learning_objective": (
                        f"{OUTCOME_VERBS.get(difficulty, 'practise')} {topic_label} "
                        f"through {article} {difficulty} {subject_label} game."
                    ),
                    "adaptation_reason": (
                        f"Outcome stays focused on {topic_label} while gameplay shifts "
                        f"to a {interaction_style} experience suited for {DEVICE_MODES.get(device_type, 'guided rounds')}."
                    ),
                    "course_outcome": {
                        "current_topic": str(profile.get('topic', 'General_Topic')),
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
                    "scene_pack": scene_pack,
                    "mechanic_lineup": mechanic_lineup,
                    "badge_track": BADGE_TRACKS[mode],
                    "timer_profile": TIMER_PROFILES[mode],
                    "difficulty_meter": DIFFICULTY_METER[difficulty],
                    "boss_stage": f"{theme} Final Gate",
                    "narrative_hook": (
                        f"Enter {scene_pack['world_name']} and clear three mechanics before the final {topic_label} test."
                    ),
                    "progression_arc": self._progression_arc(mode, difficulty),
                    "launch_label": f"Launch {game_name}",
                    "mechanic_preview": [self._mechanic_label(item) for item in mechanic_lineup],
                    "badge_preview": [badge["label"] for badge in BADGE_TRACKS[mode][:2]],
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

    def _scene_pack(self, subject: str, theme: str) -> dict:
        base = dict(SCENE_PACKS_BY_SUBJECT.get(subject, SCENE_PACKS_BY_SUBJECT["General_Knowledge"]))
        base["world_name"] = f"{theme} {base['world_name']}"
        base["scene_caption"] = f"{theme} visual layer with {', '.join(base['visual_tokens'][:2]).lower()}."
        return base

    def _mechanic_label(self, mechanic: str) -> str:
        return {
            "choice_path": "route pick",
            "pattern_stack": "pattern stack",
            "signal_scan": "signal scan",
            "build_combo": "build combo",
        }.get(mechanic, mechanic.replace("_", " "))

    def _seed(self, profile: Dict, outcome: Dict) -> int:
        payload = "|".join(
            [
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
            ]
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def _variant_id(self, profile: Dict, outcome: Dict) -> str:
        payload = "|".join(
            [
                str(profile.get("student_id", "")),
                str(profile.get("subject", "")),
                str(profile.get("topic", "")),
                str(outcome.get("next_topic", "")),
                str(outcome.get("recommended_difficulty", "")),
            ]
        )
        return f"gv-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:10]}"
