from cumulogenesis.models.aws_entity import AwsEntity

class Account(AwsEntity):
    def __init__(self, name, owner, groups=None, accountid=None):
        self.name = name
        self.owner = owner
        self.groups = groups or []
        self.account_id = accountid
        self.raw_config = None
        self.parent_references = None
        super(Account).__init__()
