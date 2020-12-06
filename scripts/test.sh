#!/usr/bin/env bash

set -eo pipefail

trap "echo 'Tests failed!'" ERR
trap "rm -f ./*.json ./*.pem" EXIT

cd securedrop/tests
openssl req -new -x509 -days 365 -nodes -out server.pem -keyout server.pem < ../../scripts/key_test_input.txt >/dev/null 2>/dev/null

files=$(find . -type f -name "*test.py")
for file in $files; do
  PYTHONPATH=$PYTHONPATH:../.. ./"$file"
done

echo "Tests succeeded!"
