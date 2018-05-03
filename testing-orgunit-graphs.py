#!/usr/bin/env python

from cumulogenesis.models.aws_entities.organization import Organization

graph = {"a": "ROOT_ACCOUNT",
         "b": "ROOT_ACCOUNT",
         "c": "b",
         "d": "e",
         "e": "f",
         "f": "d"}

org = Organization(root_account_id = '123456789')
res = org._find_path(graph, 'c', 'ROOT_ACCOUNT')
print(res)
