import re
from dataclasses import dataclass
from re import Pattern
from typing import Union

from food import FoodLookups


@dataclass
class TagRegexes:
    random: Pattern


@dataclass
class SuggestionRegexes:
    trigger: [Pattern]
    tag: Pattern
    pokes: Pattern
    sorry: Pattern
    apologising: Pattern
    off_topic: Pattern
    love: Pattern
    hug: Pattern
    food: FoodLookups
    band: Pattern
    party: Pattern
    cow: Pattern
    tags: TagRegexes
    maintenance_down: Pattern
    maintenance_up: Pattern


laugh_emojis = "[😆😂🤣]"

dots = "(?:…|\.{3,4})"


def compile_regexes(bot_user_id: Union[str, int], config: dict) -> SuggestionRegexes:
    self_id = rf"<@!?{bot_user_id}>"

    line_break_matcher = "[\t\n\r\v]"

    regexes = SuggestionRegexes(
        trigger=[re.compile(rf"^{self_id}")],
        tag=re.compile(rf"^{self_id} (.*)"),
        pokes=re.compile(rf"pokes? {self_id}", re.IGNORECASE),
        sorry=re.compile(rf"sorry,? {self_id}", re.IGNORECASE),
        apologising=re.compile(
            rf"""
            (?:
                I['"’m]+ #Match I/I'm
                |my
                |ye[ah|es]* # Match variations on yeah/yes
                |(n*o+)+
                |\(
                |^ # Match the start of a string
            )
            [,.;\s]* # Match any number of spaces/punctuation
            (?:
              (?:
                (?:sincer|great) # Matching the start of sincere/great
                (?:est|e(?:ly)?)? # Match the end of sincerest/sincere/sincerely
                |so|very|[ms]uch
              )
            .?)* # Match any number of "sincerely", "greatest", "so" etc. with or without characters in between
            \s* # Match any number of spaces
            (sorry|apologi([zs]e|es)) # Match sorry/apologise/apologies,etc.
            (?!\s*{laugh_emojis})
        """,
            re.IGNORECASE | re.VERBOSE | re.UNICODE,
        ),
        off_topic=re.compile(rf"off( +|\-)topic", re.IGNORECASE),
        love=re.compile(rf"I love( you,?)? {self_id}", re.IGNORECASE),
        hug=re.compile(rf"Hugs? {self_id}|Gives {self_id} a?\s?hugs?", re.IGNORECASE),
        food=FoodLookups(self_id, config["food"]),
        band=re.compile(
            rf"What('|’)?s +your +fav(ou?rite)? +band +{self_id} ?\?*", re.IGNORECASE
        ),
        party=re.compile(rf"(?<!third)(?<!3rd)(?:^|\s)part(?:a*y|ies)", re.IGNORECASE),
        cow=re.compile(
            r"""
            ^(?:
                c+{lb}*o+{lb}*w+{lb}*s*
                |
                m+{lb}*o{lb}*o+{lb}?
            )
            [\s\t\n\r\v]*
            $""".format(
                lb=line_break_matcher
            ),
            re.IGNORECASE | re.VERBOSE,
        ),
        tags=TagRegexes(
            random=re.compile(r"^!random\s*(.*)"),
        ),
        maintenance_down=re.compile(rf"{self_id}\s+Going down in 3{dots}2{dots}1{dots}\s*", re.IGNORECASE),
        maintenance_up=re.compile(rf"Welcome back\s+{self_id}\s*", re.IGNORECASE)
    )
    return regexes
