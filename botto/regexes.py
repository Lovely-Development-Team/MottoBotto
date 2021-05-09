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
    ]

    def __init__(
        self, trigger, pokes, sorry, apologising, off_topic, love, band
    ) -> None:
        self.trigger: [Pattern] = trigger
        self.pokes: Pattern = pokes
        self.sorry: Pattern = sorry
        self.apologising: Pattern = apologising
        self.off_topic: Pattern = off_topic
        self.love: Pattern = love
        self.band: Pattern = band
        super().__init__()


def compile_regexes(bot_user_id: str) -> SuggestionRegexes:
    self_id = rf"<@!?{bot_user_id}>"

    regexes = SuggestionRegexes(
        trigger=[re.compile(rf"^{self_id}")],
        pokes=re.compile(rf"pokes? {self_id}", re.IGNORECASE),
        sorry=re.compile(rf"sorry,? {self_id}", re.IGNORECASE),
        apologising=re.compile(rf"sorry|apologi([zs]e|es)", re.IGNORECASE),
        off_topic=re.compile(rf"off( +|\-)topic", re.IGNORECASE),
        love=re.compile(rf"I love( you,?)? {self_id}", re.IGNORECASE),
        band=re.compile(
            rf"What('|’)?s +your +fav(ou?rite)? +band +{self_id} ?\?*", re.IGNORECASE
        ),
    )
    return regexes
