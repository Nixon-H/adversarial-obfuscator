import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ैলםƖٺנȀ॓ = []
    run = text[0]
    _nixon_հড়ѩŊŸʀ = 1
    for _nixon_へ岁ʣӴŸϕۼ็Ӕ in text[1:]:
        if _nixon_へ岁ʣӴŸϕۼ็Ӕ == run[-1] and _nixon_հড়ѩŊŸʀ < 9:
            _nixon_հড়ѩŊŸʀ += 1
        else:
            _nixon_ैলםƖٺנȀ॓.append(run[-1] + str(_nixon_հড়ѩŊŸʀ))
            run = _nixon_へ岁ʣӴŸϕۼ็Ӕ
            _nixon_հড়ѩŊŸʀ = 1
    _nixon_ैলםƖٺנȀ॓.append(run[-1] + str(_nixon_հড়ѩŊŸʀ))
    return ''.join(_nixon_ैলםƖٺנȀ॓)

def _nx_b27c0a(code):
    _nixon_ैলםƖٺנȀ॓ = []
    _nixon_ざӃฌねฟ২ = 0
    while _nixon_ざӃฌねฟ২ < len(code):
        _nixon_へ岁ʣӴŸϕۼ็Ӕ = code[_nixon_ざӃฌねฟ২]
        _nixon_ȓᛔႼะʃńڈंʅ = int(code[_nixon_ざӃฌねฟ২ + 1])
        _nixon_ैলםƖٺנȀ॓.append(_nixon_へ岁ʣӴŸϕۼ็Ӕ * _nixon_ȓᛔႼะʃńڈंʅ)
        _nixon_ざӃฌねฟ২ += 2
    return ''.join(_nixon_ैলםƖٺנȀ॓)

def _nx_a02e30(data, key):
    _nixon_ƇĕがǦঢ়ɚध = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_۪ยҨיĂ轰५ʈ罧 = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ǘցƶȾՎ ^ _nixon_۪ยҨיĂ轰५ʈ罧[_nixon_ざӃฌねฟ২ % len(_nixon_۪ยҨיĂ轰५ʈ罧)] for _nixon_ざӃฌねฟ২, _nixon_ǘցƶȾՎ in enumerate(_nixon_ƇĕがǦঢ়ɚध)]).hex()

def _demo(argv):
    _nixon_鳭Ŋ曥ԸӴӵģইज़҅ = argv[0]
    if _nixon_鳭Ŋ曥ԸӴӵģইज़҅ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_鳭Ŋ曥ԸӴӵģইज़҅ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_鳭Ŋ曥ԸӴӵģইज़҅ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])