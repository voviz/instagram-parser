import pathlib
import sys

from loguru import logger

# root directory
ROOT_PATH = str(pathlib.Path(__file__).parent.parent)

logger.remove(0)
logger.add(sys.stderr, colorize=True)
logger.add(ROOT_PATH + '/logs.log', level='WARNING', rotation='100 MB', compression='zip', mode='a')
custom_logger = logger.bind(specific=True)