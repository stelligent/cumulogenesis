'''
Provides Policy
'''
from cumulogenesis.models.aws_entity import AwsEntity

class Policy(AwsEntity):
    '''
    Represents an AWS Service Control Policy entity
    '''
    def __init__(self, name, description=None, document=None):
        self.name = name
        self.description = description
        self.document = document
        super(Policy).__init__()
