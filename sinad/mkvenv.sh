#!/bin/bash

set -o errexit
set -o nounset

rm -fr .venv pydwf-examples

python3 -m venv .venv
. .venv/bin/activate

pip install -r requirements.txt
pip install --no-deps pysnr

#python -m pydwf extract-examples
