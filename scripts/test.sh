#!/usr/bin/env bash

set -eo pipefail

trap "echo 'Tests failed!'" ERR

rm -f securedrop/tests/*.json securedrop/tests/*.crt securedrop/tests/*.key
bash scripts/keygen.sh < scripts/key_test_input.txt >/dev/null 2>/dev/null

cd securedrop/tests
PYTHONPATH=$PYTHONPATH:../.. python3 client_test.py
PYTHONPATH=$PYTHONPATH:../.. python3 command_test.py

echo "All tests passed successfully!"