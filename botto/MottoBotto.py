import logging
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from emoji import UNICODE_EMOJI
import subprocess

import discord
from airtable import Airtable
from discord import Message, Member

import reactions
from message_checks import is_botto, is_dm

log = logging.getLogger("MottoBotto")
log.setLevel(logging.DEBUG)


CHANNEL_REGEX = re.compile("<#(\d+)>")


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
        log.info("Rules: %s", self.config["rules"])

        intents = discord.Intents(
            messages=True, members=True, guilds=True, reactions=True
        )
        super().__init__(intents=intents)

    async def on_ready(self):
        log.info("We have logged in as {0.user}".format(self))

    async def add_reaction(
        self, message: Message, reaction_type: str, default: str = None
    ):
        if reaction := self.config["reactions"].get(reaction_type, default):
            await message.add_reaction(reaction)

    async def on_raw_reaction_add(self, payload):

        if payload.emoji.name not in (self.config["approval_reaction"], self.config["confirm_delete_reaction"]):
            return

        log.info(f"Reaction received: {payload}")

        channel = await self.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        log.info(f"Channel: {channel}")
        log.info(f"Message: {message}")
        log.info(f"Reactions: {message.reactions}")

        if payload.emoji.name == self.config["approval_reaction"]:

            pending_reaction = any(
                r.me and r.emoji == self.config["reactions"]["pending"]
                for r in message.reactions
            )
            if not pending_reaction:
                log.info(f"Ignoring message not pending approval.")
                return

            motto_message: Message = message.reference.resolved
            log.info(f"Motto Message: {motto_message} / {motto_message.author.id}")
            if motto_message.author.id != payload.user_id:
                log.info(f"Ignoring approval from somebody other than motto author.")
                return

            motto_record = self.mottos.match("Message ID", str(motto_message.id))
            if not motto_record:
                log.info(f"Couldn't find matching message in Airtable.")
                return

            actual_motto = self.clean_message(motto_message)

            if self.is_repeat_message(motto_message, check_id=False):
                self.mottos.delete(motto_record["id"])
                await reactions.duplicate(self, message)
                return

            self.mottos.update(
                motto_record["id"], {"Motto": actual_motto, "Approved by Author": True}
            )
            await reactions.stored(self, message, motto_message)

            nominee = await self.get_or_add_member(motto_message.author)
            nominator = await self.get_or_add_member(message.author)
            await self.update_name(nominee, motto_message.author)
            await self.update_name(nominator, message.author)

            return

        if payload.emoji.name == self.config["confirm_delete_reaction"]:

            if message.author != self.user:
                log.info(f"Ignoring message not by MottoBotto")
                return

            if not isinstance(channel, discord.DMChannel):
                log.info(f"Ingoring reaction not in DM")
                return

            request = message.reference.resolved if message.reference else None
            if not request or request.content.strip().lower() != "!delete":
                log.info(f"Ignoring reaction to message not replying to !delete")
                return

            pending_reaction = any(
                r.me and r.emoji == self.config["reactions"]["pending"]
                for r in message.reactions
            )
            if not pending_reaction:
                log.info(f"Ignoring message not pending approval.")
                return

            member_record = self.members.match("Discord ID", payload.user_id)
            if member_record:
                log.info(f"Removing mottos by {member_record['fields']['Username']}: {member_record['fields']['Mottos']}")
                self.mottos.batch_delete(member_record["fields"]["Mottos"])
                log.info(f"Removing {member_record['fields']['Username']} ({member_record['id']}")
                self.members.delete(member_record["id"])
            await message.remove_reaction(self.config["reactions"]["pending"], self.user)
            await message.add_reaction(self.config["reactions"]["delete_confirmed"])
            await channel.send("All of your data has been removed. If you approve or nominate another motto in future, your user data and any future approved mottos will be captured again.")
            return


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

        await self.remove_unapproved_messages()

        await self.process_suggestion(message)

    def clean_message(self, message: Message) -> str:

        actual_motto = message.content

        for channel_id in CHANNEL_REGEX.findall(actual_motto):
            channel = self.get_channel(int(channel_id))
            if not channel:
                continue
            actual_motto = actual_motto.replace(f"<#{channel_id}>", f"#{channel.name}")

        return actual_motto

    def is_repeat_message(self, message: Message, check_id=True) -> str:
        filter_motto = self.clean_message(message).replace("'", r"\'")
        filter_formula = f"REGEX_REPLACE(REGEX_REPLACE(LOWER(TRIM('{filter_motto}')), '[^\w ]+', ''), '\s+', ' ') = REGEX_REPLACE(REGEX_REPLACE(LOWER(TRIM({{Motto}})), '[^\w ]+', ''), '\s+', ' ')"
        if check_id:
            filter_formula = (
                f"OR({filter_formula}, '{str(message.id)}' = {{Message ID}})"
            )
        log.debug("Searching with filter %r", filter_formula)
        matching_mottos = self.mottos.get_all(filterByFormula=filter_formula)
        return bool(matching_mottos)

    def is_valid_message(self, message: Message) -> bool:
        if (
            not all(r.search(message.content) for r in self.config["rules"]["matching"])
            or any(r.search(message.content) for r in self.config["rules"]["excluding"])
            or any(
                r.match(message.content) for r in self.config["triggers"]["new_motto"]
            )
        ):
            return False
        return True

    def get_name(self, member: Member):
        return member.nick if getattr(member, 'nick', None) else member.display_name

    async def get_or_add_member(self, member: Member):
        member_record = self.members.match("Discord ID", member.id)
        if not member_record:
            data = {}
            data["Username"] = member.name
            data["Discord ID"] = str(member.id)
            member_record = self.members.insert(data)
            log.debug(f"Added member {member_record} to AirTable")
        return member_record

    async def set_nick_option(self, member: Member, on=False):
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
            discord_nickname = self.get_name(member)

            if airtable_nickname != discord_nickname:
                update_dict["Nickname"] = discord_nickname
        elif member_record["fields"].get("Nickname"):
            update_dict["Nickname"] = ""

        if update_dict:
            log.debug(f"Recorded changes {update_dict}")
            self.members.update(member_record["id"], update_dict)

    async def update_emoji(self, member_record: dict, emoji: str):
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

    async def process_suggestion(self, message: Message):

        triggers = self.config["triggers"]["new_motto"]
        if self.config["trigger_on_mention"]:
            triggers = [re.compile(rf"^<@!{self.user.id}>")] + triggers

        if not any(
            t.match(message.content) for t in triggers
        ):
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

        actual_motto = self.clean_message(motto_message)

        if self.is_repeat_message(motto_message):
            await reactions.duplicate(self, message)
            return

        # Find the nominee and nominator
        nominee = await self.get_or_add_member(motto_message.author)
        nominator = await self.get_or_add_member(message.author)

        auto_approve = any(
            r.name.strip("'") == self.config["approval_opt_in_role"]
            for r in motto_message.author.roles
        )

        motto_data = {
            "Motto": actual_motto if auto_approve else "",
            "Message ID": str(motto_message.id),
            "Date": motto_message.created_at.isoformat(),
            "Member": [nominee["id"]],
            "Nominated By": [nominator["id"]],
            "Approved": not self.config["human_moderation_required"],
        }

        self.mottos.insert(motto_data)
        log.debug("Added Motto to AirTable")

        if auto_approve:
            await reactions.stored(self, message, motto_message)
        else:
            await reactions.pending(self, message, motto_message)

        await self.update_name(nominee, motto_message.author)
        await self.update_name(nominator, message.author)

    async def process_dm(self, message: Message):

        if message.author == self.user:
            return

        log.info(
            f"Received direct message (ID: {message.id}) from {message.author}: {message.content}"
        )

        message_content = message.content.lower().strip()

        if message_content in ("!help", "help", "help!", "halp", "halp!", "!halp"):
            await message.author.dm_channel.send(
                f"""
`!link`: Get a link to the leaderboard.
`!emoji <emoji>`: Set your emoji on the leaderboard. A response of {self.config["reactions"]["invalid_emoji"]} means the emoji you requested is not valid.
`!emoji`: Clear your emoji from the leaderboard.
`!nick on`: Use your server-specific nickname on the leaderboard instead of your Discord username.
`!nick off`: Use your Discord username on the leaderboard instead of your server-specific nickname.
`!delete`: Remove all your data from the leaderboard. Confirmation is required.
""".strip()
            )
            return

        if message_content == "!version":
            git_version = subprocess.check_output(["git", "describe", "--tags"]).decode("utf-8")
            await message.author.dm_channel.send(f"Version: {git_version}")
            return

        if message_content == "!link" and self.config["leaderboard_link"] != None:
            await message.author.dm_channel.send(self.config["leaderboard_link"])
            return

        if message_content.startswith("!nick"):
            try:
                _, option = message_content.split(None, 1)
            except ValueError:
                option = None
            if option == "on":
                await self.set_nick_option(message.author, on=True)
                await message.author.dm_channel.send("The leaderboard will now display your server-specific nickname instead of your Discord username. To return to your username, type `!nick off`.")
            elif option == "off":
                await self.set_nick_option(message.author, on=False)
                await message.author.dm_channel.send("The leaderboard will now display your Discord username instead of your server-specific nickname. To return to your nickname, type `!nick on`.")
            else:
                await message.author.dm_channel.send("To display your server-specific nickname on the leaderboard, type `!nick on`. To use your Discord username, type `!nick off`.")
            return

        if message_content == "!delete":
            sent_message = await message.reply(f"Are you sure you want to delete all your data from the leaderboard? This will include any mottos of yours that were nominated by other people. If so, react to this message with {self.config['confirm_delete_reaction']}. Otherwise, ignore this message.")
            await sent_message.add_reaction(self.config["reactions"]["pending"])
            return

        if message_content.startswith("!emoji"):
            try:
                _, content = message_content.split(None, 1)
            except ValueError:
                content = None
            else:
                content = content.strip().strip("\ufe0f")

            log.debug(f"User {message.author} wants to change emoji: {content!r}")

            if not content:
                log.debug(f"Removing emoji")
                member = await self.get_or_add_member(message.author)
                await self.update_emoji(member, emoji="")
                await reactions.valid_emoji(self, message)
            elif content in UNICODE_EMOJI["en"]:
                log.debug(f"Updating emoji")
                member = await self.get_or_add_member(message.author)
                await self.update_emoji(member, emoji=content)
                await reactions.valid_emoji(self, message)
            else:
                await reactions.invalid_emoji(self, message)

            return

        await reactions.unknown_dm(self, message)

    async def remove_unapproved_messages(self):

        # Don't do this for every message
        if random.random() < 0.1:
            for motto in self.mottos.search("Motto", ""):
                motto_date = datetime.strptime(motto['fields']['Date'], "%Y-%m-%dT%H:%M:%S.%f%z")
                motto_expiry_date = datetime.now(timezone.utc) - timedelta(hours=self.config['delete_unapproved_after_hours'])
                if motto_date < motto_expiry_date:
                    log.debug(f'Deleting motto {motto["id"]} - message ID {motto["fields"]["Message ID"]}')
                    self.mottos.delete(motto['id'])

