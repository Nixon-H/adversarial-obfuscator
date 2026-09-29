import sys

def _nx_385816(text):
    _nixon_წ鱱蒕Ÿ๊ = []
    for _nixon_ᛐӢνוখ in text.lower():
        if _nixon_ᛐӢνוখ.isalnum():
            _nixon_წ鱱蒕Ÿ๊.append(_nixon_ᛐӢνוখ)
        elif _nixon_წ鱱蒕Ÿ๊ and _nixon_წ鱱蒕Ÿ๊[-1] != '-':
            _nixon_წ鱱蒕Ÿ๊.append('-')
    return ''.join(_nixon_წ鱱蒕Ÿ๊).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ϛौǟऑॅŦףᛖյځ = argv[0]
    _nixon_Ɏॐゖǩج = ' '.join(argv[1:])
    if _nixon_ϛौǟऑॅŦףᛖյځ == 'slugify':
        print(_nx_385816(_nixon_Ɏॐゖǩج))
    elif _nixon_ϛौǟऑॅŦףᛖյځ == 'count_words':
        print(_nx_385101(_nixon_Ɏॐゖǩج))
    elif _nixon_ϛौǟऑॅŦףᛖյځ == 'reverse_words':
        print(_nx_31b169(_nixon_Ɏॐゖǩج))
    elif _nixon_ϛौǟऑॅŦףᛖյځ == 'shout':
        print(_nx_8ca8c6(_nixon_Ɏॐゖǩج))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])