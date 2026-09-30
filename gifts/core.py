"""好友礼物：每日赠送上限、赠送幂等、领取幂等、超期未领取自动退回。

缺陷：重复赠送重复生效、不看每日上限、过期礼物不退回、每次查询全扫礼物表。
"""

DAILY_LIMIT = 3
EXPIRE_MS = 86400000
DAY_MS = 86400000


class Gifts:
    """礼物台账。"""

    def __init__(self, daily_limit=DAILY_LIMIT, expire_ms=EXPIRE_MS):
        self.daily_limit = daily_limit
        self.expire_ms = expire_ms
        self.gifts = {}
        self.daily = {}
        self.scanned = 0

    def send(self, gift_id, sender, receiver, item, now_ms):
        """赠送礼物。缺陷：不去重、不查每日上限。"""
        self.gifts[gift_id] = [sender, receiver, item, now_ms, False]
        key = (sender, now_ms // DAY_MS)
        self.daily[key] = self.daily.get(key, 0) + 1
        return True

    def claim(self, gift_id, now_ms):
        """领取礼物。缺陷：重复领取重复给、过期礼物照样能领。"""
        gift = self.gifts.get(gift_id)
        if gift is None:
            return None
        gift[4] = True
        return gift[2]

    def expire(self, now_ms):
        """回收超期未领取的礼物。缺陷：什么都不做，礼物也不退回。"""
        self.scanned += len(self.gifts)
        return 0

    def day_count(self, sender, day_key):
        """某发送者当天的赠送次数。缺陷：每次全扫礼物表。"""
        self.scanned += len(self.gifts)
        return self.daily.get((sender, day_key), 0)

    def scanned_count(self):
        return self.scanned
