import asyncio
import logging
import random
from collections import AsyncGenerator
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Literal, Callable, Awaitable

import aiohttp
from aiohttp import ClientSession
from discord import Member as DiscordMember

from models import Motto, Member, AirTableError

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

    async def get_random_motto(self, search: str) -> Optional[Motto]:
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

    async def get_support_users(self) -> list:
        """
        Return a list of support Members.
        """
        raise NotImplementedError

    async def get_leaders(self, count=10) -> list:
        """
        Return the Members with the top Motto counts.
        """
        raise NotImplementedError

    async def remove_unapproved_messages(self, safe_period=24):
        raise NotImplementedError


async def run_request(
    action_to_run: Callable[[ClientSession], Awaitable[dict]],
    session: Optional[ClientSession] = None,
):
    if not session:
        async with aiohttp.ClientSession() as new_session:
            return await action_to_run(new_session)
    else:
        return await action_to_run(session)


async def airtable_sleep():
    await asyncio.sleep(1.0 / 5)


class AirtableMottoStorage(MottoStorage):
    def __init__(
        self,
        airtable_base: str,
        airtable_key: str,
        bot_id: Optional[str],
        random_motto_source_view: str
    ):
        self.airtable_key = airtable_key
        self.bot_id = bot_id
        self.motto_url = "https://api.airtable.com/v0/{base}/Motto".format(
            base=airtable_base
        )
        self.members_url = "https://api.airtable.com/v0/{base}/Member".format(
            base=airtable_base
        )
        self.random_motto_source_view = random_motto_source_view
        self.auth_header = {"Authorization": f"Bearer {self.airtable_key}"}
        self.semaphore = asyncio.Semaphore(5)

    async def _get(
        self,
        url: str,
        params: Optional[dict[str, str]] = None,
        session: Optional[ClientSession] = None,
    ) -> dict:
        async def run_fetch(session_to_use: ClientSession):
            async with session_to_use.get(
                url,
                params=params,
                headers=self.auth_header,
            ) as r:
                if r.status != 200:
                    print(r.url)
                    raise AirTableError(r.url, await r.json())
                motto_response: dict = await r.json()
                return motto_response

        async with self.semaphore:
            result = await run_request(run_fetch, session)
            await airtable_sleep()
            return result

    async def _list(
        self,
        base_url: str,
        filter_by_formula: Optional[str],
        session: Optional[ClientSession] = None,
        view: Optional[str] = None
    ) -> dict:
        params = {}
        if filter_by_formula := filter_by_formula:
            params.update({"filterByFormula": filter_by_formula})
        if view := view:
            params.update({"view": view})
        response = await self._get(base_url, params, session)
        return response.get("records", [])

    async def _iterate(
        self,
        base_url: str,
        filter_by_formula: str,
        sort: Optional[list[str]] = None,
        session: Optional[ClientSession] = None,
    ) -> AsyncGenerator[dict]:
        params = {"filterByFormula": filter_by_formula}
        if sort:
            for idx, field in enumerate(sort):
                params.update({"sort[{index}][field]".format(index=idx): field})
                params.update({"sort[{index}][direction]".format(index=idx): "desc"})
        offset = None
        while True:
            if offset:
                params.update(offset=offset)
            async with self.semaphore:
                response = await self._get(base_url, params, session)
                await airtable_sleep()
            records = response.get("records", [])
            for record in records:
                yield record
            offset = response.get("offset")
            if not offset:
                break

    async def _delete(
        self,
        base_url: str,
        records_to_delete: [str],
        session: Optional[ClientSession] = None,
    ):
        async def run_delete(session_to_use: ClientSession):
            async with session_to_use.delete(
                (
                    base_url
                    if len(records_to_delete) > 1
                    else base_url + f"/{records_to_delete[0]}"
                ),
                params=(
                    {"records": records_to_delete}
                    if len(records_to_delete) > 1
                    else None
                ),
                headers=self.auth_header,
            ) as r:
                if r.status != 200:
                    log.warning(f"Failed to delete IDs: {records_to_delete}")
                    raise AirTableError(r.url, await r.json())

        async with self.semaphore:
            result = await run_request(run_delete, session)
            await airtable_sleep()
            return result

    async def _modify(
        self,
        url: str,
        method: Literal["post", "patch"],
        record: dict,
        session: Optional[ClientSession] = None,
    ) -> dict:
        async def run_insert(session_to_use: ClientSession):
            data = {"fields": record}
            async with session_to_use.request(
                method,
                url,
                json=data,
                headers=self.auth_header,
            ) as r:
                if r.status != 200:
                    raise AirTableError(r.url, await r.json())
                motto_response: dict = await r.json()
                return motto_response

        async with self.semaphore:
            result = await run_request(run_insert, session)
            await airtable_sleep()
            return result

    async def _insert(
        self, url: str, record: dict, session: Optional[ClientSession] = None
    ) -> dict:
        return await self._modify(url, "post", record, session)

    async def _update(
        self, url: str, record: dict, session: Optional[ClientSession] = None
    ):
        await self._modify(url, "patch", record, session)

    async def _list_mottos(
        self, filter_by_formula: Optional[str], session: Optional[ClientSession] = None, view: Optional[str] = None
    ) -> dict:
        return await self._list(self.motto_url, filter_by_formula, session, view)

    async def _list_members(
        self, filter_by_formula: str, session: Optional[ClientSession] = None
    ) -> dict:
        return await self._list(self.members_url, filter_by_formula, session)

    def _list_all_members(
        self,
        filter_by_formula: str,
        sort: [str],
        session: Optional[ClientSession] = None,
    ) -> AsyncGenerator[dict]:
        return self._iterate(self.members_url, filter_by_formula, sort, session)

    async def _find_member_by_discord_id(
        self, discord_id: str, session: Optional[ClientSession] = None
    ) -> Optional[dict]:
        members = await self._list_members(
            filter_by_formula="{{Discord ID}}={value}".format(value=discord_id),
            session=session,
        )
        return members[0] if members else None

    async def _retrieve_member(
        self, member_id: str, session: Optional[ClientSession] = None
    ) -> dict:
        return await self._get(f"{self.members_url}/{member_id}", session=session)

    async def _delete_mottos(
        self, mottos: [Union[str, Motto]], session: aiohttp.ClientSession = None
    ):
        def extract_id(motto_or_id) -> str:
            if type(motto_or_id) is str:
                return motto_or_id
            elif type(motto_or_id) is dict:
                return Motto.from_airtable(motto_or_id).primary_key
            elif isinstance(motto_or_id, Motto):
                return motto_or_id.primary_key

        motto_ids = [extract_id(motto) for motto in mottos]
        # AirTable API only allows us to batch delete 10 records at a time, so we need to split up requests
        motto_ids_length = len(motto_ids)
        delete_batches = (
            motto_ids[offset : offset + 10] for offset in range(0, motto_ids_length, 10)
        )

        for records_to_delete in delete_batches:
            await self._delete(self.motto_url, records_to_delete, session)

    async def _delete_members(
        self, members: [str], session: aiohttp.ClientSession = None
    ):
        # AirTable API only allows us to batch delete 10 records at a time, so we need to split up requests
        member_ids_length = len(members)
        delete_batches = (
            members[offset : offset + 10] for offset in range(0, member_ids_length, 10)
        )

        for records_to_delete in delete_batches:
            await self._delete(self.motto_url, records_to_delete, session)

    async def insert_motto(
        self, motto_record: dict, session: Optional[ClientSession] = None
    ):
        await self._insert(self.motto_url, motto_record, session)

    async def insert_member(
        self, motto_record: dict, session: Optional[ClientSession] = None
    ) -> dict:
        return await self._insert(self.members_url, motto_record, session)

    async def update_motto(
        self,
        record_id: str,
        motto_record: dict,
        session: Optional[ClientSession] = None,
    ):
        await self._update(self.motto_url + "/" + record_id, motto_record, session)

    async def update_member(
        self,
        record_id: str,
        motto_record: dict,
        session: Optional[ClientSession] = None,
    ):
        await self._update(self.members_url + "/" + record_id, motto_record, session)

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
            await self.update_motto(motto_data["id"], motto_data["fields"])
            log.info(f"Updated Motto from message ID {motto.message_id} in AirTable")
        else:
            await self.insert_motto(motto_data["fields"])
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

    async def get_random_motto(self, search=None, search_regex=None) -> Optional[Motto]:

        filter_func = lambda x: x

        if search_regex:
            filter_func = lambda x: search_regex.search(x["fields"]["Motto"])
        elif search:
            filter_func = lambda x: search.lower() in x["fields"]["Motto"].lower()

        try:
            motto = Motto.from_airtable(
                random.choice([
                    m for m in
                    await self._list_mottos(
                        filter_by_formula=None,
                        view=self.random_motto_source_view
                    )
                    if filter_func(m)
                ])
            )
        except IndexError:
            return
        motto.member = await self.get_member(pk=motto.member)
        return motto

    async def delete_motto(self, pk: str):
        await self._delete_mottos([pk])

    async def get_or_add_member(self, member: DiscordMember) -> Member:
        """
        Fetches an existing member or adds a new record for them.
        :param member: The member
        :return: The record from AirTable for this member
        """
        member_record = await self._find_member_by_discord_id(member.id)
        if not member_record:
            data = {
                "Username": member.name,
                "Discord ID": str(member.id),
                "Bot ID": self.bot_id or "",
            }
            member_record = await self.insert_member(data)
            log.debug(f"Added member {member_record} to AirTable")
        return Member.from_airtable(member_record)

    async def get_member(
        self, pk: Optional[str] = None, discord_id: Optional[int] = None
    ) -> Optional[Member]:
        if pk:
            member_record = await self._retrieve_member(pk)
        elif discord_id:
            member_record = await self._find_member_by_discord_id(str(discord_id))
        else:
            raise TypeError("Must be called with either pk or discord_id.")
        return Member.from_airtable(member_record) if member_record else None

    async def remove_all_data(self, discord_id: Optional[int] = None):
        member_record = await self.get_member(discord_id=discord_id)
        if member_record:
            log.info(
                f"Removing mottos by {member_record.username}: {member_record.mottos}"
            )
            async with aiohttp.ClientSession() as session:
                await self._delete_mottos(member_record.mottos, session)
                log.info(
                    f"Removing {member_record.username} ({member_record.primary_key}"
                )
                await self._delete_members([member_record.primary_key], session)

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
        await self.update_member(member_record.primary_key, update)

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
            await self.update_member(member_record.primary_key, update_dict)

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
            await self.update_member(member_record.primary_key, data)

    async def get_support_users(self) -> list:
        members_iterator = self._list_all_members(
            sort=["Username"], filter_by_formula="{Support}=TRUE()"
        )
        return [Member.from_airtable(x) async for x in members_iterator]

    async def get_leaders(self, count=10) -> list:
        members_iterator = self._list_all_members(
                sort=["Total Points"], filter_by_formula="{Motto Count}>0"
        )
        leaders = []
        leaders_fetched = 0
        async for leader in members_iterator:
            leaders.append(Member.from_airtable(leader))
            leaders_fetched += 1
            if leaders_fetched >= count:
                break
        return leaders

    async def remove_unapproved_messages(self, safe_period=24):
        async with aiohttp.ClientSession() as session:
            mottos_to_delete = []
            fetched_mottos = await self._list_mottos(
                filter_by_formula="NOT({Motto})", session=session
            )
            for motto in fetched_mottos:
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
                    mottos_to_delete.append(motto)

            if len(mottos_to_delete) > 0:
                log.debug(
                    "Deleting {motto_count} unapproved mottos".format(
                        motto_count=len(mottos_to_delete)
                    )
                )
                await self._delete_mottos(mottos_to_delete, session)
                log.info(
                    "Deleted {motto_count} unapproved mottos".format(
                        motto_count=len(mottos_to_delete)
                    )
                )
