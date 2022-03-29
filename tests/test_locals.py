from typing import Any
from scyjava import get_local, set_local
from threading import Thread

def test_get_local():
    """Ensures that setting a local in one thread does not set it in another."""
    attr = 'foo'
    def assert_local(expected_val: Any, equality: bool) -> bool:
        try:
            actual = expected_val == get_local(attr)
        except AttributeError:
            actual = False
        assert actual == equality

    set_local(attr, 1)
    assert_local(1, True)
    t: Thread = Thread(target=assert_local, args=[1, False])
    t.start()
    t.join()

def test_set_local():
    """Ensures that setting a local in one thread does not set it in another."""
    attr = 'foo'
    def set_local_func(val: Any) -> None:
        set_local(attr, val)
    
    set_local(attr, 1)
    t: Thread = Thread(target=set_local_func, args=[2])
    t.start()
    t.join()

    assert get_local(attr) == 1
