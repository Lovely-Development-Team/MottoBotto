import asyncio
import logging
import os
import random
import datetime
import re
from typing import Optional

from emoji import UNICODE_EMOJI
import subprocess

import discord
from discord import Message, DeletedReferencedMessage, Guild

import reactions
from regexes import SuggestionRegexes, compile_regexes
from message_checks import is_botto, is_dm

from models import Motto

log = logging.getLogger("MottoBotto")
log.setLevel(logging.DEBUG)


CHANNEL_REGEX = re.compile(r"<#(\d+)>")
NUMBERS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
]


class MottoBotto(discord.Client):
    def __init__(self, config: dict, motto_storage):
        self.config = config
        self.storage = motto_storage

        log.info(
            "Replies are enabled"
            if self.config["should_reply"]
            else "Replies are disabled"
        )
        log.info("Responding to phrases: %s", self.config["triggers"])
        log.info("Rules: %s", self.config["rules"])

        self.regexes: Optional[SuggestionRegexes] = None

        self._cache = {
            "random": {
                "users": {},
                "last": None,
            },
        }

        intents = discord.Intents(messages=True, guilds=True, reactions=True)
        super().__init__(intents=intents)

    async def on_connect(self):
        if not self.regexes and self.user:
            self.regexes = compile_regexes(self.user.id, self.config)

    async def on_ready(self):
        log.info("We have logged in as {0.user}".format(self))
        if not self.regexes:
            self.regexes = compile_regexes(self.user.id, self.config)

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=self.config["watching_status"],
            )
        )

    async def on_disconnect(self):
        log.warning("Bot disconnected")

    async def add_reaction(
        self, message: Message, reaction_type: str, default: str = None
    ):
        if reaction := self.config["reactions"].get(reaction_type, default):
            await message.add_reaction(reaction)

    async def on_raw_reaction_add(self, payload):

        if payload.emoji.name not in [
            self.config["approval_reaction"],
            self.config["confirm_delete_reaction"],
        ]:
            return

        log.info(f"Reaction received: {payload}")
        reactor = payload.member

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

            if isinstance(motto_message, DeletedReferencedMessage):
                log.info(f"Ignoring approval for a message that's been deleted.")
                await reactions.deleted(self, message)
                return

            log.info(f"Motto Message: {motto_message} / {motto_message.author.id}")
            if motto_message.author.id != payload.user_id:
                log.info(f"Ignoring approval from somebody other than motto author.")
                return

            motto = await self.storage.get_motto(message_id=motto_message.id)
            if not motto:
                log.info(f"Couldn't find matching message.")
                return

            trigger = None
            for t in self.triggers:
                if t.match(message.content):
                    trigger = t
                    break

            if not trigger:
                log.info(f"Ignoring approval on non-trigger message.")
                return

            trigger_message_content = self.clean_trigger_message(trigger, message.content)
            log.info(f"Trigger message content: {trigger_message_content!r}")

            if trigger_message_content:
                if trigger_message_content not in motto_message.content:
                    log.info(f"Ignoring approval on quoted exerpt {trigger_message_content!r} not found in existing message {motto_message.content!r}")
                    return
                actual_motto = self.clean_message(trigger_message_content, message.guild)

            else:
                actual_motto = self.clean_message(motto_message.content, motto_message.guild)

            if await self.is_repeat_message(motto_message, check_id=False):
                await self.storage.delete_motto(pk=motto.primary_key)
                await reactions.duplicate(self, message)
                return

            motto.motto = actual_motto
            motto.approved_by_author = True
            await self.storage.save_motto(motto, fields=["motto", "approved_by_author"])
            await reactions.stored(self, message, motto_message)

            nominee = await self.storage.get_or_add_member(reactor)
            nominator = await self.storage.get_or_add_member(message.author)
            await self.storage.update_name(nominee, reactor)
            await self.storage.update_name(nominator, message.author)

            return

        if payload.emoji.name == self.config["confirm_delete_reaction"]:

            if message.author != self.user:
                log.info(f"Ignoring message not by MottoBotto")
                return

            if not isinstance(channel, discord.DMChannel):
                log.info(f"Ignoring reaction not in DM")
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

            async with channel.typing():
                await self.storage.remove_all_data(payload.user_id)

                await message.remove_reaction(
                    self.config["reactions"]["pending"], self.user
                )
                await message.add_reaction(self.config["reactions"]["delete_confirmed"])
                await channel.send(
                    "All of your data has been removed. If you approve or nominate another motto in future, your user "
                    "data and any future approved mottos will be captured again. "
                )
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

        await self.process_suggestion(message)
        await self.remove_unapproved_messages()

    def clean_trigger_message(self, trigger, message) -> str:
        return trigger.sub("", message).strip().strip("'\"”“")

    def clean_message(self, actual_motto: str, guild: Guild) -> str:

        for channel_id in CHANNEL_REGEX.findall(actual_motto):
            channel = self.get_channel(int(channel_id))
            if not channel:
                continue
            actual_motto = actual_motto.replace(f"<#{channel_id}>", f"#{channel.name}")

        server_emojis = {x.name: str(x) for x in guild.emojis}
        for emoji in server_emojis:
            if server_emojis[emoji] in actual_motto:
                actual_motto = actual_motto.replace(server_emojis[emoji], f":{emoji}:")

        return actual_motto

    async def is_repeat_message(self, message: Message, check_id=True) -> bool:
        matching_mottos = await self.storage.get_matching_mottos(
            self.clean_message(message.content, message.guild), message_id=message.id if check_id else None
        )
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

    def is_random_request_allowed(self, user):

        now = datetime.datetime.now()
        oldest = datetime.datetime(1970, 1, 1, 0, 0, 0)

        last_random = self._cache["random"]["last"] or oldest
        allowed = last_random + datetime.timedelta(minutes=self.config["minimum_random_interval_minutes"])
        if allowed < now:

            last_random_for_user = self._cache["random"]["users"].get(user, oldest)
            allowed = last_random_for_user + datetime.timedelta(minutes=self.config["minimum_random_interval_minutes_per_user"])
            if allowed < now:

                self._cache["random"]["users"][user] = now
                self._cache["random"]["last"] = now
                return True

            else:

                log.info(f"{user} not allowed to request a random motto until {allowed}")
                return False

        else:
            log.info(f"Nobody allowed to request a random motto until {allowed}")
            return False

    async def process_tag(self, message: Message, content: list):

        log.info(f"Tagged message incoming: {message.content} / {content}")

        if not content:
            await reactions.wave(self, message)
            return

        content = content[0].strip()

        if partial := self.regexes.tags.random.findall(content):

            log.info(f"Call to !random with regex: {partial!r} from {message.author}")

            if not self.is_random_request_allowed(message.author):
                await reactions.rate_limit(self, message)
                return

            partial = partial[0]
            try:
                partial_regex = re.compile(partial, re.IGNORECASE)
            except re.error:
                partial_regex = None

            async with message.channel.typing():
                motto = await self.storage.get_random_motto(search=partial, search_regex=partial_regex)
                log.info(f"Got random motto! {motto}")
                if not motto:
                    await reactions.shrug(self, message)
                else:
                    await message.reply(f"{motto.motto}—{motto.member.display_name}")

        return

    @property
    def triggers(self):
        triggers = self.config["triggers"]["new_motto"]
        if self.config["trigger_on_mention"]:
            triggers = self.regexes.trigger + triggers
        return triggers

    async def process_suggestion(self, message: Message):

        if (result := self.regexes.tag.findall(message.content)) and not message.reference:
            await self.process_tag(message, result)
            return

        trigger = None
        for t in self.triggers:
            if t.match(message.content):
                trigger = t
                break

        if not trigger:

            if self.regexes.pokes.search(message.content):
                await reactions.poke(self, message)
            if self.regexes.sorry.search(message.content):
                await reactions.love(self, message)
            if self.regexes.love.search(message.content):
                await reactions.love(self, message)
            if self.regexes.hug.search(message.content):
                await reactions.hug(self, message)
            if self.regexes.band.search(message.content):
                await reactions.favorite_band(self, message)
            if message.content.strip().lower() in ("i am 🐌", "i am snail"):
                await reactions.snail(self, message)
            if self.regexes.cow.search(message.content):
                await reactions.cow(self, message)
            if food := self.regexes.food.food_regex.search(message.content):
                food_char = food.group(1)
                await reactions.food(self, message, food_char)
            elif self.regexes.food.not_food_regex.search(message.content):
                await reactions.unrecognised_food(self, message)

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

        trigger_message_content = self.clean_trigger_message(trigger, message.content)
        log.info(f"Trigger message content: {trigger_message_content!r}")

        if trigger_message_content and trigger_message_content not in motto_message.content:
            log.info(f"Quoted exerpt {trigger_message_content!r} not found in existing message {motto_message.content!r}")
            await reactions.not_reply(self, message)
            return

        if await self.is_repeat_message(motto_message):
            await reactions.duplicate(self, message)
            return

        # Find the nominee and nominator
        try:
            nominee, nominator = await asyncio.gather(
                self.storage.get_or_add_member(motto_message.author),
                self.storage.get_or_add_member(message.author),
            )
            log.info(
                f"Fetched/added nominee {nominee.username!r} and nominator {nominator.username!r}"
            )

            motto = Motto(
                motto="",
                message_id=str(motto_message.id),
                date=motto_message.created_at,
                member=nominee,
                nominated_by=nominator,
                approved=not self.config["human_moderation_required"],
                bot_id=self.config["id"],
            )
            await self.storage.save_motto(motto)
            log.info(f"Added Motto from message ID {motto.message_id} to AirTable")

            await reactions.pending(self, message, motto_message)

            await asyncio.gather(
                self.storage.update_name(nominee, motto_message.author),
                self.storage.update_name(nominator, message.author),
            )
            log.debug("Updated names in airtable")
        except Exception as e:
            log.error("Failed to process suggestion", exc_info=True)
            raise e

    async def process_dm(self, message: Message):

        if message.author == self.user:
            return

        log.info(
            f"Received direct message (ID: {message.id}) from {message.author}: {message.content}"
        )
        await message.channel.trigger_typing()

        message_content = message.content.lower().strip()

        if message_content in ("!help", "help", "help!", "halp", "halp!", "!halp"):
            trigger = (
                f"@{self.user.display_name}"
                if self.config["trigger_on_mention"]
                else "a trigger word"
            )

            help_message = f"""
Reply to a great motto in the supported channels with {trigger} to tell me about it! You can nominate a section of a message with \"{trigger} <excerpt>\". (Note: you can't nominate yourself.)

To get inspired, tag me in a supported channel with `@{self.user.display_name} !random`. I'll reply with a hand-selected motto from our database. You can only do this once every {self.config["minimum_random_interval_minutes_per_user"]} minutes, though, and others will have to wait {self.config["minimum_random_interval_minutes"]} minutes before they can do it too.

You can DM me the following commands:
`!random`: Get a random motto.
`!leaderboard`: Display the top motto authors.
`!link`: Get a link to the leaderboard.
`!emoji <emoji>`: Set your emoji on the leaderboard. A response of {self.config["reactions"]["invalid_emoji"]} means the emoji you requested is not valid.
`!emoji`: Clear your emoji from the leaderboard.
`!nick on`: Use your server-specific nickname on the leaderboard instead of your Discord username. Nickname changes will auto-update the next time you approve a motto.
`!nick off`: Use your Discord username on the leaderboard instead of your server-specific nickname.
`!delete`: Remove all your data from MottoBotto. Confirmation is required.
""".strip()

            help_channel = self.config["support_channel"]
            users = ", ".join(
                f"<@{user.discord_id}>" for user in await self.storage.get_support_users()
            )

            if help_channel or users:
                message_add = "\nIf your question was not answered here, please"
                if help_channel:
                    message_add = f"{message_add} ask for help in #{help_channel}"
                    if users:
                        message_add = f"{message_add}, or"
                if users:
                    message_add = f"{message_add} DM one of the following users: {users}. They are happy to receive your DMs about MottoBotto without prior permission but otherwise usual rules apply"
                help_message = f"{help_message}\n{message_add}."

            await message.author.dm_channel.send(help_message)
            return

        if message_content == "!leaderboard":
            leaders = await self.storage.get_leaders(count=5)

            if not leaders:
                await message.author.dm_channel.send(
                    "There doesn't appear to be anybody on the leaderboard!"
                )
                return

            leaders_message = ""
            previous_count = None
            previous_position = 1
            for position, leader in enumerate(leaders, 1):
                pos = (
                    previous_position
                    if previous_count == leader.motto_count
                    else position
                )
                plural = "s" if leader.motto_count > 1 else ""
                leaders_message = f"{leaders_message}:{NUMBERS[pos]}: <@{leader.discord_id}> {leader.display_name} ({leader.motto_count} motto{plural})\n"
                if previous_count != leader.motto_count:
                    previous_count = leader.motto_count
                    previous_position = position
            await message.author.dm_channel.send(leaders_message)
            return

        if message_content == "!version":
            git_version = os.getenv("MOTTOBOTTO_VERSION", "🤷")
            try:
                git_version = (
                    subprocess.check_output(["git", "describe", "--tags"])
                    .decode("utf-8")
                    .strip()
                )
            except subprocess.CalledProcessError as error:
                log.warning(
                    "Git command failed with code: {code}".format(code=error.returncode)
                )
            except FileNotFoundError:
                log.warning(
                    "Git command not found"
                )
            response = f"Version: {git_version}"
            if bot_id := self.config["id"]:
                response = f"{response} ({bot_id})"
            await message.author.dm_channel.send(response)
            return

        if message_content.startswith("!random"):

            partial = None
            partial_regex = None

            parts = message_content.split(None, 1)
            if len(parts) > 1:
                partial = parts[-1]
                try:
                    partial_regex = re.compile(partial, re.IGNORECASE)
                except re.error:
                    partial_regex = None

            async with message.author.dm_channel.typing():
                random_motto = await self.storage.get_random_motto(search=partial, search_regex=partial_regex)
                if not random_motto:
                    await message.author.dm_channel.send("Sorry mate, I'm all out.")
                    return
                await message.author.dm_channel.send(
                    f"{random_motto.motto}—{random_motto.member.display_name}"
                )
            return

        if message_content == "!link" and self.config["leaderboard_link"] is not None:
            await message.author.dm_channel.send(self.config["leaderboard_link"])
            return

        if message_content.startswith("!nick"):
            try:
                _, option = message_content.split(None, 1)
            except ValueError:
                option = None
            if option == "on":
                await self.storage.set_nick_option(message.author, on=True)
                await message.author.dm_channel.send(
                    "The leaderboard will now display your server-specific nickname instead of your Discord username. "
                    "To return to your username, type `!nick off`. "
                )
            elif option == "off":
                await self.storage.set_nick_option(message.author, on=False)
                await message.author.dm_channel.send(
                    "The leaderboard will now display your Discord username instead of your server-specific nickname. "
                    "To return to your nickname, type `!nick on`. "
                )
            else:
                await message.author.dm_channel.send(
                    "To display your server-specific nickname on the leaderboard, type `!nick on`. To use your "
                    "Discord username, type `!nick off`. "
                )
            return

        if message_content == "!delete":
            sent_message = await message.reply(
                "Are you sure you want to delete all your data from the leaderboard? This will include any mottos of "
                "yours that were nominated by other people. If so, react to this message with "
                f"{self.config['confirm_delete_reaction']}. Otherwise, ignore this message. "
            )
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
                member = await self.storage.get_or_add_member(message.author)
                await self.storage.update_emoji(member, emoji="")
                await reactions.valid_emoji(self, message)
            elif content in UNICODE_EMOJI["en"]:
                log.debug(f"Updating emoji")
                member = await self.storage.get_or_add_member(message.author)
                await self.storage.update_emoji(member, emoji=content)
                await reactions.valid_emoji(self, message)
            else:
                await reactions.invalid_emoji(self, message)

            return

        await reactions.unknown_dm(self, message)

    async def remove_unapproved_messages(self):
        # Don't do this for every message
        if random.random() < 0.1:
            await self.storage.remove_unapproved_messages(
                self.config["delete_unapproved_after_hours"]
            )
