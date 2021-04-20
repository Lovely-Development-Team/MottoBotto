import logging

import discord
from discord import Message

from message_checks import is_botto

log = logging.getLogger("MottoBotto")
log.setLevel(logging.DEBUG)


class MottoBotto(discord.Client):
    def __init__(self, mottos, members):
        super(MottoBotto, self).__init__()

        self.mottos = mottos
        self.members = members

    async def on_ready(self):
        log.info("We have logged in as {0.user}".format(self))

    async def on_message(self, message: Message):
        if not message.content.startswith("!motto"):
            return

        if is_botto(message, self.user):
            log.info(f"{message.author} attempted to activate Skynet!")
            await message.reply("Skynet prevention")
        elif not message.reference:
            await message.reply("I see no motto!")
        else:
            motto_message = message.reference.resolved
            log.info(f'Motto suggestion incoming: "{motto_message.content}"')

            actual_motto = motto_message.content
            filter_motto = actual_motto.replace("'", r"\'")

            filter_formula = f"REGEX_REPLACE(LOWER(TRIM('{filter_motto}')), '[^\w ]+', '') = REGEX_REPLACE(LOWER(TRIM({{Motto}})), '[^\w ]+', '')"
            log.debug("Searching with filter %r", filter_formula)
            matching_mottos = self.mottos.get_all(filterByFormula=filter_formula)
            if matching_mottos:
                log.debug("Ignoring motto, it's a duplicate.")
                await message.add_reaction("♻️")
                return

            await message.add_reaction("📥")
            log.debug("Reaction added")
            await message.reply(f'"{motto_message.content}" will be considered!')
            log.debug("Reply sent")

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

    async def get_or_add_member(self, member):
        member_record = self.members.match("Discord ID", member.id)
        if not member_record:
            member_data = {"Name": member.display_name, "Discord ID": str(member.id)}
            member_record = self.members.insert(member_data)
            log.debug(f"Added member {member_record} to AirTable")

        return member_record
