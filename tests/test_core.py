import unittest

from gifts.core import Gifts


class SendTest(unittest.TestCase):
    def test_send_returns_true(self):
        self.assertTrue(Gifts().send("g-1", "a", "b", "gem", 0))

    def test_send_counts_today(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.day_count("a", 0), 1)


class ClaimTest(unittest.TestCase):
    def test_claim_returns_item(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.claim("g-1", 0), "gem")

    def test_claim_missing_returns_none(self):
        self.assertIsNone(Gifts().claim("missing", 0))


if __name__ == "__main__":
    unittest.main()
