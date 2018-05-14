'''
Provides SessionService
'''

import time
import boto3

from cumulogenesis import exceptions

class SessionService(object):
    '''
    Provides methods for building Boto3 sessions from the provided account,
    profile, and role information
    '''

    #pylint: disable=line-too-long,too-many-arguments
    def __init__(self, profile_name=None, default_role_name=None, access_key=None, secret_key=None, default_region=None):
        self.profile_name = profile_name
        self.default_role_name = default_role_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.default_region = default_region

    def get_base_session(self, region=None):
        '''
        Returns a base boto3 session from the profile_name or access_key and secret_key
        properties set during initialization
        '''
        session_parameters = {}
        if self.access_key or self.secret_key:
            if not self.access_key and self.secret_key:
                #pylint: disable=line-too-long
                raise exceptions.AccessKeysInvalidException("Both access_key and secret_key must be provided if either is provided.")
            else:
                session_parameters['aws_access_key_id'] = self.access_key
                session_parameters['aws_secret_access_key'] = self.secret_key
        elif self.profile_name:
            session_parameters['profile_name'] = self.profile_name
        if region:
            session_parameters['region_name'] = region
        elif self.default_region:
            session_parameters['region_name'] = region
        return boto3.Session(**session_parameters)

    def get_account_role_session(self, account_id, region=None, role_name=None):
        '''
        Returns a boto3 session that is an assumed role in the specified account and
        region
        '''
        base_session = self.get_base_session(region=region)
        sts = base_session.client('sts')
        if not role_name and not self.default_role_name:
            raise exceptions.RoleNameNotSpecifiedException('Neither a role name nor default role name were specified.')
        elif not role_name:
            role_name = self.default_role_name
        assume_role_parameters = {
            "RoleArn": 'arn:aws:iam::%s:role/%s' % (account_id, role_name),
            "RoleSessionName": 'cumulogenesis-%s' % str(int(time.time()))}
        assumed_role = sts.assume_role(**assume_role_parameters)
        credentials = assumed_role['Credentials']
        assume_role_session_parameters = {
            "aws_access_key_id": credentials['AccessKeyId'],
            "aws_secret_access_key": credentials['SecretAccessKey'],
            "aws_session_token": credentials['SessionToken']}
        if region:
            assume_role_session_parameters['region_name'] = region
        elif self.default_region:
            assume_role_session_parameters['region_name'] = self.default_region
        assumed_role_session = boto3.Session(**assume_role_session_parameters)
        return assumed_role_session
