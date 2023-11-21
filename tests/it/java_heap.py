"""
Test scyjava JVM memory-related functions.
"""

import scyjava

mb_initial = 50  # initial MB of memory to snarf up

scyjava.config.set_heap_min(mb=mb_initial)
scyjava.config.set_heap_max(gb=1)

assert not scyjava.jvm_started()
scyjava.start_jvm()

assert scyjava.available_processors() >= 1

mb_max = scyjava.memory_max() // 1024 // 1024
mb_total = scyjava.memory_total() // 1024 // 1024
mb_used = scyjava.memory_used() // 1024 // 1024

# Used memory should be less than the current memory total,
# which should be less than the maximum heap size.
assert mb_used <= mb_total <= mb_max, f"{mb_used=} {mb_total=} {mb_max=}"

# The maximum heap size should be approximately 1 GB.
assert 900 <= mb_max <= 1024, f"{mb_max=}"

# Most of that memory should still be free; i.e.,
# we should not be using more than a few MB yet.
assert mb_used <= 5, f"{mb_used=}"

# The total MB available to Java at this moment
# should be close to our requested initial amount.
assert abs(mb_total - mb_initial) < 5, f"{mb_total=} {mb_initial=}"
