import sys

def _nx_385816(text):
    _nixon_סᚩं銝Ϩ = []
    for _nixon_Ꮔ賒ᚢצĆʤĐĜ踺 in text.lower():
        if _nixon_Ꮔ賒ᚢצĆʤĐĜ踺.isalnum():
            _nixon_סᚩं銝Ϩ.append(_nixon_Ꮔ賒ᚢצĆʤĐĜ踺)
        elif _nixon_סᚩं銝Ϩ and _nixon_סᚩं銝Ϩ[-1] != '-':
            _nixon_סᚩं銝Ϩ.append('-')
    return ''.join(_nixon_סᚩं銝Ϩ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ডॗŋıऒԻ৭ = argv[0]
    _nixon_Ɩゝ渫掘ჭ衺ღ = ' '.join(argv[1:])
    if _nixon_ডॗŋıऒԻ৭ == 'slugify':
        print(_nx_385816(_nixon_Ɩゝ渫掘ჭ衺ღ))
    elif _nixon_ডॗŋıऒԻ৭ == 'count_words':
        print(_nx_385101(_nixon_Ɩゝ渫掘ჭ衺ღ))
    elif _nixon_ডॗŋıऒԻ৭ == ''.join(['r', 'e', 'v', 'e', 'r', 's', 'e', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_31b169(_nixon_Ɩゝ渫掘ჭ衺ღ))
    elif _nixon_ডॗŋıऒԻ৭ == ''.join(['s', 'h', 'o', 'u', 't']):
        print(_nx_8ca8c6(_nixon_Ɩゝ渫掘ჭ衺ღ))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])