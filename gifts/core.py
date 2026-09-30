"""好友礼物：每日赠送上限、赠送幂等、领取幂等、超期未领取自动退回。

实现要点：
- 每日上限：按 (发送者, 服务日) 计数，当日成功赠送达到 daily_limit 后拒绝，
  被拒绝的赠送不占额度、不占用 gift_id。
- 赠送幂等：gift_id 成功赠送一次即永久登记，重复赠送返回 False 且不占额度。
- 领取幂等：礼物状态机 active -> claimed / returned，只有 active 能领取。
- 过期退回：按发送日分桶 + 小根堆索引，expire 整体回收到期日之前的桶，
  再逐条检查边界日桶；每份礼物至多回收一次，单次摊还 O(1)。
- 查询代价：day_count 是纯字典查询；scanned 只统计 expire 边界桶逐条
  检查的礼物数，不随礼物总量线性增长。
"""

import heapq

DAILY_LIMIT = 3
EXPIRE_MS = 86400000
DAY_MS = 86400000

ACTIVE = "active"
CLAIMED = "claimed"
RETURNED = "returned"


class Gifts:
    """礼物台账。"""

    def __init__(self, daily_limit=DAILY_LIMIT, expire_ms=EXPIRE_MS):
        self.daily_limit = daily_limit
        self.expire_ms = expire_ms
        self.gifts = {}        # gift_id -> [sender, receiver, item, sent_at_ms, status]
        self.daily = {}        # (sender, day_key) -> 成功赠送次数，只增不减
        self.by_day = {}       # day_key -> {未领取未退回的 gift_id, ...}
        self._day_heap = []    # 发送日小根堆，含惰性失效的重复项
        self.scanned = 0       # expire 边界桶逐条检查过的礼物数

    def send(self, gift_id, sender, receiver, item, now_ms):
        """赠送礼物：gift_id 重复或当日已达上限时返回 False。"""
        if gift_id in self.gifts:
            return False
        day_key = now_ms // DAY_MS
        key = (sender, day_key)
        if self.daily.get(key, 0) >= self.daily_limit:
            return False
        self.gifts[gift_id] = [sender, receiver, item, now_ms, ACTIVE]
        self.by_day.setdefault(day_key, set()).add(gift_id)
        heapq.heappush(self._day_heap, day_key)
        self.daily[key] = self.daily.get(key, 0) + 1
        return True

    def claim(self, gift_id, now_ms):
        """领取礼物：只有在架且未过期的礼物能领，每份礼物只能领一次。"""
        gift = self.gifts.get(gift_id)
        if gift is None or gift[4] != ACTIVE:
            return None
        if now_ms - gift[3] > self.expire_ms:
            return None
        gift[4] = CLAIMED
        day_key = gift[3] // DAY_MS
        bucket = self.by_day.get(day_key)
        if bucket is not None:
            bucket.discard(gift_id)
            if not bucket:
                del self.by_day[day_key]
        return gift[2]

    def expire(self, now_ms):
        """回收超过 expire_ms 未领取的礼物并退回，返回本次退回数量。"""
        threshold = now_ms - self.expire_ms
        threshold_day = threshold // DAY_MS
        returned = 0
        while self._day_heap and self._day_heap[0] < threshold_day:
            day_key = heapq.heappop(self._day_heap)
            bucket = self.by_day.pop(day_key, None)
            if bucket is None:
                continue
            for gift_id in bucket:
                self.gifts[gift_id][4] = RETURNED
                returned += 1
        bucket = self.by_day.get(threshold_day)
        if bucket:
            for gift_id in list(bucket):
                self.scanned += 1
                gift = self.gifts[gift_id]
                if gift[3] < threshold:
                    gift[4] = RETURNED
                    bucket.discard(gift_id)
                    returned += 1
            if not bucket:
                del self.by_day[threshold_day]
        return returned

    def day_count(self, sender, day_key):
        """某发送者当天的成功赠送次数：纯字典查询，不扫礼物表。"""
        return self.daily.get((sender, day_key), 0)

    def scanned_count(self):
        return self.scanned
