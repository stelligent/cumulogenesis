'''
Logging
'''
import logging

LOGGER = logging.getLogger('cumulogenesis')
LOGGER.setLevel(logging.DEBUG)

def enable_console_logging(level='INFO'):
    '''
    Adds a StreamHandler to the logger to log to STDERR when called
    '''
    if level:
        numeric_log_level = getattr(logging, level.upper(), None)
    LOGGER.setLevel(numeric_log_level)
    LOGGER.addHandler(logging.StreamHandler())
