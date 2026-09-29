import sys

def _nx_385816(text):
    _nixon_Ꭱ้ᏌĥڱЧᏚ = []
    for _nixon_やѱȡԾҁחדү in text.lower():
        if _nixon_やѱȡԾҁחדү.isalnum():
            _nixon_Ꭱ้ᏌĥڱЧᏚ.append(_nixon_やѱȡԾҁחדү)
        elif _nixon_Ꭱ้ᏌĥڱЧᏚ and _nixon_Ꭱ้ᏌĥڱЧᏚ[-1] != '-':
            _nixon_Ꭱ้ᏌĥڱЧᏚ.append('-')
    return ''.join(_nixon_Ꭱ้ᏌĥڱЧᏚ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return chr(32).join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + chr(33)

def _demo(argv):
    _nixon_ȍაԶগॣऱ = argv[0]
    _nixon_Ϯٔแɫҿהșै = ' '.join(argv[1:])
    if _nixon_ȍაԶগॣऱ == 'slugify':
        print(_nx_385816(_nixon_Ϯٔแɫҿהșै))
    elif _nixon_ȍაԶগॣऱ == 'count_words':
        print(_nx_385101(_nixon_Ϯٔแɫҿהșै))
    elif _nixon_ȍაԶগॣऱ == ''.join(['r', 'e', 'v', 'e', 'r', 's', 'e', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_31b169(_nixon_Ϯٔแɫҿהșै))
    elif _nixon_ȍაԶগॣऱ == 'shout':
        print(_nx_8ca8c6(_nixon_Ϯٔแɫҿהșै))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])