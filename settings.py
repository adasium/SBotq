from getenv import getenv
from logger import get_logger


logger = get_logger('settings')


DEFAULT_PREFIX = getenv('PREFIX', default='!')
DB_URI = 'sqlite:///sbotq.db'
DISCORD_MESSAGE_LIMIT = 2000
MARKOV_MIN_WORD_COUNT = 3
RANDOM_MARKOV_MESSAGE_CHANCE = 0.0007
RANDOM_MARKOV_MESSAGE_COUNT = 4


logger.info('============================== SETTINGS ==============================')
logger.info(f'DEFAULT_PREFIX={DEFAULT_PREFIX!r}')
logger.info('======================================================================')
