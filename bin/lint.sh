#!/bin/sh

dir=$(dirname "$0")
cd "$dir/.."

black src tests
python -m flake8 src tests
