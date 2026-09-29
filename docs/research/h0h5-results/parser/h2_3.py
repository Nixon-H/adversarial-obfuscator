import sys

def _nx_385816(text):
    _nixon_瀁ᏳƩこדמȁ坒ศ = []
    for _nixon_ǂŉĽטनঀĒᛤʜお in text.lower():
        if _nixon_ǂŉĽטनঀĒᛤʜお.isalnum():
            _nixon_瀁ᏳƩこדמȁ坒ศ.append(_nixon_ǂŉĽטनঀĒᛤʜお)
        elif _nixon_瀁ᏳƩこדמȁ坒ศ and _nixon_瀁ᏳƩこדמȁ坒ศ[-1] != '-':
            _nixon_瀁ᏳƩこדמȁ坒ศ.append(chr(45))
    return ''.join(_nixon_瀁ᏳƩこדמȁ坒ศ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return chr(32).join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ᎱרᏢこϼেʍ朶 = argv[0]
    _nixon_ͶϯႰᎢτᎮИᎶ = ' '.join(argv[1:])
    if _nixon_ᎱרᏢこϼেʍ朶 == 'slugify':
        print(_nx_385816(_nixon_ͶϯႰᎢτᎮИᎶ))
    elif _nixon_ᎱרᏢこϼেʍ朶 == 'count_words':
        print(_nx_385101(_nixon_ͶϯႰᎢτᎮИᎶ))
    elif _nixon_ᎱרᏢこϼেʍ朶 == 'reverse_words':
        print(_nx_31b169(_nixon_ͶϯႰᎢτᎮИᎶ))
    elif _nixon_ᎱרᏢこϼেʍ朶 == 'shout':
        print(_nx_8ca8c6(_nixon_ͶϯႰᎢτᎮИᎶ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])