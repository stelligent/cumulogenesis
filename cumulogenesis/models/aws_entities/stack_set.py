'''
Provides StackSet
'''
from cumulogenesis.models.aws_entity import AwsEntity

class StackSet(AwsEntity):
    '''
    Represents an AWS Stack Set resource entity
    '''
    #pylint: disable=too-many-arguments
    def __init__(self, name, groups=None, accounts=None, orgunits=None, template=None):
        self.name = name
        self.groups = groups or []
        self.accounts = accounts or []
        self.orgunits = orgunits or []
        self.template = template
        super(StackSet).__init__()
