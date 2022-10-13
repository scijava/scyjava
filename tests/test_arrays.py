import numpy as np
from jpype import JArray, JDouble, JInt

from scyjava import jarray, to_python


class TestArrays(object):
    def test_non_primitive_jarray(self):
        pass

    def test_jarray_to_ndarray_1d(self):
        nums = [11, 6, 2, 15, 5]
        jints = jarray("i", len(nums))
        for i in range(len(nums)):
            jints[i] = nums[i]

        assert isinstance(jints, JArray(JInt))
        assert len(nums) == len(jints)
        for i in range(len(nums)):
            assert nums[i] == jints[i]

        pints = to_python(jints)
        assert isinstance(pints, np.ndarray)
        assert np.int32 == pints.dtype
        assert (5,) == pints.shape
        for i in range(len(nums)):
            assert nums[i] == pints[i]

    def test_jarray_to_ndarray_2d(self):
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

        assert isinstance(jdoubles, JArray(JArray(JDouble)))
        assert 5 == len(jdoubles)
        assert 3 == len(jdoubles[0])

        pdoubles = to_python(jdoubles)
        assert isinstance(pdoubles, np.ndarray)
        assert np.float64 == pdoubles.dtype
        assert (5, 3) == pdoubles.shape
        for i in range(len(nums)):
            for j in range(len(nums[i])):
                assert nums[i][j] == pdoubles[i][j]
