'''
Provides CloudformationService
'''
import boto3
from botocore.client import ClientError

from cumulogenesis.log_handling import LOGGER as logger
# raise NotImplementedError()


class CloudformationService:
    ''' Instance constructor - requires a pre-configured boto3 Session object '''
    def __init__(self, session):
        self.session = session
        self.client = boto3.client('cloudformation', session)

    def upsert_stackset(self, stackset):
        ''' Create or update a stack-set '''
        aws_stackset = self._retrieve_stackset(stackset_name=stackset.name)
        if aws_stackset:
            logger.debug(aws_stackset)
            # involves diff of a stack-set's innate attributes
            return self._update_stackset(stackset=stackset)

        return self._create_stackset(stackset=stackset)

    def _retrieve_stackset(self, stackset_name):
        '''
        {
            'StackSet': {
                'StackSetName': 'string',
                'StackSetId': 'string',
                'Description': 'string',
                'Status': 'ACTIVE'|'DELETED',
                'TemplateBody': 'string',
                'Parameters': [
                    {
                        'ParameterKey': 'string',
                        'ParameterValue': 'string',
                        'UsePreviousValue': True|False,
                        'ResolvedValue': 'string'
                    },
                ],
                'Capabilities': [
                    'CAPABILITY_IAM'|'CAPABILITY_NAMED_IAM',
                ],
                'Tags': [
                    {
                        'Key': 'string',
                        'Value': 'string'
                    },
                ],
                'StackSetARN': 'string',
                'AdministrationRoleARN': 'string'
            }
        }
        '''
        try:
            response = self.client.describe_stack_set(
                StackSetName=stackset_name
            )
            return response
        except ClientError as err:
            if err.response['Error']['Code'] != "ResourceNotFoundException":
                print('Error: {}.'.format(err.response['Error']['Message']))
                raise err
        return None

    def _create_stackset(self, stackset):
        '''
        {
            'StackSetId': 'string'
        }
        '''
        response = self.client.create_stack_set(
            StackSetName=stackset.name,
            Description='string',
            TemplateBody='string',
            TemplateURL='string',
            # Parameters=[
            #     {
            #         'ParameterKey': 'string',
            #         'ParameterValue': 'string',
            #         'UsePreviousValue': False,
            #         'ResolvedValue': 'string'
            #     },
            # ],
            Capabilities=[
                'CAPABILITY_IAM',
                'CAPABILITY_NAMED_IAM'
            ],
            # Tags=[
            #     {
            #         'Key': 'string',
            #         'Value': 'string'
            #     }
            # ]
            AdministrationRoleARN='string'
        )
        return response

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

    def _retrieve_stackset_instances(self, stackset):
        '''
        Sadly, boto3 1.7.12 lacks a paginator for `{cloudformation client}.list_stack_instances`,
        so we create our own.
        [
            {
                'StackSetId': 'string',
                'Region': 'string',
                'Account': 'string',
                'StackId': 'string',
                'Status': 'CURRENT'|'OUTDATED'|'INOPERABLE',
                'StatusReason': 'string'
            }
        ]
        '''
        results = []
        next_token = None
        while True:
            response = self._page_stackset_instances(
                stackset_name=stackset.name,
                next_token=next_token
            )
            results.extend(response.get('Summaries'))
            next_token = response.get('NextToken')
            if next_token is None:
                break

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
