"""对照自证：随机「赠送 + 重发 + 领取 + 过期」序列与参考实现逐步比对。"""

import random
import unittest

from gifts.core import DAY_MS, Gifts


class RefGifts:
    """参考实现：每日上限 + 双向幂等 + 过期退回，全表扫描，逻辑直白。"""

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
        self.gifts[gift_id] = [sender, receiver, item, now_ms, "active"]
        self.daily[key] = self.daily.get(key, 0) + 1
        return True

    def claim(self, gift_id, now_ms):
        gift = self.gifts.get(gift_id)
        if gift is None or gift[4] != "active":
            return None
        if now_ms - gift[3] > self.expire_ms:
            return None
        gift[4] = "claimed"
        return gift[2]

    def expire(self, now_ms):
        returned = 0
        for gift in self.gifts.values():
            if gift[4] == "active" and now_ms - gift[3] > self.expire_ms:
                gift[4] = "returned"
                returned += 1
        return returned

    def day_count(self, sender, day_key):
        return self.daily.get((sender, day_key), 0)


def random_sequence(rng):
    daily_limit = rng.randint(1, 4)
    expire_ms = rng.choice([50, 200, 1000, DAY_MS])
    horizon = 3 * expire_ms + 10
    senders = ["s-%d" % index for index in range(3)]
    known_ids = []
    ops = []
    for _ in range(rng.randint(30, 80)):
        now_ms = rng.randrange(0, horizon)
        roll = rng.random()
        if roll < 0.35:
            gift_id = "g-%d" % rng.randrange(0, 12)
            known_ids.append(gift_id)
            ops.append(("send", gift_id, rng.choice(senders), "r-0",
                        rng.choice(["gem", "coin"]), now_ms))
        elif roll < 0.55 and known_ids:
            ops.append(("send", rng.choice(known_ids), rng.choice(senders),
                        "r-0", "gem", now_ms))
        elif roll < 0.75:
            if known_ids and rng.random() < 0.8:
                gift_id = rng.choice(known_ids)
            else:
                gift_id = "g-missing"
            ops.append(("claim", gift_id, now_ms))
        elif roll < 0.9:
            ops.append(("expire", now_ms))
        else:
            ops.append(("day_count", rng.choice(senders),
                        rng.randrange(0, horizon // DAY_MS + 1)))
    return daily_limit, expire_ms, ops


def run_ops(model, ops):
    results = []
    for op in ops:
        if op[0] == "send":
            results.append(model.send(op[1], op[2], op[3], op[4], op[5]))
        elif op[0] == "claim":
            results.append(model.claim(op[1], op[2]))
        elif op[0] == "expire":
            results.append(model.expire(op[1]))
        else:
            results.append(model.day_count(op[1], op[2]))
    return results


class ReferenceMatchTest(unittest.TestCase):
    def test_matches_reference_on_random_sequences(self):
        rng = random.Random(20261001)
        for trial in range(200):
            daily_limit, expire_ms, ops = random_sequence(rng)
            expected = run_ops(RefGifts(daily_limit, expire_ms), ops)
            actual = run_ops(Gifts(daily_limit=daily_limit, expire_ms=expire_ms), ops)
            replay = run_ops(Gifts(daily_limit=daily_limit, expire_ms=expire_ms), ops)
            self.assertEqual(actual, expected, "trial %d 与参考实现不一致" % trial)
            self.assertEqual(replay, actual, "trial %d 重放结果不一致" % trial)


if __name__ == "__main__":
    unittest.main()
