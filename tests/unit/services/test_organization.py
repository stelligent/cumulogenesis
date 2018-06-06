'''
Tests for cumulogenesis.services.organization
'''

import unittest
from unittest import mock
from collections import OrderedDict
import boto3
from botocore.stub import Stubber
from cumulogenesis.services.organization import OrganizationService
from cumulogenesis.models.aws_entities import Organization
from cumulogenesis import exceptions
from cumulogenesis import helpers

#pylint: disable=too-many-public-methods
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

        This tests the enumeration for an effective organization hierarchy of:

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
        child_orgunit_response2 = {"Children": [{"Id": "ou-987654321"}]}
        child_account_response2 = {"Children": [{"Id": "123456789"}]}
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
        helpers.print_expected_actual_diff(expected_ids_to_children, org_mock.ids_to_children)
        assert expected_ids_to_children == org_mock.ids_to_children

    def test_load_orgunits(self):
        '''
        Tests OrganizationService.load_orgunits

        This tests the loading of orgunits for an effective organization hierarchy of:

        r-1234:
          orgunits:
            ou-123456789:
                accounts:
                    - 123456789
                orgunits:
                    ou-987654321: {}
        '''
        ids_to_children_mock = {
            "r-1234": {"orgunits": ["ou-123456789"], "accounts": []},
            "ou-123456789": {"orgunits": ["ou-987654321"], "accounts": ["123456789"]},
            "ou-987654321": {"orgunits": [], "accounts": []}}
        desc_ou_response1 = {
            "OrganizationalUnit": {
                "Id": "ou-123456789", "Name": "orgunit_a"}}
        desc_ou_response2 = {
            "OrganizationalUnit": {
                "Id": "ou-987654321", "Name": "orgunit_b"}}
        for response in [desc_ou_response1, desc_ou_response2]:
            self.stubber.add_response('describe_organizational_unit', response)
        account_ids_to_names_mock = {"123456789": "account_a"}
        orgunit_ids_to_names_mock = {
            "ou-123456789": "orgunit_a",
            "ou-987654321": "orgunit_b"}
        expected_orgunits = {
            "orgunit_a": {
                "id": "ou-123456789", "name": "orgunit_a",
                "child_orgunits": ["orgunit_b"], "accounts": ["account_a"]},
            "orgunit_b": {
                "id": "ou-987654321", "name": "orgunit_b",
                "child_orgunits": [], "accounts": []}}
        org_mock = self._get_mock_org(ids_to_children=ids_to_children_mock,
                                      account_ids_to_names=account_ids_to_names_mock,
                                      orgunit_ids_to_names=orgunit_ids_to_names_mock,
                                      root_parent_id="r-1234", orgunits={})
        org_service = self._get_org_service()
        org_service.load_orgunits(organization=org_mock)
        helpers.print_expected_actual_diff(expected_orgunits, org_mock.orgunits)
        assert expected_orgunits == org_mock.orgunits

    def test_load_policies(self):
        '''
        Tests OrganizationService.load_policies
        '''
        list_policies_response = {
            "Policies": [
                {"Id": "p-123456", "Name": "PolicyOne",
                 "Description": "The first policy", "AwsManaged": True}]}
        describe_policy_response = {
            "Policy": {
                "Content": '{"This": "is a mock JSON document"}'}}
        #pylint: disable=invalid-name
        list_targets_for_policy_response = {
            "Targets": [
                {"Type": "Mock"}]}
        self.stubber.add_response('list_policies', list_policies_response)
        self.stubber.add_response('describe_policy', describe_policy_response)
        self.stubber.add_response('list_targets_for_policy', list_targets_for_policy_response)
        expected_document_content = OrderedDict({"This": "is a mock JSON document"})
        expected_policies = {
            "PolicyOne": {"id": "p-123456", "description": "The first policy",
                          "aws_managed": True, "name": "PolicyOne",
                          "document": {"content": expected_document_content}}}
        org_mock = self._get_mock_org(policies={})
        with mock.patch.object(OrganizationService, "_add_policy_to_target") as policy_to_target_mock:
            org_service = self._get_org_service()
            org_service.load_policies(organization=org_mock)
            policy_to_target_mock.assert_called_with(
                org_model=org_mock, target=list_targets_for_policy_response['Targets'][0],
                policy_name="PolicyOne")
            helpers.print_expected_actual_diff(expected_policies, org_mock.policies)
            assert expected_policies == org_mock.policies

    def test_add_policy_to_target_root(self):
        '''
        Tests OrganizationService._add_policy_to_target when the target type is ROOT
        '''
        mock_policy_name = "SomePolicy"
        target_mock = {"Type": "ROOT"}
        expected_policies = ["SomePolicy"]
        org_mock = self._get_mock_org(root_policies=[])
        org_service = self._get_org_service()
        org_service._add_policy_to_target(org_model=org_mock, target=target_mock,
                                          policy_name=mock_policy_name)
        helpers.print_expected_actual_diff(expected_policies, org_mock.root_policies)
        assert org_mock.root_policies == expected_policies

    def test_add_policy_to_target_account(self):
        '''
        Tests OrganizationService._add_policy_to_target when the target type is ACCOUNT
        '''
        mock_policy_name = "SomePolicy"
        target_mock = {"Type": "ACCOUNT", "Name": "account_a"}
        mock_accounts = {"account_a": {}}
        expected_accounts = {"account_a": {"policies": [mock_policy_name]}}
        org_mock = self._get_mock_org(accounts=mock_accounts)
        org_service = self._get_org_service()
        org_service._add_policy_to_target(org_model=org_mock, target=target_mock,
                                          policy_name=mock_policy_name)
        helpers.print_expected_actual_diff(expected_accounts, org_mock.accounts)
        assert expected_accounts == org_mock.accounts

    def test_add_policy_to_target_orgunit(self):
        '''
        Tests OrganizationService._add_policy_to_target when the target type is ORGANIZATIONAL_UNIT
        '''
        mock_policy_name = "SomePolicy"
        target_mock = {"Type": "ORGANIZATIONAL_UNIT", "Name": "orgunit_a"}
        mock_orgunits = {"orgunit_a": {}}
        expected_orgunits = {"orgunit_a": {"policies": [mock_policy_name]}}
        org_mock = self._get_mock_org(orgunits=mock_orgunits)
        org_service = self._get_org_service()
        org_service._add_policy_to_target(org_model=org_mock, target=target_mock,
                                          policy_name=mock_policy_name)
        helpers.print_expected_actual_diff(expected_orgunits, org_mock.orgunits)
        assert expected_orgunits == org_mock.orgunits

    def test_load_accounts(self):
        '''
        Tests OrganizationService.load_accounts
        '''
        list_accounts_response = {
            "Accounts": [{
                "Name": "account_a", "Email": "foo@bar.com",
                "Id": "123456789"}]}
        self.stubber.add_response('list_accounts', list_accounts_response)
        expected_accounts = {
            "account_a": {
                "name": "account_a", "owner": "foo@bar.com",
                "id": "123456789", "regions": []}}
        expected_account_ids_to_names = {
            "123456789": "account_a"}
        org_mock = self._get_mock_org(accounts={}, account_ids_to_names={})
        org_service = self._get_org_service()
        org_service.load_accounts(org_mock)
        helpers.print_expected_actual_diff(expected_accounts, org_mock.accounts)
        assert expected_accounts == org_mock.accounts
        helpers.print_expected_actual_diff(expected_account_ids_to_names,
                                           org_mock.account_ids_to_names)
        assert expected_account_ids_to_names == org_mock.account_ids_to_names

    def test_upsert_organization(self):
        '''
        Tests OrganizationService.upsert_organization when the action is create
        '''
        actions = {'organization': {'action': 'create'}}
        list_parents_response = {
            'Parents': [
                {'Id': 'r-1234', 'Type': 'ROOT'}]}
        expected_create_params = {'FeatureSet': 'ALL'}
        expected_list_parents_params = {'ChildId': '123456789'}
        expected_enable_policy_params = {
            'RootId': 'r-1234', 'PolicyType': 'SERVICE_CONTROL_POLICY'}
        self.stubber.add_response('create_organization', {'Organization': {}},
                                  expected_create_params)
        self.stubber.add_response('list_parents', list_parents_response,
                                  expected_list_parents_params)
        self.stubber.add_response('enable_policy_type', {'Root': {}},
                                  expected_enable_policy_params)
        expected_changes = {"organization": {"change": "created"}}
        org_mock = self._get_mock_org(featureset='ALL', root_parent_id=None)
        org_service = self._get_org_service()
        changes = org_service.upsert_organization(organization=org_mock, actions=actions)
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert expected_changes == changes

    def test_upsert_organization_exists(self):
        '''
        Tests OrganizationService.upsert_organization when the action is not create
        '''
        actions = {'organization': {'action': 'update'}}
        expected_changes = {}
        org_mock = self._get_mock_org(featureset='ALL', root_parent_id=None)
        org_service = self._get_org_service()
        changes = org_service.upsert_organization(organization=org_mock, actions=actions)
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert expected_changes == changes

    def test_update_orgunit_policies(self):
        '''
        Tests OrganizationService.update_orgunit_policies with changes
        '''
        orgunit_mock = {'orgunit_a': {
            "id": "ou-123456",
            "policies": ["foo", "bar"]}}
        aws_orgunit_mock = {'orgunit_a': {
            "id": "ou-123456",
            "policies": ["bar", "baz"]}}
        aws_org_mock = self._get_mock_org(orgunits=aws_orgunit_mock)
        org_mock = self._get_mock_org(orgunits=orgunit_mock, aws_model=aws_org_mock, updated_model=aws_org_mock)
        with mock.patch.object(OrganizationService, 'update_entity_policy_attachments') as update_policy_mock:
            org_service = self._get_org_service()
            org_service.update_orgunit_policies(organization=org_mock, orgunit_name="orgunit_a")
            print(update_policy_mock.call_args_list)
            update_policy_mock.assert_called_with(
                new_policies=["foo", "bar"], old_policies=["bar", "baz"],
                org_model=org_mock, target_id="ou-123456")

    def test_update_orgunit_policies_no_changes(self):
        '''
        Tests OrganizationService.update_orgunit_policies with no changes
        '''
        orgunit_mock = {'orgunit_a': {
            "id": "ou-123456",
            "policies": ["foo", "bar"]}}
        aws_orgunit_mock = {'orgunit_a': {
            "id": "ou-123456",
            "policies": ["foo", "bar"]}}
        aws_org_mock = self._get_mock_org(orgunits=aws_orgunit_mock)
        org_mock = self._get_mock_org(orgunits=orgunit_mock, aws_model=aws_org_mock, updated_model=aws_org_mock)
        with mock.patch.object(OrganizationService, 'update_entity_policy_attachments') as update_policy_mock:
            org_service = self._get_org_service()
            org_service.update_orgunit_policies(organization=org_mock, orgunit_name="orgunit_a")
            update_policy_mock.assert_not_called()

    def test_update_entity_policy_attachments(self):
        '''
        Tests OrganizationService.update_entity_policy_attachments
        '''
        target_id = 'ou-123456'
        policies_mock = {
            "policy_a": {'id': 'p-a'},
            "policy_b": {'id': 'p-b'},
            "policy_c": {'id': 'p-c'}}
        old_policies = ["policy_a", "policy_b"]
        new_policies = ["policy_b", "policy_c"]
        expected_attach_parameters = {
            "PolicyId": "p-c", "TargetId": "ou-123456"}
        expected_detach_parameters = {
            "PolicyId": "p-a", "TargetId": "ou-123456"}
        self.stubber.add_response('attach_policy', {}, expected_attach_parameters)
        self.stubber.add_response('detach_policy', {}, expected_detach_parameters)
        updated_org_mock = self._get_mock_org(policies=policies_mock)
        org_mock = self._get_mock_org(updated_model=updated_org_mock)
        org_service = self._get_org_service()
        org_service.update_entity_policy_attachments(
            target_id=target_id, org_model=org_mock, old_policies=old_policies,
            new_policies=new_policies)

    def test_create_orgunit_root_parent(self):
        '''
        Tests OrganizationService.create_orgunit when the orgunit has the root as its parent
        '''
        create_orgunit_response = {
            "OrganizationalUnit": {"Id": "ou-123456"}}
        expected_create_orgunit_params = {"ParentId": "r-1234", "Name": "orgunit_a"}
        self.stubber.add_response(
            "create_organizational_unit", create_orgunit_response, expected_create_orgunit_params)
        orgunits_mock = {"orgunit_a": {"name": "orgunit_a"}}
        updated_org_mock = self._get_mock_org(root_parent_id='r-1234')
        org_mock = self._get_mock_org(orgunits=orgunits_mock, updated_model=updated_org_mock)
        org_service = self._get_org_service()
        orgunit_id = org_service.create_orgunit(org_model=org_mock, orgunit_name="orgunit_a",
                                                parent_name="root")
        assert orgunit_id == "ou-123456"

    def test_create_orgunit_orgunit_parent(self):
        '''
        Tests OrganizationService.create_orgunit when the orgunit has an orgunit as its parent
        '''
        create_orgunit_response = {
            "OrganizationalUnit": {"Id": "ou-123456"}}
        expected_create_orgunit_params = {"ParentId": "ou-654321", "Name": "orgunit_a"}
        self.stubber.add_response(
            "create_organizational_unit", create_orgunit_response, expected_create_orgunit_params)
        orgunits_mock = {"orgunit_a": {"name": "orgunit_a"}}
        updated_orgunits_mock = {"orgunit_b": {"name": "orgunit_b", "id": "ou-654321"}}
        updated_org_mock = self._get_mock_org(root_parent_id='r-1234', orgunits=updated_orgunits_mock)
        org_mock = self._get_mock_org(orgunits=orgunits_mock, updated_model=updated_org_mock)
        org_service = self._get_org_service()
        orgunit_id = org_service.create_orgunit(org_model=org_mock, orgunit_name="orgunit_a",
                                                parent_name="orgunit_b")
        assert orgunit_id == "ou-123456"

    def test_upsert_policy_create(self):
        '''
        Tests OrganizationService.upsert_policy when the action is create
        '''
        action = {'action': 'create'}
        policies_mock = {
            "policy_a": {
                "name": "policy_a",
                "description": "policy_a description",
                "document": {"content": {"foo": "bar"}}}}
        expected_create_policy_params = {
            "Content": '{"foo": "bar"}',
            "Description": "policy_a description",
            "Name": "policy_a",
            "Type": "SERVICE_CONTROL_POLICY"}
        create_policy_response = {
            "Policy": {"PolicySummary": {"Id": "p-a"}}}
        expected_changes = {"change": "created", "id": "p-a"}
        self.stubber.add_response("create_policy", create_policy_response,
                                  expected_create_policy_params)
        org_mock = self._get_mock_org(policies=policies_mock)
        org_service = self._get_org_service()
        changes = org_service.upsert_policy(
            organization=org_mock, policy_name="policy_a", action=action)
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert changes == expected_changes

    def test_upsert_policy_update(self):
        '''
        Tests OrganizationService.upsert_policy when the action is update
        '''
        action = {'action': 'update'}
        updated_policies_mock = {
            "policy_a": {
                "id": "p-a",
                "name": "policy_a",
                "description": "policy_a description",
                "document": {"content": {"foo": "bar"}}}}
        policies_mock = {
            "policy_a": {
                "name": "policy_a",
                "description": "policy_a description",
                "document": {"content": {"foo": "bar"}}}}
        expected_update_policy_params = {
            "Content": '{"foo": "bar"}',
            "Description": "policy_a description",
            "Name": "policy_a",
            "PolicyId": "p-a"}
        update_policy_response = {
            "Policy": {"PolicySummary": {"Id": "p-a"}}}
        expected_changes = {"change": "updated", "id": "p-a"}
        self.stubber.add_response("update_policy", update_policy_response,
                                  expected_update_policy_params)
        updated_org_mock = self._get_mock_org(policies=updated_policies_mock)
        org_mock = self._get_mock_org(updated_model=updated_org_mock, policies=policies_mock)
        org_service = self._get_org_service()
        changes = org_service.upsert_policy(
            organization=org_mock, policy_name="policy_a", action=action)
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert changes == expected_changes

    def test_delete_policy(self):
        '''
        Tests OrganizationService.delete_policy
        '''
        aws_policies_mock = {
            "policy_a": {"id": "p-a"}}
        expected_delete_policy_params = {"PolicyId": "p-a"}
        expected_changes = {"change": "deleted", "id": "p-a"}
        self.stubber.add_response("delete_policy", {}, expected_delete_policy_params)
        aws_org_mock = self._get_mock_org(policies=aws_policies_mock)
        org_mock = self._get_mock_org(aws_model=aws_org_mock)
        org_service = self._get_org_service()
        changes = org_service.delete_policy(organization=org_mock, policy_name="policy_a")
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert changes == expected_changes

    def test_delete_orgunit_error(self):
        '''
        Tests OrganizationService.delete_orgunit

        When a client error is raised when deleting the Orgunit, the method
        should return None, with the assumption that the Orgunit doesn't exist.
        '''
        self.stubber.add_client_error('delete_organizational_unit')
        orgunit_mock = {"orgunit_a": {"id": "ou-123456"}}
        aws_org_mock = self._get_mock_org(orgunits=orgunit_mock)
        org_mock = self._get_mock_org(aws_model=aws_org_mock)
        org_service = self._get_org_service()
        result = org_service.delete_orgunit(organization=org_mock, orgunit_name="orgunit_a")
        helpers.print_expected_actual_diff(None, result)
        assert result is None

    def test_delete_orgunit(self):
        '''
        Tests OrganizationService.delete_orgunit
        '''
        expected_delete_orgunit_params = {
            "OrganizationalUnitId": "ou-123456"}
        self.stubber.add_response('delete_organizational_unit', {},
                                  expected_delete_orgunit_params)
        orgunit_mock = {"orgunit_a": {"id": "ou-123456"}}
        expected_changes = {"change": "deleted", "id": "ou-123456"}
        aws_org_mock = self._get_mock_org(orgunits=orgunit_mock)
        org_mock = self._get_mock_org(aws_model=aws_org_mock)
        org_service = self._get_org_service()
        changes = org_service.delete_orgunit(organization=org_mock, orgunit_name="orgunit_a")
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert expected_changes == changes

    #pylint: disable=too-many-locals
    def test_create_accounts(self):
        '''
        Tests OrganizationService.create_accounts

        Tests one each of a create account result status where the state is
        SUCCEEDED, FAILED, or an unknown status.
        '''
        account_a_response = {
            "CreateAccountStatus": {
                "Id": "req-123456", "AccountName": "account_a", "State": "IN_PROGRESS"}}
        account_b_response = {
            "CreateAccountStatus": {
                "Id": "req-654321", "AccountName": "account_b", "State": "IN_PROGRESS"}}
        account_c_response = {
            "CreateAccountStatus": {
                "Id": "req-456789", "AccountName": "account_c", "State": "IN_PROGRESS"}}
        account_a_expected_params = {
            "AccountName": "account_a", "Email": "account_a@example.com"}
        account_b_expected_params = {
            "AccountName": "account_b", "Email": "account_b@example.com"}
        account_c_expected_params = {
            "AccountName": "account_c", "Email": "account_c@example.com"}
        self.stubber.add_response('create_account', account_a_response, account_a_expected_params)
        self.stubber.add_response('create_account', account_b_response, account_b_expected_params)
        self.stubber.add_response('create_account', account_c_response, account_c_expected_params)
        accounts_mock = {
            "account_a": {"owner": "account_a@example.com", "name": "account_a"},
            "account_b": {"owner": "account_b@example.com", "name": "account_b"},
            "account_c": {"owner": "account_c@example.com", "name": "account_c"}}
        accounts_to_create = ['account_a', 'account_b', 'account_c']
        expected_changes = {
            "account_a": {"change": "created"},
            "account_b": {"change": "failed"},
            "account_c": {"change": "unknown"}}
        # self is just provided here as the method being mocked is an instance method
        #pylint: disable=unused-argument
        def _new_wait_on_account_creation(self, creation_statuses):
            waiter_response = {
                "account_a": {"State": "SUCCEEDED"},
                "account_b": {"State": "FAILED"},
                "account_c": {"State": "ERROR"}}
            for account in creation_statuses:
                creation_statuses[account] = waiter_response[account]
        with mock.patch.object(OrganizationService, "_wait_on_account_creation",
                               new=_new_wait_on_account_creation):
            org_mock = self._get_mock_org(accounts=accounts_mock)
            org_service = self._get_org_service()
            changes = org_service.create_accounts(organization=org_mock, accounts=accounts_to_create)
            helpers.print_expected_actual_diff(expected_changes, changes)
            assert changes == expected_changes

    def test_wait_on_account_creation(self):
        '''
        Tests OrganizationService.wait_on_account_creation
        '''
        creation_statuses = {
            "account_a": {"Id": "req-123456", "State": "IN_PROGRESS"}}
        in_progress_response = {
            "CreateAccountStatus": {"Id": "req-123456", "State": "IN_PROGRESS"}}
        succeeded_response = {
            "CreateAccountStatus": {"Id": "req-123456", "State": "SUCCEEDED"}}
        expected_describe_status_params = {"CreateAccountRequestId": "req-123456"}
        self.stubber.add_response("describe_create_account_status", in_progress_response,
                                  expected_describe_status_params)
        self.stubber.add_response("describe_create_account_status", succeeded_response,
                                  expected_describe_status_params)
        expected_creation_statuses = {
            "account_a": {"Id": "req-123456", "State": "SUCCEEDED"}}
        # Patch time.sleep so we don't actually wait 20 seconds for this test to complete.
        with mock.patch('cumulogenesis.services.organization.time.sleep'):
            org_service = self._get_org_service()
            org_service._wait_on_account_creation(creation_statuses)
        helpers.print_expected_actual_diff(expected_creation_statuses, creation_statuses)
        assert expected_creation_statuses == creation_statuses

    def test_move_account_root(self):
        '''
        Tests OrganizationService.move_account when the parent_name is root
        '''
        updated_accounts_mock = {"account_a": {"id": "987654321"}}
        expected_changes = {"changes": "reassociated", "parent": "r-1234"}
        list_parents_response = {
            "Parents": [{"Id": "ou-123456"}]}
        expected_list_parents_params = {"ChildId": "987654321"}
        expected_move_account_params = {
            "AccountId": "987654321", "SourceParentId": "ou-123456",
            "DestinationParentId": "r-1234"}
        self.stubber.add_response("list_parents", list_parents_response,
                                  expected_list_parents_params)
        self.stubber.add_response("move_account", {}, expected_move_account_params)
        updated_org_mock = self._get_mock_org(accounts=updated_accounts_mock)
        aws_org_mock = self._get_mock_org(root_parent_id='r-1234')
        org_mock = self._get_mock_org(aws_model=aws_org_mock, updated_model=updated_org_mock)
        org_service = self._get_org_service()
        changes = org_service.move_account(organization=org_mock, account_name="account_a",
                                           parent_name="root")
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert changes == expected_changes

    def test_move_account_no_change(self):
        '''
        Tests OrganizationService.move_account when the source and destination IDs match
        '''
        updated_accounts_mock = {"account_a": {"id": "987654321"}}
        expected_changes = {}
        list_parents_response = {
            "Parents": [{"Id": "r-1234"}]}
        expected_list_parents_params = {"ChildId": "987654321"}
        self.stubber.add_response("list_parents", list_parents_response,
                                  expected_list_parents_params)
        updated_org_mock = self._get_mock_org(accounts=updated_accounts_mock)
        aws_org_mock = self._get_mock_org(root_parent_id='r-1234')
        org_mock = self._get_mock_org(aws_model=aws_org_mock, updated_model=updated_org_mock)
        org_service = self._get_org_service()
        changes = org_service.move_account(organization=org_mock, account_name="account_a",
                                           parent_name="root")
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert changes == expected_changes

    def test_move_account_orgunit(self):
        '''
        Tests OrganizationService.move_account when the parent_name is an orgunit
        (not "root")
        '''
        updated_accounts_mock = {"account_a": {"id": "987654321"}}
        updated_orgunits_mock = {"orgunit_a": {"id": "ou-654321"}}
        expected_changes = {"changes": "reassociated", "parent": "ou-654321"}
        list_parents_response = {
            "Parents": [{"Id": "ou-123456"}]}
        expected_list_parents_params = {"ChildId": "987654321"}
        expected_move_account_params = {
            "AccountId": "987654321", "SourceParentId": "ou-123456",
            "DestinationParentId": "ou-654321"}
        self.stubber.add_response("list_parents", list_parents_response,
                                  expected_list_parents_params)
        self.stubber.add_response("move_account", {}, expected_move_account_params)
        updated_org_mock = self._get_mock_org(accounts=updated_accounts_mock,
                                              orgunits=updated_orgunits_mock)
        aws_org_mock = self._get_mock_org()
        org_mock = self._get_mock_org(aws_model=aws_org_mock, updated_model=updated_org_mock)
        org_service = self._get_org_service()
        changes = org_service.move_account(organization=org_mock, account_name="account_a",
                                           parent_name="orgunit_a")
        helpers.print_expected_actual_diff(expected_changes, changes)
        assert changes == expected_changes
