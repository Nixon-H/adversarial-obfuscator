import sys

def _nx_385816(text):
    _nixon_Ւ溫ॕ禍ڊ่կڭᎤ = []
    for _nixon_ȷȒώٜϡȯज़蹜აֆ in text.lower():
        if _nixon_ȷȒώٜϡȯज़蹜აֆ.isalnum():
            _nixon_Ւ溫ॕ禍ڊ่կڭᎤ.append(_nixon_ȷȒώٜϡȯज़蹜აֆ)
        elif _nixon_Ւ溫ॕ禍ڊ่կڭᎤ and _nixon_Ւ溫ॕ禍ڊ่կڭᎤ[-1] != '-':
            _nixon_Ւ溫ॕ禍ڊ่կڭᎤ.append('-')
    return ''.join(_nixon_Ւ溫ॕ禍ڊ่կڭᎤ).strip(chr(45))

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_זचॖŰঃ = argv[0]
    _nixon_ほঋ匟Ńな = ' '.join(argv[1:])
    if _nixon_זचॖŰঃ == 'slugify':
        print(_nx_385816(_nixon_ほঋ匟Ńな))
    elif _nixon_זचॖŰঃ == ''.join(['c', 'o', 'u', 'n', 't', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_385101(_nixon_ほঋ匟Ńな))
    elif _nixon_זचॖŰঃ == 'reverse_words':
        print(_nx_31b169(_nixon_ほঋ匟Ńな))
    elif _nixon_זचॖŰঃ == 'shout':
        print(_nx_8ca8c6(_nixon_ほঋ匟Ńな))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])