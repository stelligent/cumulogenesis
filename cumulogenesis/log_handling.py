'''
Logging
'''
import logging

LOGGER = logging.getLogger('cumulogenesis')
LOGGER.setLevel(logging.DEBUG)
def enable_console_logging():
    '''
    Adds a StreamHandler to the logger to log to STDERR when called
    '''
    LOGGER.addHandler(logging.StreamHandler())
