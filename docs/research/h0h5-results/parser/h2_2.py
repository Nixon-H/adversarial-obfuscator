import sys

def _nx_385816(text):
    _nixon_堯েכԹЫ禠ʧ = []
    for _nixon_ϧɨᏖᛣᚻِ in text.lower():
        if _nixon_ϧɨᏖᛣᚻِ.isalnum():
            _nixon_堯েכԹЫ禠ʧ.append(_nixon_ϧɨᏖᛣᚻِ)
        elif _nixon_堯েכԹЫ禠ʧ and _nixon_堯েכԹЫ禠ʧ[-1] != chr(45):
            _nixon_堯েכԹЫ禠ʧ.append('-')
    return ''.join(_nixon_堯েכԹЫ禠ʧ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ႹڙᎫ۴Օךɱ = argv[0]
    _nixon_ᎪךڟיᏔƐ = ' '.join(argv[1:])
    if _nixon_ႹڙᎫ۴Օךɱ == ''.join(['s', 'l', 'u', 'g', 'i', 'f', 'y']):
        print(_nx_385816(_nixon_ᎪךڟיᏔƐ))
    elif _nixon_ႹڙᎫ۴Օךɱ == chr(99) + chr(111) + chr(117) + chr(110) + chr(116) + chr(95) + chr(119) + chr(111) + chr(114) + chr(100) + chr(115):
        print(_nx_385101(_nixon_ᎪךڟיᏔƐ))
    elif _nixon_ႹڙᎫ۴Օךɱ == ''.join(['r', 'e', 'v', 'e', 'r', 's', 'e', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_31b169(_nixon_ᎪךڟיᏔƐ))
    elif _nixon_ႹڙᎫ۴Օךɱ == 'shout':
        print(_nx_8ca8c6(_nixon_ᎪךڟיᏔƐ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])