import logging
from datetime import datetime

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
        log.info('We have logged in as {0.user}'.format(self))


    async def on_message(self, message: Message):
        if not message.content.startswith('!motto'):
            return

        if is_botto(message, self.user):
            log.info(f'{message.author} attempted to activate Skynet!')
            await message.reply('Skynet prevention')
        elif not message.reference:
            await message.reply('I see no motto!')
        else:
            motto_message = message.reference.resolved
            log.info(f'Motto suggestion incoming: "{motto_message.content}"')
            await message.add_reaction('👾')
            log.debug("Reaction added")
            await message.reply(f'"{motto_message.content}" will be considered!')
            log.debug("Reply sent")
            motto_data = {'Motto': motto_message.content,
                          "Message ID": str(motto_message.id),
                          "Date":motto_message.created_at.isoformat(),
                          # "Member":motto_message.author.display_name,
                          # "Nominated By": message.author.display_name
                          }
            self.mottos.insert(motto_data)
            log.debug("Added Motto to AirTable")