import sys

def _nx_385816(text):
    _nixon_ऍդډႷבᛋՍ = []
    for _nixon_הеؗʏჂᚬ in text.lower():
        if _nixon_הеؗʏჂᚬ.isalnum():
            _nixon_ऍդډႷבᛋՍ.append(_nixon_הеؗʏჂᚬ)
        elif _nixon_ऍդډႷבᛋՍ and _nixon_ऍդډႷבᛋՍ[-1] != '-':
            _nixon_ऍդډႷבᛋՍ.append(''.join(['-']))
    return ''.join(_nixon_ऍդډႷבᛋՍ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + ''.join(['!'])

def _demo(argv):
    _nixon_ᚣさىסѪϿو = argv[0]
    _nixon_Έغขڋţńד缇おϟ = ' '.join(argv[1:])
    if _nixon_ᚣさىסѪϿو == ''.join(['s', 'l', 'u', 'g', 'i', 'f', 'y']):
        print(_nx_385816(_nixon_Έغขڋţńד缇おϟ))
    elif _nixon_ᚣさىסѪϿو == 'count_words':
        print(_nx_385101(_nixon_Έغขڋţńד缇おϟ))
    elif _nixon_ᚣさىסѪϿو == 'reverse_words':
        print(_nx_31b169(_nixon_Έغขڋţńד缇おϟ))
    elif _nixon_ᚣさىסѪϿو == 'shout':
        print(_nx_8ca8c6(_nixon_Έغขڋţńד缇おϟ))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])