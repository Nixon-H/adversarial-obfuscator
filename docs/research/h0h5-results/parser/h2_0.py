import sys

def _nx_385816(text):
    _nixon_Ȝあᚯذᛦ = []
    for _nixon_ᏥƇӚŋたג in text.lower():
        if _nixon_ᏥƇӚŋたג.isalnum():
            _nixon_Ȝあᚯذᛦ.append(_nixon_ᏥƇӚŋたג)
        elif _nixon_Ȝあᚯذᛦ and _nixon_Ȝあᚯذᛦ[-1] != '-':
            _nixon_Ȝあᚯذᛦ.append('-')
    return ''.join(_nixon_Ȝあᚯذᛦ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ᚨ竽םǶべᛤพ = argv[0]
    _nixon_ᛖԲঅႱͼप = chr(32).join(argv[1:])
    if _nixon_ᚨ竽םǶべᛤพ == 'slugify':
        print(_nx_385816(_nixon_ᛖԲঅႱͼप))
    elif _nixon_ᚨ竽םǶべᛤพ == chr(99) + chr(111) + chr(117) + chr(110) + chr(116) + chr(95) + chr(119) + chr(111) + chr(114) + chr(100) + chr(115):
        print(_nx_385101(_nixon_ᛖԲঅႱͼप))
    elif _nixon_ᚨ竽םǶべᛤพ == 'reverse_words':
        print(_nx_31b169(_nixon_ᛖԲঅႱͼप))
    elif _nixon_ᚨ竽םǶべᛤพ == chr(115) + chr(104) + chr(111) + chr(117) + chr(116):
        print(_nx_8ca8c6(_nixon_ᛖԲঅႱͼप))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])