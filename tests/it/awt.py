"""
Test scyjava AWT-related functions.
"""

import platform
import sys

import scyjava

if platform.system() == "Darwin":
    # NB: This test would hang on macOS, due to AWT threading issues.
    sys.exit(0)

assert not scyjava.jvm_started()
scyjava.start_jvm()

if scyjava.is_jvm_headless():
    # NB: We did not configure the JVM to run in headless mode.
    # But it is still headless, which indicates we are running
    # on a headless system, such as continuous integration (CI).
    # In that case, we are not able to perform this test.
    sys.exit(0)

assert not scyjava.is_awt_initialized()

Frame = scyjava.jimport("java.awt.Frame")
f = Frame()

assert scyjava.is_awt_initialized()
