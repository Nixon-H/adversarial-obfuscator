import sys

def _nx_385816(text):
    _nixon_ǈέธঢ়ᚩ = []
    for _nixon_ͻπŹٌĞǌᛡむ in text.lower():
        if _nixon_ͻπŹٌĞǌᛡむ.isalnum():
            _nixon_ǈέธঢ়ᚩ.append(_nixon_ͻπŹٌĞǌᛡむ)
        elif _nixon_ǈέธঢ়ᚩ and _nixon_ǈέธঢ়ᚩ[-1] != '-':
            _nixon_ǈέธঢ়ᚩ.append('-')
    return ''.join(_nixon_ǈέธঢ়ᚩ).strip(chr(45))

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ŎĪᏍჅٿყ = argv[0]
    _nixon_缊ちĕȡʩۭძแไ = ''.join([' ']).join(argv[1:])
    if _nixon_ŎĪᏍჅٿყ == 'slugify':
        print(_nx_385816(_nixon_缊ちĕȡʩۭძแไ))
    elif _nixon_ŎĪᏍჅٿყ == ''.join(['c', 'o', 'u', 'n', 't', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_385101(_nixon_缊ちĕȡʩۭძแไ))
    elif _nixon_ŎĪᏍჅٿყ == 'reverse_words':
        print(_nx_31b169(_nixon_缊ちĕȡʩۭძแไ))
    elif _nixon_ŎĪᏍჅٿყ == 'shout':
        print(_nx_8ca8c6(_nixon_缊ちĕȡʩۭძแไ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])