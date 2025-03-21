"""
Test scyjava JVM memory-related functions.
"""

import scyjava

from assertpy import assert_that

mb_initial = 50  # initial MB of memory to snarf up
mb_tolerance = 10  # ceiling of expected MB in use

scyjava.config.set_heap_min(mb=mb_initial)
scyjava.config.set_heap_max(gb=1)

assert_that(scyjava.jvm_started()).is_false()

scyjava.start_jvm()

assert_that(scyjava.available_processors()).is_greater_than_or_equal_to(1)

mb_max = scyjava.memory_max() // 1024 // 1024
mb_total = scyjava.memory_total() // 1024 // 1024
mb_used = scyjava.memory_used() // 1024 // 1024

assert_that(
    mb_used, "Used memory should be less than the current memory total"
).is_less_than_or_equal_to(mb_total)
assert_that(
    mb_total, "current memory total should be less than maximum memory"
).is_less_than_or_equal_to(mb_max)
assert_that(mb_max, "maximum heap size should be approx. 1 GB").is_between(900, 1024)

assert_that(mb_used, "most memory should be available").is_less_than(mb_tolerance)
assert_that(mb_total, "total memory should be close to initial").is_close_to(
    mb_initial, tolerance=mb_tolerance
)
