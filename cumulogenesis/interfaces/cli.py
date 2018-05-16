'''
Provides a command line interface for running dry runs and convergence
based on the provided Organization model configuration
'''

import argparse
from cumulogenesis import helpers, log_handling
from cumulogenesis.loaders import config as config_loader
from cumulogenesis.log_handling import LOGGER as logger

DESCRIPTION = '''
    Loads an Organization model from the configuration in the specified YAML file,
    loads the corresponding existing resources from AWS, then executes a comparison
    dry run and generates a report of the differences.

    Optionally, it will converge the differences to make the Organization in AWS
    match what is specified in the configuration when run with the --converge
    option.

    Both dry run and converge reports are printed to the console by default.
    Reports can be written to the files specified with --dry-run-report-file and
    --converge-report-file
    '''

def run():
    '''
    Parses arguments and executes from the command line.
    '''
    args = _parse_args()
    provisioner_overrides = {}
    if args.profile:
        provisioner_overrides['profile'] = args.profile
    log_handling.enable_console_logging(level=args.log_level)
    org_model = config_loader.load_organization_from_yaml_file(args.config_file)
    dry_run_report = org_model.dry_run(provisioner_overrides=provisioner_overrides)
    _dump_report_organizations(dry_run_report)
    dry_run_report_yaml = helpers.ordered_yaml_dump(dry_run_report)
    logger.info('Dry run report follows.')
    logger.info(dry_run_report_yaml)
    if args.dry_run_report_file:
        helpers.write_report(report=dry_run_report_yaml, output_file=args.dry_run_report_file)
    if args.converge:
        converge_report = org_model.converge(provisioner_overrides=provisioner_overrides)
        _dump_report_organizations(converge_report)
        converge_report_yaml = helpers.ordered_yaml_dump(converge_report)
        logger.info('Converge report follows.')
        logger.info(converge_report_yaml)
        if args.converge_report_file:
            helpers.write_report(report=converge_report_yaml, output_file=args.converge_report_file)

def _dump_report_organizations(report):
    for key in ['configured_organization', 'actual_organization']:
        report[key] = config_loader.dump_organization_to_config(report[key])

def _parse_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        '--config-file', type=str, dest='config_file', required=True,
        help='The path to the YAML file containing the configured Organization model.')
    parser.add_argument(
        '--profile', type=str, dest='profile',
        help='The name of the AWS CLI profile to use when initializing AWS API sessions.')
    parser.add_argument(
        '--converge', action='store_true', dest='converge',
        help='''When specified, will attempt to converge differences between the configured
              Organization model and the AWS resources after executing a dry run.''')
    parser.add_argument(
        '--dry-run-report-file', type=str, dest='dry_run_report_file',
        help='The path to the file that should contain the dry run report in addition to being printed to the console.')
    parser.add_argument(
        '--converge-report-file', type=str, dest='converge_report_file',
        #pylint: disable=line-too-long
        help='The path to the file that should contain the convergence report in addition to being printed to the console.')
    parser.add_argument(
        '--log-level', type=str, dest='log_level', default='INFO',
        help='The console log level to set. Valid values include DEBUG, INFO, WARNING, ERROR, CRITICAL')

    args = parser.parse_args()
    return args
