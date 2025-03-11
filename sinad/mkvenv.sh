#!/bin/bash

set -o errexit
set -o nounset

rm -fr .venv pydwf-examples

python3 -m venv .venv
. .venv/bin/activate
pip install pydwf
pip install matplotlib
pip install scipy
pip install --no-deps scipy pysnr

#python -m pydwf extract-examples
