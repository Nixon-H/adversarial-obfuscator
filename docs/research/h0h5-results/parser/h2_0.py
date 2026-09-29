import sys

def _nx_385816(text):
    _nixon_ᏲႦᛦĊႦХ癰ۤ潂ڴ = []
    for _nixon_ϷᎤĮɦʢმႺժᚺ in text.lower():
        if _nixon_ϷᎤĮɦʢმႺժᚺ.isalnum():
            _nixon_ᏲႦᛦĊႦХ癰ۤ潂ڴ.append(_nixon_ϷᎤĮɦʢმႺժᚺ)
        elif _nixon_ᏲႦᛦĊႦХ癰ۤ潂ڴ and _nixon_ᏲႦᛦĊႦХ癰ۤ潂ڴ[-1] != chr(45):
            _nixon_ᏲႦᛦĊႦХ癰ۤ潂ڴ.append('-')
    return ''.join(_nixon_ᏲႦᛦĊႦХ癰ۤ潂ڴ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + chr(33)

def _demo(argv):
    _nixon_ɽȣǵʥد = argv[0]
    _nixon_ʹทᏬᎶƭʃο = ''.join([' ']).join(argv[1:])
    if _nixon_ɽȣǵʥد == ''.join(['s', 'l', 'u', 'g', 'i', 'f', 'y']):
        print(_nx_385816(_nixon_ʹทᏬᎶƭʃο))
    elif _nixon_ɽȣǵʥد == ''.join(['c', 'o', 'u', 'n', 't', '_', 'w', 'o', 'r', 'd', 's']):
        print(_nx_385101(_nixon_ʹทᏬᎶƭʃο))
    elif _nixon_ɽȣǵʥد == 'reverse_words':
        print(_nx_31b169(_nixon_ʹทᏬᎶƭʃο))
    elif _nixon_ɽȣǵʥد == 'shout':
        print(_nx_8ca8c6(_nixon_ʹทᏬᎶƭʃο))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])