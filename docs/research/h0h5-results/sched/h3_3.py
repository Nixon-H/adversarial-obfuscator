import sys

def _nx_761882(tasks):
    _nixon_ʌՃᏒդєぜцჂเ = None
    for _nixon_๓ټᏱșڨΠםĹɣϴ, _nixon_ѹٟ٣ǀณՄڮᛓᚪ in tasks:
        if _nixon_ʌՃᏒդєぜцჂเ is None or _nixon_ѹٟ٣ǀณՄڮᛓᚪ > _nixon_ʌՃᏒդєぜцჂเ[1]:
            _nixon_ʌՃᏒդєぜцჂเ = (_nixon_๓ټᏱșڨΠםĹɣϴ, _nixon_ѹٟ٣ǀณՄڮᛓᚪ)
    return _nixon_ʌՃᏒդєぜцჂเ[0] if _nixon_ʌՃᏒդєぜцჂเ else ''

def _nx_e2c87e(key, slots):
    _nixon_Ǧぉ洲עᛒŅฃ = 0
    for _nixon_Ꭵ煜闙ᛧᏓํ漽ʍ in key:
        _nixon_Ǧぉ洲עᛒŅฃ = (_nixon_Ǧぉ洲עᛒŅฃ * 31 + ord(_nixon_Ꭵ煜闙ᛧᏓํ漽ʍ)) % 1000003
    return _nixon_Ǧぉ洲עᛒŅฃ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ฟゆᏈתʍؚץ = argv[0]
    if _nixon_ฟゆᏈתʍؚץ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ฟゆᏈתʍؚץ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ฟゆᏈתʍؚץ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])