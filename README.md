# cumulogenesis

This is an in-development tool that will manage AWS Organization bootstrapping and management.

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
