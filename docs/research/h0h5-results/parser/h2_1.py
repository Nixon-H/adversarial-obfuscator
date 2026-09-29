import sys

def _nx_385816(text):
    _nixon_ऌঋǣӘղϧঢ় = []
    for _nixon_祪Ⴋʡᛁ趐 in text.lower():
        if _nixon_祪Ⴋʡᛁ趐.isalnum():
            _nixon_ऌঋǣӘղϧঢ়.append(_nixon_祪Ⴋʡᛁ趐)
        elif _nixon_ऌঋǣӘղϧঢ় and _nixon_ऌঋǣӘղϧঢ়[-1] != ''.join(['-']):
            _nixon_ऌঋǣӘղϧঢ়.append('-')
    return ''.join(_nixon_ऌঋǣӘղϧঢ়).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return chr(32).join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + chr(33)

def _demo(argv):
    _nixon_मบおरႹ = argv[0]
    _nixon_ᎼტʓĖぢǛצ = ' '.join(argv[1:])
    if _nixon_मบおरႹ == 'slugify':
        print(_nx_385816(_nixon_ᎼტʓĖぢǛצ))
    elif _nixon_मบおरႹ == ''.join(['c', 'o', 'u', 'n', 't', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_385101(_nixon_ᎼტʓĖぢǛצ))
    elif _nixon_मบおरႹ == 'reverse_words':
        print(_nx_31b169(_nixon_ᎼტʓĖぢǛצ))
    elif _nixon_मบおरႹ == 'shout':
        print(_nx_8ca8c6(_nixon_ᎼტʓĖぢǛצ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])