import logging
logging.basicConfig(
    level=logging.NOTSET,
    format='[%(asctime)s] [%(levelname)8s] --- %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger()
