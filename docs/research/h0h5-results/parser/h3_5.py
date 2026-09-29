import sys

def _nx_385816(text):
    _nixon_Ӥڈべʎฅ = []
    for _nixon_ՉჄذŔĶุႿ in text.lower():
        if _nixon_ՉჄذŔĶุႿ.isalnum():
            _nixon_Ӥڈべʎฅ.append(_nixon_ՉჄذŔĶุႿ)
        elif _nixon_Ӥڈべʎฅ and _nixon_Ӥڈべʎฅ[-1] != '-':
            _nixon_Ӥڈべʎฅ.append('-')
    return ''.join(_nixon_Ӥڈべʎฅ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ѝȠᏠՠҮΙ岅 = argv[0]
    _nixon_Ÿᛒ辮Ⴈえҫがۭ = ' '.join(argv[1:])
    if _nixon_ѝȠᏠՠҮΙ岅 == 'slugify':
        print(_nx_385816(_nixon_Ÿᛒ辮Ⴈえҫがۭ))
    elif _nixon_ѝȠᏠՠҮΙ岅 == 'count_words':
        print(_nx_385101(_nixon_Ÿᛒ辮Ⴈえҫがۭ))
    elif _nixon_ѝȠᏠՠҮΙ岅 == 'reverse_words':
        print(_nx_31b169(_nixon_Ÿᛒ辮Ⴈえҫがۭ))
    elif _nixon_ѝȠᏠՠҮΙ岅 == 'shout':
        print(_nx_8ca8c6(_nixon_Ÿᛒ辮Ⴈえҫがۭ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])