'''
Provides Provisioner
'''
class Provisioner:
    '''
    Represents the Organization's resource provisioner
    '''
    def __init__(self, role='org-bootstrapper', provisioner_type='cfn-stack-set'):
        self.role = role
        self.type = provisioner_type
        self.raw_config = None
