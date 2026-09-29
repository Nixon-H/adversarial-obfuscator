import sys

def _nx_385816(text):
    _nixon_קゎᎤฤᎭぐ = []
    for _nixon_աЋҐᚼՋ in text.lower():
        if _nixon_աЋҐᚼՋ.isalnum():
            _nixon_קゎᎤฤᎭぐ.append(_nixon_աЋҐᚼՋ)
        elif _nixon_קゎᎤฤᎭぐ and _nixon_קゎᎤฤᎭぐ[-1] != '-':
            _nixon_קゎᎤฤᎭぐ.append('-')
    return ''.join(_nixon_קゎᎤฤᎭぐ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_יշบבҞدՋᚡק = argv[0]
    _nixon_ʐ愍ʝᎿջԽʧ = ' '.join(argv[1:])
    if _nixon_יշบבҞدՋᚡק == 'slugify':
        print(_nx_385816(_nixon_ʐ愍ʝᎿջԽʧ))
    elif _nixon_יշบבҞدՋᚡק == 'count_words':
        print(_nx_385101(_nixon_ʐ愍ʝᎿջԽʧ))
    elif _nixon_יշบבҞدՋᚡק == 'reverse_words':
        print(_nx_31b169(_nixon_ʐ愍ʝᎿջԽʧ))
    elif _nixon_יշบבҞدՋᚡק == 'shout':
        print(_nx_8ca8c6(_nixon_ʐ愍ʝᎿջԽʧ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])