import scyjava


class TestJVM(object):
    """
    Tests scyjava JVM management functions.
    """

    def test_jvm_version(self):
        """
        Tests the jvm_version() function.
        """

        before_version = scyjava.jvm_version()
        assert before_version is not None
        assert len(before_version) >= 3
        assert before_version[0] > 0

        scyjava.config.add_option("-Djava.awt.headless=true")
        scyjava.start_jvm()

        after_version = scyjava.jvm_version()
        assert after_version is not None
        assert len(after_version) >= 3
        assert after_version[0] > 0

        assert before_version == after_version
