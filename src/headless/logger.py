import logging
import sys

logger = logging.getLogger('headless-kivy-pi')
logger.setLevel(logging.INFO)
logger.propagate = False


def add_stdout_handler():
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(
        logging.Formatter(
            '%(created)f [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S',
        ),
    )
    logger.addHandler(stdout_handler)


def add_file_handler():
    file_handler = logging.FileHandler('headless-kivy-pi.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            '%(created)f [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S',
        ),
    )
    logger.addHandler(file_handler)


__all__ = ('logger', 'add_stdout_handler')
