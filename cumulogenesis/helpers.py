'''
Helpers
'''
from collections import OrderedDict
import pprint
import yaml
from deepdiff import DeepDiff

#pylint: disable=invalid-name
def ordered_yaml_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    '''
    Deserializes from YAML representing all mappings as OrderedDict
    '''
    #pylint: disable=too-many-ancestors
    class _OrderedLoader(Loader):
        '''
        Our custom YAML loader
        '''
        @classmethod
        def remove_implicit_resolver(cls, tag_to_remove):
            """
            Remove implicit resolvers for a particular tag

            Takes care not to modify resolvers in super classes.

            We want to load datetimes as strings, not dates, because we
            go on to serialise as json which doesn't have the advanced types
            of yaml, and leads to incompatibilities down the track.
            """
            if 'yaml_implicit_resolvers' not in cls.__dict__:
                cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()

            for first_letter, mappings in cls.yaml_implicit_resolvers.items():
                cls.yaml_implicit_resolvers[first_letter] = [(tag, regexp)
                                                             for tag, regexp in mappings
                                                             if tag != tag_to_remove]
    _OrderedLoader.remove_implicit_resolver('tag:yaml.org,2002:timestamp')
    def _construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    _OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_mapping)
    return yaml.load(stream, _OrderedLoader)

#pylint: disable=invalid-name
def ordered_yaml_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    '''
    Serializes to YAML preserving the order from OrderedDict mappings
    '''
    #pylint: disable=too-many-ancestors
    class _OrderedDumper(Dumper):
        '''
        Our custom YAML dumper
        '''
        pass
    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())
    _OrderedDumper.add_representer(OrderedDict, _dict_representer)
    _OrderedDumper.ignore_aliases = lambda *args: True
    return yaml.dump(data, stream, _OrderedDumper, **kwds)

def pretty_print(data, width=120):
    '''
    Wrapper for pprint that allows the line width to be specified.
    '''
    pprinter = pprint.PrettyPrinter(width=width)
    return pprinter.pprint(data)

def _convert_to_dict_if_ordered(item):
    if isinstance(item, OrderedDict):
        item = dict(item)
    return item

def deep_diff(dict1, dict2):
    '''
    Diffs two objects and returns a dict describing the differences
    '''
    item1 = _convert_to_dict_if_ordered(dict1)
    item2 = _convert_to_dict_if_ordered(dict2)
    return DeepDiff(item1, item2, ignore_order=True)

def print_expected_actual_diff(expected, actual):
    '''
    Pretty prints two objects and their differences after a deep diff
    '''
    print("Expected:")
    pretty_print(expected)
    print("\nActual:")
    pretty_print(actual)
    print("\nDifference:")
    diff = deep_diff(expected, actual)
    pretty_print(diff)

def write_report(report, output_file):
    '''
    Convenience method for writing a report to an output file
    '''
    with open(output_file, 'w') as file_handle:
        file_handle.write(report)
