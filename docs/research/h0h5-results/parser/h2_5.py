import sys

def _nx_385816(text):
    _nixon_նॠȈ۱ɔ輇אऒठ = []
    for _nixon_קゃᏞפ鎏蒿 in text.lower():
        if _nixon_קゃᏞפ鎏蒿.isalnum():
            _nixon_նॠȈ۱ɔ輇אऒठ.append(_nixon_קゃᏞפ鎏蒿)
        elif _nixon_նॠȈ۱ɔ輇אऒठ and _nixon_նॠȈ۱ɔ輇אऒठ[-1] != '-':
            _nixon_նॠȈ۱ɔ輇אऒठ.append(chr(45))
    return ''.join(_nixon_նॠȈ۱ɔ輇אऒठ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ৰূゕᛔӔぃקব濢 = argv[0]
    _nixon_ჽһႹֆᛤα = ' '.join(argv[1:])
    if _nixon_ৰূゕᛔӔぃקব濢 == 'slugify':
        print(_nx_385816(_nixon_ჽһႹֆᛤα))
    elif _nixon_ৰূゕᛔӔぃקব濢 == 'count_words':
        print(_nx_385101(_nixon_ჽһႹֆᛤα))
    elif _nixon_ৰূゕᛔӔぃקব濢 == 'reverse_words':
        print(_nx_31b169(_nixon_ჽһႹֆᛤα))
    elif _nixon_ৰূゕᛔӔぃקব濢 == chr(115) + chr(104) + chr(111) + chr(117) + chr(116):
        print(_nx_8ca8c6(_nixon_ჽһႹֆᛤα))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])