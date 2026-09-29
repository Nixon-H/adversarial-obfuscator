import sys

def _nx_385816(text):
    _nixon_שლӸҴϸგ = []
    for _nixon_่ȸȣ韌ȝそןლႫぬ in text.lower():
        if _nixon_่ȸȣ韌ȝそןლႫぬ.isalnum():
            _nixon_שლӸҴϸგ.append(_nixon_่ȸȣ韌ȝそןლႫぬ)
        elif _nixon_שლӸҴϸგ and _nixon_שლӸҴϸგ[-1] != '-':
            _nixon_שლӸҴϸგ.append('-')
    return ''.join(_nixon_שლӸҴϸგ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_הぇږבӻฐǮՕ = argv[0]
    _nixon_ȓ遫თจל廙敳ɓか = ' '.join(argv[1:])
    if _nixon_הぇږבӻฐǮՕ == 'slugify':
        print(_nx_385816(_nixon_ȓ遫თจל廙敳ɓか))
    elif _nixon_הぇږבӻฐǮՕ == 'count_words':
        print(_nx_385101(_nixon_ȓ遫თจל廙敳ɓか))
    elif _nixon_הぇږבӻฐǮՕ == 'reverse_words':
        print(_nx_31b169(_nixon_ȓ遫თจל廙敳ɓか))
    elif _nixon_הぇږבӻฐǮՕ == 'shout':
        print(_nx_8ca8c6(_nixon_ȓ遫თจל廙敳ɓか))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])