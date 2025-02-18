#!/bin/bash

set -o errexit
set -o nounset

python3 -m venv .
. bin/activate
pip install pydwf
pip install matplotlib
pip install scipy
pip install --no-deps scipy pysnr

#python -m pydwf extract-examples
