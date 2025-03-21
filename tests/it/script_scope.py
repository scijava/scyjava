"""
Test the enable_python_scripting function, but here explictly testing import scope for declared functions.
"""

import sys

import scyjava

from assertpy import assert_that

scyjava.config.endpoints.extend(
    ["org.scijava:scijava-common:2.94.2", "org.scijava:scripting-python:MANAGED"]
)

# Create minimal SciJava context with a ScriptService.
Context = scyjava.jimport("org.scijava.Context")
ScriptService = scyjava.jimport("org.scijava.script.ScriptService")
# HACK: Avoid "[ERROR] Cannot create plugin" spam.
WidgetService = scyjava.jimport("org.scijava.widget.WidgetService")
ctx = Context(ScriptService, WidgetService)

# Enable the Python script language.
scyjava.enable_python_scripting(ctx)

# Assert that the Python script language is available.
ss = ctx.service("org.scijava.script.ScriptService")
lang = ss.getLanguageByName("Python")
assert_that(lang).is_not_none()
assert_that(lang.getNames()).contains("Python")

# Construct a script.
script = """
#@ int age
#@output String cbrt_age
import numpy as np

def calculate_cbrt(age):
    # check whether defined function can import module from global namespace
    if round(age ** (1. / 3)) == round(np.cbrt(age)):
        return round(age ** (1. /3))

cbrt_age = calculate_cbrt(age)
f"The rounded cube root of my age is {cbrt_age}"
"""
StringReader = scyjava.jimport("java.io.StringReader")
ScriptInfo = scyjava.jimport("org.scijava.script.ScriptInfo")
info = ScriptInfo(ctx, "script.py", StringReader(script))
info.setLanguage(lang)

# Run the script.
future = ss.run(info, True, "age", 13)
try:
    module = future.get()
    outputs = module.getOutputs()
    statement = outputs["cbrt_age"]
    return_value = module.getReturnValue()
except Exception as e:
    sys.stderr.write("-- SCRIPT EXECUTION FAILED --\n")
    trace = scyjava.jstacktrace(e)
    if trace:
        sys.stderr.write(f"{trace}\n")
    raise e

assert_that(statement).is_equal_to("2")
assert_that(return_value).is_equal_to("The rounded cube root of my age is 2")
