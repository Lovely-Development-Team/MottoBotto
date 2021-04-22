import re


def parse(config):

    defaults = {
        "authentication": {
            "discord": "",
            "airtable_key": "",
            "airtable_base": "",
        },
        "rules": {
            "matching": [
                r"^.{5,240}$",      # Between 5 and 240 characters
                r"^(\S+\s)\S+",     # At least two "words"
            ],
            "excluding": [
                r"<@.*>",           # Contains an @username reference
                r"^[\d\s]*$",       # Purely numeric or whitespace
            ],
        },
        "channels": {
            "include": [],
            "exclude": [],
        },
        "reactions": {},
        "triggers": {
            "new_motto": [
                r"!motto$"
            ],
            "change_emoji": [
                r"!emoji"
            ],
        },
        "should_reply": True,
    }

    for key in ("authentication", "channels", "reactions", "triggers", "rules"):
        defaults[key].update(config.get(key, {}))
    defaults["should_reply"] = config.get("should_reply", defaults["should_reply"])

    for key, triggers in defaults["triggers"].items():
        defaults["triggers"][key] = [re.compile(f"^{t}", re.IGNORECASE) for t in triggers]

    for key, rules in defaults["rules"].items():
        defaults["rules"][key] = [re.compile(r) for r in rules]

    return defaults
