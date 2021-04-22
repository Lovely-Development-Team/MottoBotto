import logging
import re
from typing import Optional
from emoji import UNICODE_EMOJI

import discord
from airtable import Airtable
from discord import Message, Member

import reactions
from message_checks import is_botto, is_dm

log = logging.getLogger("MottoBotto")
log.setLevel(logging.DEBUG)


class MottoBotto(discord.Client):
    def __init__(
        self,
        config: dict,
        mottos: Airtable,
        members: Airtable,
    ):
        self.config = config
        self.mottos = mottos
        self.members = members

        log.info(
            "Replies are enabled"
            if self.config["should_reply"]
            else "Replies are disabled"
        )
        log.info("Responding to phrases: %s", self.config["triggers"])

        intents = discord.Intents(messages=True, members=True, guilds=True)
        super().__init__(intents=intents)

    async def on_ready(self):
        log.info("We have logged in as {0.user}".format(self))

    async def add_reaction(
        self, message: Message, reaction_type: str, default: str = None
    ):
        if reaction := self.config["reactions"].get(reaction_type, default):
            await message.add_reaction(reaction)

    async def on_message(self, message: Message):

        if is_dm(message):
            await self.process_dm(message)
            return

        channel_name = message.channel.name

        if (
            self.config["channels"]["include"]
            and channel_name not in self.config["channels"]["include"]
        ):
            return
        else:
            if channel_name in self.config["channels"]["exclude"]:
                return

        await self.process_suggestion(message)

    async def on_member_update(self, before: Member, after: Member):
        member_record = self.update_existing_member(after)
        if member_record:
            log.debug(
                f"Recorded name change '{before.display_name}' to '{after.display_name}'"
            )

    def is_valid_message(self, message: Message) -> bool:

        message_length = len(message.content)
        message_words = len(message.content.split())

        log.debug(
            f"Validating message against {self.config['rules']}. Length: {message_length}. Words: {message_words}"
        )

        if message_length < self.config["rules"]["min_chars"]:
            return False
        if message_length > self.config["rules"]["max_chars"]:
            return False
        if message_words < self.config["rules"]["min_words"]:
            return False
        if re.search(r"<@.*>", message.content):
            # Messages with usernames in are not valid mottos
            return False
        if re.search(r"^[\d\s]*$", message.content):
            # Messages that are just numeric in are not valid mottos
            return False
        return True

    async def get_or_add_member(self, member: Member, emoji: Optional[str] = None):
        member_record = self.members.match("Discord ID", member.id)
        data = {
            "Name": member.display_name,
        }
        if emoji is not None:
            data["Emoji"] = emoji

        if not member_record:
            data["Discord ID"] = str(member.id)
            member_record = self.members.insert(data)
            log.debug(f"Added member {member_record} to AirTable")
        elif emoji is not None and member_record["fields"].get("Emoji", "") != emoji:
            log.debug("Updating member details")
            self.members.update(member_record["id"], data)

        return member_record

    def update_existing_member(self, member: Member, emoji: Optional[str] = None) -> Optional[dict]:
        """
        Updates an existing member's record. This will not add new members
        :param member: the updated member from Discord
        :return: the member record if they exist, otherwise None
        """
        member_record = self.members.match("Discord ID", member.id)
        if not member_record:
            return None
        update_dict = {
            "Name": member.display_name,
        }
        if emoji is not None:
            update_dict["Emoji"] = emoji
        self.members.update(member_record["id"], update_dict)
        return member_record

    async def process_suggestion(self, message: Message):

        if message.content.upper() not in self.config["triggers"]["new_motto"]:
            return

        if is_botto(message, self.user):
            await reactions.skynet_prevention(self, message)
            return

        if not message.reference:
            await reactions.not_reply(self, message)
            return

        motto_message: Message = message.reference.resolved

        if not self.is_valid_message(motto_message):
            await reactions.invalid(self, message)
            return

        if motto_message.author == message.author:
            await reactions.fishing(self, message)
            return

        log.info(f'Motto suggestion incoming: "{motto_message.content}"')

        actual_motto = motto_message.content
        filter_motto = actual_motto.replace("'", r"\'")

        filter_formula = f"REGEX_REPLACE(REGEX_REPLACE(LOWER(TRIM('{filter_motto}')), '[^\w ]+', ''), '\s+', ' ') = REGEX_REPLACE(REGEX_REPLACE(LOWER(TRIM({{Motto}})), '[^\w ]+', ''), '\s+', ' ')"
        log.debug("Searching with filter %r", filter_formula)
        matching_mottos = self.mottos.get_all(filterByFormula=filter_formula)
        if matching_mottos:
            await reactions.duplicate(self, message)
            return

        # Find the nominee and nominator
        nominee = await self.get_or_add_member(motto_message.author)
        nominator = await self.get_or_add_member(message.author)

        motto_data = {
            "Motto": actual_motto,
            "Message ID": str(motto_message.id),
            "Date": motto_message.created_at.isoformat(),
            "Member": [nominee["id"]],
            "Nominated By": [nominator["id"]],
        }
        self.mottos.insert(motto_data)
        log.debug("Added Motto to AirTable")

        await reactions.stored(self, message, motto_message)

    async def process_dm(self, message: Message):

        log.info(
            f"Received direct message (ID: {message.id}) from {message.author}: {message.content}"
        )

        upper_content = message.content.upper()

        if emoji_trigger := [t for t in self.config["triggers"]["change_emoji"] if upper_content.startswith(t)]:

            emoji_trigger = emoji_trigger[0]
            content = message.content[len(emoji_trigger):].strip().strip('\ufe0f')
            log.debug(f"User {message.author} wants to change emoji: {content!r} (trigger: {emoji_trigger})")

            if not content:
                log.debug(f"Removing emoji")
                await self.get_or_add_member(message.author, emoji="")
                await reactions.valid_emoji(self, message)
            elif content in UNICODE_EMOJI["en"]:
                log.debug(f"Updating emoji")
                await self.get_or_add_member(message.author, emoji=content)
                await reactions.valid_emoji(self, message)
            else:
                await reactions.invalid_emoji(self, message)

            return

        await reactions.unknown_dm(self, message)
