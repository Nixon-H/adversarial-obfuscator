import sys

def _nx_385816(text):
    _nixon_Ċれफঠĺǿऱً = []
    for _nixon_ॷԱք८Շųי in text.lower():
        if _nixon_ॷԱք८Շųי.isalnum():
            _nixon_Ċれफঠĺǿऱً.append(_nixon_ॷԱք८Շųי)
        elif _nixon_Ċれफঠĺǿऱً and _nixon_Ċれफঠĺǿऱً[-1] != '-':
            _nixon_Ċれफঠĺǿऱً.append('-')
    return ''.join(_nixon_Ċれफঠĺǿऱً).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_əწ黔ᏎО = argv[0]
    _nixon_ჃͲ৾るᎱょסぞᛞ = ' '.join(argv[1:])
    if _nixon_əწ黔ᏎО == 'slugify':
        print(_nx_385816(_nixon_ჃͲ৾るᎱょסぞᛞ))
    elif _nixon_əწ黔ᏎО == 'count_words':
        print(_nx_385101(_nixon_ჃͲ৾るᎱょסぞᛞ))
    elif _nixon_əწ黔ᏎО == 'reverse_words':
        print(_nx_31b169(_nixon_ჃͲ৾るᎱょסぞᛞ))
    elif _nixon_əწ黔ᏎО == 'shout':
        print(_nx_8ca8c6(_nixon_ჃͲ৾るᎱょסぞᛞ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])