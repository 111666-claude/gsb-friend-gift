"""命令行入口：跑好友礼物样例。"""

import argparse

from .core import EXPIRE_MS, Gifts


def build_parser():
    parser = argparse.ArgumentParser(prog="friend-gift", description="好友礼物")
    parser.add_argument("--sample", default="limit", help="limit / dup / expire / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "limit":
        gifts = Gifts(daily_limit=3)
        results = []
        for index in range(4):
            results.append(gifts.send("g-%d" % index, "a", "b", "gem", index))
        print("fourth=%s count=%d" % (str(results[3]).lower(), gifts.day_count("a", 0)))
    elif args.sample == "dup":
        gifts = Gifts(daily_limit=3)
        first = gifts.send("g-1", "a", "b", "gem", 0)
        second = gifts.send("g-1", "a", "b", "gem", 10)
        print("second=%s count=%d" % (str(second).lower(), gifts.day_count("a", 0)))
    elif args.sample == "expire":
        gifts = Gifts()
        gifts.send("g-1", "a", "b", "gem", 0)
        returned = gifts.expire(EXPIRE_MS + 1)
        claimed = gifts.claim("g-1", EXPIRE_MS + 1)
        print("returned=%d claimed=%s" % (returned, claimed))
    elif args.sample == "scan":
        gifts = Gifts(daily_limit=100000)
        for index in range(3000):
            gifts.send("g-%d" % index, "a", "b", "gem", index)
        for query in range(3000):
            gifts.day_count("a", query)
        print("scanned=%d" % gifts.scanned_count())
    else:
        raise SystemExit("需要 --sample limit|dup|expire|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
