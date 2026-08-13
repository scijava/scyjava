"""
Test scyjava headless mode.
"""

from assertpy import assert_that

import scyjava

scyjava.config.enable_headless_mode()

assert_that(scyjava.jvm_started()).is_false()
scyjava.start_jvm()
assert_that(scyjava.is_jvm_headless()).is_true()

Frame = scyjava.jimport("java.awt.Frame")
assert_that(Frame).raises(Exception).when_called_with().is_equal_to(
    "java.awt.HeadlessException"
)
