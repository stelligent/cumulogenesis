#!/bin/sh

echo "Running unit tests with nosestests"
nosetests
echo "\nRunning static code analysis with pylint"
pylint cumulogenesis tests

