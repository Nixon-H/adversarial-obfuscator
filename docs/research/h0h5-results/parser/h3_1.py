import sys

def _nx_385816(text):
    _nixon_ঠՏᚺǪᏦষ顡くć = []
    for _nixon_Րरऽعすゕžѝჲ in text.lower():
        if _nixon_Րरऽعすゕžѝჲ.isalnum():
            _nixon_ঠՏᚺǪᏦষ顡くć.append(_nixon_Րरऽعすゕžѝჲ)
        elif _nixon_ঠՏᚺǪᏦষ顡くć and _nixon_ঠՏᚺǪᏦষ顡くć[-1] != '-':
            _nixon_ঠՏᚺǪᏦষ顡くć.append('-')
    return ''.join(_nixon_ঠՏᚺǪᏦষ顡くć).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_Пむ簘৬ᚠᏃ·ʓθΘ = argv[0]
    _nixon_ȿণᎿ罉כόǊɩᚡも = ' '.join(argv[1:])
    if _nixon_Пむ簘৬ᚠᏃ·ʓθΘ == 'slugify':
        print(_nx_385816(_nixon_ȿণᎿ罉כόǊɩᚡも))
    elif _nixon_Пむ簘৬ᚠᏃ·ʓθΘ == 'count_words':
        print(_nx_385101(_nixon_ȿণᎿ罉כόǊɩᚡも))
    elif _nixon_Пむ簘৬ᚠᏃ·ʓθΘ == 'reverse_words':
        print(_nx_31b169(_nixon_ȿণᎿ罉כόǊɩᚡも))
    elif _nixon_Пむ簘৬ᚠᏃ·ʓθΘ == 'shout':
        print(_nx_8ca8c6(_nixon_ȿণᎿ罉כόǊɩᚡも))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])