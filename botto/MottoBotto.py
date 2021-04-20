import logging

import discord
from discord import Message

from message_checks import is_botto

log = logging.getLogger("MottoBotto")
log.setLevel(logging.DEBUG)


TRIGGER_PHRASES = (
    "!motto",
    "Accurate. New motto?",
)


class MottoBotto(discord.Client):
    def __init__(self, include_channels, exclude_channels, reactions, mottos, members):
        self.include_channels = include_channels or ()
        self.exclude_channels = exclude_channels or ()
        self.reactions = reactions
        self.mottos = mottos
        self.members = members
        super(MottoBotto, self).__init__()

    async def on_ready(self):
        log.info("We have logged in as {0.user}".format(self))

    async def add_reaction(self, message, reaction_type, default=None):
        if reaction := self.reactions.get(reaction_type, default):
            await message.add_reaction(reaction)

    async def on_message(self, message: Message):
        channel_name = message.channel.name

        if self.include_channels and channel_name not in self.include_channels:
            return
        else:
            if channel_name in self.exclude_channels:
                return

        if message.content not in TRIGGER_PHRASES:
            return

        if is_botto(message, self.user):
            log.info(f"{message.author} attempted to activate Skynet!")
            await self.add_reaction(message, "skynet", "❌")
            await message.reply("Skynet prevention")
        elif not message.reference:
            await self.add_reaction(message, "unknown", "❓")
            await message.reply("I see no motto!")
        else:
            motto_message = message.reference.resolved

            if motto_message.author == message.author:
                log.info(f'Motto fishing from: "{motto_message.author}"')
                await self.add_reaction(message, "fishing", "🎣")
                return

            log.info(f'Motto suggestion incoming: "{motto_message.content}"')

            actual_motto = motto_message.content
            filter_motto = actual_motto.replace("'", r"\'")

            filter_formula = f"REGEX_REPLACE(LOWER(TRIM('{filter_motto}')), '[^\w ]+', '') = REGEX_REPLACE(LOWER(TRIM({{Motto}})), '[^\w ]+', '')"
            log.debug("Searching with filter %r", filter_formula)
            matching_mottos = self.mottos.get_all(filterByFormula=filter_formula)
            if matching_mottos:
                log.debug("Ignoring motto, it's a duplicate.")
                await self.add_reaction(message, "repeat", "😅")
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

            await self.add_reaction(message, "success", "📥")
            log.debug("Reaction added")
            await message.reply(f'"{motto_message.content}" will be considered!')
            log.debug("Reply sent")

    async def get_or_add_member(self, member):
        member_record = self.members.match("Discord ID", member.id)
        if not member_record:
            member_data = {"Name": member.display_name, "Discord ID": str(member.id)}
            member_record = self.members.insert(member_data)
            log.debug(f"Added member {member_record} to AirTable")

        return member_record
