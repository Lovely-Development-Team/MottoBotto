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

    async def on_ready(self):
        log.info('We have logged in as {0.user}'.format(self))

    async def on_message(self, message: Message):
        if message.content not in TRIGGER_PHRASES:
            return

        if is_botto(message, self.user):
            log.info(f'{message.author} attempted to activate Skynet!')
            await message.reply('Skynet prevention')
        elif not message.reference:
            await message.reply('I see no motto!')
        else:
            motto_message = message.reference.resolved
            
            if motto_message.author == message.author:
                log.info(f'Motto fishing from: "{motto_message.author}"')
                await message.add_reaction("🎣")
                return
            
            log.info(f'Motto suggestion incoming: "{motto_message.content}"')
            await message.add_reaction('👾')
            log.debug("Reaction added")
            await message.reply(f'"{motto_message.content}" will be considered!')
            log.debug("Reply sent")
