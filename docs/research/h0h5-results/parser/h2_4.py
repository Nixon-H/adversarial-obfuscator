import sys

def _nx_385816(text):
    _nixon_むӹᏤօђৄॳǫᛇפ = []
    for _nixon_ঢ়ʚیבЈԹᏨく५ in text.lower():
        if _nixon_ঢ়ʚیבЈԹᏨく५.isalnum():
            _nixon_むӹᏤօђৄॳǫᛇפ.append(_nixon_ঢ়ʚیבЈԹᏨく५)
        elif _nixon_むӹᏤօђৄॳǫᛇפ and _nixon_むӹᏤօђৄॳǫᛇפ[-1] != '-':
            _nixon_むӹᏤօђৄॳǫᛇפ.append('-')
    return ''.join(_nixon_むӹᏤօђৄॳǫᛇפ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ''.join([' ']).join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + chr(33)

def _demo(argv):
    _nixon_ゎ荹うəعᏈן瀻 = argv[0]
    _nixon_Вَ蠠ჭႸڱᎴʏע = ' '.join(argv[1:])
    if _nixon_ゎ荹うəعᏈן瀻 == chr(115) + chr(108) + chr(117) + chr(103) + chr(105) + chr(102) + chr(121):
        print(_nx_385816(_nixon_Вَ蠠ჭႸڱᎴʏע))
    elif _nixon_ゎ荹うəعᏈן瀻 == ''.join(['c', 'o', 'u', 'n', 't', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_385101(_nixon_Вَ蠠ჭႸڱᎴʏע))
    elif _nixon_ゎ荹うəعᏈן瀻 == 'reverse_words':
        print(_nx_31b169(_nixon_Вَ蠠ჭႸڱᎴʏע))
    elif _nixon_ゎ荹うəعᏈן瀻 == 'shout':
        print(_nx_8ca8c6(_nixon_Вَ蠠ჭႸڱᎴʏע))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])