'''
Provides CloudformationService
'''
import boto3
from botocore.client import ClientError

from cumulogenesis.log_handling import LOGGER as logger


class CloudformationService(object):
    ''' Instance constructor - requires a pre-configured boto3 Session object '''
    def __init__(self, session_builder):
        self.session_builder = session_builder
        # To do: When working with for stack(set)s in a given account/region,
        # use something along the lines of:
        #   session = self.session_builder.get_account_role_session(accountid, region)
        #   session.client('cloudformation')
        #
        # It's anticipated that instances of this service may need to  work with
        # multiple account/region pairs, so don't do that in __init__
        #
        # Remove the below once implemented.
        #
        self.session = session_builder.get_base_session()
        self.client = boto3.client('cloudformation', self.session)

    def upsert_stackset(self, organization, stackset_name):
        '''
        Create or update a stack-set from the stackset model dict in the
        organization model.

        The caller is responsible for ensuring that the organization
        is in a suitable state for the stackset to be updated, (e.g.,
        all required parameter stacks have been upserted, necessary account,
        orgunit resources are in place).
        '''
        logger.info('Using organization rooted in account %s', organization.root_account_id)
        logger.info('Discovering stackset %s', stackset_name)
        aws_stackset = self._retrieve_stackset(stackset_name=stackset_name)
        if aws_stackset:
            return self._update_stackset(stackset=aws_stackset)
        return self._create_stackset(stackset=aws_stackset)

    def upsert_account_parameter_stacks(self, organization):
        '''
        Not implemented

        For each account in the organization model:

        Given that the organization has accounts in its accounts dict,
        for each account:
        Given that the account's regions key is a dict of regions:
        For each region dict, if it has a parameters key, the parameters dict
        should be a key=>value mapping of Parameter Store parameters that should
        be set for the account in the region.

        e.g.,
        organization.accounts = {
            "account_a": {
                "id": "123456789",
                "name": "account_a",
                "regions": {
                    "us-east-1": {},
                    "us-east-2": {
                        "parameters": {
                            "cloudtrail-bucket": "some_cloudtrail_bucket"}}}}}

        This method should dynamically generate a CloudFormation template for
        each of these account/region mappings if any parameters are set and upsert
        a CloudFormation stack from it. The parameter paths should have the prefix
        /cumulogenesis/ to keep them distinct from other Parameter Store parameters
        created by the user.

        The caller is responsible for ensuring that the account exists
        before calling this method.
        '''
        raise NotImplementedError()

    def load_stacksets(self, organization, status='ACTIVE'):
        '''
        Loads existing policies into organization.policies.

        The caller is responsible for ensuring that accounts and orgunits
        have already been loaded into the Organization model so that policy
        associations can be loaded into them.
        '''
        stack_sets = []
        paginator = self.client.get_paginator('list_stack_sets')

        for page in paginator.paginate(Status=status):
            if page['Summaries']:
                stack_sets = stack_sets + page['Summaries']

        for stack_set in stack_sets:
            name = stack_set['StackSetName']
            stack_set_detail = self._retrieve_stackset(stackset_name=name)
            stack_instances = self._retrieve_stackset_instances(stackset_name=name)

            stack_set_model = {
                'name': name,
                'id': stack_set['StackSetId'],
                'description': stack_set['Description'],
                'status': stack_set['Status'],
                'arn': stack_set_detail['StackSetARN'],
                'administration_role_arn': stack_set_detail['AdministrationRoleARN'],
                'capabilities': stack_set_detail['Capabilities'],
                'parameters': [
                    {
                        'key': parameter['ParameterKey'],
                        'value': parameter['ParameterValue'],
                        'use_previous': parameter['UsePreviousValue']
                    }
                    for parameter in stack_set_detail['Parameters']
                ],
                'tags': [
                    {
                        'key': tag['Key'],
                        'value': tag['Value']
                    }
                    for tag in stack_set_detail['Tags']
                ],
                'template_body': stack_set_detail['TemplateBody'],
                'instances': [
                    {
                        'stack_set_id': instance['StackSetId'],
                        'region': instance['Region'],
                        'account': instance['Account'],
                        'stack_id': instance['StackId'],
                        'status': instance['Status'],
                        'reason': instance.get('StatusReason', None)
                    }
                    for instance in stack_instances
                ]
            }

            organization.stack_sets[name] = stack_set_model
            # policy_targets_res = self.client.list_targets_for_policy(PolicyId=policy["Id"])
            # for target in policy_targets_res["Targets"]:
            #     self._add_policy_to_target(org_model=organization, target=target, policy_name=policy['Name'])

    def _retrieve_stackset(self, stackset_name):
        try:
            response = self.client.describe_stack_set(
                StackSetName=stackset_name
            )
            return response
        except ClientError as err:
            if err.response['Error']['Code'] != "ResourceNotFoundException":
                print('Error: {}.'.format(err.response['Error']['Message']))
                raise err
            else:
                return None

    def _create_stackset(self, stackset):
        '''
        '''
        raise NotImplementedError()

    def _update_stackset(self, stackset):
        '''
        {
            'OperationId': 'string'
        }
        '''
        response = self.client.update_stack_set(
            StackSetName=stackset.name,
            Description='string',
            TemplateBody='string',
            TemplateURL='string',
            UsePreviousTemplate=False,
            Parameters=[
                {
                    'ParameterKey': 'string',
                    'ParameterValue': 'string',
                    'UsePreviousValue': False,
                    'ResolvedValue': 'string'
                },
            ],
            Capabilities=[
                'CAPABILITY_IAM',
                'CAPABILITY_NAMED_IAM',
            ],
            Tags=[
                {
                    'Key': 'string',
                    'Value': 'string'
                },
            ],
            OperationPreferences={
                'RegionOrder': [
                    'string',
                ],
                'FailureToleranceCount': 123,
                'FailureTolerancePercentage': 123,
                'MaxConcurrentCount': 123,
                'MaxConcurrentPercentage': 123
            },
            AdministrationRoleARN='string',
            OperationId='string'
        )
        return response

    def upsert_stack_instance(self, stackset, accounts):
        '''
        Update a set of stack instances based on an accounts list.
        '''
        for account in accounts:
            response = self.client.create_stack_instances(
                StackSetName=stackset.name,
                Accounts=[
                    account.id
                ],
                Regions=account.raw_config.get('regions'),
                ParameterOverrides=[
                    {
                        'ParameterKey': 'string',
                        'ParameterValue': 'string',
                        'UsePreviousValue': False,
                        'ResolvedValue': 'string'
                    },
                ],
                OperationPreferences={
                    'RegionOrder': [
                        'string',
                    ],
                    'FailureToleranceCount': 123,
                    'FailureTolerancePercentage': 123,
                    'MaxConcurrentCount': 123,
                    'MaxConcurrentPercentage': 123
                },
                OperationId='string'
            )
        return response

    def _retrieve_stackset_instances(self, stackset_name):
        '''
        '''
        results = []
        next_token = None
        while True:
            response = self._page_stackset_instances(
                stackset_name=stackset_name,
                next_token=next_token
            )
            results.extend(response.get('Summaries'))
            next_token = response.get('NextToken', None)
            if next_token is None:
                break
        return results

    def _page_stackset_instances(self, stackset_name, next_token=None):
        '''
        {
            'Summaries': [
                {
                    'StackSetId': 'string',
                    'Region': 'string',
                    'Account': 'string',
                    'StackId': 'string',
                    'Status': 'CURRENT'|'OUTDATED'|'INOPERABLE',
                    'StatusReason': 'string'
                },
            ],
            'NextToken': 'string'
        }
        '''
        if next_token:
            response = self.client.list_stack_instances(
                StackSetName=stackset_name,
                NextToken=next_token
            )
        else:
            response = self.client.list_stack_instances(
                StackSetName=stackset_name
            )
        return response
