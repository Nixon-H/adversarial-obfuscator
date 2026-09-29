import sys

def _nx_385816(text):
    _nixon_ᛅשำЂȯϿこʋぴご = []
    for _nixon_ՂЧᏦđБΊϨ in text.lower():
        if _nixon_ՂЧᏦđБΊϨ.isalnum():
            _nixon_ᛅשำЂȯϿこʋぴご.append(_nixon_ՂЧᏦđБΊϨ)
        elif _nixon_ᛅשำЂȯϿこʋぴご and _nixon_ᛅשำЂȯϿこʋぴご[-1] != '-':
            _nixon_ᛅשำЂȯϿこʋぴご.append('-')
    return ''.join(_nixon_ᛅשำЂȯϿこʋぴご).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_Օӭ幥יᛟġƿぎوৗ = argv[0]
    _nixon_ᛏɵϫʃぜঃϘןםᏟ = ' '.join(argv[1:])
    if _nixon_Օӭ幥יᛟġƿぎوৗ == 'slugify':
        print(_nx_385816(_nixon_ᛏɵϫʃぜঃϘןםᏟ))
    elif _nixon_Օӭ幥יᛟġƿぎوৗ == 'count_words':
        print(_nx_385101(_nixon_ᛏɵϫʃぜঃϘןםᏟ))
    elif _nixon_Օӭ幥יᛟġƿぎوৗ == 'reverse_words':
        print(_nx_31b169(_nixon_ᛏɵϫʃぜঃϘןםᏟ))
    elif _nixon_Օӭ幥יᛟġƿぎوৗ == 'shout':
        print(_nx_8ca8c6(_nixon_ᛏɵϫʃぜঃϘןםᏟ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])