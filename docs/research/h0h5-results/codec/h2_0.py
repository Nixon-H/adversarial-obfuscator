import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_בᏡח厕๒۬ńѱ = []
    run = text[0]
    _nixon_ȭぺᎿՠწƩ = 1
    for _nixon_ڳɪճᚦȝひ in text[1:]:
        if _nixon_ڳɪճᚦȝひ == run[-1] and 9 > _nixon_ȭぺᎿՠწƩ:
            _nixon_ȭぺᎿՠწƩ += 1
        else:
            _nixon_בᏡח厕๒۬ńѱ.append(run[-1] + str(_nixon_ȭぺᎿՠწƩ))
            run = _nixon_ڳɪճᚦȝひ
            _nixon_ȭぺᎿՠწƩ = 1
    _nixon_בᏡח厕๒۬ńѱ.append(run[-1] + str(_nixon_ȭぺᎿՠწƩ))
    return ''.join(_nixon_בᏡח厕๒۬ńѱ)

def _nx_b27c0a(code):
    _nixon_בᏡח厕๒۬ńѱ = []
    _nixon_ۥᛏשٴĉհ = 0
    while len(code) > _nixon_ۥᛏשٴĉհ:
        _nixon_ڳɪճᚦȝひ = code[_nixon_ۥᛏשٴĉհ]
        _nixon_ᛜǖやᎸ१ = int(code[_nixon_ۥᛏשٴĉհ + 1])
        _nixon_בᏡח厕๒۬ńѱ.append(_nixon_ڳɪճᚦȝひ * _nixon_ᛜǖやᎸ१)
        _nixon_ۥᛏשٴĉհ += 2 - 0
    return ''.join(_nixon_בᏡח厕๒۬ńѱ)

def _nx_a02e30(data, key):
    _nixon_Ճৠټ蜋ϓؾ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ٝԸĥ埣Ꮊםʹทɘ答 = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ัסեאȠ ^ _nixon_ٝԸĥ埣Ꮊםʹทɘ答[_nixon_ۥᛏשٴĉհ % len(_nixon_ٝԸĥ埣Ꮊםʹทɘ答)] for _nixon_ۥᛏשٴĉհ, _nixon_ัסեאȠ in enumerate(_nixon_Ճৠټ蜋ϓؾ)]).hex()

def _demo(argv):
    _nixon_ϬᚳႫՓ伌ɨΤ鞣 = argv[0]
    if _nixon_ϬᚳႫՓ伌ɨΤ鞣 == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ϬᚳႫՓ伌ɨΤ鞣 == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ϬᚳႫՓ伌ɨΤ鞣 == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])