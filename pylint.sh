#!/bin/bash

# This is a shim for editor linter plugins like Atom's linter-pylint
# that need an executable they can call directly to run pylint.
pipenv run pylint $@
