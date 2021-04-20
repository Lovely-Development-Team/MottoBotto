import configparser
import logging

config = configparser.ConfigParser()

log = logging.getLogger("MottoBotto")


def read_config() -> bool:
    """
    Reads in the config file.
    :return: True if successful, false otherwise
    """
    read_result = config.read("config.ini")
    return "config.ini" in read_result


def get_discord_token() -> str:
    return config["authentication"]["discord"]


def get_airtable_tokens() -> (str, str):
    return (
        config["authentication"]["airtable_base"],
        config["authentication"]["airtable_key"],
    )


def get_channels() -> (str, str):

    try:
        include = config.get('channels', 'include')
    except (configparser.NoSectionError, configparser.NoOptionError):
        include = ""

    try:
        exclude = config.get('channels', 'exclude')
    except (configparser.NoSectionError, configparser.NoOptionError):
        exclude = ""

    return (
        tuple(x.strip() for x in include.split(",")) if include else None,
        tuple(x.strip() for x in exclude.split(",")) if exclude else None,
    )


