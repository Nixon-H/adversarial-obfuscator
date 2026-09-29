import sys

def _nx_385816(text):
    _nixon_הՊϚᎢᎫ = []
    for _nixon_Ƚنาव倷 in text.lower():
        if _nixon_Ƚنาव倷.isalnum():
            _nixon_הՊϚᎢᎫ.append(_nixon_Ƚنาव倷)
        elif _nixon_הՊϚᎢᎫ and _nixon_הՊϚᎢᎫ[-1] != '-':
            _nixon_הՊϚᎢᎫ.append('-')
    return ''.join(_nixon_הՊϚᎢᎫ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_جκᎾᎹ緘ʓզჍלѾ = argv[0]
    _nixon_ʒצČۋびʠԼ钾 = ' '.join(argv[1:])
    if _nixon_جκᎾᎹ緘ʓզჍלѾ == 'slugify':
        print(_nx_385816(_nixon_ʒצČۋびʠԼ钾))
    elif _nixon_جκᎾᎹ緘ʓզჍלѾ == 'count_words':
        print(_nx_385101(_nixon_ʒצČۋびʠԼ钾))
    elif _nixon_جκᎾᎹ緘ʓզჍלѾ == 'reverse_words':
        print(_nx_31b169(_nixon_ʒצČۋびʠԼ钾))
    elif _nixon_جκᎾᎹ緘ʓզჍלѾ == 'shout':
        print(_nx_8ca8c6(_nixon_ʒצČۋびʠԼ钾))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])