from getenv import getenv
from logger import get_logger


logger = get_logger('settings')


DEFAULT_PREFIX = '!'
PREFIX = getenv('PREFIX', default='!')
COMMON_PREFIXES = ('!', '$', ';')
BETA_PREFIX = ';'

DB_URI = 'sqlite:///sbotq.db'
DISCORD_MESSAGE_LIMIT = 2000
MARKOV_MIN_WORD_COUNT = 3
RANDOM_MARKOV_MESSAGE_CHANCE = 0.0007
RANDOM_MARKOV_MESSAGE_COUNT = 4
TOKEN = getenv('TOKEN')


logger.info('============================== SETTINGS ==============================')
logger.info(f'PREFIX={PREFIX!r}')
logger.info('======================================================================')
