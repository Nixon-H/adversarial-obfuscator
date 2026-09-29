import sys

def _nx_385816(text):
    _nixon_ぐᏀႸĲᚤ = []
    for _nixon_ᛡᎭѼӛʚΆʆᛎƢ in text.lower():
        if _nixon_ᛡᎭѼӛʚΆʆᛎƢ.isalnum():
            _nixon_ぐᏀႸĲᚤ.append(_nixon_ᛡᎭѼӛʚΆʆᛎƢ)
        elif _nixon_ぐᏀႸĲᚤ and _nixon_ぐᏀႸĲᚤ[-1] != '-':
            _nixon_ぐᏀႸĲᚤ.append('-')
    return ''.join(_nixon_ぐᏀႸĲᚤ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_์ぐؤโɕრٗԶ = argv[0]
    _nixon_ᛊٻহʐնᏋĈজ = ' '.join(argv[1:])
    if _nixon_์ぐؤโɕრٗԶ == 'slugify':
        print(_nx_385816(_nixon_ᛊٻহʐնᏋĈজ))
    elif _nixon_์ぐؤโɕრٗԶ == 'count_words':
        print(_nx_385101(_nixon_ᛊٻহʐնᏋĈজ))
    elif _nixon_์ぐؤโɕრٗԶ == 'reverse_words':
        print(_nx_31b169(_nixon_ᛊٻহʐնᏋĈজ))
    elif _nixon_์ぐؤโɕრٗԶ == 'shout':
        print(_nx_8ca8c6(_nixon_ᛊٻহʐնᏋĈজ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])