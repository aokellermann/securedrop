#!/usr/bin/env bash

set -eo pipefail

trap "echo 'Tests failed!'" ERR

cd securedrop/tests
rm -f *.json *.pem
openssl req -new -x509 -days 365 -nodes -out server.pem -keyout server.pem < ../../scripts/key_test_input.txt >/dev/null 2>/dev/null

PYTHONPATH=$PYTHONPATH:../.. python3 client_test.py
#PYTHONPATH=$PYTHONPATH:../.. python3 client_server_base_test.py

echo "All tests passed successfully!"