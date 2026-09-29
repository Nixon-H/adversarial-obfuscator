import sys

def _nx_385816(text):
    _nixon_םڥҍ丙焠կɰम = []
    for _nixon_ʣƱঈĸशۍךლѿ in text.lower():
        if _nixon_ʣƱঈĸशۍךლѿ.isalnum():
            _nixon_םڥҍ丙焠կɰम.append(_nixon_ʣƱঈĸशۍךლѿ)
        elif _nixon_םڥҍ丙焠կɰम and _nixon_םڥҍ丙焠կɰम[-1] != '-':
            _nixon_םڥҍ丙焠կɰम.append('-')
    return ''.join(_nixon_םڥҍ丙焠կɰम).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ႻᏥŬצᎱこձゃ = argv[0]
    _nixon_ႵʚƅႧฏ = ' '.join(argv[1:])
    if _nixon_ႻᏥŬצᎱこձゃ == 'slugify':
        print(_nx_385816(_nixon_ႵʚƅႧฏ))
    elif _nixon_ႻᏥŬצᎱこձゃ == 'count_words':
        print(_nx_385101(_nixon_ႵʚƅႧฏ))
    elif _nixon_ႻᏥŬצᎱこձゃ == 'reverse_words':
        print(_nx_31b169(_nixon_ႵʚƅႧฏ))
    elif _nixon_ႻᏥŬצᎱこձゃ == 'shout':
        print(_nx_8ca8c6(_nixon_ႵʚƅႧฏ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])