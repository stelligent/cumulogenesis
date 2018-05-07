'''
Provides OrganizationalUnit
'''
from cumulogenesis.models.aws_entity import AwsEntity

class OrganizationalUnit(AwsEntity):
    '''
    Represents an AWS Organizational Unit entity
    '''
    def __init__(self, name, policies=None, accounts=None, child_orgunits=None):
        self.name = name
        self.policies = policies or []
        self.accounts = accounts or []
        self.child_orgunits = child_orgunits or []
        self.parent_references = []
        super(OrganizationalUnit).__init__()
