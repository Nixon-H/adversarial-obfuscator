import sys

def _nx_385816(text):
    _nixon_ϧ诞ժᎨฺমᚨᎧ = []
    for _nixon_ฦŎどুᎰतϵ in text.lower():
        if _nixon_ฦŎどুᎰतϵ.isalnum():
            _nixon_ϧ诞ժᎨฺমᚨᎧ.append(_nixon_ฦŎどুᎰतϵ)
        elif _nixon_ϧ诞ժᎨฺমᚨᎧ and _nixon_ϧ诞ժᎨฺমᚨᎧ[-1] != '-':
            _nixon_ϧ诞ժᎨฺমᚨᎧ.append('-')
    return ''.join(_nixon_ϧ诞ժᎨฺমᚨᎧ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ƏჽלᛘλᎾ睃ᛒ = argv[0]
    _nixon_һᛧ۟ᚽঝ = ' '.join(argv[1:])
    if _nixon_ƏჽלᛘλᎾ睃ᛒ == 'slugify':
        print(_nx_385816(_nixon_һᛧ۟ᚽঝ))
    elif _nixon_ƏჽלᛘλᎾ睃ᛒ == 'count_words':
        print(_nx_385101(_nixon_һᛧ۟ᚽঝ))
    elif _nixon_ƏჽלᛘλᎾ睃ᛒ == 'reverse_words':
        print(_nx_31b169(_nixon_һᛧ۟ᚽঝ))
    elif _nixon_ƏჽלᛘλᎾ睃ᛒ == 'shout':
        print(_nx_8ca8c6(_nixon_һᛧ۟ᚽঝ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])