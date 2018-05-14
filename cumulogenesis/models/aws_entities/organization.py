'''
Provides the Organization AwsEntity model class
'''
from cumulogenesis import exceptions
from cumulogenesis.services.session import SessionService
from cumulogenesis.services.organization import OrganizationService
from cumulogenesis.services.cloudformation import CloudformationService

# pylint: disable=too-many-instance-attributes
class Organization(object):
    '''
    Models an AWS Organization entitiy
    '''
    def __init__(self, root_account_id, source=None):
        self.root_account_id = root_account_id
        self.featureset = None
        self.accounts = {}
        self.account_ids_to_names = {}
        self.policies = {}
        self.orgunits = {}
        self.orgunit_ids_to_names = {}
        self.ids_to_children = {}
        self.stacks = {}
        self.groups = None
        self.provisioner = None
        self.raw_config = None
        self.session_builder = None
        self.source = source
        self.aws_model = None
        self.exists = True
        self.root_parent_id = None
        self.root_policies = []
        self.org_id = None
        super(Organization).__init__()

    def get_orgunit_hierarchy(self):
        '''
        Returns a dict representing the hierarchy of accounts and orgunits in the Organization model
        '''
        orgunit_hierarchy = self._orgunits_to_hierarchy()
        # Add orphaned orgunits and accounts to the hierarchy as a separate root key
        orphaned_accounts = self._find_orphaned_accounts()
        if orphaned_accounts:
            orgunit_hierarchy['ORPHANED_ACCOUNTS'] = orphaned_accounts
        return orgunit_hierarchy

    def raise_if_invalid(self):
        '''
        Raises cumulogenesis.exceptions.InvalidOrganizationException if any
        issues are found with the organization's structure.
        '''
        problems = self.validate()
        if problems:
            raise exceptions.InvalidOrganizationException(problems)

    def regenerate_groups(self):
        '''
        Rebuilds the groups dict from the current accounts and stacks attributes.
        '''
        self.groups = {}
        for account in self.accounts.values():
            for group in account.get('groups', []):
                self._add_entity_to_group(group_name=group, entity_name=account['name'],
                                          entity_type='accounts')
        for stack in self.stacks.values():
            for group in stack.get('groups', []):
                self._add_entity_to_group(group_name=group, entity_name=stack['name'],
                                          entity_type='stacks')

    def validate(self):
        '''
        Inspects the organization's structure and returns a dict of problems.
        If no problems are found, returns None
        '''
        problems = {}
        orgunit_problems = self._validate_orgunits()
        if orgunit_problems:
            problems['orgunits'] = orgunit_problems
        account_problems = self._validate_accounts()
        if account_problems:
            problems['accounts'] = account_problems
        stack_problems = self._validate_stacksets()
        if stack_problems:
            problems['stacks'] = stack_problems
        group_problems = self._validate_groups()
        if group_problems:
            problems['groups'] = group_problems
        return problems

    def initialize_aws_model(self):
        '''
        Initializes a new model of the organization loaded from AWS as the
        Organization's aws_model attribute.
        '''
        self.aws_model = Organization(root_account_id=self.root_account_id)
        self.aws_model.source = "aws"
        self.aws_model.provisioner = self.provisioner
        self.aws_model.load()

    def load(self):
        '''
        Builds out the Organization model from what exists in AWS
        '''
        if self.source != "aws":
            raise exceptions.NotAwsModelException('load()')
        self._load_organization()
        self._load_stacksets()

    def _initialize_session_builder(self):
        session_builder_params = {}
        if 'access_key' in self.provisioner:
            session_builder_params["access_key"] = self.provisioner.get('access_key', None)
            session_builder_params["secret_key"] = self.provisioner.get('secret_key', None)
        elif 'profile' in self.provisioner:
            session_builder_params['profile_name'] = self.provisioner['profile']
        if 'default_region' in self.provisioner:
            session_builder_params['default_region'] = self.provisioner['default_region']
        if 'role' in self.provisioner:
            session_builder_params['default_role_name'] = self.provisioner['role']
        self.session_builder = SessionService(**session_builder_params)

    def _get_session_builder(self):
        if not self.session_builder:
            self._initialize_session_builder()
        return self.session_builder

    def _load_organization(self):
        session_builder = self._get_session_builder()
        organization_service = OrganizationService(session_builder=session_builder)
        organization_service.load_organization(organization=self)
        organization_service.load_accounts(organization=self)
        organization_service.load_orgunits(organization=self)
        organization_service.load_policies(organization=self)

    def _load_stacksets(self):
        session_builder = self._get_session_builder()
        cloudformation_service = CloudformationService(session_builder=session_builder)
        cloudformation_service.load_stacksets(organization=self)

    def _initialize_account_parent_references(self):
        for account_name in self.accounts:
            self.accounts[account_name]['parent_references'] = []

    def _validate_orgunit(self, orgunit_name):
        problems = []
        orgunit = self.orgunits[orgunit_name]
        for child in orgunit.get('child_orgunits', []):
            if not child in self.orgunits:
                problems.append('references missing child orgunit %s' % child)
        for account_name in orgunit.get('accounts', []):
            if not account_name in self.accounts:
                problems.append('references missing account %s' % account_name)
            else:
                self.accounts[account_name]['parent_references'].append(orgunit['name'])
        for policy_name in orgunit.get('policies', []):
            if not policy_name in self.policies:
                problems.append('references missing policy %s' % policy_name)
        return problems

    def _validate_orgunits(self):
        self._initialize_account_parent_references()
        problems = {}
        for orgunit_name in self.orgunits:
            orgunit_problems = self._validate_orgunit(orgunit_name)
            if orgunit_problems:
                problems[orgunit_name] = orgunit_problems
        return problems

    def _validate_account(self, account_name):
        problems = []
        account = self.accounts[account_name]
        if not account['parent_references'] and not account.get('account_id', None) == self.root_account_id:
            problems.append('orphaned')
        elif len(account['parent_references']) > 1:
            #pylint: disable=line-too-long
            problems.append('referenced as a child of multiple orgunits: %s' % ', '.join(account['parent_references']))
        return problems

    def _validate_accounts(self):
        problems = {}
        for account_name in self.accounts:
            account_problems = self._validate_account(account_name)
            if account_problems:
                problems[account_name] = account_problems
        return problems

    def _validate_stackset(self, stackset_name):
        problems = []
        stackset = self.stacks[stackset_name]
        for account in stackset.get('accounts', []):
            if not account in self.accounts:
                problems.append('references missing account %s' % account)
        for orgunit in stackset.get('orgunits', []):
            if not orgunit in self.orgunits:
                problems.append('references missing orgunit %s' % orgunit)
        for group in stackset.get('groups', []):
            if not group in self.groups:
                problems.append('references missing group %s' % group)
        return problems

    def _validate_stacksets(self):
        problems = {}
        for stackset_name in self.stacks:
            stackset_problems = self._validate_stackset(stackset_name)
            if stackset_problems:
                problems[stackset_name] = stackset_problems
        return problems

    def _validate_group(self, group_name):
        problems = []
        group = self.groups[group_name]
        if not 'accounts' in group or not group['accounts']:
            problems.append('has no accounts listed')
        if not 'stacks' in group or not group['stacks']:
            problems.append('has no stacks listed')

    def _validate_groups(self):
        problems = {}
        self.regenerate_groups()
        for group_name in self.groups:
            group_problems = self._validate_group(group_name)
            if group_problems:
                problems[group_name] = group_problems
        return problems

    def _add_entity_to_group(self, group_name, entity_name, entity_type):
        if not group_name in self.groups:
            self.groups[group_name] = {"name": group_name}
        if not entity_type in self.groups[group_name]:
            self.groups[group_name][entity_type] = []
        self.groups[group_name][entity_type].append(entity_name)

    def _append_path(self, root, orgunit_name):
        '''
        Recursive function that decends through an OU path building out the
        OU hierarchy.
        '''
        if self.orgunits[orgunit_name].get('child_orgunits', []):
            root['orgunits'] = {}
            for child in self.orgunits[orgunit_name]['child_orgunits']:
                root['orgunits'][child] = {}
                self._append_path(root['orgunits'][child], child)
        if self.orgunits[orgunit_name]['accounts']:
            root['accounts'] = self.orgunits[orgunit_name]['accounts']

    def _generate_orgunit_parent_references(self):
        for orgunit in self.orgunits.values():
            orgunit['parent_references'] = []
        for orgunit in self.orgunits:
            for child in self.orgunits[orgunit]['child_orgunits']:
                self.orgunits[child]['parent_references'].append(orgunit)

    def _orgunits_to_hierarchy(self):
        self._generate_orgunit_parent_references()
        hierarchy = {"ROOT_ACCOUNT": {'orgunits': {}}}
        top_level_orgunits = [orgunit['name'] for orgunit in self.orgunits.values() if not orgunit['parent_references']]
        for orgunit in top_level_orgunits:
            hierarchy['ROOT_ACCOUNT']['orgunits'][orgunit] = {}
            self._append_path(hierarchy['ROOT_ACCOUNT']['orgunits'][orgunit], orgunit)
        return hierarchy

    def _find_orphaned_accounts(self):
        orphaned_accounts = []
        for account in self.accounts.values():
            # We specifically want to check that parent_references is 0 and not None
            #pylint: disable=len-as-condition
            if len(account['parent_references']) == 0 and not account.get('account_id', None) == self.root_account_id:
                orphaned_accounts.append(account['name'])
        return orphaned_accounts
