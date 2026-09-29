import sys

def _nx_385816(text):
    _nixon_צϸĜზȾႶ = []
    for _nixon_ǖלろΞɺ in text.lower():
        if _nixon_ǖלろΞɺ.isalnum():
            _nixon_צϸĜზȾႶ.append(_nixon_ǖלろΞɺ)
        elif _nixon_צϸĜზȾႶ and _nixon_צϸĜზȾႶ[-1] != '-':
            _nixon_צϸĜზȾႶ.append('-')
    return ''.join(_nixon_צϸĜზȾႶ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_১ΰりᚻȅมڡɸ६ʚ = argv[0]
    _nixon_Ħ०ٿșᛊƫ = ' '.join(argv[1:])
    if _nixon_১ΰりᚻȅมڡɸ६ʚ == 'slugify':
        print(_nx_385816(_nixon_Ħ०ٿșᛊƫ))
    elif _nixon_১ΰりᚻȅมڡɸ६ʚ == 'count_words':
        print(_nx_385101(_nixon_Ħ०ٿșᛊƫ))
    elif _nixon_১ΰりᚻȅมڡɸ६ʚ == 'reverse_words':
        print(_nx_31b169(_nixon_Ħ०ٿșᛊƫ))
    elif _nixon_১ΰりᚻȅมڡɸ६ʚ == 'shout':
        print(_nx_8ca8c6(_nixon_Ħ०ٿșᛊƫ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])