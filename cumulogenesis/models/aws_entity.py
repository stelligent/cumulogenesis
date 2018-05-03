class AwsEntity(object):
    def __init__(self):
        self.should_provision = None
        self.should_update = None
        self.should_delete = None
        self.raw_config = None
        self.source = None
        self.renderable_attributes = []
        self.name = None
        self.aws_identifier = None
