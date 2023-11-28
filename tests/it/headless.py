"""
Test scyjava headless mode.
"""

import scyjava

scyjava.config.enable_headless_mode()

assert not scyjava.jvm_started()
scyjava.start_jvm()

assert scyjava.is_jvm_headless()

Frame = scyjava.jimport("java.awt.Frame")
try:
    f = Frame()
    assert False, "HeadlessException should have occurred"
except Exception as e:
    assert "java.awt.HeadlessException" == str(e)
