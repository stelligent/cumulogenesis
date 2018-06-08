# cumulogenesis

This is a tool that allows an AWS Organization to be described in a YAML format and subsequently deployed. Key features:

- Creation and management of AWS Organizations, Organizational Units, Accounts, and Service Control Policies
- Dry runs that produce reports that demonstrate the expected and existing Organization states and list the required changes to converge the actual Organization state to the expected state.
- A simple command line interface for executing bothdry runs and convergence.

It is implemented in Python 3 and uses [pipenv](https://docs.pipenv.org/) to manage Python virtualenv configuration and dependency management.

## Installation

1. [Install pipenv](https://docs.pipenv.org/#install-pipenv-today). You may need to update your `pipenv` installation as some older versions do not support the `Pipfile` `[scripts]` entrypoints used in the examples below.

2. Clone this repository

3. Install virtualenv and module dependencies

```
cd cumulogenesis
pipenv install
```

## Usage

1. Create a configuration that describes the desired state of your organization. See [the examples](examples/).

2. Run the `pipenv run cumulogenesis` wrapper to run the CLI in the `pipenv` created virtualenv.

When run without `--converge`, a dry run report will be logged to the console that demonstrates the changes that will be made during convergence. When run with `--converge`, a dry run will be executed and a YAML report will logged to the console, then convergence will be run and a report demonstrating changes that were made will be logged to the console.

These YAML reports can also be written to the filesystem with the `--dry-run-report-file` and `--converge-report-file` arguments.

```
$ pipenv run cumulogenesis --help
usage: cumulogenesis.py [-h] --config-file CONFIG_FILE [--profile PROFILE]
                        [--converge]
                        [--dry-run-report-file DRY_RUN_REPORT_FILE]
                        [--converge-report-file CONVERGE_REPORT_FILE]
                        [--log-level LOG_LEVEL]

Loads an Organization model from the configuration in the specified YAML file,
loads the corresponding existing resources from AWS, then executes a
comparison dry run and generates a report of the differences. Optionally, it
will converge the differences to make the Organization in AWS match what is
specified in the configuration when run with the --converge option. Both dry
run and converge reports are printed to the console by default. Reports can be
written to the files specified with --dry-run-report-file and --converge-
report-file

optional arguments:
  -h, --help            show this help message and exit
  --config-file CONFIG_FILE
                        The path to the YAML file containing the configured
                        Organization model.
  --profile PROFILE     The name of the AWS CLI profile to use when
                        initializing AWS API sessions.
  --converge            When specified, will attempt to converge differences
                        between the configured Organization model and the AWS
                        resources after executing a dry run.
  --dry-run-report-file DRY_RUN_REPORT_FILE
                        The path to the file that should contain the dry run
                        report in addition to being printed to the console.
  --converge-report-file CONVERGE_REPORT_FILE
                        The path to the file that should contain the
                        convergence report in addition to being printed to the
                        console.
  --log-level LOG_LEVEL
                        The console log level to set. Valid values include
                        DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Recommended IAM Policy

Running Cumulogenesis will require some permissions on your AWS account. Below are the minimum requirements for the full feature set of this software.

See [the example IAM Policy to use Cumulogenesis](examples/aws/iam-policy.json).

## Opinionated Features

### Account regions

_Opinion:_ Accounts should be used only for a single application or business use case. As a result, there shouldn't be a case where one set of resources is deployed in one region for an account while a separate set of resources is deployed in a different region.

Accounts have `region` parameters, which represent the regions in which resources associated with the account should be provisioned. Resources like Stack Sets will be provisioned against each region for the account, and this cannot be overridden.

### Policies

- When not specified, Orgunit and Account entities will have the `FullAWSAccess` AWS-managed policy attached to them. This policy will be replaced by the user-specified policies if any are specified. If you plan to use deny-only policies, ensure that `FullAWSAccess` is still specified somewhere in the Organization hierarchy.

## Implemented/To Do

See the [project board](https://github.com/stelligent/cumulogenesis/projects/1).

## Running tests

### Unit/static code/intramodule integration tests

1. Install development dependencies

```
pipenv install --dev
```

2. Execute tests:

```
pipenv run tests
```

## Generating Documentation

Auto-generated documentation is provided by [pydoc-markdown](https://github.com/NiklasRosenstein/pydoc-markdown). To build the documentation and run a local webserver to view it:

1. Install development dependencies

```
pipenv install --dev
```

2. Run the documentation server

```
pipenv run doc-server
```

3. Visit https://localhost:8000/ in your browser.

## Acknowledgements

Huge thanks to @jedugas and everyone else on the Stelligent team whose previous work informed this project.
