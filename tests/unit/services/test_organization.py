'''
Tests for cumulogenesis.services.organization
'''

import unittest
from unittest import mock
import boto3
from botocore.stub import Stubber
from cumulogenesis.services.organization import OrganizationService
from cumulogenesis.models.aws_entities import Organization
from cumulogenesis import exceptions
from cumulogenesis import helpers

class TestOrganizationService(unittest.TestCase):
    '''
    Tests for cumulogenesis.services.organization.OrganizationService
    '''

    def setUp(self):
        client = boto3.client('organizations')
        self.stubber = Stubber(client)
        self.stubber.activate()
        base_session_mock = mock.Mock()
        base_session_mock.client.return_value = client
        self.session_builder_mock = mock.Mock()
        self.session_builder_mock.get_base_session.return_value = base_session_mock

    @staticmethod
    def _get_mock_org(**kwargs):
        return mock.Mock(spec=Organization, root_account_id='123456789', **kwargs)

    def _get_org_service(self):
        return OrganizationService(session_builder=self.session_builder_mock)

    def test_load_organization_not_exist(self):
        '''
        Tests OrganizationService.load_organization when the organization doesn't exist

        It should set organization.exists = False and should not call
        _set_organization_attributes
        '''
        with mock.patch.object(OrganizationService, '_set_organization_attributes') as _set_attributes_mock:
            org_service = self._get_org_service()
            self.stubber.add_client_error('describe_organization')
            org_mock = self._get_mock_org(exists=True)
            org_service.load_organization(organization=org_mock)
            assert org_mock.exists is False
            _set_attributes_mock.assert_not_called()

    def test_load_organization_exists(self):
        '''
        Tests OrganizationService.load_organization when the organization exists

        It should set organization.exists = False and should not call
        _set_organization_attributes
        '''
        with mock.patch.object(OrganizationService, '_set_organization_attributes') as _set_attributes_mock:
            org_service = self._get_org_service()
            describe_org_response = {
                'Organization': {
                    "Id": "o-123456789",
                    "MasterAccountId": "123456789"}}
            self.stubber.add_response('describe_organization', describe_org_response)
            org_mock = self._get_mock_org(exists=True)
            org_service.load_organization(organization=org_mock)
            assert org_mock.exists is True
            _set_attributes_mock.assert_called_with(org_model=org_mock,
                                                    describe_org_response=describe_org_response['Organization'])

    def test_set_organization_attributes_not_master(self):
        '''
        Tests OrganizationService._set_organization_attributes when the account is not master

        When the MasterAccountId for the organization does not match the root_account_id of
        the organization model, cumulogenesis.exceptions.OrganizationMemberAccountException
        should be raised
        '''
        with mock.patch.object(OrganizationService, '_get_root_parent_id'):
            with mock.patch.object(OrganizationService, '_set_org_ids_to_children'):
                org_service = self._get_org_service()
                describe_org_response = {
                    'MasterAccountId': '987654321'}
                org_mock = self._get_mock_org()
                with self.assertRaises(exceptions.OrganizationMemberAccountException):
                    org_service._set_organization_attributes(org_model=org_mock,
                                                             describe_org_response=describe_org_response)

    def test_set_organization_attributes(self):
        '''
        Tests OrganizationService._set_organization_attributes
        '''
        with mock.patch.object(OrganizationService, '_get_root_parent_id') as root_parent_id_mock:
            with mock.patch.object(OrganizationService, '_set_org_ids_to_children'):
                org_service = self._get_org_service()
                describe_org_response = {
                    'MasterAccountId': '123456789',
                    'FeatureSet': 'ALL',
                    'Id': 'o-123456789'}
                root_parent_id_mock.return_value = "r-1234"
                org_mock = self._get_mock_org()
                org_service._set_organization_attributes(org_model=org_mock,
                                                         describe_org_response=describe_org_response)
                assert org_mock.featureset == 'ALL'
                assert org_mock.org_id == 'o-123456789'
                assert org_mock.root_parent_id == 'r-1234'

    def test_get_root_parent_id(self):
        '''
        Tests OrganizationService._get_root_parent_id
        '''
        org_service = self._get_org_service()
        list_parents_response = {
            'Parents': [{
                'Type': 'ROOT',
                'Id': 'r-1234'}]}
        self.stubber.add_response('list_parents', list_parents_response)
        result = org_service._get_root_parent_id(root_account_id='123456789')
        assert result == 'r-1234'

    def test_set_org_ids_to_children(self):
        '''
        Tests OrganizationService._set_org_ids_to_children

        This tests the enumeration for an effective account hierarchy of:

        r-1234:
          orgunits:
            ou-123456789:
                accounts:
                    - 123456789
                orgunits:
                    ou-987654321: {}

        This test is sensitive to ordering and assumes that list_children will
        first be called with ChildType=ORGANIZATIONAL_UNIT and then
        ChildType=ACCOUNT in each iteration of the recursive function.
        '''
        child_orgunit_response1 = {"Children": [{"Id": "ou-123456789"}]}
        child_account_response2 = {"Children": [{"Id": "123456789"}]}
        child_orgunit_response2 = {"Children": [{"Id": "ou-987654321"}]}
        child_empty_response = {"Children": []}
        response_order = [
            # First iteration: orgunit, account
            child_orgunit_response1, child_empty_response,
            # Second iteration
            child_orgunit_response2, child_account_response2,
            # Third iteration
            child_empty_response, child_empty_response]
        # Set the stub responses in order
        for response in response_order:
            self.stubber.add_response('list_children', response)
        expected_ids_to_children = {
            "r-1234": {"orgunits": ["ou-123456789"], "accounts": []},
            "ou-123456789": {"orgunits": ["ou-987654321"], "accounts": ["123456789"]},
            "ou-987654321": {"orgunits": [], "accounts": []}}
        org_service = self._get_org_service()
        org_mock = self._get_mock_org(ids_to_children={})
        org_service._set_org_ids_to_children(org_model=org_mock, parent="r-1234")
        print("Expected:")
        helpers.pretty_print(expected_ids_to_children)
        print("\nActual:")
        helpers.pretty_print(org_mock.ids_to_children)
        print("\nDifference:")
        diff = helpers.deep_diff(expected_ids_to_children, org_mock.ids_to_children)
        helpers.pretty_print(diff)
        assert expected_ids_to_children == org_mock.ids_to_children
