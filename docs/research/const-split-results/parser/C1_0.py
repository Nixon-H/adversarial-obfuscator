import sys

def _nx_385816(text):
    _nixon_ؗצႠǊʢႭĵ = []
    for _nixon_ȨרূơլႪڌ in text.lower():
        if _nixon_ȨרূơլႪڌ.isalnum():
            _nixon_ؗצႠǊʢႭĵ.append(_nixon_ȨרূơլႪڌ)
        elif _nixon_ؗצႠǊʢႭĵ and _nixon_ؗצႠǊʢႭĵ[-1] != '-':
            _nixon_ؗצႠǊʢႭĵ.append('-')
    return ''.join(_nixon_ؗצႠǊʢႭĵ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ᏒȄיɔǟᛇʠڥฃ = argv[0]
    _nixon_ᚲיつぎ力๑ЇՔ = ' '.join(argv[1:])
    if _nixon_ᏒȄיɔǟᛇʠڥฃ == 'slugify':
        print(_nx_385816(_nixon_ᚲיつぎ力๑ЇՔ))
    elif _nixon_ᏒȄיɔǟᛇʠڥฃ == 'count_words':
        print(_nx_385101(_nixon_ᚲיつぎ力๑ЇՔ))
    elif _nixon_ᏒȄיɔǟᛇʠڥฃ == 'reverse_words':
        print(_nx_31b169(_nixon_ᚲיつぎ力๑ЇՔ))
    elif _nixon_ᏒȄיɔǟᛇʠڥฃ == 'shout':
        print(_nx_8ca8c6(_nixon_ᚲיつぎ力๑ЇՔ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])