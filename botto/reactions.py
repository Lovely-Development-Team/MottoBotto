import logging

from discord import Message, Member

import MottoBotto

log = logging.getLogger("MottoBotto").getChild("reactions")
log.setLevel(logging.DEBUG)


async def skynet_prevention(botto: MottoBotto, message: Message):
    log.info(f"{message.author} attempted to activate Skynet!")
    await botto.add_reaction(message, "skynet", "❌")
    if botto.should_reply:
        await message.reply("Skynet prevention")


async def not_reply(botto: MottoBotto, message: Message):
    log.info(
        f"Suggestion from {message.author} was not a reply (Message ID {message.id})"
    )
    await botto.add_reaction(message, "unknown", "❓")
    if botto.should_reply:
        await message.reply("I see no motto!")


async def fishing(botto: MottoBotto, message: Message):
    log.info(f'Motto fishing from: "{message.author}"')
    await botto.add_reaction(message, "fishing", "🎣")


async def duplicate(botto: MottoBotto, message: Message):
    log.debug("Ignoring motto, it's a duplicate.")
    await botto.add_reaction(message, "repeat", "😅")


async def stored(botto: MottoBotto, message: Message, motto_message: Message):
    await botto.add_reaction(message, "success", "📥")
    log.debug("Reaction added")
    if botto.should_reply:
        await message.reply(f'"{motto_message.content}" will be considered!')
    log.debug("Reply sent")
