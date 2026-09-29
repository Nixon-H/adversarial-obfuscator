import sys

def _nx_385816(text):
    _nixon_皅หへيϘᏇʋぴნび = []
    for _nixon_ৼঊᎳȤȿよơ in text.lower():
        if _nixon_ৼঊᎳȤȿよơ.isalnum():
            _nixon_皅หへيϘᏇʋぴნび.append(_nixon_ৼঊᎳȤȿよơ)
        elif _nixon_皅หへيϘᏇʋぴნび and _nixon_皅หへيϘᏇʋぴნび[-1] != '-':
            _nixon_皅หへيϘᏇʋぴნび.append('-')
    return ''.join(_nixon_皅หへيϘᏇʋぴნび).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return chr(32).join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + ''.join(['!'])

def _demo(argv):
    _nixon_ɃļᏕংƽԾᏜĬҭ = argv[0]
    _nixon_ɪڥॄशই়ʠهづʃ = chr(32).join(argv[1:])
    if _nixon_ɃļᏕংƽԾᏜĬҭ == 'slugify':
        print(_nx_385816(_nixon_ɪڥॄशই়ʠهづʃ))
    elif _nixon_ɃļᏕংƽԾᏜĬҭ == 'count_words':
        print(_nx_385101(_nixon_ɪڥॄशই়ʠهづʃ))
    elif _nixon_ɃļᏕংƽԾᏜĬҭ == 'reverse_words':
        print(_nx_31b169(_nixon_ɪڥॄशই়ʠهづʃ))
    elif _nixon_ɃļᏕংƽԾᏜĬҭ == 'shout':
        print(_nx_8ca8c6(_nixon_ɪڥॄशই়ʠهづʃ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])