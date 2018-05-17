'''
Provides the Organization AwsEntity model class
'''
from collections import OrderedDict
from cumulogenesis import exceptions, helpers
from cumulogenesis.services.session import SessionService
from cumulogenesis.services.organization import OrganizationService
from cumulogenesis.services.cloudformation import CloudformationService
from cumulogenesis.log_handling import LOGGER as logger

# pylint: disable=too-many-instance-attributes
class Organization(object):
    '''
    Models an AWS Organization entity. Can be created from configuration via
    #cumulogenesis.loaders.config, or can be loaded as a representation of what
    currently exists in AWS via #initialize_from_aws

    #### Instance attributes

    ##### Core model attributes

    - `accounts`: The accounts in the Organization represented as a dict of
    account names to dicts representing the accounts. See Account below.
    - `featureset`: The feature set that is enabled on the AWS Organization.
    - `orgunits`: The Organizational Units in the Organization, represented
    as a dict of orgunit names to dicts representing the orgunits. See Orgunit below.
    - `policies`: The Service Control Policies in the Organization, represented
    as a dict of policy names to dicts representing the policies. See Policy below.
    - `root_account_id`: The ID of the AWS account that is the Organization master.
    This must be supplied to `__init__` when the model is instantiated.
    - `root_policies`: A list of Service Control Policies that are applied to
    the Organization's root.
    - `stacks`: The stack resources that should exist in the Organization, represented
    as a dict of stack names to dicts representing the stack resources. See Stack
    below.
    - `stack_instances`: The stack instances that should exist per account/region,
    represented as a list of dicts representing the stack instances. See Stack Instance
    below.

    ##### Additional attributes

    - `account_ids_to_names`: A dict that maps Account IDs to Account names. Generated
    when loading an Organization model from AWS.
    - `aws_model`: An Organization instance created from what exists in AWS
    when #Organization.load is called.
    - `exists`: Indicates whether the Organization currently exists in AWS. Set
    when loading an Organization model from AWS.
    - `groups`: Deprecated and will be removed in the future.
    - `ids_to_children`: A dict that maps Organization hierarchy entities (Org root and
    Orgunits) to child Orgunits and Accounts. Generated when loading an Organization model
    from AWS.
    - `org_id`: The ID of the AWS organization. Generated when loading an Organization model
    from AWS.
    - `orgunit_ids_to_names`: A dict that maps Orgunit IDs to Orgunit names. Generated
    when loading an organization model from AWS.
    - `provisioner`: A dict that contains parameters passed to AWS Service provisioners.
    Valid keys:
        - `access_key`: The AWS IAM Access Key to be used when creating `boto3` sessions.
        When specified, `profile` will be ignored. Requires `secret_key` to also be specified.
        - `profile`: The AWS CLI profile to use when creating `boto3` sessions.
        By default, no profile will be passed to `boto3`. Overridden by `access_key` and
        `secret_key`.
        - `role`: The name of the Organization role to create for Organization access
        to member accounts.
        - `secret_key`: The AWS IAM Secret Key to be used when creatinb `boto3` sessions.
        Requires `access_key` to also be specified.
        - `type`: The Stack provisioner engine to use. Defaults to cfn-stack-set.
    - `raw_config`: An OrderedDict representation of the config passed if the Organization
    model was initialized from configuration.
    - `root_parent_id`: The ID of the Organization's root. Generated when loading an
    Organization model from AWS.
    - `session_builder`: A #cumulogenesis.services.session.SessionBuilder instance
    that's passed to other AWS Service instances for building `boto3` sessions.
    - `source`: A string that represents the source of the Organization model. Valid states:
        - _config_: Indicates that the model was initialized from configuration.
        - _aws_: Indicates that the model was initialized from AWS.

    #### Entity Models

    The parameters above contain models of entities and resources with AWS Organizations.
    The schema of those models are described below.

    ##### Account

    A dict representing an Account in an Organzation.

    ```
    {
        "account_id": str(account_id),
        "name": str(account_name),
        "owner": str(account_owner),
        "parent_references": [str(orgunit_name), ...]
        "policies": [str(policy_name), ...]
        "regions": {
            str(region_name): {
                "parameters": {
                    str(parameter_name): parameter_value}}}}
    ```


    - `account_id`: The AWS ID of the Account. If loaded from configuration, this
    indicates that the Account should already exist and should be invited to the
    Organization rather than being created as a new member. Will always exist when
    loading the model from AWS.
    - `name`: The name of the Account.
    - `owner`: The owner email address associated with the Account.
    - `parent_references`: A list of Orgunit names that claim this account as a child.
    Generated when #validate is called. Used to identify problems in the Organization
    structure such as orphaned Accounts or multiple Orgunits claiming the same Account
    as a child.
    - `policies`: A list of Policy names that target the Account.
    - `regions`: A dict of AWS region names to region configuration. Represents
    the regions in which all Stack resources targeting the account should have
    Stack Instances created. Keys of the region dicts follow:
        - `parameters`: A dict of parameter names to parameter values. A Parameter
        Store parameter should be created in the region's parameter Stack Instance
        for each member of this dict. The parameter value may be any type accepted by
        Parameter Store.

    ##### Orgunit

    A dict representing an Organizational Unit in an Organization.

    ```
    {
        "accounts": [str(account_name), ...],
        "child_orgunits": [str(orgunit_name), ...],
        "id": str(orgunit_id),
        "name": str(orgunit_name)
        "parent_references": [str(orgunit_name), ...],
        "policies": [str(policy_name), ...]}
    ```

    - `accounts`: A list of Account names that are children of this Orgunit.
    - `child_orgunits`: A list of Orgunit names that are children of this Orgunit.
    - `id`: The ID of this Orgunit. Generated when loading the Orgunit from AWS.
    - `name`: The name of this Orgunit.
    - `parent_references`: A list of Orgunit names that claim this Orgunit as a child.
    Generated when #validate or #get_orgunit_hierarchy are called. Used ot identify
    problems in the Organization structure such as multiple Orgunits claiming the same
    Orgunit as a child.
    - `policies`: A list of Policy names that target this Orgunit.

    ##### Policy

    A dict representing a Service Control Policy attached to an Organization.

    ```
    {
        "aws_managed": bool,
        "description": str(description),
        "document": {
            "content": OrderedDict(policy_document) }},
        "id": str(policy_id),
        "name": str(policy_name)}
    ```

    - `aws_managed`: If `True`, indicates that the Policy is managed by AWS. Defaults
    to `False`.
    - `description`: The description applied to the Policy.
    - `document`: A dict representing the Policy Document.
        - `content`: An OrderedDict representing the contents of the Policy document.
    - `id`: The AWS ID of the Policy.
    - `name`: The name of the Policy.

    ##### Stacks

    A dict representing a Stack resource. Not yet fully implemented.

    ##### Stack Instance

    A dict representing an instance of a Stack resource. Not yet fully implemented.
    '''

    _comparable_account_attributes = ['name', 'policies']
    _comparable_orgunit_attributes = ['name', 'policies']
    _comparable_policy_attributes = ['name', 'description', 'document']
    _policies_aws_managed = ["FullAWSAccess"]

    def __init__(self, root_account_id, source=None):
        self.root_account_id = str(root_account_id)
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

    def dry_run(self, provisioner_overrides=None):
        '''
        Loads a corresponding model from AWS and generates a report of a comparison
        against it and actions that would be taken to converge the AWS resources to
        match this model.
        '''
        if provisioner_overrides:
            for name, value in provisioner_overrides.items():
                self.provisioner[name] = value
        report = OrderedDict()
        self.raise_if_invalid()
        logger.info("Loading model from existing AWS resources.")
        self.initialize_aws_model()
        aws_model_problems = self.aws_model.validate()
        if aws_model_problems:
            report['aws_model_problems'] = aws_model_problems
        report = self.compare_against_aws_model(report=report)
        logger.warning('dry_run not fully implemented')
        return report

    def compare_against_aws_model(self, report):
        '''
        Compares this Organization model against the already initialized model in
        loaded in the aws_model attribute and returns a report of required changes
        to converge.
        '''
        report['configured_organization'] = self
        report['actual_organization'] = self.aws_model
        report['actions'] = OrderedDict()
        if not self.aws_model.exists:
            self._add_action_to_report(report=report, entity_type='organization',
                                       entity_name='organization', action='create')
            return report
        else:
            self._compare_organizations(report)
        self._compare_accounts(report)
        self._compare_orgunits(report)
        self._compare_policies(report)
        return report

    #pylint: disable=too-many-arguments
    @staticmethod
    def _add_action_to_report(report, entity_type, entity_name, action, old_value=None, new_value=None):
        if not entity_type in report['actions']:
            report['actions'][entity_type] = OrderedDict()
        action_dict = {"action": action}
        if old_value:
            action_dict['existing_entity'] = old_value
        if new_value:
            action_dict['configured_entity'] = new_value
        report['actions'][entity_type][entity_name] = action_dict

    @staticmethod
    def _render_comparable_entity(entity, renderable_attributes):
        comparable_entity = OrderedDict()
        for attribute in renderable_attributes:
            if attribute in entity:
                comparable_entity[attribute] = entity[attribute]
                if isinstance(comparable_entity[attribute], dict):
                    comparable_entity[attribute] = OrderedDict(comparable_entity[attribute])
        return comparable_entity

    def _compare_organizations(self, report):
        configured_organization = self.get_organization_configuration()
        aws_organization = self.aws_model.get_organization_configuration()
        if helpers.deep_diff(configured_organization, aws_organization):
            self._add_action_to_report(
                report=report, entity_type='organization', entity_name='organization',
                action='update', old_value=aws_organization, new_value=configured_organization)

    def _compare_accounts(self, report):
        for account in self.accounts:
            if not account in self.aws_model.accounts:
                action = 'invite' if 'account_id' in self.accounts[account] else 'create'
                self._add_action_to_report(
                    report=report, entity_type='account', entity_name=account,
                    action=action)
            else:
                configured_account = self._render_comparable_entity(
                    entity=self.accounts[account], renderable_attributes=self._comparable_account_attributes)
                aws_account = self._render_comparable_entity(
                    entity=self.aws_model.accounts[account], renderable_attributes=self._comparable_account_attributes)
                if helpers.deep_diff(configured_account, aws_account):
                    self._add_action_to_report(
                        report=report, entity_type='account', entity_name=account,
                        action='update', old_value=aws_account, new_value=configured_account)
        for account in self.aws_model.accounts:
            if not account in self.accounts:
                if not 'unknown_accounts' in report:
                    report['unknown_accounts'] = OrderedDict()
                aws_account = self._render_comparable_entity(
                    entity=self.aws_model.accounts[account], renderable_attributes=self._comparable_account_attributes)
                report['unknown_accounts'][account] = aws_account
        self._compare_account_associations(report)

    def _compare_policies(self, report):
        for policy in self.policies:
            if self.policies[policy].get('aws_managed', None):
                continue
            if not policy in self.aws_model.policies:
                self._add_action_to_report(
                    report=report, entity_type='policy', entity_name=policy,
                    action='create')
            else:
                configured_policy = self._render_comparable_entity(
                    entity=self.policies[policy], renderable_attributes=self._comparable_policy_attributes)
                aws_policy = self._render_comparable_entity(
                    entity=self.aws_model.policies[policy], renderable_attributes=self._comparable_policy_attributes)
                if helpers.deep_diff(configured_policy, aws_policy):
                    self._add_action_to_report(
                        report=report, entity_type='policy', entity_name=policy,
                        action='update', old_value=aws_policy, new_value=configured_policy)
        for policy in self.aws_model.policies:
            if not policy in self.policies:
                if self.aws_model.policies[policy].get('aws_managed', None):
                    continue
                self._add_action_to_report(
                    report=report, entity_type='policy', entity_name=policy, action='delete')

    @staticmethod
    def _add_association_to_report(report, entity_type, entity_name, parent_name):
        action_key = "%s_associations" % entity_type
        if not action_key in report['actions']:
            report['actions'][action_key] = OrderedDict()
        action_dict = {'action': 'associate', 'parent': parent_name}
        report['actions'][action_key][entity_name] = action_dict

    @staticmethod
    def _get_association_for_account(org_model, account_name):
        parent_references = org_model.accounts[account_name]['parent_references']
        if parent_references:
            return parent_references[0]
        return 'root'

    def _compare_account_associations(self, report):
        for account in self.accounts:
            if self.accounts[account].get('account_id', None) == self.root_account_id:
                continue
            # If the account hasn't yet been created in the AWS model,
            # add an association entry demonstrating where it should be located
            # after creation.
            if not account in self.aws_model.accounts:
                self._add_association_to_report(
                    report=report, entity_type='account', entity_name=account,
                    parent_name=self._get_association_for_account(self, account))
            else:
                # If the account has been created but doesn't exist in the hierarchy
                # where we expect it to, add an association entry demonstrating where
                # it should be located.
                configured_parent = self._get_association_for_account(self, account)
                aws_parent = self._get_association_for_account(self.aws_model, account)
                if configured_parent != aws_parent:
                    self._add_association_to_report(
                        report=report, entity_type='account', entity_name=account,
                        parent_name=configured_parent)
        # Any accounts that aren't in the model and are associated with an orgunit
        # that shouldn't exist should be moved to the root account. A problem
        # will be added to report['aws_model_problems'] to indicate that the account
        # will be orphaned.
        for account in self.aws_model.accounts:
            if self.aws_model.accounts[account]['account_id'] == self.root_account_id:
                continue
            if account not in self.accounts:
                aws_parent = self._get_association_for_account(self.aws_model, account)
                if aws_parent != 'root' and aws_parent not in self.orgunits:
                    self._add_association_to_report(
                        report=report, entity_type='account',
                        entity_name=account, parent_name='root')
                    self._add_orphaned_account_problem_to_report(
                        report=report, account_name=account, parent_name=aws_parent)

    @staticmethod
    def _add_orphaned_account_problem_to_report(report, account_name, parent_name):
        if 'problems' not in report:
            report['problems'] = {}
        if 'accounts' not in report['problems']:
            report['problems']['accounts'] = {}
        if account_name not in report['problems']['accounts']:
            report['problems']['accounts'][account_name] = []
        report['problems']['accounts'][account_name].append(
            "%s will be orphaned by the removal of parent orgunit %s" % (account_name, parent_name))

    @staticmethod
    def _get_association_for_orgunit(org_model, orgunit_name):
        parent_references = org_model.orgunits[orgunit_name]['parent_references']
        if parent_references:
            return parent_references[0]
        return 'root'

    def _compare_orgunit_associations(self, report):
        # The flow of this function is similar to what's described in the comments
        # on _compare_account_associations, except we don't need to check for
        # orgunits that aren't in the model, since we'll fully manage orgunits.
        for orgunit in self.orgunits:
            if not orgunit in self.aws_model.orgunits:
                self._add_association_to_report(
                    report=report, entity_type='orgunit', entity_name=orgunit,
                    parent_name=self._get_association_for_orgunit(self, orgunit))
            else:
                configured_parent = self._get_association_for_orgunit(self, orgunit)
                aws_parent = self._get_association_for_orgunit(self, orgunit)
                if configured_parent != aws_parent:
                    self._add_association_to_report(
                        report=report, entity_type='orgunit', entity_name=orgunit,
                        parent_name=configured_parent)

    def _compare_orgunits(self, report):
        for orgunit in self.orgunits:
            if not orgunit in self.aws_model.orgunits:
                self._add_action_to_report(
                    report=report, entity_type='orgunit', entity_name=orgunit,
                    action='create')
            else:
                configured_orgunit = self._render_comparable_entity(
                    entity=self.orgunits[orgunit], renderable_attributes=self._comparable_orgunit_attributes)
                aws_orgunit = self._render_comparable_entity(
                    entity=self.aws_model.orgunits[orgunit], renderable_attributes=self._comparable_orgunit_attributes)
                if helpers.deep_diff(configured_orgunit, aws_orgunit):
                    self._add_action_to_report(
                        report=report, entity_type='orgunit', entity_name=orgunit,
                        action='update', old_value=aws_orgunit, new_value=configured_orgunit)
        for orgunit in self.aws_model.orgunits:
            if not orgunit in self.orgunits:
                self._add_action_to_report(
                    report=report, entity_type='orgunit', entity_name=orgunit,
                    action='delete')
        self._compare_orgunit_associations(report)

    def get_organization_configuration(self):
        '''
        Returns a dict describing the organization's configuration for use in comparison.
        '''
        configuration = {
            "featureset": self.featureset,
            "root_policies": self.root_policies}
        return configuration

    @staticmethod
    def converge():
        '''
        Executes a dry run, then converges the dry run's proposed changes. Returns
        a report of actions taken.
        '''
        logger.warning('converge not implemented')
        return "Not implemented."

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
        self._generate_orgunit_parent_references()
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
        Organization's `aws_model` attribute.
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
        self._validate_policies_on_entity(entity=orgunit, problems=problems)
        return problems

    def _validate_orgunits(self):
        self._initialize_account_parent_references()
        problems = {}
        for orgunit_name in self.orgunits:
            orgunit_problems = self._validate_orgunit(orgunit_name)
            if orgunit_problems:
                problems[orgunit_name] = orgunit_problems
        return problems

    def _validate_policies_on_entity(self, entity, problems):
        for policy in entity.get('policies', []):
            if not policy in self.policies and not policy in self._policies_aws_managed:
                problems.append('references missing policy %s' % policy)

    def _validate_account(self, account_name):
        problems = []
        account = self.accounts[account_name]
        if not account['parent_references'] and not account.get('account_id', None) == self.root_account_id:
            problems.append('orphaned')
        elif len(account['parent_references']) > 1:
            #pylint: disable=line-too-long
            problems.append('referenced as a child of multiple orgunits: %s' % ', '.join(account['parent_references']))
        self._validate_policies_on_entity(entity=account, problems=problems)
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
        if self.orgunits[orgunit_name].get('accounts', None):
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
