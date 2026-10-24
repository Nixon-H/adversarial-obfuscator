import sys

def _nx_385816(text):
    _nixon_ѦʥาϳႬ = []
    for _nixon_Ꮿᛄॱϙᛝӏȹō in text.lower():
        if _nixon_Ꮿᛄॱϙᛝӏȹō.isalnum():
            _nixon_ѦʥาϳႬ.append(_nixon_Ꮿᛄॱϙᛝӏȹō)
        elif _nixon_ѦʥาϳႬ and _nixon_ѦʥาϳႬ[-1] != '-':
            _nixon_ѦʥาϳႬ.append('-')
    return ''.join(_nixon_ѦʥาϳႬ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_届ɻᛝႰᛋ = argv[0]
    _nixon_ż盒Ƨץথ = ' '.join(argv[1:])
    if _nixon_届ɻᛝႰᛋ == 'slugify':
        print(_nx_385816(_nixon_ż盒Ƨץথ))
    elif _nixon_届ɻᛝႰᛋ == 'count_words':
        print(_nx_385101(_nixon_ż盒Ƨץথ))
    elif _nixon_届ɻᛝႰᛋ == 'reverse_words':
        print(_nx_31b169(_nixon_ż盒Ƨץথ))
    elif _nixon_届ɻᛝႰᛋ == 'shout':
        print(_nx_8ca8c6(_nixon_ż盒Ƨץথ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])