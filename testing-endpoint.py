#!/usr/bin/env python

import sys
import yaml
import pyaml
import cumulogenesis.loaders.config as config_loader

input_file = sys.argv[1]
with open(input_file, 'r') as f:
    config = yaml.load(f)

org = config_loader.load_organization_from_config(config)
print("\nOrg validation output follows (an empty dict means no problems detected).")
print(org.validate())
print("\nThe Org orgunit/account hierarchy follows.")
print(pyaml.dump(org.get_orgunit_hierarchy()))
print("\nThe dumped Org model configuration follows.")
print(pyaml.dump(config_loader.dump_organization_to_config(org)))
