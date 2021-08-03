from typing import Union

import discord


async def get_dm_channel(
    user: Union[discord.Member, discord.User]
) -> discord.DMChannel:
    return user.dm_channel if user.dm_channel else await user.create_dm()
