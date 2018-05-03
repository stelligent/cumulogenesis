class Provisioner(object):
    def __init__(self, role='org-bootstrapper', provisioner_type='cfn-stack-set'):
        self.role = role
        self.type = provisioner_type
        self.raw_config = None
