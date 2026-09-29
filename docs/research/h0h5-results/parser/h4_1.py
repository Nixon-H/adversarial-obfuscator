import sys

def _nx_385816(text):
    _nixon_իשᎭϡᎵ = []
    for _nixon_ոႴᎽႬƱϦŎᎼとŮ in text.lower():
        if _nixon_ոႴᎽႬƱϦŎᎼとŮ.isalnum():
            _nixon_իשᎭϡᎵ.append(_nixon_ոႴᎽႬƱϦŎᎼとŮ)
        elif _nixon_իשᎭϡᎵ and _nixon_իשᎭϡᎵ[-1] != '-':
            _nixon_իשᎭϡᎵ.append('-')
    return ''.join(_nixon_իשᎭϡᎵ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ႲᎽভჸծŠלႾϜȚ = argv[0]
    _nixon_蛪ɘ殭ϷĲনॣゎȁ = ' '.join(argv[1:])
    if _nixon_ႲᎽভჸծŠלႾϜȚ == 'slugify':
        print(_nx_385816(_nixon_蛪ɘ殭ϷĲনॣゎȁ))
    elif _nixon_ႲᎽভჸծŠלႾϜȚ == 'count_words':
        print(_nx_385101(_nixon_蛪ɘ殭ϷĲনॣゎȁ))
    elif _nixon_ႲᎽভჸծŠלႾϜȚ == 'reverse_words':
        print(_nx_31b169(_nixon_蛪ɘ殭ϷĲনॣゎȁ))
    elif _nixon_ႲᎽভჸծŠלႾϜȚ == 'shout':
        print(_nx_8ca8c6(_nixon_蛪ɘ殭ϷĲনॣゎȁ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])