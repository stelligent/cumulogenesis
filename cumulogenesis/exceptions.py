'''
Exceptions
'''
import pyaml

class MissingRequiredParameterException(Exception):
    '''
    Indicates that a required configuration parameter was not provided
    '''
    def __init__(self, parameter, parent):
        message = "Missing required parameter %s for %s" % (parameter, parent)
        Exception.__init__(self, message)

class MultipleParametersSpecifiedException(Exception):
    '''
    Indicates that multiple configuration parameters were supplied when
    only one was expected
    '''
    def __init__(self, parameters, parent):
        #pylint: disable=line-too-long
        message = 'Only one of the parameters %s were expected to be provided for %s' % (', '.join(parameters), parent)
        Exception.__init__(self, message)

class ParameterTypeMismatchException(Exception):
    '''
    Indicates that the provided configuration parameter was not of
    the expected type
    '''
    def __init__(self, parameter, expected_type, parent):
        #pylint: disable=line-too-long
        message = 'Expected parameter %s provided for %s to be of type %s' % (parameter, parent, expected_type)
        Exception.__init__(self, message)

class DuplicateNamesException(Exception):
    '''
    Indicates that multiple entities of the same type were provided
    with the same name
    '''
    def __init__(self, name, entity_type):
        #pylint: disable=line-too-long
        message = 'Found multiple entities named "%s" of type %s. All entity names must be unique.' % (name, entity_type)
        Exception.__init__(self, message)

class InvalidOrganizationException(Exception):
    '''
    Indicates that an Organization model's structure is invalid
    '''
    def __init__(self, problems):
        message = 'Organization structure is invalid. Problems:\n%s' % pyaml.dump(problems)
        Exception.__init__(self, message)

class OrgunitHierarchyCycleException(Exception):
    '''
    Indicates that a cycle was found in an Organization model's
    orgunit hierarchy
    '''
    def __init__(self, cycle_path):
        message = 'Detected cycle in the orgunit hierarchy:\n   %s' % '\n=> '.join(cycle_path)
        Exception.__init__(self, message)

class AccessKeysInvalidException(Exception):
    '''
    Indicates that there was a problem with the provided access keys when building
    a boto3 session.
    '''
    pass

class RoleNameNotSpecifiedException(Exception):
    '''
    Indicates that a role name wasn't provided and the session builder wasn't given
    a default role name to use otherwise.
    '''
    pass

class NotAwsModelException(Exception):
    '''
    Indicates that a method was called on a model that assumes the source for the model
    was the AWS API when the method is only intended to be used with an AWS model
    e.g., loading it from what currently exists or converging differences.
    '''
    def __init__(self, method):
        message = '%s was called on a model that was not initialized with a source of "aws"' % method
        Exception.__init__(self, message)

class OrganizationMemberAccountException(Exception):
    '''
    Indicates that the account is already a member account of an organization and so
    cannot become an organization root account.
    '''
    def __init__(self, account_id, master_account_id):
        #pylint: disable=line-too-long
        message = 'The desired root account %s is already a member of an organization with master account %s' % (account_id, master_account_id)
        Exception.__init__(self, message)
