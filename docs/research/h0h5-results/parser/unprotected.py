import sys


def slugify(text):
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")


def count_words(text):
    return len(text.split())


def reverse_words(text):
    return " ".join(text.split()[::-1])


def shout(text):
    return text.upper() + "!"


def _demo(argv):
    op = argv[0]
    rest = " ".join(argv[1:])
    if op == "slugify":
        print(slugify(rest))
    elif op == "count_words":
        print(count_words(rest))
    elif op == "reverse_words":
        print(reverse_words(rest))
    elif op == "shout":
        print(shout(rest))
    else:
        print("unknown op")


if __name__ == "__main__":
    _demo(sys.argv[1:])
