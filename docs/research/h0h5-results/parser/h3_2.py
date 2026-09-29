import sys

def _nx_385816(text):
    _nixon_კせŤӿۇěႩ筶čᏌ = []
    for _nixon_ŪבঐმॿΧͲ in text.lower():
        if _nixon_ŪבঐმॿΧͲ.isalnum():
            _nixon_კせŤӿۇěႩ筶čᏌ.append(_nixon_ŪבঐმॿΧͲ)
        elif _nixon_კせŤӿۇěႩ筶čᏌ and _nixon_კせŤӿۇěႩ筶čᏌ[-1] != '-':
            _nixon_კせŤӿۇěႩ筶čᏌ.append('-')
    return ''.join(_nixon_კせŤӿۇěႩ筶čᏌ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ƚϲνႡʁ = argv[0]
    _nixon_ϋぎΩƱŖӸƅȧॠ = ' '.join(argv[1:])
    if _nixon_ƚϲνႡʁ == 'slugify':
        print(_nx_385816(_nixon_ϋぎΩƱŖӸƅȧॠ))
    elif _nixon_ƚϲνႡʁ == 'count_words':
        print(_nx_385101(_nixon_ϋぎΩƱŖӸƅȧॠ))
    elif _nixon_ƚϲνႡʁ == 'reverse_words':
        print(_nx_31b169(_nixon_ϋぎΩƱŖӸƅȧॠ))
    elif _nixon_ƚϲνႡʁ == 'shout':
        print(_nx_8ca8c6(_nixon_ϋぎΩƱŖӸƅȧॠ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])