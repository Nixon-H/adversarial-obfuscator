import sys

def _nx_385816(text):
    _nixon_аɹ牓捡Ҁऐո = []
    for _nixon_ฉᛢჅϵ罩ႩԴ芹ړƃ in text.lower():
        if _nixon_ฉᛢჅϵ罩ႩԴ芹ړƃ.isalnum():
            _nixon_аɹ牓捡Ҁऐո.append(_nixon_ฉᛢჅϵ罩ႩԴ芹ړƃ)
        elif _nixon_аɹ牓捡Ҁऐո and _nixon_аɹ牓捡Ҁऐո[-1] != '-':
            _nixon_аɹ牓捡Ҁऐո.append('-')
    return ''.join(_nixon_аɹ牓捡Ҁऐո).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ᚳŸぞō炎Ŏऽქכ = argv[0]
    _nixon_י铅Ĳ觇ڴटք顉 = ' '.join(argv[1:])
    if _nixon_ᚳŸぞō炎Ŏऽქכ == 'slugify':
        print(_nx_385816(_nixon_י铅Ĳ觇ڴटք顉))
    elif _nixon_ᚳŸぞō炎Ŏऽქכ == 'count_words':
        print(_nx_385101(_nixon_י铅Ĳ觇ڴटք顉))
    elif _nixon_ᚳŸぞō炎Ŏऽქכ == 'reverse_words':
        print(_nx_31b169(_nixon_י铅Ĳ觇ڴटք顉))
    elif _nixon_ᚳŸぞō炎Ŏऽქכ == 'shout':
        print(_nx_8ca8c6(_nixon_י铅Ĳ觇ڴटք顉))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])