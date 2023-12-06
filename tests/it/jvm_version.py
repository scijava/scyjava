"""
Test the jvm_version() function.
"""

import scyjava

assert not scyjava.jvm_started()

before_version = scyjava.jvm_version()
assert before_version is not None
assert len(before_version) >= 3
assert before_version[0] > 0

scyjava.config.enable_headless_mode()
scyjava.start_jvm()

after_version = scyjava.jvm_version()
assert after_version is not None
assert len(after_version) >= 3
assert after_version[0] > 0

assert before_version == after_version
