import sys

def _nx_385816(text):
    _nixon_わƭそ৫ᏘŴᛧ = []
    for _nixon_আסЯחג in text.lower():
        if _nixon_আסЯחג.isalnum():
            _nixon_わƭそ৫ᏘŴᛧ.append(_nixon_আסЯחג)
        elif _nixon_わƭそ৫ᏘŴᛧ and _nixon_わƭそ৫ᏘŴᛧ[-1] != '-':
            _nixon_わƭそ৫ᏘŴᛧ.append('-')
    return ''.join(_nixon_わƭそ৫ᏘŴᛧ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ƳฆƭƗᎡႲᚩƱ৮ᛢ = argv[0]
    _nixon_ɲלᎤƸŔसǭл = ' '.join(argv[1:])
    if _nixon_ƳฆƭƗᎡႲᚩƱ৮ᛢ == 'slugify':
        print(_nx_385816(_nixon_ɲלᎤƸŔसǭл))
    elif _nixon_ƳฆƭƗᎡႲᚩƱ৮ᛢ == 'count_words':
        print(_nx_385101(_nixon_ɲלᎤƸŔसǭл))
    elif _nixon_ƳฆƭƗᎡႲᚩƱ৮ᛢ == 'reverse_words':
        print(_nx_31b169(_nixon_ɲלᎤƸŔसǭл))
    elif _nixon_ƳฆƭƗᎡႲᚩƱ৮ᛢ == 'shout':
        print(_nx_8ca8c6(_nixon_ɲלᎤƸŔसǭл))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])