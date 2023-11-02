import pathlib
import sys

from loguru import logger
import logging

# root directory
ROOT_PATH = str(pathlib.Path(__file__).parent.parent)

logger.remove(0)
logger.add(sys.stderr, colorize=True)
logger.add(ROOT_PATH + '/logs.log', level='WARNING', rotation='100 MB', compression='zip', mode='a')
custom_logger = logger.bind(specific=True)

def get_file_handler(file_name, logging_level, log_format):
    fh = logging.FileHandler(f"{ROOT_PATH}/{file_name}", mode='a', encoding='utf-8')
    fh.setFormatter(log_format)
    fh.setLevel(logging_level)
    return fh

logger = logging.getLogger("logs")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(message)s')
file_handler = get_file_handler("logs_links.log", logging.INFO, formatter)
logger.addHandler(file_handler)
