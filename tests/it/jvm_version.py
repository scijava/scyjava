"""
Test the jvm_version() function.
"""

import scyjava

from assertpy import assert_that

assert_that(scyjava.jvm_started()).is_false()

before_version = scyjava.jvm_version()
assert_that(before_version).is_not_none()
assert_that(len(before_version)).is_greater_than_or_equal_to(3)
assert_that(before_version[0]).is_greater_than(0)

scyjava.config.enable_headless_mode()
scyjava.start_jvm()

after_version = scyjava.jvm_version()
assert_that(after_version).is_not_none()
assert_that(len(after_version)).is_greater_than_or_equal_to(3)
assert_that(after_version[0]).is_greater_than(0)

assert_that(before_version).is_equal_to(after_version)
