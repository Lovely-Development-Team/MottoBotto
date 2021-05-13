import re
from dataclasses import dataclass
from re import Pattern


@dataclass
class SuggestionRegexes:
    trigger: [Pattern]
    pokes: Pattern
    sorry: Pattern
    apologising: Pattern
    off_topic: Pattern
    love: Pattern
    band: Pattern
    party: Pattern


def compile_regexes(bot_user_id: str) -> SuggestionRegexes:
    self_id = rf"<@!?{bot_user_id}>"

    regexes = SuggestionRegexes(
        trigger=[re.compile(rf"^{self_id}")],
        pokes=re.compile(rf"pokes? {self_id}", re.IGNORECASE),
        sorry=re.compile(rf"sorry,? {self_id}", re.IGNORECASE),
        apologising=re.compile(
            rf"""
            (?:I['"’m]+|my|^) # Match I/I'm/My
            \s* # Match any number of spaces
            (?:
              (?:
                (?:sincer|great) # Matching the start of sincere/great
                (?:est|e(?:ly)?)? # Match the end of sincerest/sincere/sincerely
                |so|very|[ms]uch
              )
            .?)* # Match any number of "sincerely", "greatest", "so" etc. with or without characters in between
            \s* # Match any number of spaces
            (sorry|apologi([zs]e|es)) # Match sorry/apologise/apologies,etc.
        """,
            re.IGNORECASE | re.VERBOSE,
        ),
        off_topic=re.compile(rf"off( +|\-)topic", re.IGNORECASE),
        love=re.compile(rf"I love( you,?)? {self_id}", re.IGNORECASE),
        band=re.compile(
            rf"What('|’)?s +your +fav(ou?rite)? +band +{self_id} ?\?*", re.IGNORECASE
        ),
        party=re.compile(
            rf"(?:^|\s)part(?:a*y|ies)", re.IGNORECASE
        ),
    )
    return regexes
