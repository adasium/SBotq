import logging
logging.basicConfig(
    level=logging.WARNING,
    format='[%(asctime)s] [%(levelname)8s] --- %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger
