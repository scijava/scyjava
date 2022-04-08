import scyjava
import unittest


class TestJVM(unittest.TestCase):
    """
    Tests scyjava JVM management functions.
    """

    def test_jvm_version(self):
        """
        Tests the jvm_version() function.
        """

        before_version = scyjava.jvm_version()
        self.assertTrue(before_version is not None)
        self.assertTrue(len(before_version) >= 3)
        self.assertTrue(before_version[0] > 0)

        scyjava.config.add_option("-Djava.awt.headless=true")
        scyjava.start_jvm()

        after_version = scyjava.jvm_version()
        self.assertTrue(after_version is not None)
        self.assertTrue(len(after_version) >= 3)
        self.assertTrue(after_version[0] > 0)

        self.assertEqual(before_version, after_version)


if __name__ == "__main__":
    unittest.main()
