import sys

def _nx_385816(text):
    _nixon_ףɑॄ硺ีるうุऴ = []
    for _nixon_ͼᚼᛂ١ै०ѫऑʁӖ in text.lower():
        if _nixon_ͼᚼᛂ١ै०ѫऑʁӖ.isalnum():
            _nixon_ףɑॄ硺ีるうุऴ.append(_nixon_ͼᚼᛂ١ै०ѫऑʁӖ)
        elif _nixon_ףɑॄ硺ีるうุऴ and _nixon_ףɑॄ硺ีるうุऴ[-1] != '-':
            _nixon_ףɑॄ硺ีるうุऴ.append('-')
    return ''.join(_nixon_ףɑॄ硺ีるうุऴ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ǊƧʫȦოɥڗ辕ᚬ = argv[0]
    _nixon_ϯ櫱ৄႤɓऒƵز = ' '.join(argv[1:])
    if _nixon_ǊƧʫȦოɥڗ辕ᚬ == 'slugify':
        print(_nx_385816(_nixon_ϯ櫱ৄႤɓऒƵز))
    elif _nixon_ǊƧʫȦოɥڗ辕ᚬ == 'count_words':
        print(_nx_385101(_nixon_ϯ櫱ৄႤɓऒƵز))
    elif _nixon_ǊƧʫȦოɥڗ辕ᚬ == 'reverse_words':
        print(_nx_31b169(_nixon_ϯ櫱ৄႤɓऒƵز))
    elif _nixon_ǊƧʫȦოɥڗ辕ᚬ == 'shout':
        print(_nx_8ca8c6(_nixon_ϯ櫱ৄႤɓऒƵز))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])