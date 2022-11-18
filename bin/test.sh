#!/bin/sh

# Executes the pytest framework in both JPype and Jep modes.
#
# Usage examples:
#   bin/test.sh
#   bin/test.sh tests/test_basics.py
#   bin/test.sh tests/test_convert.py::TestConvert::test2DStringArray

set -e

dir=$(dirname "$0")
cd "$dir/.."

echo
echo "-------------------------------------------"
echo "| Testing JPype mode (Java inside Python) |"
echo "-------------------------------------------"

if [ $# -gt 0 ]
then
  python -m pytest -p no:faulthandler $@
else
  python -m pytest -p no:faulthandler tests/
fi

echo
echo "-------------------------------------------"
echo "|  Testing Jep mode (Python inside Java)  |"
echo "-------------------------------------------"

# Discern the Jep installation.
site_packages=$(python -c 'import sys; print(next(p for p in sys.path if p.endswith("site-packages")))')
test -d "$site_packages/jep" || {
  echo "[ERROR] Failed to detect Jep installation in current environment!" 1>&2
  exit 1
}

# We execute the pytest framework through Jep via jgo, so that
# the surrounding JVM includes scijava-table on the classpath.
#
# Arguments to the shell script are translated into an argument
# list to the pytest.main function. A weak attempt at handling
# special characters, e.g. single quotation marks and backslashes,
# is made, but there are surely other non-working cases.

if [ $# -gt 0 ]
then
  a=$(echo "$@" | sed 's/\\/\\\\/g')     # escape backslashes
  a=$(echo "$a" | sed 's/'\''/\\'\''/g') # escape single quotes
  a=$(echo "$a" | sed 's/ /'\'','\''/g') # replace space with ','
  argString="['-v', '$a']"
else
  argString=""
fi
echo "
import logging, sys, pytest, scyjava
scyjava._logger.addHandler(logging.StreamHandler(sys.stderr))
scyjava._logger.setLevel(logging.DEBUG)
scyjava.config.set_verbose(2)
result = pytest.main($argString)
if result:
  sys.exit(result)
" > jep_test.py
jgo -vv -Djava.library.path="$site_packages/jep" black.ninia:jep:jep.Run+org.scijava:scijava-table jep_test.py
rm -f jep_test.py
