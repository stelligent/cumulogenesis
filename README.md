# cumulogenesis

This is an in-development tool that will manage AWS Organization bootstrapping and management.

## Opinionated Features

### Account regions

_Opinion:_ Accounts should be used only for a single application or business use case. As a result, there shouldn't be a case where one set of resources is deployed in one region for an account while a separate set of resources is deployed in a different region.

Accounts have `region` parameters, which represent the regions in which resources associated with the account should be provisioned. Resources like Stack Sets will be provisioned against each region for the account, and this cannot be overridden.

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
