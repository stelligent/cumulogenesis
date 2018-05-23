'''
Provides Organization service
'''

import json
import time
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
            if not describe_org_response['Organization']:
                organization.exists = False
        except botocore.exceptions.ClientError:
            logger.info("Got an error trying to describe the organization, assuming organization does not exist.")
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
                             "account_id": str(account["Id"]),
                             "regions": []}
            organization.accounts[account["Name"]] = account_model
            organization.account_ids_to_names[account["Id"]] = account["Name"]

    def upsert_organization(self, organization, actions):
        '''
        Upserts an organization based on the provided actions and organization model.
        When the provided action is `create`, it will attempt to create the organization.
        When the provided action is `update`, it will attempt to update the organization.
        Returns a dict describing the changes that were made.
        '''
        if actions['organization']['action'] == 'create':
            self._create_organization(org_model=organization)
            return {"organization": {"change": "created"}}
        return {}

    def _create_organization(self, org_model):
        logger.info('Creating organization.')
        organization_parameters = {
            "FeatureSet": org_model.featureset}
        self.client.create_organization(**organization_parameters)
        root_parent_id = self._get_root_parent_id(org_model.root_account_id)
        logger.info('Enabling Service Control Policy policy type.')
        self.client.enable_policy_type(RootId=root_parent_id,
                                       PolicyType='SERVICE_CONTROL_POLICY')

    def update_orgunit_policies(self, organization, orgunit_name):
        '''
        Updates the Service Control Policies associated with an Orgunit.
        configured model.
        '''
        orgunit_id = organization.updated_model.orgunits[orgunit_name]['id']
        policies = organization.orgunits[orgunit_name].get('policies', [])
        aws_model_policies = organization.updated_model.orgunits[orgunit_name].get('policies', [])
        if policies != aws_model_policies:
            self.update_entity_policy_attachments(target_id=orgunit_id,
                                                  old_policies=aws_model_policies,
                                                  new_policies=policies, org_model=organization)
        return {}

    def update_entity_policy_attachments(self, org_model, target_id, old_policies, new_policies):
        '''
        Updates the policies associations for the target entity
        '''
        for policy in new_policies:
            if policy not in old_policies:
                logger.info('Adding policy association for %s to target %s', policy, target_id)
                policy_id = org_model.updated_model.policies[policy]['id']
                self.client.attach_policy(PolicyId=policy_id, TargetId=target_id)
        for policy in old_policies:
            if policy not in new_policies:
                logger.info('Removing policy association for %s to target %s', policy, target_id)
                policy_id = org_model.updated_model.policies[policy]['id']
                self.client.detach_policy(PolicyId=policy_id, TargetId=target_id)

    @staticmethod
    def _get_parent_id_for_orgunit(org_model, orgunit_name):
        if org_model.orgunits[orgunit_name]['parent_references']:
            parent_id = org_model.orgunits[orgunit_name]['parent_references'][0]
        else:
            parent_id = org_model.root_parent_id
        return parent_id

    def create_orgunit(self, org_model, orgunit_name, parent_name):
        '''
        Creates the specified orgunit from the configured Organization model.

        The caller is responsible for ensuring that the Organization is in
        the appropriate state for the Organization to be created (e.g.,
        parent Orgunits have already been created.
        '''
        logger.info('Creating orgunit %s', orgunit_name)
        if parent_name == 'root':
            parent_id = org_model.aws_model.root_parent_id
        else:
            parent_id = org_model.updated_model.orgunits[parent_name]['id']
        orgunit_parameters = {
            # Set the parent ID to the root ID, we'll update it later.
            'ParentId': parent_id,
            'Name': org_model.orgunits[orgunit_name]['name']}
        create_res = self.client.create_organizational_unit(**orgunit_parameters)
        return create_res['OrganizationalUnit']['Id']

    def _update_orgunit(self, org_model, orgunit_name):
        logger.info('Updating orgunit %s', orgunit_name)
        orgunit_parameters = {
            'OrganizationalUnitId': org_model.updated_model.orgunits[orgunit_name]['id'],
            'Name': org_model.orgunits[orgunit_name]['name']}
        update_res = self.client.update_organizational_unit(**orgunit_parameters)
        return update_res['OrganizationalUnit']['Id']

    def upsert_policy(self, organization, policy_name, action):
        '''
        Upserts a Service Control Policy based on the provided actions and organization model.
        When the provided action is `create`, it will attempt to create the policy.
        When the provided action is `update`, it will attempt to update the policy to
        match what's in the configured Organization model.
        '''
        if action['action'] == 'create':
            policy_id = self._create_policy(org_model=organization, policy_name=policy_name)
            return {'change': 'created', 'id': policy_id}
        if action['action'] == 'update':
            policy_id = self._update_policy(org_model=organization, policy_name=policy_name)
            return {'change': 'updated', 'id': policy_id}
        return {}

    def _create_policy(self, org_model, policy_name):
        logger.info('Creating policy %s', policy_name)
        content_json = json.dumps(org_model.policies[policy_name]['document']['content'])
        policy_parameters = {
            'Content': content_json,
            'Description': org_model.policies[policy_name]['description'],
            'Name': org_model.policies[policy_name]['name'],
            'Type': 'SERVICE_CONTROL_POLICY'}
        create_res = self.client.create_policy(**policy_parameters)
        return create_res['Policy']['PolicySummary']['Id']

    def delete_policy(self, organization, policy_name):
        '''
        Deletes a Service Control Policy from the organization and returns a
        changes dict for the converge report.

        The caller is responsible for ensuring that all policy attachments have
        already been removed to ensure successful deletion.
        '''
        logger.info('Deleting policy %s', policy_name)
        policy_id = organization.aws_model.policies[policy_name]['id']
        self.client.delete_policy(PolicyId=policy_id)
        return {'change': 'deleted', 'id': policy_id}

    def delete_orgunit(self, organization, orgunit_name):
        '''
        Deletes an OrganizationalUnit from the organization and returns a
        changes dict for the converge report.

        The caller is responsible for ensuring that the Orgunit to be deleted has
        no child Accounts or Orgunits to ensure successful deletion.
        '''
        logger.info('Deleting orgunit %s', orgunit_name)
        orgunit_id = organization.aws_model.orgunits[orgunit_name]['id']
        try:
            self.client.delete_organizational_unit(OrganizationalUnitId=orgunit_id)
            return {'change': 'deleted', 'id': orgunit_id}
        except botocore.exceptions.ClientError as err:
            logger.info('Orgunit %s already deleted.', orgunit_name)
            logger.info(str(err))
            return None

    def _update_policy(self, org_model, policy_name):
        logger.info('Updating policy %s', policy_name)
        content_json = json.dumps(org_model.policies[policy_name]['document']['content'])
        policy_parameters = {
            'Content': content_json,
            'Description': org_model.policies[policy_name]['description'],
            'Name': org_model.policies[policy_name]['name'],
            'PolicyId': org_model.updated_model.policies[policy_name]['id']}
        update_res = self.client.update_policy(**policy_parameters)
        return update_res['Policy']['PolicySummary']['Id']

    def create_accounts(self, organization, accounts):
        '''
        Creates one or more accounts in the Organization. As account creation
        is asynchronous, it waits until each account finishes creating, then
        returns a changes dict for the report.
        '''
        creation_statuses = {}
        for account in accounts:
            logger.info('Creating account %s', account)
            create_account_params = {
                'Email': organization.accounts[account]['owner'],
                'AccountName': organization.accounts[account]['name']}
            create_res = self.client.create_account(**create_account_params)
            creation_statuses[account] = create_res['CreateAccountStatus']
        self._wait_on_account_creation(creation_statuses)
        changes = {}
        for account, status in creation_statuses.items():
            if status['State'] == 'SUCCEEDED':
                change = 'created'
            elif status['State'] == 'FAILED':
                change = 'failed'
            else:
                change = 'unknown'
            changes[account] = {"change": change}
            if status == 'failed':
                changes[account]['reason'] = status['FailureReason']
        return changes


    def _wait_on_account_creation(self, creation_statuses):
        logger.info('Waiting on account creation to complete.')
        waiting_accounts = creation_statuses.keys()
        while waiting_accounts:
            time.sleep(15)
            for account in waiting_accounts:
                request_id = creation_statuses[account]['Id']
                creation_statuses[account] = self.client.describe_create_account_status(
                    CreateAccountRequestId=request_id)['CreateAccountStatus']
            waiting_accounts = [
                account for account in waiting_accounts
                if creation_statuses[account]['State'] == 'IN_PROGRESS']


    def move_account(self, organization, account_name, parent_name):
        '''
        Reassociates an account with a new parent and returns a changes dict
        for the converge report.

        No change will be made if the account is currently associated with the
        specified parent.
        '''
        if parent_name == 'root':
            dest_parent_id = organization.aws_model.root_parent_id
        else:
            dest_parent_id = organization.updated_model.orgunits[parent_name]['id']
        account_id = organization.updated_model.accounts[account_name]['account_id']
        list_parents_res = self.client.list_parents(ChildId=account_id)
        source_parent_id = list_parents_res['Parents'][0]['Id']
        if dest_parent_id != source_parent_id:
            logger.info('Associating account %s with parent %s', account_name, parent_name)
            self.client.move_account(AccountId=account_id, SourceParentId=source_parent_id,
                                     DestinationParentId=dest_parent_id)
            return {"action": "reassociated", "parent": dest_parent_id}
        return {}

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
