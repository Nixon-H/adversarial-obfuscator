import sys

def _nx_385816(text):
    _nixon_ʓΩงᚾКĂզৠҰ城 = []
    for _nixon_Ӷɹ๗ɕɃՐᛂङӊʟ in text.lower():
        if _nixon_Ӷɹ๗ɕɃՐᛂङӊʟ.isalnum():
            _nixon_ʓΩงᚾКĂզৠҰ城.append(_nixon_Ӷɹ๗ɕɃՐᛂङӊʟ)
        elif _nixon_ʓΩงᚾКĂզৠҰ城 and _nixon_ʓΩงᚾКĂզৠҰ城[-1] != '-':
            _nixon_ʓΩงᚾКĂզৠҰ城.append('-')
    return ''.join(_nixon_ʓΩงᚾКĂզৠҰ城).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ᏀლՅผ๐ฏჯぉᎠ = argv[0]
    _nixon_अգăႬζ = ' '.join(argv[1:])
    if _nixon_ᏀლՅผ๐ฏჯぉᎠ == 'slugify':
        print(_nx_385816(_nixon_अգăႬζ))
    elif _nixon_ᏀლՅผ๐ฏჯぉᎠ == 'count_words':
        print(_nx_385101(_nixon_अգăႬζ))
    elif _nixon_ᏀლՅผ๐ฏჯぉᎠ == 'reverse_words':
        print(_nx_31b169(_nixon_अգăႬζ))
    elif _nixon_ᏀლՅผ๐ฏჯぉᎠ == 'shout':
        print(_nx_8ca8c6(_nixon_अգăႬζ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])