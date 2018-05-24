"""
This module exports a Log class that wraps the logging python package

Uses the standard python logging utilities, just provides
nice formatting out of the box.

Usage:

    from insar.log import get_log
    logger = get_log()

    logger.info("Something happened")
    logger.warning("Something concerning happened")
    logger.error("Something bad happened")
    logger.critical("Something just awful happened")
    logger.debug("Extra printing we often don't need to see.")
    # Custom output for this module:
    logger.success("Something great happened: highlight this success")
"""
import argparse
import logging
import time

from colorlog import ColoredFormatter


def get_log(debug=False, name=__file__, verbose=False):
    """Creates a nice log format for use across multiple files.

    Default logging level is INFO

    Args:
        name (Optional[str]): The name the logger will use when printing statements
        debug (Optional[bool]): If true, sets logging level to DEBUG

    """
    logger = logging.getLogger(name)
    return format_log(logger, debug=debug, verbose=verbose)


def format_log(logger, debug=False, verbose=False):
    """Makes the logging output pretty and colored with times"""
    log_level = logging.DEBUG if debug else logging.INFO

    if debug:
        format_ = '[%(asctime)s] [%(log_color)s%(levelname)s/%(process)d %(filename)s %(reset)s] %(message)s%(reset)s'
    else:
        format_ = '[%(asctime)s] [%(log_color)s%(levelname)s %(filename)s%(reset)s] %(message)s%(reset)s'
    formatter = ColoredFormatter(
        format_,
        datefmt='%m/%d %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG': 'blue',
            'INFO': 'cyan',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'black,bg_red',
            'SUCCESS': 'white,bg_blue'
        })

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.SUCCESS = 25  # between WARNING and INFO
    logging.addLevelName(logging.SUCCESS, 'SUCCESS')
    setattr(logger, 'success', lambda message, *args: logger._log(logging.SUCCESS, message, args))

    if not logger.handlers:
        logger.addHandler(handler)
        logger.setLevel(log_level)

        if verbose:
            logger.info('Logger initialized: %s' % (logger.name, ))

    if debug:
        logger.setLevel(debug)

    return logger


logger = get_log()


def log_runtime(f):
    """
    Logs how long a decorated function takes to run

    Args:
        f (function): The function to wrap

    Returns:
        function: The wrapped function

    Example:
        >>> @log_runtime
        >>> def my_func():
        >>>     ...
        >>> my_func()
        "Total elapsed time for my_func (minutes): X.YZ

    """

    def wrapper(*args, **kwargs):
        t1 = time.time()

        result = f(*args, **kwargs)

        t2 = time.time()
        elapsed_time = t2 - t1
        time_string = 'Total elapsed time for {} (minutes): {}'.format(
            f.__name__, "{0:.2f}".format(elapsed_time / 60.0))

        logger.info(time_string)
        return result

    return wrapper


if __name__ == '__main__':
    # Example usage
    p = argparse.ArgumentParser()
    p.add_argument('--debug', action='store_true', required=False, help='Show debug output')

    args = p.parse_args()
    debug = args.debug or False

    log = get_log(debug=debug)

    log.critical('Sample critical')
    try:
        print(1 / 0)
    except ZeroDivisionError:
        log.exception('Sample exception (prints traceback by default)')
        log.error('Sample error (uses exc_info for traceback)', exc_info=True)
    log.error('Other kind of error.')
    log.warning('Sample warning')
    log.success('Sample SUCCESS!')
    log.debug('Sample debug')
