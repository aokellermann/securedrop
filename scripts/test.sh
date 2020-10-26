#!/usr/bin/env bash

./scripts/keygen.sh < scripts/key_test_input.txt >/dev/null 2>/dev/null

PYTHONPATH=$PYTHONPATH:. ./securedrop/tests/client_test.py
PYTHONPATH=$PYTHONPATH:. ./securedrop/tests/command_test.py