import logging

from airtable import Airtable

from MottoBotto import MottoBotto
from config import read_config, get_discord_token, get_channels, get_airtable_tokens

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("MottoBotto")
log.setLevel(logging.DEBUG)

if not read_config():
    log.error("No config file present")
    exit(1)
discord_token = None
try:
    discord_token = get_discord_token()
    airtable_base_key, airtable_api_key = get_airtable_tokens()
except KeyError as error:
    log.error(f"Config missing required key: {error}")
    exit(1)

mottos = Airtable(airtable_base_key, "motto", airtable_api_key)
members = Airtable(airtable_base_key, "member", airtable_api_key)
include_channels, exclude_channels = get_channels()

client = MottoBotto(include_channels, exclude_channels, mottos, members)
client.run(discord_token)
