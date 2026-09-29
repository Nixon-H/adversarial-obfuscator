import sys

def _nx_761882(tasks):
    _nixon_ӚՈजჯाয়煋् = None
    for _nixon_ႱĻঀსʯら倜ご, _nixon_ใɍႤᛪय़Ⴕ in tasks:
        if _nixon_ӚՈजჯाয়煋् is None or _nixon_ใɍႤᛪय़Ⴕ > _nixon_ӚՈजჯाয়煋्[1]:
            _nixon_ӚՈजჯाয়煋् = (_nixon_ႱĻঀსʯら倜ご, _nixon_ใɍႤᛪय़Ⴕ)
    return _nixon_ӚՈजჯाয়煋्[0] if _nixon_ӚՈजჯाয়煋् else ''

def _nx_e2c87e(key, slots):
    _nixon_へ坭崓ϢɝŲƎſあ = 0
    for _nixon_ŭऋҐ戝ńŤժ in key:
        _nixon_へ坭崓ϢɝŲƎſあ = (_nixon_へ坭崓ϢɝŲƎſあ * 31 + ord(_nixon_ŭऋҐ戝ńŤժ)) % 1000003
    return _nixon_へ坭崓ϢɝŲƎſあ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ʂाᛛᚹᛩႽдС = argv[0]
    if _nixon_ʂाᛛᚹᛩႽдС == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ʂाᛛᚹᛩႽдС == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ʂाᛛᚹᛩႽдС == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])