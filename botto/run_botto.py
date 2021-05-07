import os
import json
import logging
import logging.config

from airtable import Airtable

from MottoBotto import MottoBotto
from motto_storage import AirtableMottoStorage
from config import parse

# Configure logging
logging.config.fileConfig(fname="log.conf", disable_existing_loggers=False)
logging.getLogger("discord").setLevel(logging.CRITICAL)
logging.getLogger("discord.gateway").setLevel(logging.INFO)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("urllib").setLevel(logging.CRITICAL)
log = logging.getLogger("MottoBotto")

try:
    config_path = os.getenv("MOTTOBOTTO_CONFIG", "config.json")
    log.debug(f"Config path: %s", config_path)
    config = parse(json.load(open(config_path)))
except (IOError, OSError, ValueError) as err:
    log.error(f"Config file invalid: {err}")
    exit(1)

log.info(f"Triggers: {config['triggers']}")

mottos = Airtable(
    config["authentication"]["airtable_base"],
    "motto",
    config["authentication"]["airtable_key"],
)
members = Airtable(
    config["authentication"]["airtable_base"],
    "member",
    config["authentication"]["airtable_key"],
)

storage = AirtableMottoStorage(
    mottos,
    members,
    config["authentication"]["airtable_base"],
    config["authentication"]["airtable_key"],
    config["id"],
)

client = MottoBotto(config, storage)
client.run(config["authentication"]["discord"])
