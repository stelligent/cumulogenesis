import pyaml

class MissingRequiredParameterException(Exception):
    def __init__(self, parameter, parent):
        message = "Missing required parameter item %s for %s" % (parameter, parent)
        Exception.__init__(self, message)

class MultipleParametersSpecifiedException(Exception):
    def __init__(self, parameters, parent):
        #pylint: disable=line-too-long
        message = 'Only one of the parameters %s were expected to be provided for %s' % (', '.join(parameters), parent)
        Exception.__init__(self, message)

class ParameterTypeMismatchException(Exception):
    def __init__(self, parameter, expected_type, parent):
        #pylint: disable=line-too-long
        message = 'Expected parameter %s provided for %s to be of type %s' % (parameter, parent, expected_type)
        Exception.__init__(self, message)

class DuplicateNamesException(Exception):
    def __init__(self, name, entity_type):
        #pylint: disable=line-too-long
        message = 'Found multiple entities named "%s" of type %s. All entity names must be unique.' % (name, entity_type)
        Exception.__init__(self, message)

class InvalidOrganizationException(Exception):
    def __init__(self, problems):
        message = 'Organization structure is invalid. Problems:\n%s' % pyaml.dump(problems)
        Exception.__init__(self, message)

class OrgunitHierarchyCycleException(Exception):
    def __init__(self, cycle_path):
        message = 'Detected cycle in the orgunit hierarchy:\n   %s' % '\n=> '.join(cycle_path)
        Exception.__init__(self, message)
