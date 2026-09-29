import sys

def _nx_385816(text):
    _nixon_ϦैיɵőᏩʩ = []
    for _nixon_ӣԳΩבᛓĦɡᚽ in text.lower():
        if _nixon_ӣԳΩבᛓĦɡᚽ.isalnum():
            _nixon_ϦैיɵőᏩʩ.append(_nixon_ӣԳΩבᛓĦɡᚽ)
        elif _nixon_ϦैיɵőᏩʩ and _nixon_ϦैיɵőᏩʩ[-1] != '-':
            _nixon_ϦैיɵőᏩʩ.append('-')
    return ''.join(_nixon_ϦैיɵőᏩʩ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ЇљそĦɥԱǡə = argv[0]
    _nixon_آΛמღჴূ = ' '.join(argv[1:])
    if _nixon_ЇљそĦɥԱǡə == 'slugify':
        print(_nx_385816(_nixon_آΛמღჴূ))
    elif _nixon_ЇљそĦɥԱǡə == 'count_words':
        print(_nx_385101(_nixon_آΛמღჴূ))
    elif _nixon_ЇљそĦɥԱǡə == 'reverse_words':
        print(_nx_31b169(_nixon_آΛמღჴূ))
    elif _nixon_ЇљそĦɥԱǡə == 'shout':
        print(_nx_8ca8c6(_nixon_آΛמღჴূ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])