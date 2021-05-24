import enum
import logging
import re
from enum import Enum

from emoji import UNICODE_EMOJI

log = logging.getLogger("MottoBotto").getChild("food")
log.setLevel(logging.INFO)

default_config = {
    "standard": {
        "triggers": [
            "🍇",
            "🍈",
            "🍉",
            "🍊",
            "🍌",
            "🍍",
            "🥭",
            "🍎",
            "🍏",
            "🍐",
            "🍒",
            "🍓",
            "🫐",
            "🥝",
            "🍅",
            "🫒",
            "🥥",
            "🥑",
            "🥔",
            "🌽",
            "🥜",
            "🌰",
            "🍞",
            "🥐",
            "🥖",
            "🫓",
            "🥨",
            "🥯",
            "🧇",
            "🍖",
            "🍗",
            "🥓",
            "🍔",
            "🍕",
            "🌭",
            "🍟",
            "🥪",
            "🌮",
            "🌯",
            "🫔",
            "🧆",
            "🍳",
            "🍿",
            "🧈",
            "🍘",
            "🍙",
            "🍠",
            "🍢",
            "🥮",
            "🍡",
            "🥟",
            "🥠",
            "🦪",
            "🍩",
            "🍪",
            "🍰",
            "🧁",
            "🍬",
            "🍭",
            "🍼",
            "🥛",
            "☕",
            "🍵",
            "🥤",
            "🧋",
            "🧃",
            "🧉",
        ],
        "responses": ["😋", "echo"],
    },
    "chocolate": {"triggers": "🍫", "responses": ["😋", "🍫", "💜"]},
    "alcohol": {
        "triggers": ["🍶", "🍾", "🍷", "🍸", "🍹", "🍺", "🍻", "🥂", "🥃"],
        "responses": ["echo", "🥴"],
    },
    "teapot": {"triggers": "🫖", "responses": ["😋", "☕"]},
    "cutlery_foods": {
        "triggers": ["🥘", "🫕", "🥗", "🍝", "🥧", "🥙", "🥞", "🥩"],
        "responses": ["😋", "echo", "🍴"],
    },
    "chopstick_foods": {
        "triggers": ["🍲", "🍱", "🍚", "🍛", "🍜", "🍣", "🍤", "🍥", "🥡"],
        "responses": ["😋", "echo", "🥢"],
    },
    "spoon_foods": {
        "triggers": ["🥣", "🍧", "🍨", "🍮", "🍯"],
        "responses": ["😋", "echo", "🥄"],
    },
    "tongue_foods": {"triggers": "🍦", "responses": ["👅", "echo", "😋"]},
    "rabbit_food": {"triggers": ["🥬", "🥕"], "responses": ["🐰"]},
    "mouse_food": {"triggers": "🧀", "responses": ["🐭"]},
    "weird_foods": {
        "triggers": ["🍋", "🍆", "🍑", "🫑", "🥒", "🥦", "🧄", "🧅", "🍄", "🥚", "🧈"],
        "responses": ["😕"],
    },
    "eye_roll_foods": {"triggers": ["🍽️"], "responses": ["🙄"]},
    "dangerous_foods": {
        "triggers": ["💣", "🧨", "🗡️", "🔪", "🦠", "🧫"],
        "responses": ["🙅", "😨"],
    },
    "nausea": {"triggers": "🚬", "responses": ["🙅", "🤢"]},
    "vomit": {"triggers": ["🐛", "🐜", "🪲", "🦟", "🐞", "🦗", "🪰"], "responses": ["🤢", "🤮", "😭"]},
    "bee": {"triggers": "🐝", "responses": ["🙅", "echo", "🌻", "👉", "🍯", "😊"]},
    "baby": {"triggers": "👶", "responses": ["🙅", "😢"]},
    "alien": {"triggers": "🛸", "responses": ["👽"]},
    "zombie": {"triggers": "🧠", "responses": ["🧟"]},
    "vampire": {"triggers": ["🩸", "🆎", "🅱️", "🅾️", "🅰️"], "responses": ["🧛"]},
    "spicy": {"triggers": "🌶️", "responses": ["🥵"]},
    "ice": {"triggers": "🧊", "responses": ["🥶"]},
    "bone": {"triggers": "🦴", "responses": ["🐶"]},
    "celebrate": {"triggers": "🎂", "responses": ["😋", "party"]},
    "money": {"triggers": ["💸", "💰", "💵"], "responses": ["🤑"]}
}


class SpecialAction(Enum):
    echo = enum.auto()
    party = enum.auto()


def convert_response(response: str):
    if response == "echo" or response == "party":
        return SpecialAction[response]
    else:
        return response


class FoodLookups:
    def __init__(self, self_id: str, food_config: dict):
        self.lookup = {}
        for item in food_config.values():
            triggers = item["triggers"]
            responses = [convert_response(response) for response in item["responses"]]
            if type(triggers) is list:
                for emoji in triggers:
                    self.lookup.update({emoji: responses})
            else:
                self.lookup.update({triggers: responses})
        self.food_chars = "".join(self.lookup.keys())
        self.food_regex = re.compile(
            r"""(?:feed|pour)?s?\s{self_id}
                    .*
                    ([{chars}])""".format(
                self_id=self_id, chars=self.food_chars
            ),
            re.IGNORECASE | re.VERBOSE | re.UNICODE,
        )
        self.not_food_regex = re.compile(
            r"""(?:feed|pour)?s?\s{self_id}
                    .*
                    ([{chars}])""".format(
                self_id=self_id, chars="".join(UNICODE_EMOJI["en"].keys())
            ),
            re.IGNORECASE | re.VERBOSE | re.UNICODE,
        )
        log.info(f"Loaded {len(self.lookup)} types of food in {len(food_config)} categories")
