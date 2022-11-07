import numpy as np

from scyjava import is_jarray, jarray, to_python
from scyjava.config import Mode, mode


class TestArrays(object):
    def test_non_primitive_jarray(self):
        pass

    def test_jarray1d_to_python(self):
        nums = [11, 6, 2, 15, 5]
        jints = jarray("i", len(nums))
        for i in range(len(nums)):
            jints[i] = nums[i]

        assert is_jarray(jints)
        assert len(nums) == len(jints)
        for i in range(len(nums)):
            assert nums[i] == jints[i]

        def assert_array_conversion_works(jarr, expected):
            pobj = to_python(jarr)

            if mode == Mode.JEP:
                assert isinstance(pobj, list)
                assert all(isinstance(v, int) for v in pobj)
                assert len(expected) == len(pobj)

            elif mode == Mode.JPYPE:
                assert isinstance(pobj, np.ndarray)
                assert np.int32 == pobj.dtype
                assert (len(expected),) == pobj.shape

            for i in range(len(expected)):
                assert expected[i] == pobj[i]

        assert_array_conversion_works(jints, nums)

        # mutate Java array element values
        deltas = [4, 100, 36, 133, 3]
        for i in range(len(deltas)):
            jints[i] = deltas[i]

        # convert to Python again and make sure it matches
        assert_array_conversion_works(jints, deltas)

    def test_jarray2d_to_python(self):
        nums = [
            [1.2, 3.4, 5.6],
            [7.8, 9.1, 2.3],
            [4.5, 6.7, 8.9],
            [0.2, 4.6, 8.0],
            [1.3, 5.7, 9.1],
        ]
        jdoubles = jarray("d", [len(nums), len(nums[0])])
        for i in range(len(nums)):
            for j in range(len(nums[i])):
                jdoubles[i][j] = nums[i][j]

        assert is_jarray(jdoubles)
        assert 5 == len(jdoubles)
        assert 3 == len(jdoubles[0])

        pdoubles = to_python(jdoubles)

        if mode == Mode.JEP:
            assert isinstance(pdoubles, list)
            assert all(isinstance(v, list) for v in pdoubles)
            assert len(nums) == len(pdoubles)

        elif mode == Mode.JPYPE:
            assert isinstance(pdoubles, np.ndarray)
            assert np.float64 == pdoubles.dtype
            assert (5, 3) == pdoubles.shape

        for i in range(len(nums)):
            for j in range(len(nums[i])):
                assert nums[i][j] == pdoubles[i][j]

    def test_jarray2d_to_python_updates(self):
        nums_init = [
            [1.2, 3.4, 5.6],
            [7.8, 9.1, 2.3],
            [4.5, 6.7, 8.9],
            [0.2, 4.6, 8.0],
            [1.3, 5.7, 9.1],
        ]
        nums_delta = [
            [15.3, 3.4, 5.6],
            [7.8, 9.1, 22.3],
            [90.5, 0.7, 8.9],
            [80.2, 3.6, 59.0],
            [1.5, 95.4, 9.1],
        ]
        jdoubles = jarray("d", [len(nums_init), len(nums_init[0])])
        for i in range(len(nums_init)):
            for j in range(len(nums_init[i])):
                jdoubles[i][j] = nums_init[i][j]

        # assert narr initial state
        pdoubles = to_python(jdoubles)
        if mode == Mode.JEP:
            assert isinstance(pdoubles, list)
            assert isinstance(pdoubles[0][0], float)
            assert len(pdoubles) == 5
            assert len(pdoubles[0]) == 3
        elif mode == Mode.JPYPE:
            assert isinstance(pdoubles, np.ndarray)
            assert np.float64 == pdoubles.dtype
            assert (5, 3) == pdoubles.shape
        for i in range(len(nums_init)):
            for j in range(len(nums_init[i])):
                assert nums_init[i][j] == pdoubles[i][j]

        # change jdoubles data state
        for i in range(len(nums_delta)):
            for j in range(len(nums_delta[i])):
                jdoubles[i][j] = nums_delta[i][j]

        # assert narr delta state
        pdoubles = to_python(jdoubles)
        if mode == Mode.JEP:
            assert isinstance(pdoubles, list)
            assert isinstance(pdoubles[0][0], float)
            assert len(pdoubles) == 5
            assert len(pdoubles[0]) == 3
        elif mode == Mode.JPYPE:
            assert isinstance(pdoubles, np.ndarray)
            assert np.float64 == pdoubles.dtype
            assert (5, 3) == pdoubles.shape
        for i in range(len(nums_delta)):
            for j in range(len(nums_delta[i])):
                assert nums_delta[i][j] == pdoubles[i][j]
