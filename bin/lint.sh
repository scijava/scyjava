#!/bin/sh

dir=$(dirname "$0")
cd "$dir/.."

exitCode=0
ruff check
code=$?; test $code -eq 0 || exitCode=$code
ruff format --check
code=$?; test $code -eq 0 || exitCode=$code
validate-pyproject pyproject.toml
code=$?; test $code -eq 0 || exitCode=$code
exit $exitCode
