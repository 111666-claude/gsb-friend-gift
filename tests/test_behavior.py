import unittest

from gifts.core import DAY_MS, EXPIRE_MS, Gifts


class DailyLimitTest(unittest.TestCase):
    def test_fourth_send_same_day_rejected(self):
        gifts = Gifts(daily_limit=3)
        results = [gifts.send("g-%d" % i, "a", "b", "gem", i) for i in range(4)]
        self.assertEqual(results, [True, True, True, False])
        self.assertEqual(gifts.day_count("a", 0), 3)

    def test_limit_resets_next_day(self):
        gifts = Gifts(daily_limit=1)
        self.assertTrue(gifts.send("g-1", "a", "b", "gem", 0))
        self.assertFalse(gifts.send("g-2", "a", "b", "gem", 1))
        self.assertTrue(gifts.send("g-3", "a", "b", "gem", DAY_MS))
        self.assertEqual(gifts.day_count("a", 1), 1)

    def test_limit_is_per_sender(self):
        gifts = Gifts(daily_limit=1)
        self.assertTrue(gifts.send("g-1", "a", "b", "gem", 0))
        self.assertTrue(gifts.send("g-2", "c", "b", "gem", 0))

    def test_rejected_send_reserves_nothing(self):
        gifts = Gifts(daily_limit=1)
        self.assertTrue(gifts.send("g-1", "a", "b", "gem", 0))
        self.assertFalse(gifts.send("g-2", "a", "b", "gem", 1))
        self.assertTrue(gifts.send("g-2", "a", "b", "gem", DAY_MS))


class SendIdempotencyTest(unittest.TestCase):
    def test_duplicate_send_returns_false(self):
        gifts = Gifts()
        self.assertTrue(gifts.send("g-1", "a", "b", "gem", 0))
        self.assertFalse(gifts.send("g-1", "a", "b", "gem", 10))

    def test_duplicate_send_does_not_consume_quota(self):
        gifts = Gifts(daily_limit=2)
        gifts.send("g-1", "a", "b", "gem", 0)
        gifts.send("g-1", "a", "b", "gem", 1)
        self.assertTrue(gifts.send("g-2", "a", "b", "gem", 2))
        self.assertEqual(gifts.day_count("a", 0), 2)

    def test_resend_after_claim_still_rejected(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.claim("g-1", 1), "gem")
        self.assertFalse(gifts.send("g-1", "a", "b", "gem", 2))

    def test_resend_after_expire_still_rejected(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.expire(EXPIRE_MS + 1), 1)
        self.assertFalse(gifts.send("g-1", "a", "b", "gem", EXPIRE_MS + 2))


class ClaimIdempotencyTest(unittest.TestCase):
    def test_second_claim_returns_none(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.claim("g-1", 1), "gem")
        self.assertIsNone(gifts.claim("g-1", 2))

    def test_claimed_gift_not_returned_by_expire(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        gifts.claim("g-1", 1)
        self.assertEqual(gifts.expire(EXPIRE_MS + 1), 0)


class ExpireTest(unittest.TestCase):
    def test_unclaimed_gift_returned(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.expire(EXPIRE_MS + 1), 1)

    def test_expired_gift_cannot_be_claimed(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        gifts.expire(EXPIRE_MS + 1)
        self.assertIsNone(gifts.claim("g-1", EXPIRE_MS + 1))

    def test_overdue_gift_rejected_even_before_reclaim(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertIsNone(gifts.claim("g-1", EXPIRE_MS + 1))

    def test_fresh_gift_not_returned(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.expire(EXPIRE_MS), 0)
        self.assertEqual(gifts.claim("g-1", EXPIRE_MS), "gem")

    def test_expire_is_idempotent(self):
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        self.assertEqual(gifts.expire(EXPIRE_MS + 1), 1)
        self.assertEqual(gifts.expire(EXPIRE_MS + 2), 0)

    def test_expire_only_reclaims_old_gifts(self):
        gifts = Gifts()
        gifts.send("g-old", "a", "b", "gem", 0)
        gifts.send("g-new", "a", "b", "gem", EXPIRE_MS)
        self.assertEqual(gifts.expire(EXPIRE_MS + 1), 1)
        self.assertEqual(gifts.claim("g-new", EXPIRE_MS + 1), "gem")

    def test_day_count_not_decremented_by_expire(self):
        gifts = Gifts(daily_limit=3, expire_ms=10)
        for index in range(3):
            gifts.send("g-%d" % index, "a", "b", "gem", index)
        self.assertEqual(gifts.expire(11), 1)
        self.assertEqual(gifts.day_count("a", 0), 3)
        self.assertFalse(gifts.send("g-3", "a", "b", "gem", 12))


class ScaleTest(unittest.TestCase):
    def test_day_count_does_not_scan_gift_table(self):
        gifts = Gifts(daily_limit=100000)
        for index in range(3000):
            gifts.send("g-%d" % index, "a", "b", "gem", index)
        before = gifts.scanned_count()
        for query in range(3000):
            gifts.day_count("a", query)
        self.assertEqual(gifts.scanned_count(), before)

    def test_expire_scans_only_boundary_bucket(self):
        gifts = Gifts(daily_limit=1)
        for index in range(10000):
            gifts.send("g-%d" % index, "a", "b", "gem", index * DAY_MS)
        now_ms = 9998 * DAY_MS + EXPIRE_MS + 1
        self.assertEqual(gifts.expire(now_ms), 9999)
        self.assertLessEqual(gifts.scanned_count(), 1)
        self.assertEqual(gifts.claim("g-9999", now_ms), "gem")


if __name__ == "__main__":
    unittest.main()
