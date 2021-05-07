import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from airtable import Airtable
from discord import Member as DiscordMember

from models import Motto, Member

log = logging.getLogger(__name__)


def get_name(member: DiscordMember):
    return member.nick if getattr(member, "nick", None) else member.display_name


class MottoStorage:
    async def save_motto(self, motto: Motto, fields=None):
        """
        Save the provided Motto.
        If it has no primary key, inserts a new instance, otherwise updates the old instance.
        If a list of fields are specified, only saves/updates those fields.
        """
        raise NotImplementedError

    async def get_matching_mottos(self, motto: str, message_id=None) -> list:
        """
        Return Mottos that are duplicates of the provided motto text.
        If message_id is provided, that is also used in the uniqueness test.
        """
        raise NotImplementedError

    async def get_motto(self, message_id: str) -> Optional[Motto]:
        """
        Return a Motto with the given Discord message_id.
        """
        raise NotImplementedError

    async def get_random_motto(self) -> Optional[Motto]:
        """
        Return a random approved Motto.
        """
        raise NotImplementedError

    async def delete_motto(self, pk: str):
        """
        Delete a Motto with the provided primary key.
        """
        raise NotImplementedError

    async def get_or_add_member(self, member: DiscordMember) -> Member:
        """
        Get or add a Member object based on the provided Discord Member.
        """
        raise NotImplementedError

    async def get_member(self, pk: str) -> Optional[Member]:
        """
        Return the Member with the specified primary key.
        """
        raise NotImplementedError

    async def remove_all_data(self, discord_id: Optional[int] = None):
        """
        Remove all member data for a given Discord ID.
        """
        raise NotImplementedError

    async def set_nick_option(self, member: DiscordMember, on=False):
        """
        Set the Member use_nickname option to either on or off for the provided Discord Member.
        """
        raise NotImplementedError

    async def update_name(self, member_record: Member, member: DiscordMember):
        """
        Update the Member's name information from the provided Discord Member.
        """
        raise NotImplementedError

    async def update_emoji(self, member_record: Member, emoji: str):
        """
        Update the Member's emoji.
        """
        raise NotImplementedError

    def get_support_users(self) -> list:
        """
        Return a list of support Members.
        """
        raise NotImplementedError

    def get_leaders(self, count=10) -> list:
        """
        Return the Members with the top Motto counts.
        """
        raise NotImplementedError

    async def remove_unapproved_messages(self, safe_period=24):
        raise NotImplementedError


class AirtableMottoStorage(MottoStorage):
    def __init__(
        self,
        mottos: Airtable,
        members: Airtable,
        airtable_base: str,
        airtable_key: str,
        bot_id: Optional[str],
    ):
        self.mottos = mottos
        self.members = members
        self.airtable_key = airtable_key
        self.bot_id = bot_id
        self.motto_url = "https://api.airtable.com/v0/{base}/Motto".format(
            base=airtable_base
        )
        self.members_url = "https://api.airtable.com/v0/{base}/Members".format(
            base=airtable_base
        )
        self.auth_header = {"Authorization": f"Bearer {self.airtable_key}"}

    async def _list_mottos(self, filter_by_formula: str):
        params = {"filterByFormula": filter_by_formula}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.motto_url,
                params=params,
                headers=self.auth_header,
            ) as r:
                motto_response: dict = await r.json()
                return motto_response.get("records", [])

    async def save_motto(self, motto: Motto, fields=None):
        fields = fields or [
            "motto",
            "message_id",
            "member",
            "date",
            "nominated_by",
            "approved",
            "bot_id",
        ]
        motto_data = motto.to_airtable(fields=fields)
        log.info(f"Adding motto data: {motto_data['fields']}")
        if motto.primary_key:
            self.mottos.update(motto_data["id"], motto_data["fields"])
            log.info(f"Updated Motto from message ID {motto.message_id} in AirTable")
        else:
            self.mottos.insert(motto_data["fields"])
            log.info(f"Added Motto from message ID {motto.message_id} to AirTable")

    async def get_matching_mottos(self, motto: str, message_id=None) -> bool:
        filter_motto = motto.replace("'", r"\'")
        filter_formula = f"REGEX_REPLACE(REGEX_REPLACE(LOWER(TRIM('{filter_motto}')), '[^\w ]+', ''), '\s+', ' ') = REGEX_REPLACE(REGEX_REPLACE(LOWER(TRIM({{Motto}})), '[^\w ]+', ''), '\s+', ' ')"
        if message_id:
            filter_formula = (
                f"OR({filter_formula}, '{str(message_id)}' = {{Message ID}})"
            )
        log.debug("Searching with filter %r", filter_formula)
        fetched_mottos = await self._list_mottos(filter_by_formula=filter_formula)
        log.info(fetched_mottos)
        matching_mottos = [Motto.from_airtable(x) for x in fetched_mottos]
        return bool(matching_mottos)

    async def get_motto(self, message_id: str) -> Optional[Motto]:
        motto_record = await self._list_mottos(
            filter_by_formula="{{Message ID}}={value}".format(value=message_id)
        )
        if not motto_record:
            log.info(f"Couldn't find matching message in Airtable.")
            return
        return Motto.from_airtable(motto_record[0])

    async def get_random_motto(self) -> Optional[Motto]:
        try:
            motto = Motto.from_airtable(
                random.choice(
                    await self._list_mottos(
                        filter_by_formula="{Approved by Author}=TRUE()"
                    )
                )
            )
        except IndexError:
            return
        motto.member = await self.get_member(pk=motto.member)
        return motto

    async def delete_motto(self, pk: str):
        self.mottos.delete(pk)

    async def get_or_add_member(self, member: DiscordMember) -> Member:
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
        return Member.from_airtable(member_record)

    async def get_member(
        self, pk: Optional[str] = None, discord_id: Optional[int] = None
    ) -> Optional[Member]:
        if pk:
            member_record = self.members.get(pk)
        elif discord_id:
            member_record = self.members.match("Discord ID", str(discord_id))
        else:
            raise TypeError("Must be called with either pk or discord_id.")
        return Member.from_airtable(member_record) if member_record else None

    async def remove_all_data(self, discord_id: Optional[int] = None):
        member_record = await self.get_member(discord_id=discord_id)
        if member_record:
            log.info(
                f"Removing mottos by {member_record.username}: {member_record.mottos}"
            )
            self.mottos.batch_delete(member_record.mottos)
            log.info(f"Removing {member_record.username} ({member_record.primary_key}")
            self.members.delete(member_record.primary_key)

    async def set_nick_option(self, member: DiscordMember, on=False):
        """
        Changes the "Use Nickname" setting for a member
        :param member: The DiscordMember being changed
        :param on: The new value for "Use Nickname"
        """
        member_record = await self.get_or_add_member(member)
        update = {
            "Use Nickname": on,
        }
        if not on:
            update["Nickname"] = None
        log.debug(f"Recording changes for {member}: {update}")
        self.members.update(member_record.primary_key, update)

    async def update_name(self, member_record: Member, member: DiscordMember):

        airtable_username = member_record.username
        discord_username = member.name

        update_dict = {}
        if airtable_username != discord_username:
            update_dict["Username"] = discord_username

        if member_record.use_nickname:
            airtable_nickname = member_record.nickname
            discord_nickname = get_name(member)

            if (
                airtable_nickname != discord_nickname
                and discord_nickname != member_record.username
            ):
                update_dict["Nickname"] = discord_nickname
        elif member_record.nickname:
            update_dict["Nickname"] = ""

        if update_dict:
            log.debug(f"Recorded changes {update_dict}")
            self.members.update(member_record.primary_key, update_dict)

    async def update_emoji(self, member_record: Member, emoji: str):
        """
        Updates the emoji associated with a member.
        :param member_record: The Airtable member record for this member
        :param emoji: The new emoji to associate
        """
        data = {"Emoji": emoji}

        log.debug(f"Update data: {data}")
        log.debug(f"DiscordMember record: {member_record}")

        if member_record.emoji != data.get("Emoji"):
            log.debug("Updating member emoji details")
            self.members.update(member_record.primary_key, data)

    def get_support_users(self) -> list:
        return [
            Member.from_airtable(x)
            for x in self.members.get_all(
                sort=["Username"], filterByFormula="{Support}=TRUE()"
            )
        ]

    def get_leaders(self, count=10) -> list:
        return [
            Member.from_airtable(x)
            for x in self.members.get_all(
                sort=["-Motto Count"], filterByFormula="{Motto Count}>0"
            )[:count]
        ]

    async def remove_unapproved_messages(self, safe_period=24):

        for motto in self.mottos.search("Motto", ""):
            motto_date = datetime.strptime(
                motto["fields"]["Date"], "%Y-%m-%dT%H:%M:%S.%f%z"
            )
            motto_expiry_date = datetime.now(timezone.utc) - timedelta(
                hours=safe_period
            )
            if motto_date < motto_expiry_date:
                log.debug(
                    f'Deleting motto {motto["id"]} - message ID {motto["fields"]["Message ID"]}'
                )
                self.mottos.delete(motto["id"])
