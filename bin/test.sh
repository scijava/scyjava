#!/bin/sh

# Runs the unit tests.
#
# Usage examples:
#   bin/test.sh
#   bin/test.sh tests/test_basics.py
#   bin/test.sh tests/test_convert.py::TestConvert::test2DStringArray

set -e

dir=$(dirname "$0")
cd "$dir/.."

echo
echo "----------------------"
echo "| Running unit tests |"
echo "----------------------"

if [ $# -gt 0 ]
then
  uv run python -m pytest -v -p no:faulthandler $@
else
  uv run python -m pytest -v -p no:faulthandler tests/
fi
jpypeCode=$?

echo
echo "-----------------------------"
echo "| Running integration tests |"
echo "-----------------------------"
itCode=0
for t in tests/it/*.py
do
  uv run python "$t"
  code=$?
  printf -- "--> %s " "$t"
  if [ "$code" -eq 0 ]
  then
    echo "[OK]"
  else
    echo "[FAILED]"
    itCode=$code
  fi
done

test "$jpypeCode" -ne 0 && exit "$jpypeCode"
test "$itCode" -ne 0 && exit "$itCode"
exit 0
