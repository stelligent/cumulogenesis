'''
Unit tests for cumulogenesis.models.aws_entities.organization
'''

import unittest
from unittest import mock
from cumulogenesis import exceptions
from cumulogenesis import helpers
from cumulogenesis.models.aws_entities import Organization

class TestOrganization(unittest.TestCase):
    '''
    Tests for cumulogenesis.models.aws_entities.organization.Organization
    '''

    def setUp(self):
        '''
        Set up tests
        '''
        self.dummy_root_account_id = '123456789'

    def _get_base_organization(self):
        return Organization(root_account_id=self.dummy_root_account_id)

    @staticmethod
    def _add_name_to_entity_mocks(mock_dict):
        '''
        Helper to aid in adding "name" properties to mock.Mock instances
        '''
        for entity_name in mock_dict:
            mock_dict[entity_name]['name'] = entity_name
        return mock_dict

    def test_raise_if_invalid_when_invalid(self):
        '''
        Test Organization.raise_if_invalid when problems found

        When Organization.validate() returns problems, it should raise
        exceptions.InvalidOrganizationException
        '''
        with mock.patch('cumulogenesis.models.aws_entities.Organization.validate') as validate_mock:
            validate_mock.return_value = {"accounts": {"not-a-real-account": ["some_problem"]}}
            org = self._get_base_organization()
            with self.assertRaises(exceptions.InvalidOrganizationException):
                org.raise_if_invalid()

    def test_raise_if_invalid_when_valid(self):
        '''
        Test Organization.raise_if_invalid when no problems are found

        When Organization.validate() returns no problems, it should not raise
        exceptions.InvalidOrganizationException
        '''
        with mock.patch('cumulogenesis.models.aws_entities.Organization.validate') as validate_mock:
            validate_mock.return_value = {}
            org = self._get_base_organization()
            try:
                org.raise_if_invalid()
            except exceptions.InvalidOrganizationException:
                self.fail('exceptions.InvalidOrganizationException raised unexpectedly')

    def test_get_orgunit_hierarchy_valid(self):
        '''
        Test Organization._get_orgunit_hierarchy when no orphans

        When the Organization contains no orphans, a nested dict representing
        the Organizations's orgunit and account hierarchy should be returned
        that shouldn't contain the ORPHANED root key
        '''
        accounts_mock = {"account_a": {"parent_references": ["ou_a"]},
                         "account_b": {"parent_references": ["ou_b"]},
                         "account_c": {"parent_references": ["ou_c"]}}
        orgunits_mock = {"ou_a": {"child_orgunits": ["ou_b"], "accounts": ["account_a"], "parent_references": []},
                         "ou_b": {"child_orgunits": [], "accounts": ["account_b"], "parent_references": []},
                         "ou_c": {"child_orgunits": [], "accounts": ["account_c"], "parent_references": []}}
        org = self._get_base_organization()
        org.orgunits = self._add_name_to_entity_mocks(orgunits_mock)
        org.accounts = self._add_name_to_entity_mocks(accounts_mock)
        expected_hierarchy = {
            "ROOT_ACCOUNT": {
                "orgunits": {
                    "ou_a": {
                        "accounts": ["account_a"],
                        "orgunits": {
                            "ou_b": {"accounts": ["account_b"]}}},
                    "ou_c": {
                        "accounts": ["account_c"]}}}}
        hierarchy = org.get_orgunit_hierarchy()
        helpers.print_expected_actual_diff(expected_hierarchy, hierarchy)
        assert hierarchy == expected_hierarchy


    def test_get_orgunit_hierarchy_invalid_orphan(self):
        '''
        Test Organization._get_orgunit_hierarchy when orphans

        When the Organization contains orphans, the resulting hierarchy should
        contain an top level ORPHANED key containing the orphaned account.
        '''
        accounts_mock = {"account_a": {"parent_references": ["ou_a"]},
                         "account_b": {"parent_references": ["ou_b"]},
                         "account_c": {"parent_references": []}}
        orgunits_mock = {"ou_a": {"child_orgunits": ["ou_b"], "accounts": ["account_a"], "parent_references": []},
                         "ou_b": {"child_orgunits": [], "accounts": ["account_b"], "parent_references": []},
                         "ou_c": {"child_orgunits": [], "accounts": [], "parent_references": []}}
        org = self._get_base_organization()
        org.orgunits = self._add_name_to_entity_mocks(orgunits_mock)
        org.accounts = self._add_name_to_entity_mocks(accounts_mock)
        expected_hierarchy = {
            "ORPHANED_ACCOUNTS": ["account_c"],
            "ROOT_ACCOUNT": {
                "orgunits": {
                    "ou_a": {
                        "accounts": ["account_a"],
                        "orgunits": {
                            "ou_b": {"accounts": ["account_b"]}}},
                    "ou_c": {}}}}
        hierarchy = org.get_orgunit_hierarchy()
        helpers.print_expected_actual_diff(expected_hierarchy, hierarchy)
        assert hierarchy == expected_hierarchy

    def test_validate(self):
        '''
        Test Organization.validate

        This test should generate a problem for one of each potential
        invalid Organization state.
        '''
        orgunits_mock = {
            "missing_account": {"accounts": ["nonexistent"], "policies": [], "child_orgunits": []},
            "missing_policy": {"accounts": [], "policies": ["nonexistent"], "child_orgunits": []},
            "missing_orgunit": {"accounts": [], "policies": [], "child_orgunits": ["nonexistent"]},
            "valid_ou_a": {"accounts": ["multiple_references", "valid_account_a"],
                           "policies": [], "child_orgunits": []},
            "valid_ou_b": {"accounts": ["multiple_references"], "policies": [], "child_orgunits": []}}
        accounts_mock = {
            "orphaned_account": {"parent_references": None, "regions": ["us-east-1"]},
            "multiple_references": {"parent_references": None, "regions": ["us-east-1"]},
            "valid_account_a": {"parent_references": None, "regions": ["us-east-1"]}}
        org = self._get_base_organization()
        org.orgunits = self._add_name_to_entity_mocks(orgunits_mock)
        org.accounts = self._add_name_to_entity_mocks(accounts_mock)
        expected_problems = {'orgunits': {'missing_account': ['references missing account nonexistent'],
                                          'missing_orgunit': ['references missing child orgunit nonexistent'],
                                          'missing_policy': ['references missing policy nonexistent']},
                             'accounts': {'orphaned_account': ['orphaned'],
                                          #pylint: disable=line-too-long
                                          'multiple_references': ['referenced as a child of multiple orgunits: valid_ou_a, valid_ou_b']}}
        problems = org.validate()
        helpers.print_expected_actual_diff(expected_problems, problems)
        assert expected_problems == problems

    @mock.patch('cumulogenesis.models.aws_entities.Organization.raise_if_invalid')
    @mock.patch('cumulogenesis.models.aws_entities.Organization.initialize_aws_model')
    #pylint: disable=unused-argument
    def test_dry_run(self, initialize_mock, raise_mock):
        '''
        Test Organization.dry_run
        '''
        provisioner_overrides = {"profile": "foo"}
        provisioner = {"role": "bar"}
        expected_provisioner = {"profile": "foo", "role": "bar"}
        expected_report = {"actions": {}}
        with mock.patch('cumulogenesis.models.aws_entities.Organization.validate') as validate_mock:
            validate_mock.return_value = {"organization": "some_problem"}
            expected_compare_report_arg = {"aws_model_problems": {"organization": "some_problem"}}
            with mock.patch('cumulogenesis.models.aws_entities.Organization.compare_against_aws_model') as compare_mock:
                compare_mock.return_value = {"actions": {}}
                org_mock = self._get_base_organization()
                org_mock.aws_model = self._get_base_organization()
                org_mock.provisioner = provisioner
                report = org_mock.dry_run(provisioner_overrides=provisioner_overrides)
                helpers.print_expected_actual_diff(expected_report, report)
                compare_mock.assert_called_with(report=expected_compare_report_arg)
                assert expected_report == report
                helpers.print_expected_actual_diff(expected_provisioner, provisioner)
                assert org_mock.provisioner == expected_provisioner

    @staticmethod
    def _get_mock_org_service_instance():
        org_service_instance = mock.Mock
        org_service_instance.load_organization = mock.Mock()
        org_service_instance.load_accounts = mock.Mock()
        org_service_instance.load_orgunits = mock.Mock()
        org_service_instance.load_policies = mock.Mock()
        org_service_instance.load_organization.return_value = None
        org_service_instance.load_accounts.return_value = None
        org_service_instance.load_orgunits.return_value = None
        org_service_instance.load_policies.return_value = None
        return org_service_instance

    @mock.patch('cumulogenesis.models.aws_entities.Organization._get_session_builder')
    @mock.patch('cumulogenesis.models.aws_entities.organization.OrganizationService')
    #pylint: disable=unused-argument
    def test_load_not_exists(self, org_service_mock, session_builder_mock):
        '''
        Test Organization.load when the organization does not exist

        When Organization.exists is False after calling OrganizationService.load_organization,
        it should not attempt to load the rest of the Organization entities.
        '''
        org_mock = self._get_base_organization()
        org_service_instance = mock.Mock
        org_mock.source = "aws"
        org_mock.exists = False
        org_service_instance = self._get_mock_org_service_instance()
        org_service_mock.return_value = org_service_instance
        org_mock.provisioner = {"profile": "foo"}
        org_mock.load()
        org_service_instance.load_organization.assert_called()
        org_service_instance.load_accounts.assert_not_called()
        org_service_instance.load_orgunits.assert_not_called()
        org_service_instance.load_policies.assert_not_called()

    @mock.patch('cumulogenesis.models.aws_entities.Organization._get_session_builder')
    @mock.patch('cumulogenesis.models.aws_entities.organization.OrganizationService')
    #pylint: disable=unused-argument
    def test_load_exists(self, org_service_mock, session_builder_mock):
        '''
        Test Organization.load when the organization exists

        When Organization.exists is True after calling OrganizationService.load_organization,
        it should not attempt to load the rest of the Organization entities.
        '''
        org_mock = self._get_base_organization()
        org_service_instance = mock.Mock
        org_mock.source = "aws"
        org_mock.exists = True
        org_service_instance = self._get_mock_org_service_instance()
        org_service_mock.return_value = org_service_instance
        org_mock.provisioner = {"profile": "foo"}
        org_mock.load()
        org_service_instance.load_organization.assert_called()
        org_service_instance.load_accounts.assert_called()
        org_service_instance.load_orgunits.assert_called()
        org_service_instance.load_policies.assert_called()

    def test_load_not_aws(self):
        '''
        Test Organization.load when Organization source is not "aws"

        When the "source" attribute on the Organization on which load is called is
        not AWS, it should raise NotAwsModelException.
        '''
        org_mock = self._get_base_organization()
        org_mock.source = "config"
        with self.assertRaises(exceptions.NotAwsModelException):
            org_mock.load()
