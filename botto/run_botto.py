import logging

from MottoBotto import MottoBotto
from config import read_config, get_discord_token

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("MottoBotto")
log.setLevel(logging.DEBUG)

if not read_config():
    log.error('No config file present')
    exit(1)
discord_token = None
try:
    discord_token = get_discord_token()
except KeyError as error:
    log.error(f'Config missing required key: {error}')
    exit(1)

client = MottoBotto()

client.run(discord_token)
