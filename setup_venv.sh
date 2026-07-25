#!/bin/bash
# Creates (or rebuilds) this project's venv. Location-independent -- always
# operates on the directory this script actually lives in, so it survives
# being moved around (e.g. into ~/projects/).
set -e
cd "$(dirname "$0")"

rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev,dq]"
deactivate

echo "Done. Activate with: source $(pwd)/.venv/bin/activate"
