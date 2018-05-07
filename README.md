# cumulogenesis

This is a stub repository for a tool that will manage AWS Organization bootstrapping and management. This is under active development.

## Opinionated Features

### Account regions

_Opinion:_ Accounts should be used only for a single application or business use case. As a result, there shouldn't be a case where one set of resources is deployed in one region for an account while a separate set of resources is deployed in a different region.

Accounts have `region` parameters, which represent the regions in which resources associated with the account should be provisioned. Resources like Stacks will be provisioned against each region for the account, and this cannot be overridden.
## Implemented/To Do

### Implemented

- POC AWS Organization model
- Configuration loader/dumper
- Integration tests for the above

### To Do

- Unit tests for the AWS Organization model
- Unit tests for the configuration loader/dumper
- Everything else labelled _backlog_ in the GitHub issues

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
