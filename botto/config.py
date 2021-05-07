import re
import os


def parse(config):

    defaults = {
        "id": None,
        "authentication": {
            "discord": "",
            "airtable_key": "",
            "airtable_base": "",
        },
        "rules": {
            "matching": [
                r"^.{5,240}$",  # Between 5 and 240 characters
                r"^(\S+\s+)\S+",  # At least two "words"
            ],
            "excluding": [
                r"<@.*>",  # Contains an @username reference
                r"^[\d\W\s]*$",  # Purely numeric or whitespace
            ],
        },
        "channels": {
            "include": [],
            "exclude": [],
        },
        "reactions": {
            "success": "📥",
            "repeat": "♻️",
            "unknown": "❓",
            "skynet": "👽",
            "fishing": "🎣",
            "invalid": "🙅",
            "pending": "⏳",
            "deleted": "🗑",
            "invalid_emoji": "⚠️",
            "valid_emoji": "✅",
            "reject": "❌",
            "poke": ["👈", "👆", "👇", "👉", "😢", "🤪", "😝"],
            "love": [
                "❤️",
                "💕",
                "♥️",
                "💖",
                "💙",
                "💗",
                "💜",
                "💞",
                "💛",
                "💚",
                "❣️",
                "🧡",
                "💘",
                "💝",
                "💟",
                "🤍",
                "🤎",
                "💌",
                "😍",
                "🥰",
            ],
            "rule_1": ["⚠️", "1️⃣", "⚠️"],
            "favorite_band": ["🇧", "🇹", "🇸"],
            "off_topic": ["😆", "🤣", "😂", "🤪"],
            "delete_confirmed": "✅",
        },
        "special_reactions": {},
        "triggers": {
            "new_motto": [],
        },
        "should_reply": True,
        "approval_reaction": "mottoapproval",
        "human_moderation_required": False,
        "leaderboard_link": None,
        "delete_unapproved_after_hours": 24,
        "trigger_on_mention": True,
        "confirm_delete_reaction": "🧨",
        "support_channel": None,
        "watching_status": "for inspiration",
        "baby": False,
    }

    for key in defaults.keys():
        if isinstance(defaults[key], dict):
            defaults[key].update(config.get(key, {}))
        else:
            defaults[key] = config.get(key, defaults[key])

    # Compile trigger regexes
    for key, triggers in defaults["triggers"].items():
        defaults["triggers"][key] = [
            re.compile(f"^{t}", re.IGNORECASE) for t in triggers
        ]

    # Compile rule regexes
    for key, rules in defaults["rules"].items():
        defaults["rules"][key] = [re.compile(r, re.MULTILINE) for r in rules]

    # Environment variables override config files

    if token := os.getenv("MOTTOBOTTO_DISCORD_TOKEN"):
        defaults["authentication"]["discord"] = token

    if token := os.getenv("MOTTOBOTTO_AIRTABLE_KEY"):
        defaults["authentication"]["airtable_key"] = token

    if token := os.getenv("MOTTOBOTTO_AIRTABLE_BASE"):
        defaults["authentication"]["airtable_base"] = token

    return defaults
