import configparser
import logging

config = configparser.ConfigParser()

log = logging.getLogger("MottoBotto")


def read_config() -> bool:
    """
    Reads in the config file.
    :return: True if successful, false otherwise
    """
    read_result = config.read('config.ini')
    return 'config.ini' in read_result


def get_discord_token() -> str:
    return config['authentication']['discord']
