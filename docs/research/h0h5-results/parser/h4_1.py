import sys

def _nx_385816(text):
    _nixon_尳אჄϬʋǱכϩ = []
    for _nixon_ざौᎪևत in text.lower():
        if _nixon_ざौᎪևत.isalnum():
            _nixon_尳אჄϬʋǱכϩ.append(_nixon_ざौᎪևत)
        elif _nixon_尳אჄϬʋǱכϩ and _nixon_尳אჄϬʋǱכϩ[-1] != '-':
            _nixon_尳אჄϬʋǱכϩ.append('-')
    return ''.join(_nixon_尳אჄϬʋǱכϩ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ᚴ堝ΣƝᛊႶყᚷף = argv[0]
    _nixon_ᏛტڸۋᏍϘוی = ' '.join(argv[1:])
    if _nixon_ᚴ堝ΣƝᛊႶყᚷף == 'slugify':
        print(_nx_385816(_nixon_ᏛტڸۋᏍϘוی))
    elif _nixon_ᚴ堝ΣƝᛊႶყᚷף == 'count_words':
        print(_nx_385101(_nixon_ᏛტڸۋᏍϘוی))
    elif _nixon_ᚴ堝ΣƝᛊႶყᚷף == 'reverse_words':
        print(_nx_31b169(_nixon_ᏛტڸۋᏍϘוی))
    elif _nixon_ᚴ堝ΣƝᛊႶყᚷף == 'shout':
        print(_nx_8ca8c6(_nixon_ᏛტڸۋᏍϘוی))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])