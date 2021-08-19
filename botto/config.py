import base64
import binascii
import json
import logging
import re
import os

import food

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def decode_base64_env(key: str):
    if meals := os.getenv(key):
        decoded = None
        try:
            decoded = base64.b64decode(meals)
            return json.loads(decoded)
        except binascii.Error:
            log.error(f"Unable to decode base64 {key} config", exc_info=True)
            raise
        except json.JSONDecodeError as error:
            log.error(f"Unable to parse decoded {key} config: {error}", exc_info=True)
            if decoded:
                log.debug(f"Decoded config file: {decoded}")
            raise


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
            "hug": ["🤗", "🫂"],
            "rule_1": ["⚠️", "1️⃣", "⚠️"],
            "favorite_band": ["🇧", "🇹", "🇸"],
            "off_topic": ["😆", "🤣", "😂", "🤪"],
            "party": ["🎉", "🎂", "🎈", "🥳", "🍾", "🎁", "🎊", "🪅", "👯", "🎆", "🎇"],
            "cow": ["🐮", "🐄"],
            "delete_confirmed": "✅",
            "sleep": "😴",
            "wave": "👋",
        },
        "food": food.default_config,
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
        "minimum_random_interval_minutes": 5,
        "minimum_random_interval_minutes_per_user": 30,
        "random_source_view": "Display",
        "maintainer_ids": ["328674204780068864"],
    }

    for key in defaults.keys():
        if isinstance(defaults[key], dict):
            defaults[key].update(config.get(key, {}))
        else:
            defaults[key] = config.get(key, defaults[key])

    if triggers := decode_base64_env("MOTTOBOTTO_TRIGGERS"):
        defaults["triggers"] = triggers
    # Compile trigger regexes
    for key, triggers in defaults["triggers"].items():
        defaults["triggers"][key] = [
            re.compile(f"^{t}", re.IGNORECASE) for t in triggers
        ]

    # Compile rule regexes
    for key, rules in defaults["rules"].items():
        defaults["rules"][key] = [re.compile(r, re.DOTALL) for r in rules]

    # Environment variables override config files

    if token := os.getenv("MOTTOBOTTO_DISCORD_TOKEN"):
        defaults["authentication"]["discord"] = token

    if token := os.getenv("MOTTOBOTTO_AIRTABLE_KEY"):
        defaults["authentication"]["airtable_key"] = token

    if token := os.getenv("MOTTOBOTTO_AIRTABLE_BASE"):
        defaults["authentication"]["airtable_base"] = token

    if channels := decode_base64_env("MOTTOBOTTO_CHANNELS"):
        defaults["channels"] = channels

    if id := os.getenv("MOTTOBOTTO_ID"):
        defaults["id"] = id

    if should_reply := os.getenv("MOTTOBOTTO_SHOULD_REPLY"):
        defaults["should_reply"] = should_reply.lower() == "true"

    if maintainer_ids := decode_base64_env("MOTTOBOTTO_MAINTAINER_IDS"):
        defaults["maintainer_ids"] = maintainer_ids

    if random_source_view := os.getenv("MOTTOBOTTO_RANDOM_MOTTO_SOURCE_VIEW"):
        defaults["random_source_view"] = random_source_view

    log.info(f"Random motto source view: {defaults['random_source_view']}")
    defaults["maintainer_ids"] = set(defaults["maintainer_ids"])
    log.info(f"Maintainer IDs: {defaults['maintainer_ids']}")

    return defaults
