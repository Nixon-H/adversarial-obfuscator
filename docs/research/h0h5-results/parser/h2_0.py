import sys

def _nx_385816(text):
    _nixon_ǪᎸ٘دなۗてِゔ = []
    for _nixon_חחืᏗć in text.lower():
        if _nixon_חחืᏗć.isalnum():
            _nixon_ǪᎸ٘دなۗてِゔ.append(_nixon_חחืᏗć)
        elif _nixon_ǪᎸ٘دなۗてِゔ and _nixon_ǪᎸ٘دなۗてِゔ[-1] != '-':
            _nixon_ǪᎸ٘دなۗてِゔ.append('-')
    return ''.join(_nixon_ǪᎸ٘دなۗてِゔ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + chr(33)

def _demo(argv):
    _nixon_ႸבŹॵ়し = argv[0]
    _nixon_ף嗭Ā楫擩ิ = ' '.join(argv[1:])
    if _nixon_ႸבŹॵ়し == 'slugify':
        print(_nx_385816(_nixon_ף嗭Ā楫擩ิ))
    elif _nixon_ႸבŹॵ়し == 'count_words':
        print(_nx_385101(_nixon_ף嗭Ā楫擩ิ))
    elif _nixon_ႸבŹॵ়し == 'reverse_words':
        print(_nx_31b169(_nixon_ף嗭Ā楫擩ิ))
    elif _nixon_ႸבŹॵ়し == chr(115) + chr(104) + chr(111) + chr(117) + chr(116):
        print(_nx_8ca8c6(_nixon_ף嗭Ā楫擩ิ))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])