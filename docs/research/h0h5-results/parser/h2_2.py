import sys

def _nx_385816(text):
    _nixon_স۲۰อǒะӘɲ = []
    for _nixon_竃ᏓǱᎶנჺקעᚴӜ in text.lower():
        if _nixon_竃ᏓǱᎶנჺקעᚴӜ.isalnum():
            _nixon_স۲۰อǒะӘɲ.append(_nixon_竃ᏓǱᎶנჺקעᚴӜ)
        elif _nixon_স۲۰อǒะӘɲ and _nixon_স۲۰อǒะӘɲ[-1] != ''.join(['-']):
            _nixon_স۲۰อǒะӘɲ.append('-')
    return ''.join(_nixon_স۲۰อǒะӘɲ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return chr(32).join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + ''.join(['!'])

def _demo(argv):
    _nixon_ϷוᎣƈछ嬪Ŷ鄂ড়Ȝ = argv[0]
    _nixon_ᏙँոӹӑΣᚮόჭ譞 = ' '.join(argv[1:])
    if _nixon_ϷוᎣƈछ嬪Ŷ鄂ড়Ȝ == chr(115) + chr(108) + chr(117) + chr(103) + chr(105) + chr(102) + chr(121):
        print(_nx_385816(_nixon_ᏙँոӹӑΣᚮόჭ譞))
    elif _nixon_ϷוᎣƈछ嬪Ŷ鄂ড়Ȝ == 'count_words':
        print(_nx_385101(_nixon_ᏙँոӹӑΣᚮόჭ譞))
    elif _nixon_ϷוᎣƈछ嬪Ŷ鄂ড়Ȝ == 'reverse_words':
        print(_nx_31b169(_nixon_ᏙँոӹӑΣᚮόჭ譞))
    elif _nixon_ϷוᎣƈछ嬪Ŷ鄂ড়Ȝ == 'shout':
        print(_nx_8ca8c6(_nixon_ᏙँոӹӑΣᚮόჭ譞))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])