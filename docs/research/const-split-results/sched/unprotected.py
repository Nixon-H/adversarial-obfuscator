import sys


def priority_pick(tasks):
    best = None
    for name, prio in tasks:
        if best is None or prio > best[1]:
            best = (name, prio)
    return best[0] if best else ""


def slot_hash(key, slots):
    total = 0
    for ch in key:
        total = (total * 31 + ord(ch)) % 1000003
    return total % slots


def rotate_list(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]


def _demo(argv):
    op = argv[0]
    if op == "priority_pick":
        print(priority_pick([("a", 1), ("b", 5), ("c", 3)]))
    elif op == "slot_hash":
        print(slot_hash(argv[1], int(argv[2])))
    elif op == "rotate_list":
        print(",".join(rotate_list(argv[1].split(","), int(argv[2]))))
    else:
        print("unknown op")


if __name__ == "__main__":
    _demo(sys.argv[1:])
