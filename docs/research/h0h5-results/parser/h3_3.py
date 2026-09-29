import sys

def _nx_385816(text):
    _nixon_ٟҋᚶজȔշ選էŁ = []
    for _nixon_քΛȠŇऊŬըƃ in text.lower():
        if _nixon_քΛȠŇऊŬըƃ.isalnum():
            _nixon_ٟҋᚶজȔշ選էŁ.append(_nixon_քΛȠŇऊŬըƃ)
        elif _nixon_ٟҋᚶজȔշ選էŁ and _nixon_ٟҋᚶজȔշ選էŁ[-1] != '-':
            _nixon_ٟҋᚶজȔշ選էŁ.append('-')
    return ''.join(_nixon_ٟҋᚶজȔշ選էŁ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_わ迮מႷѹهᎫनᛑČ = argv[0]
    _nixon_ᏭᚱᛒุĊ = ' '.join(argv[1:])
    if _nixon_わ迮מႷѹهᎫनᛑČ == 'slugify':
        print(_nx_385816(_nixon_ᏭᚱᛒุĊ))
    elif _nixon_わ迮מႷѹهᎫनᛑČ == 'count_words':
        print(_nx_385101(_nixon_ᏭᚱᛒุĊ))
    elif _nixon_わ迮מႷѹهᎫनᛑČ == 'reverse_words':
        print(_nx_31b169(_nixon_ᏭᚱᛒุĊ))
    elif _nixon_わ迮מႷѹهᎫनᛑČ == 'shout':
        print(_nx_8ca8c6(_nixon_ᏭᚱᛒุĊ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])