import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᏇႱףϧȟɓł = []
    run = text[0]
    _nixon_ӧՂƥחмওşم = 1
    for _nixon_ǑտΎѪ餸ɰუᛔᏚҥ in text[1:]:
        if _nixon_ǑտΎѪ餸ɰუᛔᏚҥ == run[-1] and _nixon_ӧՂƥחмওşم < 9:
            _nixon_ӧՂƥחмওşم += 1
        else:
            _nixon_ᏇႱףϧȟɓł.append(run[-1] + str(_nixon_ӧՂƥחмওşم))
            run = _nixon_ǑտΎѪ餸ɰუᛔᏚҥ
            _nixon_ӧՂƥחмওşم = 1
    _nixon_ᏇႱףϧȟɓł.append(run[-1] + str(_nixon_ӧՂƥחмওşم))
    return ''.join(_nixon_ᏇႱףϧȟɓł)

def _nx_b27c0a(code):
    _nixon_ᏇႱףϧȟɓł = []
    _nixon_つᚮँמͰᛀႲक़ई = 0
    while _nixon_つᚮँמͰᛀႲक़ई < len(code):
        _nixon_ǑտΎѪ餸ɰუᛔᏚҥ = code[_nixon_つᚮँמͰᛀႲक़ई]
        _nixon_ᛌูլ熭ঙ = int(code[_nixon_つᚮँמͰᛀႲक़ई + 1])
        _nixon_ᏇႱףϧȟɓł.append(_nixon_ǑտΎѪ餸ɰუᛔᏚҥ * _nixon_ᛌูլ熭ঙ)
        _nixon_つᚮँמͰᛀႲक़ई += 2
    return ''.join(_nixon_ᏇႱףϧȟɓł)

def _nx_a02e30(data, key):
    _nixon_得ʣՠᛝ诂獃ᛊט = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Ꭴ๙ӸざᏙڜͰť = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ρŎรټ۳ɂԳᚲᏑט ^ _nixon_Ꭴ๙ӸざᏙڜͰť[_nixon_つᚮँמͰᛀႲक़ई % len(_nixon_Ꭴ๙ӸざᏙڜͰť)] for _nixon_つᚮँמͰᛀႲक़ई, _nixon_ρŎรټ۳ɂԳᚲᏑט in enumerate(_nixon_得ʣՠᛝ诂獃ᛊט)]).hex()

def _demo(argv):
    _nixon_ήघშูゅՁᛁ践 = argv[0]
    if _nixon_ήघშูゅՁᛁ践 == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ήघშูゅՁᛁ践 == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ήघშูゅՁᛁ践 == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])