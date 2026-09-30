"""好友礼物：每日赠送上限、赠送幂等、领取幂等、超期未领取自动退回。

实现要点：
- 赠送按 gift_id 去重：重复赠送返回 False，且不占当日额度。
- 每日额度按 (发送者, 服务日) 计数，只增不减，达到 daily_limit 后拒绝。
- 礼物状态机 pending -> claimed / expired，均为终态，领取与过期互斥。
- 过期用最小堆按发送时间回收，每次只处理到期的礼物，摊还 O(1)，
  day_count 只查计数器，scanned 不随礼物总数线性增长。
"""

import heapq

DAILY_LIMIT = 3
EXPIRE_MS = 86400000
DAY_MS = 86400000

PENDING = "pending"
CLAIMED = "claimed"
EXPIRED = "expired"


class Gifts:
    """礼物台账。"""

    def __init__(self, daily_limit=DAILY_LIMIT, expire_ms=EXPIRE_MS):
        self.daily_limit = daily_limit
        self.expire_ms = expire_ms
        self.gifts = {}
        self.daily = {}
        self.pending = []
        self.scanned = 0

    def send(self, gift_id, sender, receiver, item, now_ms):
        """赠送礼物：同一 gift_id 只生效一次，同一发送者每个服务日最多 daily_limit 次。"""
        if gift_id in self.gifts:
            return False
        key = (sender, now_ms // DAY_MS)
        if self.daily.get(key, 0) >= self.daily_limit:
            return False
        self.daily[key] = self.daily.get(key, 0) + 1
        self.gifts[gift_id] = [sender, receiver, item, now_ms, PENDING]
        heapq.heappush(self.pending, (now_ms, gift_id))
        return True

    def claim(self, gift_id, now_ms):
        """领取礼物：只能领一次，过期礼物不能领（惰性回收）。"""
        gift = self.gifts.get(gift_id)
        if gift is None or gift[4] != PENDING:
            return None
        if now_ms - gift[3] > self.expire_ms:
            gift[4] = EXPIRED
            return None
        gift[4] = CLAIMED
        return gift[2]

    def expire(self, now_ms):
        """回收超期未领取的礼物，返回本次退回数量；只弹出到期礼物，不全扫。"""
        cutoff = now_ms - self.expire_ms
        returned = 0
        while self.pending and self.pending[0][0] < cutoff:
            _, gift_id = heapq.heappop(self.pending)
            self.scanned += 1
            gift = self.gifts[gift_id]
            if gift[4] != PENDING:
                continue
            gift[4] = EXPIRED
            returned += 1
        return returned

    def day_count(self, sender, day_key):
        """某发送者当天的赠送次数：O(1) 查计数器，不扫礼物表。"""
        self.scanned += 1
        return self.daily.get((sender, day_key), 0)

    def scanned_count(self):
        return self.scanned
