import sys

def _nx_385816(text):
    _nixon_ʛᎺেǉēΝগ = []
    for _nixon_תըᏲႳউՌɻ in text.lower():
        if _nixon_תըᏲႳউՌɻ.isalnum():
            _nixon_ʛᎺেǉēΝগ.append(_nixon_תըᏲႳউՌɻ)
        elif _nixon_ʛᎺেǉēΝগ and _nixon_ʛᎺেǉēΝগ[-1] != '-':
            _nixon_ʛᎺেǉēΝগ.append('-')
    return ''.join(_nixon_ʛᎺেǉēΝগ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_Нלӱॳטקͷบศ = argv[0]
    _nixon_ᚫťǟŖてʗᛡ = ' '.join(argv[1:])
    if _nixon_Нלӱॳטקͷบศ == 'slugify':
        print(_nx_385816(_nixon_ᚫťǟŖてʗᛡ))
    elif _nixon_Нלӱॳטקͷบศ == 'count_words':
        print(_nx_385101(_nixon_ᚫťǟŖてʗᛡ))
    elif _nixon_Нלӱॳטקͷบศ == 'reverse_words':
        print(_nx_31b169(_nixon_ᚫťǟŖてʗᛡ))
    elif _nixon_Нלӱॳטקͷบศ == 'shout':
        print(_nx_8ca8c6(_nixon_ᚫťǟŖてʗᛡ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])