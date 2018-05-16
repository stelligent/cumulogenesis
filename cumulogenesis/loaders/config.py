'''
Provides methods that load/dump models to/from the config format.
Maps the loader used to the version provided.

Supported config versions and their loader mappings:

- _2018-05-04_: #cumulogenesis.loaders.config_loaders.default_config_loader.DefaultConfigLoader

Config version _default_ maps to _2018-05-04_. _default_ is used if no configuration
version is provided.
'''
from cumulogenesis.loaders.config_loaders.default_config_loader import DefaultConfigLoader
from cumulogenesis.log_handling import LOGGER as logger

_CONFIG_VERSIONS_TO_LOADERS = {
    "default": DefaultConfigLoader,
    "2018-05-04": DefaultConfigLoader}

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
    '''
    Generates an Organization model from the provided configuration. Uses the
    loader version provided in the `config` dict's _version_ key.
    '''
    config_version = config.get('version', None)
    loader = _get_config_loader_for_version(config_version)
    return loader.load_organization_from_config(config)

def dump_organization_to_config(organization, config_version=None):
    '''
    Generates configuration from the provided organization model
    '''
    loader = _get_config_loader_for_version(config_version)
    return loader.dump_organization_to_config(organization)
