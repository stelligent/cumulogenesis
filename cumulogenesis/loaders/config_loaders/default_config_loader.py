'''
Provides the DefaultConfigLoader loader class
'''
import copy
from collections import OrderedDict
#pylint: disable=line-too-long
from cumulogenesis.models.aws_entities import Organization
from cumulogenesis.log_handling import LOGGER as logger
from cumulogenesis import exceptions

class DefaultConfigLoader:
    '''
    Provides methods for loading organization models from config
    and dumping them back to the same config scheme.
    '''
    _default_featureset = 'ALL'
    _account_parameters = [{'name': 'name', 'type': str},
                           {'name': 'owner', 'type': str},
                           {'name': 'groups', 'type': list, 'optional': True},
                           {'name': 'accountid', 'type': str, 'optional': True},
                           {'name': 'regions', 'type': list}]
    _policy_parameters = [{'name': 'name', 'type': str},
                          {'name': 'description', 'type': str},
                          {'name': 'document', 'type': dict}]
    _provisioner_parameters = [{'name': 'role', 'type': str, 'optional': True},
                               {'name': 'type', 'type': str, 'optional': True}]
    _policy_document_parameters = [{'name': 'location', 'type': str},
                                   {'name': 'content', 'type': dict}]
    _orgunit_parameters = [{'name': 'name', 'type': str},
                           {'name': 'policies', 'type': list, 'optional': True},
                           {'name': 'accounts', 'type': list, 'optional': True},
                           {'name': 'orgunits', 'type': list, 'optional': True}]
    _stack_parameters = [{'name': 'name', 'type': str},
                         {'name': 'groups', 'type': list, 'optional': True},
                         {'name': 'accounts', 'type': list, 'optional': True},
                         {'name': 'orgunits', 'type': list, 'optional': True}]
    _stack_target_parameters = [{'name': 'name', 'type': str},
                                {'name': 'regions', 'type': list}]
    _stack_template_parameters = [{'name': 'location', 'type': str},
                                  {'name': 'content', 'type': dict}]
    _default_provisioner_template = {"role": "org-bootstrapper",
                                     "type": "cfn-stack-set"}

    def __init__(self):
        self.config_version = '2018-05-04'

    def dump_organization_to_config(self, organization):
        '''
        Creates a config datastructure from the provided organization model.
        Returns the created config datastructure.
        '''
        organization.raise_if_invalid()
        config = OrderedDict()
        config['root'] = organization.root_account_id
        config['featureset'] = organization.featureset
        config['version'] = self.config_version
        if organization.provisioner:
            config['provisioner'] = self._render_provisioner(organization.provisioner)
        if organization.accounts:
            config['accounts'] = self._render_accounts(organization.accounts)
        if organization.policies:
            config['policies'] = self._render_policies(organization.policies)
        if organization.orgunits:
            config['orgunits'] = self._render_orgunits(organization.orgunits,
                                                       organization.get_orgunit_hierarchy())
        if organization.stacks:
            config['stacks'] = self._render_stacks(organization.stacks)
        return config

    def load_organization_from_config(self, config):
        '''
        Creates a new organization from the provided configuration datastructure.
        Returns the created organization.
        '''
        organization = Organization(root_account_id=config['root'])
        organization.source = "config"
        organization.raw_config = config
        if 'featureset' in config:
            organization.featureset = config['featureset']
        else:
            logger.info('featureset parameter not present on organization, assuming "ALL"')
            organization.featureset = self._default_featureset
        if 'provisioner' in config:
            organization.provisioner = self._load_provisioner(config['provisioner'])
        else:
            organization.provisioner = self._load_provisioner(None)
        if 'accounts' in config:
            organization.accounts = self._load_accounts(config['accounts'])
        if 'policies' in config:
            organization.policies = self._load_policies(config['policies'])
        if 'orgunits' in config:
            organization.orgunits = self._load_orgunits(config['orgunits'])
        if 'stacks' in config:
            organization.stacks = self._load_stacks(config['stacks'])
        organization.regenerate_groups()
        return organization

    @staticmethod
    def _validate_is_type(config, parameter, parent, expected_type, optional=False):
        if not optional and not parameter in config:
            raise exceptions.MissingRequiredParameterException(parameter=parameter,
                                                               parent=parent)
        if parameter in config and not isinstance(config[parameter], expected_type):
            raise exceptions.ParameterTypeMismatchException(parameter=parameter,
                                                            parent=parent,
                                                            expected_type=expected_type)

    def _validate_each_parameter(self, config, parent, parameters):
        for parameter in parameters:
            optional = parameter.get('optional', False)
            self._validate_is_type(config=config, parent=parent,
                                   parameter=parameter['name'],
                                   expected_type=parameter['type'],
                                   optional=optional)

    def _validate_one_of_parameters(self, config, parent, parameters):
        parameters_set = set([parameter['name'] for parameter in parameters])
        found_parameters = parameters_set & set(config.keys())
        if not found_parameters:
            #pylint: disable=line-too-long
            raise exceptions.MissingRequiredParameterException(' or '.join(list(parameters_set)),
                                                               'policy.document')
        elif len(found_parameters) > 1:
            raise exceptions.MultipleParametersSpecifiedException(list(parameters_set),
                                                                  'policy.document')
        else:
            parameter = [p for p in parameters if p['name'] == list(found_parameters)[0]][0]
            self._validate_is_type(config=config, parameter=parameter['name'],
                                   parent=parent, expected_type=parameter['type'])

    @staticmethod
    def _list_to_dict_by_names(entity_list, entity_type):
        dict_by_names = {}
        for item in entity_list:
            if item['name'] in dict_by_names:
                raise exceptions.DuplicateNamesException(name=item['name'], entity_type=entity_type)
            else:
                dict_by_names[item['name']] = item
        return dict_by_names

    def _load_provisioner(self, config):
        if not config:
            logger.info('No provisioner configuration provided, initializing with defaults.')
            return copy.deepcopy(self._default_provisioner_template)
        else:
            if 'role' in config:
                self._validate_is_type(config=config, parameter='role', parent='provisioner',
                                       expected_type=str)
            if 'type' in config:
                self._validate_is_type(config=config, parameter='type', parent='provisioner',
                                       expected_type=str)
            return config

    def _load_accounts(self, config):
        accounts = []
        for account in config:
            self._validate_each_parameter(config=account, parent='account',
                                          parameters=self._account_parameters)
            account_parameters = copy.deepcopy(account)
            account_parameters['source'] = 'config'
            accounts.append(account_parameters)
        accounts_by_name = self._list_to_dict_by_names(accounts, 'account')
        return accounts_by_name

    def _load_policies(self, config):
        policies = []
        for policy in config:
            self._validate_each_parameter(config=policy, parent='policy',
                                          parameters=self._policy_parameters)
            self._validate_one_of_parameters(config=policy['document'], parent='policy.document',
                                             parameters=self._policy_document_parameters)
            policy_parameters = copy.deepcopy(policy)
            policy_parameters['source'] = 'config'
            policies.append(policy_parameters)
        policies_by_name = self._list_to_dict_by_names(policies, 'policy')
        return policies_by_name

    def _load_orgunits_from_orgunit(self, config):
        orgunits = []
        for orgunit in config:
            self._validate_each_parameter(config=orgunit, parent='orgunit',
                                          parameters=self._orgunit_parameters)
            orgunit_parameters = copy.deepcopy(orgunit)
            orgunit_parameters['child_orgunits'] = []
            if 'orgunits' in orgunit_parameters:
                children = orgunit_parameters.pop('orgunits')
                for child in children:
                    orgunit_parameters['child_orgunits'].append(child['name'])
                #pylint: disable=line-too-long
                child_orgunits = self._load_orgunits_from_orgunit(config=children)
                orgunits += child_orgunits
            orgunit_parameters['source'] = 'config'
            orgunits.append(orgunit_parameters)
        return orgunits

    def _load_orgunits(self, config):
        orgunits = self._load_orgunits_from_orgunit(config)
        orgunits_by_name = self._list_to_dict_by_names(orgunits, 'orgunit')
        return orgunits_by_name

    def _load_stacks(self, config):
        stacks = []
        for stack in config:
            self._validate_each_parameter(config=stack, parent='stack',
                                          parameters=self._stack_parameters)
            self._validate_one_of_parameters(config=stack['template'], parent='stack.template',
                                             parameters=self._stack_template_parameters)
            for key in ['accounts', 'groups', 'orgunits']:
                if key in config:
                    target_name = 'stack.%s' % key
                    self._validate_each_parameter(config=stack, parent=target_name,
                                                  parameters=self._stack_target_parameters)
            stack_parameters = copy.deepcopy(stack)
            stack_parameters['source'] = 'config'
            stacks.append(stack)
        stacks_by_name = self._list_to_dict_by_names(stacks, 'stack')
        return stacks_by_name

    @staticmethod
    def _render_from_map(source, attribute_map):
        mapped_output = OrderedDict()
        for attribute_name, config_name in attribute_map.items():
            mapped_attribute = source.get(attribute_name, None)
            if mapped_attribute:
                mapped_output[config_name] = mapped_attribute
        return mapped_output

    def _render_provisioner(self, provisioner):
        attribute_map = {"role": "role",
                         "type": "type"}
        provisioner = self._render_from_map(source=provisioner, attribute_map=attribute_map)
        return provisioner

    def _render_accounts(self, accounts):
        accounts_list = []
        attribute_map = {"name": "name",
                         "owner": "owner",
                         "groups": "groups",
                         "account_id": "account_id",
                         "regions": "regions"}
        for account in accounts.values():
            accounts_list.append(self._render_from_map(source=account, attribute_map=attribute_map))
        return accounts_list

    def _render_policies(self, policies):
        policies_list = []
        attribute_map = {"name": "name",
                         "description": "description",
                         "document": "document"}
        for policy in policies.values():
            policies_list.append(self._render_from_map(source=policy, attribute_map=attribute_map))
        return policies_list

    def _render_orgunit(self, orgunit_name, root, orgunits):
        attribute_map = {"name": "name",
                         "policies": "policies",
                         "accounts": "accounts"}
        rendered_orgunit = self._render_from_map(source=orgunits[orgunit_name],
                                                 attribute_map=attribute_map)
        if 'orgunits' in root:
            rendered_orgunit['orgunits'] = []
            for child in root['orgunits']:
                rendered_child = self._render_orgunit(child, root['orgunits'][child], orgunits)
                rendered_orgunit['orgunits'].append(rendered_child)
        return rendered_orgunit

    def _render_orgunits(self, orgunits, orgunit_hierarchy):
        rendered_orgunits = []
        root = orgunit_hierarchy['ROOT_ACCOUNT']
        if 'orgunits' in root:
            for orgunit_name in root['orgunits']:
                rendered_orgunit = self._render_orgunit(orgunit_name,
                                                        root['orgunits'][orgunit_name],
                                                        orgunits)
                rendered_orgunits.append(rendered_orgunit)
        return rendered_orgunits

    def _render_stacks(self, stacks):
        stacks_list = []
        attribute_map = {"name": "name",
                         "groups": "groups",
                         "accounts": "accounts",
                         "orgunits": "orgunits",
                         "template": "template"}
        for stack in stacks.values():
            stacks_list.append(self._render_from_map(source=stack, attribute_map=attribute_map))
        return stacks_list
