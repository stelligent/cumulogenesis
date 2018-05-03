from cumulogenesis.loaders.config_loaders.default_config_loader import DefaultConfigLoader
from cumulogenesis.log_handling import LOGGER as logger

_CONFIG_VERSIONS_TO_LOADERS = {
    "default": DefaultConfigLoader,
    "0.1": DefaultConfigLoader}

def _get_config_loader_for_version(version):
    if version in _CONFIG_VERSIONS_TO_LOADERS:
        logger.info('Using config loader for config version %s', version)
        loader = _CONFIG_VERSIONS_TO_LOADERS[version]()
    else:
        #pylint: disable=line-too-long
        logger.info('No config loader found for specified config version, or config version not specified. Using default.')
        loader = _CONFIG_VERSIONS_TO_LOADERS['default']()
    return loader

def load_organization_from_config(config):
    config_version = config.get('version', None)
    loader = _get_config_loader_for_version(config_version)
    return loader.load_organization_from_config(config)

def dump_organization_to_config(organization, config_version=None):
    loader = _get_config_loader_for_version(config_version)
    return loader.dump_organization_to_config(organization)
