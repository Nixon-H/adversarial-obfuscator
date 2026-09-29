import sys

def _nx_385816(text):
    _nixon_ڱকႫफ़ჇɼĆ҇օ = []
    for _nixon_ɥחڎᚶĺबॼट in text.lower():
        if _nixon_ɥחڎᚶĺबॼट.isalnum():
            _nixon_ڱকႫफ़ჇɼĆ҇օ.append(_nixon_ɥחڎᚶĺबॼट)
        elif _nixon_ڱকႫफ़ჇɼĆ҇օ and _nixon_ڱকႫफ़ჇɼĆ҇օ[-1] != '-':
            _nixon_ڱকႫफ़ჇɼĆ҇օ.append('-')
    return ''.join(_nixon_ڱকႫफ़ჇɼĆ҇օ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_Тलםٻुफ़ = argv[0]
    _nixon_णБмה২ႵȌւ = ' '.join(argv[1:])
    if _nixon_Тलםٻुफ़ == 'slugify':
        print(_nx_385816(_nixon_णБмה২ႵȌւ))
    elif _nixon_Тलםٻुफ़ == 'count_words':
        print(_nx_385101(_nixon_णБмה২ႵȌւ))
    elif _nixon_Тलםٻुफ़ == 'reverse_words':
        print(_nx_31b169(_nixon_णБмה২ႵȌւ))
    elif _nixon_Тलםٻुफ़ == 'shout':
        print(_nx_8ca8c6(_nixon_णБмה২ႵȌւ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])