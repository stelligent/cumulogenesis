import logging

LOGGER = logging.getLogger('aws_bootstrap')
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(logging.StreamHandler())
