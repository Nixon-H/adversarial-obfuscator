import sys

def _nx_385816(text):
    _nixon_ƣႽᏒПᏀもեѣճ = []
    for _nixon_謡Ϫᛖঁญ燶ゔ in text.lower():
        if _nixon_謡Ϫᛖঁญ燶ゔ.isalnum():
            _nixon_ƣႽᏒПᏀもեѣճ.append(_nixon_謡Ϫᛖঁญ燶ゔ)
        elif _nixon_ƣႽᏒПᏀもեѣճ and _nixon_ƣႽᏒПᏀもեѣճ[-1] != '-':
            _nixon_ƣႽᏒПᏀもեѣճ.append('-')
    return ''.join(_nixon_ƣႽᏒПᏀもեѣճ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ''.join([' ']).join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ხםᎲŝᛥό = argv[0]
    _nixon_ัęႠƂᏲə = ' '.join(argv[1:])
    if _nixon_ხםᎲŝᛥό == 'slugify':
        print(_nx_385816(_nixon_ัęႠƂᏲə))
    elif _nixon_ხםᎲŝᛥό == ''.join(['c', 'o', 'u', 'n', 't', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_385101(_nixon_ัęႠƂᏲə))
    elif _nixon_ხםᎲŝᛥό == 'reverse_words':
        print(_nx_31b169(_nixon_ัęႠƂᏲə))
    elif _nixon_ხםᎲŝᛥό == 'shout':
        print(_nx_8ca8c6(_nixon_ัęႠƂᏲə))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])