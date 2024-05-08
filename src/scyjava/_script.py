"""
Logic for making Python available to Java as a SciJava scripting language.

For the Java side of this functionality, see
https://github.com/scijava/scripting-python.
"""

import ast
import sys
import threading
import traceback
from contextlib import redirect_stdout

from jpype import JImplements, JOverride

from scyjava._convert import to_java
from scyjava._jvm import jimport


def enable_python_scripting(context):
    """
    Adds a Python script runner object to the ObjectService of the given
    SciJava context. Intended for use in conjunction with
    'org.scijava:scripting-python'.

    :param context: The org.scijava.Context containing the ObjectService
        where the PythonScriptRunner should be injected.
    """
    ObjectService = jimport("org.scijava.object.ObjectService")

    class ScriptContextWriter:
        def __init__(self, std):
            self._std_default = std
            self._thread_to_context = {}

        def addScriptContext(self, thread, scriptContext):
            self._thread_to_context[thread] = scriptContext

        def removeScriptContext(self, thread):
            if thread in self._thread_to_context:
                del self._thread_to_context[thread]

        def flush(self):
            self._writer().flush()

        def write(self, s):
            self._writer().write(s)

        def _writer(self):
            ctx = self._thread_to_context.get(threading.currentThread())
            return self._std_default if ctx is None else ctx.getWriter()

    stdoutContextWriter = ScriptContextWriter(sys.stdout)

    @JImplements("java.util.function.Supplier")
    class PythonObjectSupplier:
        def __init__(self, obj):
            self.obj = obj

        @JOverride
        def get(self):
            return self.obj

    @JImplements("java.util.function.Function")
    class PythonScriptRunner:
        @JOverride
        def apply(self, arg):
            # Copy script bindings/vars into script locals.
            script_locals = {}
            for key in arg.vars.keys():
                script_locals[key] = arg.vars[key]

            stdoutContextWriter.addScriptContext(
                threading.currentThread(), arg.scriptContext
            )

            return_value = None
            with redirect_stdout(stdoutContextWriter):
                try:
                    # NB: Execute the block, except for the last statement,
                    # which we evaluate instead to get its return value.
                    # Credit: https://stackoverflow.com/a/39381428/1207769

                    block = ast.parse(str(arg.script), mode="exec")
                    last = None
                    if (
                        len(block.body) > 0
                        and hasattr(block.body[-1], "value")
                        and not isinstance(block.body[-1], ast.Assign)
                    ):
                        # Last statement looks like an expression. Evaluate!
                        last = ast.Expression(block.body.pop().value)

                    _globals = {}
                    exec(
                        compile(block, "<string>", mode="exec"), _globals, script_locals
                    )
                    if last is not None:
                        return_value = eval(
                            compile(last, "<string>", mode="eval"),
                            _globals,
                            script_locals,
                        )
                except Exception:
                    error_writer = arg.scriptContext.getErrorWriter()
                    if error_writer is not None:
                        error_writer.write(to_java(traceback.format_exc()))

            stdoutContextWriter.removeScriptContext(threading.currentThread())

            # Copy script locals back into script bindings/vars.
            for key in script_locals.keys():
                try:
                    arg.vars[key] = to_java(script_locals[key])
                except Exception:
                    arg.vars[key] = PythonObjectSupplier(script_locals[key])
                    # error_writer = arg.scriptContext.getErrorWriter()
                    # if error_writer is not None:
                    #    error_writer.write(to_java(traceback.format_exc()))

            return to_java(return_value)

    objectService = context.service(ObjectService)
    objectService.addObject(PythonScriptRunner(), "PythonScriptRunner")
