import sys

def _nx_385816(text):
    _nixon_づʯٓ运фמ = []
    for _nixon_ᎪɨӇৌβ in text.lower():
        if _nixon_ᎪɨӇৌβ.isalnum():
            _nixon_づʯٓ运фמ.append(_nixon_ᎪɨӇৌβ)
        elif _nixon_づʯٓ运фמ and _nixon_づʯٓ运фמ[-1] != '-':
            _nixon_づʯٓ运фמ.append('-')
    return ''.join(_nixon_づʯٓ运фמ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ɨҸɬৰᏐშႭॻمق = argv[0]
    _nixon_ᏓფȯᎤکďႢᛝむ = ' '.join(argv[1:])
    if _nixon_ɨҸɬৰᏐშႭॻمق == 'slugify':
        print(_nx_385816(_nixon_ᏓფȯᎤکďႢᛝむ))
    elif _nixon_ɨҸɬৰᏐშႭॻمق == 'count_words':
        print(_nx_385101(_nixon_ᏓფȯᎤکďႢᛝむ))
    elif _nixon_ɨҸɬৰᏐშႭॻمق == 'reverse_words':
        print(_nx_31b169(_nixon_ᏓფȯᎤکďႢᛝむ))
    elif _nixon_ɨҸɬৰᏐშႭॻمق == 'shout':
        print(_nx_8ca8c6(_nixon_ᏓფȯᎤکďႢᛝむ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])