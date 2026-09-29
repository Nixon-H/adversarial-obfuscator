import sys

def _nx_385816(text):
    _nixon_琐িᏱӃϐɛᚥॕҭ = []
    for _nixon_にקτႧᛓजษʆΐ in text.lower():
        if _nixon_にקτႧᛓजษʆΐ.isalnum():
            _nixon_琐িᏱӃϐɛᚥॕҭ.append(_nixon_にקτႧᛓजษʆΐ)
        elif _nixon_琐িᏱӃϐɛᚥॕҭ and _nixon_琐িᏱӃϐɛᚥॕҭ[-1] != '-':
            _nixon_琐িᏱӃϐɛᚥॕҭ.append('-')
    return ''.join(_nixon_琐িᏱӃϐɛᚥॕҭ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_櫯ɗΪぞרᏜ = argv[0]
    _nixon_ƋႹ穇Єぬזৡ = ' '.join(argv[1:])
    if _nixon_櫯ɗΪぞרᏜ == 'slugify':
        print(_nx_385816(_nixon_ƋႹ穇Єぬזৡ))
    elif _nixon_櫯ɗΪぞרᏜ == 'count_words':
        print(_nx_385101(_nixon_ƋႹ穇Єぬזৡ))
    elif _nixon_櫯ɗΪぞרᏜ == 'reverse_words':
        print(_nx_31b169(_nixon_ƋႹ穇Єぬזৡ))
    elif _nixon_櫯ɗΪぞרᏜ == 'shout':
        print(_nx_8ca8c6(_nixon_ƋႹ穇Єぬזৡ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])