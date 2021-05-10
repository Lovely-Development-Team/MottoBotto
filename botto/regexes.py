import re
from re import Pattern


class SuggestionRegexes:
    __slots__ = [
        "trigger",
        "pokes",
        "sorry",
        "apologising",
        "off_topic",
        "love",
        "band",
        "party",
    ]

    def __init__(
        self, trigger, pokes, sorry, apologising, off_topic, love, band, party
    ) -> None:
        self.trigger: [Pattern] = trigger
        self.pokes: Pattern = pokes
        self.sorry: Pattern = sorry
        self.apologising: Pattern = apologising
        self.off_topic: Pattern = off_topic
        self.love: Pattern = love
        self.band: Pattern = band
        self.party: Pattern = party
        super().__init__()


def compile_regexes(bot_user_id: str) -> SuggestionRegexes:
    self_id = rf"<@!?{bot_user_id}>"

    regexes = SuggestionRegexes(
        trigger=[re.compile(rf"^{self_id}")],
        pokes=re.compile(rf"pokes? {self_id}", re.IGNORECASE),
        sorry=re.compile(rf"sorry,? {self_id}", re.IGNORECASE),
        apologising=re.compile(
            rf"""(?:I['"m]+|my|^) # Match I/I'm/My
            [ ]* # Match any number of spaces
            (?:
              (?:
                (?:sincer|great) # Matching the start of sincere/great
                (?:est|e(?:ly)?)? # Match the end of sincerest/sincere/sincerely
                |so|very|much|such
              )
            .?)* # Match any number of "sincerely", "greatest", "so" etc. with or without characters in between
            [ ]* # Match any number of spaces
            (sorry|apologi([zs]e|es)) # Match sorry/apologise/apologies,etc.
        """,
            re.IGNORECASE|re.VERBOSE,
        ),
        off_topic=re.compile(rf"off( +|\-)topic", re.IGNORECASE),
        love=re.compile(rf"I love( you,?)? {self_id}", re.IGNORECASE),
        band=re.compile(
            rf"What('|’)?s +your +fav(ou?rite)? +band +{self_id} ?\?*", re.IGNORECASE
        ),
        party=re.compile(
            rf"parta?y", re.IGNORECASE
        ),
    )
    return regexes
