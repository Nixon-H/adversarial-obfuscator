import sys

def _nx_385816(text):
    _nixon_び栚麄ƱᛗԴ = []
    for _nixon_ɽ搉ĈʩはᚾΛᛗא in text.lower():
        if _nixon_ɽ搉ĈʩはᚾΛᛗא.isalnum():
            _nixon_び栚麄ƱᛗԴ.append(_nixon_ɽ搉ĈʩはᚾΛᛗא)
        elif _nixon_び栚麄ƱᛗԴ and _nixon_び栚麄ƱᛗԴ[-1] != '-':
            _nixon_び栚麄ƱᛗԴ.append('-')
    return ''.join(_nixon_び栚麄ƱᛗԴ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ᛦįלǗႴ嬷ϛᛇ = argv[0]
    _nixon_हবფυ२ჹしআ服巳 = ' '.join(argv[1:])
    if _nixon_ᛦįלǗႴ嬷ϛᛇ == 'slugify':
        print(_nx_385816(_nixon_हবფυ२ჹしআ服巳))
    elif _nixon_ᛦįלǗႴ嬷ϛᛇ == 'count_words':
        print(_nx_385101(_nixon_हবფυ२ჹしআ服巳))
    elif _nixon_ᛦįלǗႴ嬷ϛᛇ == 'reverse_words':
        print(_nx_31b169(_nixon_हবფυ२ჹしআ服巳))
    elif _nixon_ᛦįלǗႴ嬷ϛᛇ == 'shout':
        print(_nx_8ca8c6(_nixon_हবფυ२ჹしআ服巳))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])