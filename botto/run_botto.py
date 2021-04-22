import json
import logging

from airtable import Airtable

from MottoBotto import MottoBotto
from config import parse

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("MottoBotto")
log.setLevel(logging.DEBUG)

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
