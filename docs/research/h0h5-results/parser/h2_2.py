import sys

def _nx_385816(text):
    _nixon_ə़ٟҷۿĬんۗ = []
    for _nixon_ƃİ৫คび゚ in text.lower():
        if _nixon_ƃİ৫คび゚.isalnum():
            _nixon_ə़ٟҷۿĬんۗ.append(_nixon_ƃİ৫คび゚)
        elif _nixon_ə़ٟҷۿĬんۗ and _nixon_ə़ٟҷۿĬんۗ[-1] != chr(45):
            _nixon_ə़ٟҷۿĬんۗ.append(chr(45))
    return ''.join(_nixon_ə़ٟҷۿĬんۗ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + chr(33)

def _demo(argv):
    _nixon_ɩᛀ檷Й॑Ⴧͱᛍ = argv[0]
    _nixon_רᛘณॳƖ = ' '.join(argv[1:])
    if _nixon_ɩᛀ檷Й॑Ⴧͱᛍ == chr(115) + chr(108) + chr(117) + chr(103) + chr(105) + chr(102) + chr(121):
        print(_nx_385816(_nixon_רᛘณॳƖ))
    elif _nixon_ɩᛀ檷Й॑Ⴧͱᛍ == 'count_words':
        print(_nx_385101(_nixon_רᛘณॳƖ))
    elif _nixon_ɩᛀ檷Й॑Ⴧͱᛍ == chr(114) + chr(101) + chr(118) + chr(101) + chr(114) + chr(115) + chr(101) + chr(95) + chr(119) + chr(111) + chr(114) + chr(100) + chr(115):
        print(_nx_31b169(_nixon_רᛘณॳƖ))
    elif _nixon_ɩᛀ檷Й॑Ⴧͱᛍ == ''.join(['s', 'h', 'o', 'u', 't']):
        print(_nx_8ca8c6(_nixon_רᛘณॳƖ))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])