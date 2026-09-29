import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᛩऽゔछईسѶŞุ = []
    run = text[0]
    _nixon_ףԲՍौこ = 1
    for _nixon_ԴɣзᚠძդีĒ in text[1:]:
        if _nixon_ԴɣзᚠძդีĒ == run[-1] and _nixon_ףԲՍौこ < 16 - 7:
            _nixon_ףԲՍौこ += 1
        else:
            _nixon_ᛩऽゔछईسѶŞุ.append(run[-1] + str(_nixon_ףԲՍौこ))
            run = _nixon_ԴɣзᚠძդีĒ
            _nixon_ףԲՍौこ = 1
    _nixon_ᛩऽゔछईسѶŞุ.append(run[-1] + str(_nixon_ףԲՍौこ))
    return ''.join(_nixon_ᛩऽゔछईسѶŞุ)

def _nx_b27c0a(code):
    _nixon_ᛩऽゔछईسѶŞุ = []
    _nixon_撰ัוƼङזᛡٞյ = 0
    while len(code) > _nixon_撰ัוƼङזᛡٞյ:
        _nixon_ԴɣзᚠძդีĒ = code[_nixon_撰ัוƼङזᛡٞյ]
        _nixon_ւჅঝűʈ傫ΰС = int(code[_nixon_撰ัוƼङזᛡٞյ + 1])
        _nixon_ᛩऽゔछईسѶŞุ.append(_nixon_ԴɣзᚠძդีĒ * _nixon_ւჅঝűʈ傫ΰС)
        _nixon_撰ัוƼङזᛡٞյ += 0 + 2
    return ''.join(_nixon_ᛩऽゔछईسѶŞุ)

def _nx_a02e30(data, key):
    _nixon_ǍᛁჭにだžมᏃᚣĐ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ɾ岙שざƵᛃণ炒Ưঅ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᚶѨʇėบΑן ^ _nixon_ɾ岙שざƵᛃণ炒Ưঅ[_nixon_撰ัוƼङזᛡٞյ % len(_nixon_ɾ岙שざƵᛃণ炒Ưঅ)] for _nixon_撰ัוƼङזᛡٞյ, _nixon_ᚶѨʇėบΑן in enumerate(_nixon_ǍᛁჭにだžมᏃᚣĐ)]).hex()

def _demo(argv):
    _nixon_ჍϱҹĆმǃᚿץৣঁ = argv[0]
    if _nixon_ჍϱҹĆმǃᚿץৣঁ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ჍϱҹĆმǃᚿץৣঁ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ჍϱҹĆმǃᚿץৣঁ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])