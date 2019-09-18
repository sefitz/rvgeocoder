#!/bin/bash

# you must specify version to make sure uploading correct version
if [[ -z "$1" ]]; then
  echo "Usage: $(basename $0) version"
  exit 1
fi

version=$1
twine upload dist/rvgeocoder-${version}*

