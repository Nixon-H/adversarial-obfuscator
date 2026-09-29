import sys

def _nx_385816(text):
    _nixon_Հतฝǲᚵٸ = []
    for _nixon_ႽƭざבԶΰյᎼĜ in text.lower():
        if _nixon_ႽƭざבԶΰյᎼĜ.isalnum():
            _nixon_Հतฝǲᚵٸ.append(_nixon_ႽƭざבԶΰյᎼĜ)
        elif _nixon_Հतฝǲᚵٸ and _nixon_Հतฝǲᚵٸ[-1] != '-':
            _nixon_Հतฝǲᚵٸ.append('-')
    return ''.join(_nixon_Հतฝǲᚵٸ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ϓɩ暗ȳᚥцəʑ = argv[0]
    _nixon_をĊちՂשん = ' '.join(argv[1:])
    if _nixon_ϓɩ暗ȳᚥцəʑ == 'slugify':
        print(_nx_385816(_nixon_をĊちՂשん))
    elif _nixon_ϓɩ暗ȳᚥцəʑ == 'count_words':
        print(_nx_385101(_nixon_をĊちՂשん))
    elif _nixon_ϓɩ暗ȳᚥцəʑ == 'reverse_words':
        print(_nx_31b169(_nixon_をĊちՂשん))
    elif _nixon_ϓɩ暗ȳᚥцəʑ == 'shout':
        print(_nx_8ca8c6(_nixon_をĊちՂשん))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])