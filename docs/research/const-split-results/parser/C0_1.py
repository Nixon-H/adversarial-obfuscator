import sys

def _nx_385816(text):
    _nixon_凑ҡᏣōᛇʨৼ़高 = []
    for _nixon_ยƃ่ᛘ餅ĥ in text.lower():
        if _nixon_ยƃ่ᛘ餅ĥ.isalnum():
            _nixon_凑ҡᏣōᛇʨৼ़高.append(_nixon_ยƃ่ᛘ餅ĥ)
        elif _nixon_凑ҡᏣōᛇʨৼ़高 and _nixon_凑ҡᏣōᛇʨৼ़高[-1] != '-':
            _nixon_凑ҡᏣōᛇʨৼ़高.append('-')
    return ''.join(_nixon_凑ҡᏣōᛇʨৼ़高).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ي緓Ϧ訌Ꮐڠʫڔڐ = argv[0]
    _nixon_鋰嬈ʯঠתΕȤǅᏧ = ' '.join(argv[1:])
    if _nixon_ي緓Ϧ訌Ꮐڠʫڔڐ == 'slugify':
        print(_nx_385816(_nixon_鋰嬈ʯঠתΕȤǅᏧ))
    elif _nixon_ي緓Ϧ訌Ꮐڠʫڔڐ == 'count_words':
        print(_nx_385101(_nixon_鋰嬈ʯঠתΕȤǅᏧ))
    elif _nixon_ي緓Ϧ訌Ꮐڠʫڔڐ == 'reverse_words':
        print(_nx_31b169(_nixon_鋰嬈ʯঠתΕȤǅᏧ))
    elif _nixon_ي緓Ϧ訌Ꮐڠʫڔڐ == 'shout':
        print(_nx_8ca8c6(_nixon_鋰嬈ʯঠתΕȤǅᏧ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])