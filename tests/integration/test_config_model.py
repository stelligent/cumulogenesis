'''
Integration tests for model loading/validation/dumping to/from config.
This serves as the primary test for the config loader system as well, though
edge cases may deserve their own unit tests as well.
'''
import unittest
import cumulogenesis.loaders.config as config_loader
from cumulogenesis import helpers

class TestConfigModel(unittest.TestCase):
    '''
    Integration tests for model loading/validation/dumping to/from config
    '''
    @staticmethod
    def _load_yaml_file(file_name):
        with open(file_name, 'r') as file_handle:
            config = helpers.ordered_yaml_load(file_handle)
        return config

    def _load_yaml_config_fixture(self, fixture):
        file_name = "tests/fixtures/config/%s.yaml" % fixture
        return self._load_yaml_file(file_name)

    def _load_yaml_hierarchy_fixture(self, fixture):
        file_name = "tests/fixtures/hierarchies/%s.yaml" % fixture
        return self._load_yaml_file(file_name)

    #pylint: disable=invalid-name
    def test_valid_model_configuration_2018_05_04(self):
        #pylint: disable=line-too-long
        '''
        Test loading/validating/dumping an Organization model from valid config for config version 2018-05-04

        When loading a valid organization, we expect the model to load without
        problems, the orgunit hierarchy to match what we expect, and for it to
        render into a comparable configuration to what was input.
        '''
        loader_version = '2018-05-04'
        fixture_name = 'valid-model-all-features-%s' % loader_version
        config = self._load_yaml_config_fixture(fixture_name)
        expected_hierarchy = self._load_yaml_hierarchy_fixture(fixture_name)
        org_model = config_loader.load_organization_from_config(config)
        problems = org_model.validate()
        print("Problems:")
        helpers.pretty_print(problems)
        assert not problems
        hierarchy = org_model.get_orgunit_hierarchy()
        assert hierarchy == expected_hierarchy
        rendered_config = config_loader.dump_organization_to_config(org_model, loader_version)
        helpers.print_expected_actual_diff(config, rendered_config)
        difference = helpers.deep_diff(config, rendered_config)
        assert difference == {}

    def test_invalid_model_orphaned_account_2018_05_04(self):
        #pylint: disable=line-too-long
        '''
        Test loading/validating/dumping an Organization model from an invalid config for config version 2018-05-04

        When the config contains an orphaned account, we expect Organization.validate()
        to return problems indicating the issue and for config.dump_organization_to_config()
        to raise exceptions.InvalidOrganizationException
        '''
        loader_version = '2018-05-04'
        fixture_name = 'invalid-model-orphaned-account-%s' % loader_version
        config = self._load_yaml_config_fixture(fixture_name)
        org_model = config_loader.load_organization_from_config(config)
        problems = org_model.validate()
        expected_problems = {"accounts": {"orphaned-account": ["orphaned"]}}
        assert expected_problems == problems
