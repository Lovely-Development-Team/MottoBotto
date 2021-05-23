from typing import Union

from dateutil import parser
from yarl import URL


class Model:
    def __init__(self, **kwargs):
        for attr in self.attributes:
            setattr(self, attr, kwargs.get(attr))

    def __str__(self):
        attrs = ", ".join(f"{attr}={getattr(self, attr)!r}" for attr in self.attributes)
        return f"{self.__class__.__name__}({attrs})"


class Motto(Model):
    attributes = [
        "primary_key",
        "motto",
        "message_id",
        "date",
        "member",
        "nominated_by",
        "approved_by_author",
        "approved",
        "bot_id",
    ]

    @classmethod
    def from_airtable(cls, data: dict) -> "Motto":
        fields = data["fields"]
        try:
            date = parser.parse(fields["Date"])
        except parser.ParserError:
            date = None
        return cls(
            primary_key=data["id"],
            motto=fields.get("Motto"),
            message_id=fields.get("Message ID"),
            date=date,
            member=fields.get("Member", [None])[0],
            nominated_by=fields.get("Nominated By", [None])[0],
            approved_by_author=fields.get("Approved by Author"),
            approved=fields.get("Approved"),
            bot_id=fields.get("Bot ID"),
        )

    def to_airtable(self, fields=None) -> dict:
        fields = fields if fields else self.attributes
        data = {}
        if "motto" in fields:
            data["Motto"] = self.motto
        if "message_id" in fields:
            data["Message ID"] = self.message_id
        if "date" in fields:
            data["Date"] = self.date.isoformat()
        if "member" in fields:
            data["Member"] = [
                self.member.primary_key
                if isinstance(self.member, Member)
                else self.member
            ]
        if "nominated_by" in fields:
            data["Nominated By"] = [
                self.nominated_by.primary_key
                if isinstance(self.nominated_by, Member)
                else self.nominated_by
            ]
        if "approved_by_author" in fields:
            data["Approved by Author"] = self.approved_by_author
        if "approved" in fields:
            data["Approved"] = self.approved
        if "bot_id" in fields:
            data["Bot ID"] = self.bot_id
        return {
            "id": self.primary_key,
            "fields": data,
        }


class Member(Model):
    attributes = [
        "primary_key",
        "username",
        "emoji",
        "discord_id",
        "support",
        "nickname",
        "use_nickname",
        "motto_count",
        "bot_id",
        "mottos",
    ]

    @classmethod
    def from_airtable(cls, data: dict) -> "Member":
        fields = data["fields"]
        return cls(
            primary_key=data["id"],
            emoji=fields.get("Emoji"),
            username=fields.get("Username"),
            discord_id=fields.get("Discord ID"),
            support=fields.get("Support", False),
            nickname=fields.get("Nickname"),
            use_nickname=fields.get("Use Nickname", False),
            motto_count=fields.get("Motto Count", 0),
            bot_id=fields.get("Bot ID", None),
            mottos=fields.get("Mottos", []),
        )

    @property
    def display_name(self):
        emoji = ""
        if self.emoji:
            emoji = f"{self.emoji} "
        name = self.nickname if self.nickname and self.use_nickname else self.username
        return f"{emoji}{name}"


class AirTableError(Exception):
    def __init__(
        self, url: URL, response_dict: Union[dict, str], *args: object
    ) -> None:
        error_dict: dict = response_dict["error"]
        self.url = url
        if type(response_dict) is dict:
            self.error_type = error_dict.get("type")
            self.error_message = error_dict.get("message")
        else:
            self.error_type = error_dict
            self.error_message = ""
        super().__init__(*args)

    def __repr__(self) -> str:
        return "{class_name}(type:{error_type}, message:'{error_message}', url:{url})".format(
            class_name=self.__class__,
            error_type=self.error_type,
            error_message=self.error_message,
            url=self.url,
        )

    def __str__(self) -> str:
        return "Error from AirTable operation of type '{error_type}', with message:'{error_message}'. Request URL: {url}".format(
            error_type=self.error_type, error_message=self.error_message, url=self.url
        )
