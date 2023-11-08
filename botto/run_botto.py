import os
import json
import logging.config

from MottoBotto import MottoBotto
from motto_storage import AirtableMottoStorage
from config import parse

# Configure logging
logging.config.fileConfig(fname="log.conf", disable_existing_loggers=False)
logging.getLogger("discord").setLevel(logging.ERROR)
logging.getLogger("discord.gateway").setLevel(logging.INFO)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("urllib").setLevel(logging.CRITICAL)
if should_log_to_file := os.getenv("LOG_TO_FILE"):
    if should_log_to_file == "false":
        logging.info("LOG_TO_FILE is false, removing FileHandlers")
        file_handlers = (handler for handler in logging.root.handlers if isinstance(handler, logging.FileHandler))
        for handler in file_handlers:
            logging.root.removeHandler(handler)
log = logging.getLogger("MottoBotto")

try:
    config_path = os.getenv("MOTTOBOTTO_CONFIG", "config.json")
    log.debug(f"Config path: %s", config_path)
    config_to_parse = {}
    if os.path.isfile(config_path):
        config_to_parse = json.load(open(config_path))
    config = parse(config_to_parse)
except (IOError, OSError, ValueError) as err:
    log.error(f"Config file invalid: {err}")
    exit(1)

log.info(f"Triggers: {config['triggers']}")

storage = AirtableMottoStorage(
    config["authentication"]["airtable_base"],
    config["authentication"]["airtable_key"],
    config["id"],
    config["random_source_view"]
)

client = MottoBotto(config, storage)
client.run(config["authentication"]["discord"])
