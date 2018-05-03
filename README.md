# cumulogenesis

This is a stub repository for a tool that will manage AWS Organization bootstrapping and management. This is under active development.

# In-progress testing

Quick and dirty testing can be done with the provided `testing-endpoint.py` script. Examples below (assume you've run `pipenv install` and `pipenv shell`):

```
(cumulogenesis-UkmCKGkR) bash-3.2$ python testing-endpoint.py example_data/import-test-1.yaml
Using config loader for config version 0.1

Org validation output follows (an empty dict means no problems detected).
{}

The Org orgunit/account hierarchy follows.
ROOT_ACCOUNT:
  orgunits:
    'IAM Federation':
      accounts:
        - pre-existing-account
    'The Foos':
      accounts:
        - foo-account
      orgunits:
        'The Bars':
          accounts:
            - bar-account


The dumped Org model configuration follows.
No config loader found for specified config version, or config version not specified. Using default.
root: 123456789
featureset: ALL
version: 0.1
provisioner:
  role: org-bootstrapper
  type: cfn-stack-set
accounts:
  - name: foo-account
    owner: foo-owner-email@mycompany.com
    groups:
      - foo-bar-group
  - name: bar-account
    owner: bar-owner-email@othercompany.com
    groups:
      - foo-bar-group
  - name: pre-existing-account
    owner: pre-existing-account-owner@othercompany.com
    accountid: 987654321
policies:
  - name: no-x-policy
    description: 'allows all services to be utilized except <X>'
    document:
      location: s3://not-a-real-bucket/or/path
  - name: scp-federation-only
    description: 'enables only those services required for IDP federation'
    document:
      content:
        isnt:
          - actually
          - a
          - real
          - policy
          - document
        wow: this
orgunits:
  - name: 'IAM Federation'
    policies:
      - scp-federation-only
    accounts:
      - pre-existing-account
  - name: 'The Foos'
    policies:
      - no-x-policy
    accounts:
      - foo-account
    orgunits:
      - name: 'The Bars'
        accounts:
          - bar-account
stacks:
  - name: core-vpc
    orgunits:
      - name: 'The Foos'
        regions:
          - us-east-1
          - us-east-2
    template:
      location: s3://also-not-a-real-bucket/or/path
  - name: federation-idp
    accounts:
      - name: pre-existing-account
        regions:
          - us-east-1
    template:
      content:
        this:
          - 'is also'
          - 'not a real document'

```

```
(cumulogenesis-UkmCKGkR) bash-3.2$ python testing-endpoint.py example_data/import-test-orphans.yaml
Using config loader for config version 0.1

Org validation output follows (an empty dict means no problems detected).
{'accounts': {'orphaned-account': ['orphaned']}}

The Org orgunit/account hierarchy follows.
ORPHANED:
  accounts:
    - orphaned-account
ROOT_ACCOUNT:
  orgunits:
    'IAM Federation':
      accounts:
        - pre-existing-account
    'The Foos':
      accounts:
        - foo-account
      orgunits:
        'The Bars':
          accounts:
            - bar-account


The dumped Org model configuration follows.
No config loader found for specified config version, or config version not specified. Using default.
Traceback (most recent call last):
  File "testing-endpoint.py", line 18, in <module>
    print(pyaml.dump(config_loader.dump_organization_to_config(org)))
  File "/Users/rmc3/git-co/cumulogenesis/cumulogenesis/loaders/config.py", line 25, in dump_organization_to_config
    return loader.dump_organization_to_config(organization)
  File "/Users/rmc3/git-co/cumulogenesis/cumulogenesis/loaders/config_loaders/default_config_loader.py", line 49, in dump_organization_to_config
    organization.raise_if_invalid()
  File "/Users/rmc3/git-co/cumulogenesis/cumulogenesis/models/aws_entities/organization.py", line 285, in raise_if_invalid
    raise exceptions.InvalidOrganizationException(problems)
cumulogenesis.exceptions.InvalidOrganizationException: Organization structure is invalid. Problems:
accounts:
  orphaned-account:
    - orphaned
```
