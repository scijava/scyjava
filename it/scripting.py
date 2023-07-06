"""
Test the enable_python_scripting function, and subsequent use of
the SciJava Python script language (org.scijava:scripting-python).

As a side effect, this script also tests Maven dependency resolution.
"""

import sys

import scyjava

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
assert lang is not None and "Python" in lang.getNames()

# Construct a script.
script = """
#@ String name
#@ int age
#@output String statement
statement = f"Hello, {name}! In one year you will be {age + 1} years old."
"A wild return value appears!"
"""
StringReader = scyjava.jimport("java.io.StringReader")
ScriptInfo = scyjava.jimport("org.scijava.script.ScriptInfo")
info = ScriptInfo(ctx, "script.py", StringReader(script))
info.setLanguage(lang)

# Run the script.
future = ss.run(info, True, "name", "Chuckles", "age", 13)
try:
    module = future.get()
    outputs = module.getOutputs()
    statement = outputs["statement"]
    return_value = module.getReturnValue()
except Exception as e:
    sys.stderr.write("-- SCRIPT EXECUTION FAILED --\n")
    trace = scyjava.jstacktrace(e)
    if trace:
        sys.stderr.write(f"{trace}\n")
    raise e

assert statement == "Hello, Chuckles! In one year you will be 14 years old."
assert return_value == "A wild return value appears!"
