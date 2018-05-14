'''
Provides Organization service
'''

import botocore
from cumulogenesis import exceptions
from cumulogenesis import helpers
from cumulogenesis.log_handling import LOGGER as logger

class OrganizationService(object):
    '''
    Provides methods for loading Organization information from AWS and
    upserting them.
    '''

    def __init__(self, session_builder):
        self.session_builder = session_builder
        self.session = session_builder.get_base_session()
        self.client = self.session.client('organizations')

    def load_organization(self, organization):
        '''
        Initializes an Organization model with information about the Organization
        and its OrganizationUnit and Account hierarchy.

        It doesn't return anything useful as it's modifying the provided Organization
        model directly.
        '''
        try:
            describe_org_response = self.client.describe_organization()
        except botocore.exceptions.ClientError:
            logger.info("Got an error trying to describe the organization, assuming organization does not exist.")
            organization.exists = False
        if not describe_org_response['Organization']:
            organization.exists = False
        if organization.exists:
            self._set_organization_attributes(
                org_model=organization,
                describe_org_response=describe_org_response['Organization'])

    def load_orgunits(self, organization):
        '''
        Loads information about OrganizationalUnits into an initialized
        AWS Organization model from AWS.

        The caller is responsible for already having loaded accounts
        into the Organization model so that account names can be loaded into
        organizations from account IDs.

        It doesn't return anything useful as it's modifying the provided Organization
        model directly.
        '''
        for orgunit_id in organization.ids_to_children[organization.root_parent_id]['orgunits']:
            self._load_orgunit(org_model=organization, orgunit_id=orgunit_id)
        self._add_orgunit_children_to_parents(org_model=organization)

    def load_policies(self, organization):
        '''
        Loads existing policies into organization.policies.

        The caller is responsible for ensuring that accounts and orgunits
        have already been loaded into the Organization model so that policy
        associations can be loaded into them.
        '''
        list_policies_res = self.client.list_policies(Filter='SERVICE_CONTROL_POLICY')
        for policy in list_policies_res['Policies']:
            policy_document = self._get_policy_document(policy_id=policy['Id'])
            policy_model = {"name": policy["Name"],
                            "id": policy["Id"],
                            "description": policy["Description"],
                            "aws_managed": policy["AwsManaged"],
                            "document": {"content": policy_document}}
            organization.policies[policy["Name"]] = policy_model
            policy_targets_res = self.client.list_targets_for_policy(PolicyId=policy["Id"])
            for target in policy_targets_res["Targets"]:
                self._add_policy_to_target(org_model=organization, target=target, policy_name=policy['Name'])

    def load_accounts(self, organization):
        '''
        Loads existing accounts into organization.accounts. It also creates
        organization.account_ids_to_names with a mapping of account Id values
        to account Name values, for use by load_orgunits in loading the names
        of child accounts.
        '''
        list_accounts_res = self.client.list_accounts()
        for account in list_accounts_res['Accounts']:
            account_model = {"name": account["Name"],
                             "owner": account["Email"],
                             "account_id": account["Id"],
                             "regions": []}
            organization.accounts[account["Name"]] = account_model
            organization.account_ids_to_names[account["Id"]] = account["Name"]

    def upsert_organization(self, organization):
        '''
        Not implemented

        Should update the organization root to match the model or create it
        if it doesn't exist.
        '''
        pass

    def upsert_orgunit(self, organization, orgunit_name):
        '''
        Not implemented

        Should update the orgunit to match the orgunit model dict in the organization model
        or create if it doesn't exist. Should place the orgunit in the hierarchy appropriately.

        The caller is responsible for ensuring that the org is in a suitable
        state for any changes to happen (e.g., that the orgunit's parent exists,
        child accounts and applicable policies have been created, etc)
        before calling this method.
        '''
        pass

    def upsert_policy(self, organization, policy_name):
        '''
        Not implemented

        Should update the policy to match the policy model dict in the organization
        model, or create it if it doesn't exist.

        The caller is responsible for ensuring that there won't be any
        unintended side effects (e.g., applying the policy to a orgunit before the
        org hierarchy has converged, leading the policy to be applied in
        unexpected places for a period of time).
        '''
        pass

    def upsert_account(self, organization, account_name):
        '''
        Not implemented

        Should update the account to match the account model dict in the organization
        model, or create it if it doesn't exist.

        The caller is responsible for ensuring that the org is in a suitable
        state for any changes to happen (e.g., that any required policies have
        been created) before calling this method.
        '''
        pass

    def _load_orgunit(self, org_model, orgunit_id):
        orgunit_response = self.client.describe_organizational_unit(
            OrganizationalUnitId=orgunit_id)['OrganizationalUnit']
        orgunit = {"id": orgunit_response['Id'],
                   "name": orgunit_response['Name']}
        accounts = [org_model.account_ids_to_names[account_id]
                    for account_id in org_model.ids_to_children[orgunit_id]['accounts']]
        orgunit['accounts'] = accounts
        org_model.orgunits[orgunit_response['Name']] = orgunit
        org_model.orgunit_ids_to_names[orgunit_response['Id']] = orgunit_response['Name']
        for child_orgunit_id in org_model.ids_to_children[orgunit_id]['orgunits']:
            self._load_orgunit(org_model=org_model, orgunit_id=child_orgunit_id)

    def _set_organization_attributes(self, org_model, describe_org_response):
        if describe_org_response['MasterAccountId'] != str(org_model.root_account_id):
            raise exceptions.OrganizationMemberAccountException(
                org_model.root_account_id,
                describe_org_response['MasterAccountId'])
        org_model.featureset = describe_org_response['FeatureSet']
        org_model.root_parent_id = self._get_root_parent_id(org_model.root_account_id)
        org_model.org_id = describe_org_response['Id']
        self._set_org_ids_to_children(org_model, parent=org_model.root_parent_id)

    def _get_root_parent_id(self, root_account_id):
        parents_response = self.client.list_parents(ChildId=root_account_id)
        root_parents = [parent['Id'] for parent in parents_response['Parents'] if parent['Type'] == 'ROOT']
        return root_parents[0]

    def _set_org_ids_to_children(self, org_model, parent):
        orgunit_children = self.client.list_children(ParentId=parent,
                                                     ChildType="ORGANIZATIONAL_UNIT")
        account_children = self.client.list_children(ParentId=parent,
                                                     ChildType="ACCOUNT")
        if not parent in org_model.ids_to_children:
            org_model.ids_to_children[parent] = {"accounts": [], "orgunits": []}
        if account_children['Children']:
            for account in account_children['Children']:
                org_model.ids_to_children[parent]['accounts'].append(account['Id'])
        if orgunit_children['Children']:
            for orgunit in orgunit_children['Children']:
                org_model.ids_to_children[parent]['orgunits'].append(orgunit['Id'])
                self._set_org_ids_to_children(org_model=org_model, parent=orgunit['Id'])

    @staticmethod
    def _add_orgunit_children_to_parents(org_model):
        for orgunit_name in org_model.orgunits:
            orgunit_id = org_model.orgunits[orgunit_name]['id']
            child_orgunits = [org_model.orgunit_ids_to_names[child_id]
                              for child_id in org_model.ids_to_children[orgunit_id]['orgunits']]
            org_model.orgunits[orgunit_name]['child_orgunits'] = child_orgunits

    @staticmethod
    def _add_policy_to_target(org_model, target, policy_name):
        if target['Type'] == 'ROOT':
            org_model.root_policies.append(policy_name)
        else:
            if target['Type'] == 'ACCOUNT':
                target_dict = org_model.accounts
            elif target['Type'] == 'ORGANIZATIONAL_UNIT':
                target_dict = org_model.orgunits
            if target['Name'] in target_dict:
                if not 'policies' in target_dict[target['Name']]:
                    target_dict[target['Name']]['policies'] = []
                target_dict[target['Name']]['policies'].append(policy_name)

    def _get_policy_document(self, policy_id):
        describe_policy_response = self.client.describe_policy(PolicyId=policy_id)
        document = helpers.ordered_yaml_load(describe_policy_response['Policy']['Content'])
        return document
