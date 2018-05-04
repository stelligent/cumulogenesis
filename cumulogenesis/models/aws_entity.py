'''
Provides AwsEntity
'''

class AwsEntity:
    '''
    Base class for AWS Entity models
    '''
    def __init__(self):
        self.should_provision = None
        self.should_update = None
        self.should_delete = None
        self.raw_config = None
        self.source = None
        self.renderable_attributes = []
        self.name = None
        self.aws_identifier = None
