 #!/bin/sh

# Executes the pytest framework through JEP via jgo, so that
# the surrounding JVM includes scijava-table on the classpath.
#
# Arguments to this shell script are translated into an argument
# list to the pytest.main function. A weak attempt at handling
# special characters, e.g. single quotation marks and backslashes,
# is made, but there are surely other non-working cases.
#
# Usage examples:
#   bin/jep-test.sh
#   bin/jep-test.sh tests/test_basics.py
#   bin/jep-test.sh tests/test_convert.py::TestConvert::test2DStringArray

if [ $# -gt 0 ]
then
  a=$(echo "$@" | sed 's/\\/\\\\/g')     # escape backslashes
  a=$(echo "$a" | sed 's/'\''/\\'\''/g') # escape single quotes
  a=$(echo "$a" | sed 's/ /'\'','\''/g') # replace space with ','
  argString="['$a']"
else
  argString=""
fi
echo "import pytest; import sys; pytest.main($argString)" > jep_test.py
jgo -Djava.library.path="$CONDA_PREFIX/lib/python3.10/site-packages/jep" black.ninia:jep:jep.Run+org.scijava:scijava-table jep_test.py
rm jep_test.py
