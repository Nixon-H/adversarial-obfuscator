import sys

def _nx_385816(text):
    _nixon_Ꮣȱוᛆํऐ = []
    for _nixon_ąѴলӉᏰই in text.lower():
        if _nixon_ąѴলӉᏰই.isalnum():
            _nixon_Ꮣȱוᛆํऐ.append(_nixon_ąѴলӉᏰই)
        elif _nixon_Ꮣȱוᛆํऐ and _nixon_Ꮣȱוᛆํऐ[-1] != '-':
            _nixon_Ꮣȱוᛆํऐ.append('-')
    return ''.join(_nixon_Ꮣȱוᛆํऐ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_Ⴂџ絟ᏈɯĞჄぐ = argv[0]
    _nixon_杲ȼႯतڴᛅͿ॔ȟ = ' '.join(argv[1:])
    if _nixon_Ⴂџ絟ᏈɯĞჄぐ == 'slugify':
        print(_nx_385816(_nixon_杲ȼႯतڴᛅͿ॔ȟ))
    elif _nixon_Ⴂџ絟ᏈɯĞჄぐ == 'count_words':
        print(_nx_385101(_nixon_杲ȼႯतڴᛅͿ॔ȟ))
    elif _nixon_Ⴂџ絟ᏈɯĞჄぐ == 'reverse_words':
        print(_nx_31b169(_nixon_杲ȼႯतڴᛅͿ॔ȟ))
    elif _nixon_Ⴂџ絟ᏈɯĞჄぐ == 'shout':
        print(_nx_8ca8c6(_nixon_杲ȼႯतڴᛅͿ॔ȟ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])