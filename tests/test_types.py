from scyjava import numeric_bounds, to_java


class TestTypes(object):
    """
    Test Java-type-related functions.
    """

    def test_numeric_bounds(self):
        v_byte = to_java(1, type="byte")
        v_short = to_java(2, type="short")
        v_int = to_java(3, type="int")
        v_long = to_java(4, type="long")
        v_bigint = to_java(5, type="bigint")
        v_float = to_java(6.7, type="float")
        v_double = to_java(7.8, type="double")
        v_bigdec = to_java(8.9, type="bigdec")

        assert (-128, 127) == numeric_bounds(type(v_byte))
        assert (-32768, 32767) == numeric_bounds(type(v_short))
        assert (-2147483648, 2147483647) == numeric_bounds(type(v_int))
        assert (-9223372036854775808, 9223372036854775807) == numeric_bounds(
            type(v_long)
        )
        assert (None, None) == numeric_bounds(type(v_bigint))
        assert (-3.4028234663852886e38, 3.4028234663852886e38) == numeric_bounds(
            type(v_float)
        )
        assert (-1.7976931348623157e308, 1.7976931348623157e308) == numeric_bounds(
            type(v_double)
        )
        assert (None, None) == numeric_bounds(type(v_bigdec))
