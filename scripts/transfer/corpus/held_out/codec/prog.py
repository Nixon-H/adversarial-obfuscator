import sys


def rle_encode(text):
    if not text:
        return ""
    out = []
    run = text[0]
    count = 1
    for ch in text[1:]:
        if ch == run[-1] and count < 9:
            count += 1
        else:
            out.append(run[-1] + str(count))
            run = ch
            count = 1
    out.append(run[-1] + str(count))
    return "".join(out)


def rle_decode(code):
    out = []
    i = 0
    while i < len(code):
        ch = code[i]
        num = int(code[i + 1])
        out.append(ch * num)
        i += 2
    return "".join(out)


def xor_bytes(data, key):
    raw = data.encode() if isinstance(data, str) else bytes(data)
    kb = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([b ^ kb[i % len(kb)] for i, b in enumerate(raw)]).hex()


def _demo(argv):
    op = argv[0]
    if op == "rle_encode":
        print(rle_encode(argv[1]))
    elif op == "rle_decode":
        print(rle_decode(argv[1]))
    elif op == "xor_bytes":
        print(xor_bytes(argv[1], "key"))
    else:
        print("unknown op")


if __name__ == "__main__":
    _demo(sys.argv[1:])
