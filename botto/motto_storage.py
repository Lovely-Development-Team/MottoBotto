import logging
from typing import Optional

from airtable import Airtable
from discord import Member

log = logging.getLogger(__name__)


def get_name(member: Member):
    return member.nick if getattr(member, "nick", None) else member.display_name


class MottoStorage:
    def __init__(self, mottos: Airtable, members: Airtable, bot_id: Optional[str]):
        self.mottos = mottos
        self.members = members
        self.bot_id = bot_id

    async def get_or_add_member(self, member: Member) -> dict:
        """
        Fetches an existing member or adds a new record for them.
        :param member: The member
        :return: The record from AirTable for this member
        """
        member_record = self.members.match("Discord ID", member.id)
        if not member_record:
            data = {
                "Username": member.name,
                "Discord ID": str(member.id),
                "Bot ID": self.bot_id or "",
            }
            member_record = self.members.insert(data)
            log.debug(f"Added member {member_record} to AirTable")
        return member_record

    async def set_nick_option(self, member: Member, on=False):
        """
        Changes the "Use Nickname" setting for a member
        :param member: The Member being changed
        :param on: The new value for "Use Nickname"
        """
        member_record = await self.get_or_add_member(member)
        update = {
            "Use Nickname": on,
        }
        if not on:
            update["Nickname"] = None
        log.debug(f"Recording changes for {member}: {update}")
        self.members.update(member_record["id"], update)

    async def update_name(self, member_record: dict, member: Member):
        airtable_username = member_record["fields"].get("Username")
        discord_username = member.name
        update_dict = {}
        if airtable_username != discord_username:
            update_dict["Username"] = discord_username

        if member_record["fields"].get("Use Nickname"):
            airtable_nickname = member_record["fields"].get("Nickname")
            discord_nickname = get_name(member)

            if (
                airtable_nickname != discord_nickname
                and discord_nickname != member_record["fields"].get("Username")
            ):
                update_dict["Nickname"] = discord_nickname
        elif member_record["fields"].get("Nickname"):
            update_dict["Nickname"] = ""

        if update_dict:
            log.debug(f"Recorded changes {update_dict}")
            self.members.update(member_record["id"], update_dict)

    async def update_emoji(self, member_record: dict, emoji: str):
        """
        Updates the emoji associated with a member.
        :param member_record: The Airtable member record for this member
        :param emoji: The new emoji to associate
        """
        data = {"Emoji": emoji}

        log.debug(f"Update data: {data}")
        log.debug(f"Member record: {member_record}")

        if member_record["fields"].get("Emoji") != data.get("Emoji"):
            log.debug("Updating member emoji details")
            self.members.update(member_record["id"], data)

    def update_existing_member(self, member: Member) -> Optional[dict]:
        """
        Updates an existing member's record. This will not add new members
        :param member: the updated member from Discord
        :return: the member record if they exist, otherwise None
        """
        member_record = self.members.match("Discord ID", member.id)
        if not member_record:
            return None
        if member_record["fields"].get("Name") == member.display_name:
            return None
        update_dict = {
            "Name": member.display_name,
        }
        self.members.update(member_record["id"], update_dict)
        return member_record

    def get_support_users(self):
        return [
            x["fields"]
            for x in self.members.get_all(
                sort=["Username"], filterByFormula="{Support}=TRUE()"
            )
        ]
