import sys

def _nx_385816(text):
    _nixon_ᚶĿפᎶךЂগᎲ分օ = []
    for _nixon_र憌ฯӍᚧগざ in text.lower():
        if _nixon_र憌ฯӍᚧগざ.isalnum():
            _nixon_ᚶĿפᎶךЂগᎲ分օ.append(_nixon_र憌ฯӍᚧগざ)
        elif _nixon_ᚶĿפᎶךЂগᎲ分օ and _nixon_ᚶĿפᎶךЂগᎲ分օ[-1] != '-':
            _nixon_ᚶĿפᎶךЂগᎲ分օ.append('-')
    return ''.join(_nixon_ᚶĿפᎶךЂগᎲ分օ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_Ҋ๒Ѱеͽफ़ิۈ = argv[0]
    _nixon_ძɩშᏍ鰶ʜנᛁ = ' '.join(argv[1:])
    if _nixon_Ҋ๒Ѱеͽफ़ิۈ == 'slugify':
        print(_nx_385816(_nixon_ძɩშᏍ鰶ʜנᛁ))
    elif _nixon_Ҋ๒Ѱеͽफ़ิۈ == 'count_words':
        print(_nx_385101(_nixon_ძɩშᏍ鰶ʜנᛁ))
    elif _nixon_Ҋ๒Ѱеͽफ़ิۈ == 'reverse_words':
        print(_nx_31b169(_nixon_ძɩშᏍ鰶ʜנᛁ))
    elif _nixon_Ҋ๒Ѱеͽफ़ิۈ == 'shout':
        print(_nx_8ca8c6(_nixon_ძɩშᏍ鰶ʜנᛁ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])