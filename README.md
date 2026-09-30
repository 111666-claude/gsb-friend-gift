# friend-gift

好友礼物：每日赠送上限、赠送幂等、领取幂等、超期未领取自动退回，只用 Python 标准库。

```
python3 -m gifts.cli --sample limit
python3 -m gifts.cli --sample dup
python3 -m gifts.cli --sample expire
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **每日上限**：同一发送者在同一服务日最多成功赠送 `daily_limit` 次，超出返回 `False`。
- **赠送幂等**：同一个 `gift_id` 重复赠送不生效（返回 `False`）且不占额度。
- **领取幂等**：同一份礼物只能领一次，第二次返回 `None`。
- **过期退回**：超过 `expire_ms` 未领取的礼物必须回收并退回（`expire` 返回退回数量），
  过期礼物不能再被领取。
- **查询代价**：`day_count` 不许每次全扫礼物表，`scanned_count()` 不随礼物数线性增长。
- **规模**：单服 200 万份礼物、每秒 10 万次赠送与查询，单次摊还 O(1)。

## 输出契约（不改格式）

```
fourth=false count=3
second=false count=1
returned=1 claimed=None
scanned<=3000
```

## 目录

```
gifts/core.py   赠送、领取与过期
gifts/cli.py    命令行入口
tests/          unittest 用例
```
