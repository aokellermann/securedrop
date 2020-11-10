#!/usr/bin/env bash

set -eo pipefail

trap "echo 'Tests failed!'" ERR
trap "rm -f securedrop.json" EXIT

for file in ./securedrop/tests/*_test.py; do
  PYTHONPATH=$PYTHONPATH:. ./"$file"
done

echo "Tests succeeded!"
