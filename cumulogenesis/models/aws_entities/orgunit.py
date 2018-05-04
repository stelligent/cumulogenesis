'''
Provides OrganizationalUnit
'''
from cumulogenesis.models.aws_entity import AwsEntity

class OrganizationalUnit(AwsEntity):
    '''
    Represents an AWS Organizational Unit entity
    '''
    def __init__(self, name, policies=None, accounts=None, parent_orgunit=None):
        self.name = name
        self.policies = policies or []
        self.accounts = accounts or []
        self.parent_orgunit = parent_orgunit
        super(OrganizationalUnit).__init__()
