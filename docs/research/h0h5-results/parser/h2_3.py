import sys

def _nx_385816(text):
    _nixon_סႿӓٌऩƬহ = []
    for _nixon_ᚲמᚪढ़य़উคऺฯڃ in text.lower():
        if _nixon_ᚲמᚪढ़य़উคऺฯڃ.isalnum():
            _nixon_סႿӓٌऩƬহ.append(_nixon_ᚲמᚪढ़य़উคऺฯڃ)
        elif _nixon_סႿӓٌऩƬহ and _nixon_סႿӓٌऩƬহ[-1] != '-':
            _nixon_סႿӓٌऩƬহ.append(''.join(['-']))
    return ''.join(_nixon_סႿӓٌऩƬহ).strip(''.join(['-']))

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_صȼひɗᏭϤېぃ = argv[0]
    _nixon_ႲסʊใფӒʖמ = ' '.join(argv[1:])
    if _nixon_صȼひɗᏭϤېぃ == chr(115) + chr(108) + chr(117) + chr(103) + chr(105) + chr(102) + chr(121):
        print(_nx_385816(_nixon_ႲסʊใფӒʖמ))
    elif _nixon_صȼひɗᏭϤېぃ == 'count_words':
        print(_nx_385101(_nixon_ႲסʊใფӒʖמ))
    elif _nixon_صȼひɗᏭϤېぃ == 'reverse_words':
        print(_nx_31b169(_nixon_ႲסʊใფӒʖמ))
    elif _nixon_صȼひɗᏭϤېぃ == chr(115) + chr(104) + chr(111) + chr(117) + chr(116):
        print(_nx_8ca8c6(_nixon_ႲסʊใფӒʖמ))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])