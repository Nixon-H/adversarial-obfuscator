import sys

def _nx_385816(text):
    _nixon_ؼ擠Ēჳᚥढėǜȟػ = []
    for _nixon_ᛌЏטłɣזμぷҜ in text.lower():
        if _nixon_ᛌЏטłɣזμぷҜ.isalnum():
            _nixon_ؼ擠Ēჳᚥढėǜȟػ.append(_nixon_ᛌЏטłɣזμぷҜ)
        elif _nixon_ؼ擠Ēჳᚥढėǜȟػ and _nixon_ؼ擠Ēჳᚥढėǜȟػ[-1] != '-':
            _nixon_ؼ擠Ēჳᚥढėǜȟػ.append('-')
    return ''.join(_nixon_ؼ擠Ēჳᚥढėǜȟػ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_玒ڹԲႿ烿ჲ丣ტŎᚫ = argv[0]
    _nixon_शضथľե = ' '.join(argv[1:])
    if _nixon_玒ڹԲႿ烿ჲ丣ტŎᚫ == 'slugify':
        print(_nx_385816(_nixon_शضथľե))
    elif _nixon_玒ڹԲႿ烿ჲ丣ტŎᚫ == 'count_words':
        print(_nx_385101(_nixon_शضथľե))
    elif _nixon_玒ڹԲႿ烿ჲ丣ტŎᚫ == 'reverse_words':
        print(_nx_31b169(_nixon_शضथľե))
    elif _nixon_玒ڹԲႿ烿ჲ丣ტŎᚫ == 'shout':
        print(_nx_8ca8c6(_nixon_शضथľե))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])