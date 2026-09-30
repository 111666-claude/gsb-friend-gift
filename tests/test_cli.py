import io
import unittest
from contextlib import redirect_stdout

from gifts.cli import main


class CliSampleTest(unittest.TestCase):
    def run_sample(self, name):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            main(["--sample", name])
        return buffer.getvalue().strip()

    def test_limit_sample(self):
        self.assertEqual(self.run_sample("limit"), "fourth=false count=3")

    def test_dup_sample(self):
        self.assertEqual(self.run_sample("dup"), "second=false count=1")

    def test_expire_sample(self):
        self.assertEqual(self.run_sample("expire"), "returned=1 claimed=None")

    def test_scan_sample(self):
        scanned = int(self.run_sample("scan").split("=")[1])
        self.assertLessEqual(scanned, 3000)


if __name__ == "__main__":
    unittest.main()
