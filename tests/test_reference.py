"""对照自证：随机 200 组「赠送 + 重发 + 领取 + 过期」序列与参考实现逐步比对。

参考实现只追求口径正确（每日上限 + 双向幂等 + 过期退回），不追求性能；
逐步比较 send / claim / expire 的每次返回值，以及各发送者各服务日的
当天次数，任何差异立即报错。
"""

import random
import unittest

from gifts.core import DAY_MS, Gifts


class ReferenceGifts:
    """正确优先的参考实现：全表扫描、逐条判定。"""

    def __init__(self, daily_limit, expire_ms):
        self.daily_limit = daily_limit
        self.expire_ms = expire_ms
        self.gifts = {}
        self.daily = {}

    def send(self, gift_id, sender, receiver, item, now_ms):
        if gift_id in self.gifts:
            return False
        key = (sender, now_ms // DAY_MS)
        if self.daily.get(key, 0) >= self.daily_limit:
            return False
        self.daily[key] = self.daily.get(key, 0) + 1
        self.gifts[gift_id] = [sender, item, now_ms, "pending"]
        return True

    def claim(self, gift_id, now_ms):
        gift = self.gifts.get(gift_id)
        if gift is None or gift[3] != "pending":
            return None
        if now_ms - gift[2] > self.expire_ms:
            gift[3] = "expired"
            return None
        gift[3] = "claimed"
        return gift[1]

    def expire(self, now_ms):
        returned = 0
        for gift in self.gifts.values():
            if gift[3] == "pending" and now_ms - gift[2] > self.expire_ms:
                gift[3] = "expired"
                returned += 1
        return returned

    def day_count(self, sender, day_key):
        return self.daily.get((sender, day_key), 0)


def play(seed):
    """对同一组随机序列执行两套实现，返回 (不匹配描述, 最终当天次数比对)。"""
    rng = random.Random(seed)
    daily_limit = rng.randint(1, 4)
    expire_ms = rng.choice([50, 500, DAY_MS])
    actual = Gifts(daily_limit=daily_limit, expire_ms=expire_ms)
    reference = ReferenceGifts(daily_limit=daily_limit, expire_ms=expire_ms)

    gift_ids = ["g-%d" % index for index in range(8)]
    senders = ["alice", "bob"]
    seen_ids = []
    now = 0
    days = {0}
    steps = rng.randint(10, 40)

    for step in range(steps):
        now += rng.choice([0, 1, 7, 60, 600, DAY_MS])
        days.add(now // DAY_MS)
        op = rng.choice(["send", "send", "resend", "claim", "expire"])

        if op in ("send", "resend") and (op == "send" or seen_ids):
            gift_id = rng.choice(gift_ids) if op == "send" else rng.choice(seen_ids)
            if gift_id not in seen_ids:
                seen_ids.append(gift_id)
            sender = rng.choice(senders)
            item = rng.choice(["gem", "coin"])
            got = actual.send(gift_id, sender, "carol", item, now)
            want = reference.send(gift_id, sender, "carol", item, now)
            if got != want:
                return "send mismatch at trial=%s step=%d: %r != %r" % (seed, step, got, want)
        elif op == "claim":
            gift_id = rng.choice(gift_ids)
            got = actual.claim(gift_id, now)
            want = reference.claim(gift_id, now)
            if got != want:
                return "claim mismatch at trial=%s step=%d: %r != %r" % (seed, step, got, want)
        else:
            got = actual.expire(now)
            want = reference.expire(now)
            if got != want:
                return "expire mismatch at trial=%s step=%d: %r != %r" % (seed, step, got, want)

        for sender in senders:
            for day in days:
                got = actual.day_count(sender, day)
                want = reference.day_count(sender, day)
                if got != want:
                    return "day_count mismatch at trial=%s step=%d (%s,%s): %r != %r" % (
                        seed, step, sender, day, got, want)

    return None


class ReferenceMatchTest(unittest.TestCase):
    def test_200_random_sequences_match_reference(self):
        mismatches = []
        for seed in range(200):
            mismatch = play(seed)
            if mismatch is not None:
                mismatches.append(mismatch)
        self.assertEqual(mismatches, [], "参考实现差异: %s" % mismatches[:5])


if __name__ == "__main__":
    unittest.main()
