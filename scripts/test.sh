#!/usr/bin/env bash

set -eo pipefail

trap "echo 'Tests failed!'" ERR

PYTHONPATH=$PYTHONPATH:../.. python3 client_test.py
PYTHONPATH=$PYTHONPATH:../.. python3 command_test.py

echo "All tests passed successfully!"
