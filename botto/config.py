def parse(config):

    defaults = {
        "authentication": {
            "discord": "",
            "airtable_key": "",
            "airtable_base": "",
        },
        "rules": {
            "min_words": 2,
            "min_chars": 5,
            "max_chars": 240
        },
        "channels": {
            "include": [],
            "exclude": [],
        },
        "reactions": {},
        "triggers": {
            "new_motto": ["!motto"],
        },
        "should_reply": True,
    }

    for key in ("authentication", "channels", "reactions", "triggers", "rules"):
        defaults[key].update(config.get(key, {}))
    defaults["should_reply"] = config.get("should_reply", defaults["should_reply"])

    return defaults
