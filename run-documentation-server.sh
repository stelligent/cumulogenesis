#!/bin/bash

# A thin wrapper that runs the pydoc documentation server.

echo "Starting the pydocmd documentation server. Once started, access http://localhost:8000 to view the documentation."
echo "Ctrl+C to quit."
cd docs && pydocmd serve
