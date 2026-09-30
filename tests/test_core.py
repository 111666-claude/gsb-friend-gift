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
"""好友礼物（新增口径用例）。"""

from gifts.core import DAY_MS, Gifts


class DailyLimitTest(unittest.TestCase):
    def test_beyond_limit_returns_false(self):
        gifts = Gifts(daily_limit=3)
        results = [gifts.send("g-%d" % i, "a", "b", "gem", i) for i in range(4)]
        self.assertEqual(results, [True, True, True, False])
        self.assertEqual(gifts.day_count("a", 0), 3)

    def test_limit_is_per_day(self):
        gifts = Gifts(daily_limit=2)
        self.assertTrue(gifts.send("g-1", "a", "b", "gem", 0))
        self.assertTrue(gifts.send("g-2", "a", "b", "gem", 1))
        self.assertFalse(gifts.send("g-3", "a", "b", "gem", 2))
        self.assertTrue(gifts.send("g-4", "a", "b", "gem", DAY_MS))
        self.assertEqual(gifts.day_count("a", 0), 2)
        self.assertEqual(gifts.day_count("a", 1), 1)

    def test_limit_is_per_sender(self):
        gifts = Gifts(daily_limit=1)
        self.assertTrue(gifts.send("g-1", "a", "b", "gem", 0))
        self.assertTrue(gifts.send("g-2", "c", "b", "gem", 0))
        self.assertFalse(gifts.send("g-3", "a", "b", "gem", 1))


class SendIdempotentTest(unittest.TestCase):
    def test_duplicate_send_returns_false(self):
        gifts = Gifts()
        self.assertTrue(gifts.send("g-1", "a", "b", "gem", 0))
        self.assertFalse(gifts.send("g-1", "a", "b", "gem", 10))

    def test_duplicate_send_does_not_consume_quota(self):
        gifts = Gifts(daily_limit=2)
        self.assertTrue(gifts.send("g-1", "a", "b", "gem", 0))
        self.assertFalse(gifts.send("g-1", "a", "b", "gem", 1))
        self.assertFalse(gifts.send("g-1", "a", "b", "gem", 2))
        self.assertEqual(gifts.day_count("a", 0), 1)
        self.assertTrue(gifts.send("g-2", "a", "b", "gem", 3))
        self.assertEqual(gifts.day_count("a", 0), 2)
        self.assertFalse(gifts.send("g-3", "a", "b", "gem", 4))

    def test_duplicate_send_after_claim_or_expire(self):
        gifts = Gifts(expire_ms=100)
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.claim("g-1", 1), "gem")
        self.assertFalse(gifts.send("g-1", "a", "b", "gem", 2))
        gifts.send("g-2", "a", "b", "gem", 0)
        self.assertEqual(gifts.expire(101), 1)
        self.assertFalse(gifts.send("g-2", "a", "b", "gem", 101))


class ClaimIdempotentTest(unittest.TestCase):
    def test_second_claim_returns_none(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.claim("g-1", 1), "gem")
        self.assertIsNone(gifts.claim("g-1", 2))

    def test_claim_other_gift_still_works(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        gifts.send("g-2", "a", "b", "coin", 0)
        self.assertEqual(gifts.claim("g-1", 0), "gem")
        self.assertIsNone(gifts.claim("g-1", 0))
        self.assertEqual(gifts.claim("g-2", 0), "coin")


class ExpireTest(unittest.TestCase):
    def test_unclaimed_gift_returned(self):
        gifts = Gifts(expire_ms=100)
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.expire(101), 1)

    def test_expired_gift_cannot_be_claimed(self):
        gifts = Gifts(expire_ms=100)
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.expire(101), 1)
        self.assertIsNone(gifts.claim("g-1", 101))

    def test_claim_without_expire_call_lazy_reclaims(self):
        gifts = Gifts(expire_ms=100)
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertIsNone(gifts.claim("g-1", 101))
        self.assertEqual(gifts.expire(102), 0)

    def test_claimed_gift_is_not_returned(self):
        gifts = Gifts(expire_ms=100)
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.claim("g-1", 50), "gem")
        self.assertEqual(gifts.expire(101), 0)

    def test_expire_boundary_is_exclusive(self):
        gifts = Gifts(expire_ms=100)
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.expire(100), 0)
        self.assertEqual(gifts.claim("g-1", 100), "gem")

    def test_expire_is_idempotent_and_selective(self):
        gifts = Gifts(expire_ms=100)
        gifts.send("g-1", "a", "b", "gem", 0)
        gifts.send("g-2", "a", "b", "gem", 50)
        gifts.send("g-3", "a", "b", "gem", 100)
        self.assertEqual(gifts.expire(101), 1)
        self.assertEqual(gifts.expire(102), 0)
        self.assertEqual(gifts.expire(151), 1)
        self.assertEqual(gifts.claim("g-3", 151), "gem")

    def test_daily_count_never_decreases(self):
        gifts = Gifts(daily_limit=3, expire_ms=100)
        gifts.send("g-1", "a", "b", "gem", 0)
        gifts.send("g-2", "a", "b", "gem", 1)
        gifts.expire(101)
        self.assertEqual(gifts.day_count("a", 0), 2)


class ReplayTest(unittest.TestCase):
    def test_same_sequence_same_results(self):
        def run():
            gifts = Gifts(daily_limit=2, expire_ms=100)
            out = []
            out.append(gifts.send("g-1", "a", "b", "gem", 0))
            out.append(gifts.send("g-1", "a", "b", "gem", 1))
            out.append(gifts.claim("g-1", 50))
            out.append(gifts.claim("g-1", 60))
            out.append(gifts.send("g-2", "a", "b", "coin", 10))
            out.append(gifts.expire(200))
            out.append(gifts.claim("g-2", 201))
            out.append(gifts.day_count("a", 0))
            return out

        self.assertEqual(run(), run())


class ScanCostTest(unittest.TestCase):
    def test_day_count_does_not_scan_gift_table(self):
        gifts = Gifts(daily_limit=100000)
        for index in range(3000):
            gifts.send("g-%d" % index, "a", "b", "gem", index)
        before = gifts.scanned_count()
        for query in range(3000):
            gifts.day_count("a", query)
        self.assertLessEqual(gifts.scanned_count() - before, 3000)

    def test_expire_scans_only_due_gifts(self):
        gifts = Gifts(daily_limit=100000, expire_ms=100)
        for index in range(1000):
            gifts.send("g-%d" % index, "a", "b", "gem", index)
        self.assertEqual(gifts.expire(150), 50)
        self.assertEqual(gifts.scanned_count(), 50)
