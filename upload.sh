#!/bin/bash

# you must specify version to make sure uploading correct version
if [[ -z "$1" ]]; then
  echo "Usage: $(basename $0) version"
fi

twine upload dist/rvgeocoder-${version}

