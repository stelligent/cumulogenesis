'''
Provides Account
'''
from cumulogenesis.models.aws_entity import AwsEntity

class Account(AwsEntity):
    '''
    Represents an AWS Account entity
    '''
    #pylint: disable=too-many-arguments
    def __init__(self, name, owner, groups=None, accountid=None, regions=None):
        self.name = name
        self.owner = owner
        self.groups = groups or []
        self.account_id = accountid
        self.raw_config = None
        self.parent_references = None
        self.regions = regions or []
        super(Account).__init__()
