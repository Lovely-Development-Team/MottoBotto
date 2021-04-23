import json
import logging
import logging.config

from airtable import Airtable

from MottoBotto import MottoBotto
from config import parse

# Configure logging
logging.config.fileConfig(fname='log.conf', disable_existing_loggers=False)
log = logging.getLogger("MottoBotto")

try:
    config = parse(json.load(open("config.json")))
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

client = MottoBotto(config, mottos, members)
client.run(config["authentication"]["discord"])
