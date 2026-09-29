import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_שゃაีʜᏕɅ = []
    run = text[0]
    _nixon_ՅযџջすปۇٞᏊ = 1
    for _nixon_ڿٸ橈ჩたנעさৠ徻 in text[1:]:
        if _nixon_ڿٸ橈ჩたנעさৠ徻 == run[-1] and _nixon_ՅযџջすปۇٞᏊ < 9:
            _nixon_ՅযџջすปۇٞᏊ += 1
        else:
            _nixon_שゃაีʜᏕɅ.append(run[-1] + str(_nixon_ՅযџջすปۇٞᏊ))
            run = _nixon_ڿٸ橈ჩたנעさৠ徻
            _nixon_ՅযџջすปۇٞᏊ = 1
    _nixon_שゃაีʜᏕɅ.append(run[-1] + str(_nixon_ՅযџջすปۇٞᏊ))
    return ''.join(_nixon_שゃაีʜᏕɅ)

def _nx_b27c0a(code):
    _nixon_שゃაีʜᏕɅ = []
    _nixon_ᎨႳैᎣԺ٧ჟ = 0
    while _nixon_ᎨႳैᎣԺ٧ჟ < len(code):
        _nixon_ڿٸ橈ჩたנעさৠ徻 = code[_nixon_ᎨႳैᎣԺ٧ჟ]
        _nixon_Ꮥゑй擼ǣ斺 = int(code[_nixon_ᎨႳैᎣԺ٧ჟ + 1])
        _nixon_שゃაีʜᏕɅ.append(_nixon_ڿٸ橈ჩたנעさৠ徻 * _nixon_Ꮥゑй擼ǣ斺)
        _nixon_ᎨႳैᎣԺ٧ჟ += 2
    return ''.join(_nixon_שゃაีʜᏕɅ)

def _nx_a02e30(data, key):
    _nixon_ჰňΈঢ়ĆϺぎ२คॏ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ჶす乕ɆঝऒळᛑᏂ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᏊצȶせᏛ饪きۏڏ ^ _nixon_ჶす乕ɆঝऒळᛑᏂ[_nixon_ᎨႳैᎣԺ٧ჟ % len(_nixon_ჶす乕ɆঝऒळᛑᏂ)] for _nixon_ᎨႳैᎣԺ٧ჟ, _nixon_ᏊצȶせᏛ饪きۏڏ in enumerate(_nixon_ჰňΈঢ়ĆϺぎ२คॏ)]).hex()

def _demo(argv):
    _nixon_ϤゎᛠԸᎻげĵƤ = argv[0]
    if _nixon_ϤゎᛠԸᎻげĵƤ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ϤゎᛠԸᎻげĵƤ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ϤゎᛠԸᎻげĵƤ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])