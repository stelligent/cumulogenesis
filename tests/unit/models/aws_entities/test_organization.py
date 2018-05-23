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
        stacks_mock = {
            "missing_account": {"accounts": ["nonexistent"], "orgunits": []},
            "missing_orgunit": {"accounts": [], "orgunits": ["nonexistent"]},
            "valid_stack_a": {"accounts": ["valid_account_a"], "orgunits": []}}
        org = self._get_base_organization()
        org.orgunits = self._add_name_to_entity_mocks(orgunits_mock)
        org.accounts = self._add_name_to_entity_mocks(accounts_mock)
        org.stacks = self._add_name_to_entity_mocks(stacks_mock)
        expected_problems = {'orgunits': {'missing_account': ['references missing account nonexistent'],
                                          'missing_orgunit': ['references missing child orgunit nonexistent'],
                                          'missing_policy': ['references missing policy nonexistent']},
                             'accounts': {'orphaned_account': ['orphaned'],
                                          #pylint: disable=line-too-long
                                          'multiple_references': ['referenced as a child of multiple orgunits: valid_ou_a, valid_ou_b']},
                             'stacks': {'missing_account': ['references missing account nonexistent'],
                                        'missing_orgunit': ['references missing orgunit nonexistent']}}
        problems = org.validate()
        helpers.print_expected_actual_diff(expected_problems, problems)
        assert expected_problems == problems
