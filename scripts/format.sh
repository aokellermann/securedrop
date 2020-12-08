#!/usr/bin/env bash

set -eo pipefail

# format the source files
if [ "$#" -eq 0 ]
then
  # format source files
  yapf -i -r securedrop bin 2>/dev/null

# check if source code is formatted.
elif [ "$1" == "check" ]
then

  yapf -d -r securedrop bin

fi
