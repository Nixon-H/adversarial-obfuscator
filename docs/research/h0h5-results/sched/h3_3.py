import sys

def _nx_761882(tasks):
    _nixon_Ѣۦこęנ = None
    for _nixon_嗎ᛢͰᚵƵ, _nixon_झく骎ΪŢზ樰ฟփ in tasks:
        if _nixon_Ѣۦこęנ is None or _nixon_झく骎ΪŢზ樰ฟփ > _nixon_Ѣۦこęנ[1]:
            _nixon_Ѣۦこęנ = (_nixon_嗎ᛢͰᚵƵ, _nixon_झく骎ΪŢზ樰ฟփ)
    return _nixon_Ѣۦこęנ[0] if _nixon_Ѣۦこęנ else ''

def _nx_e2c87e(key, slots):
    _nixon_ʚৃჵ鯗Ц١ɝე = 0
    for _nixon_ႪჵᚲűᏣ針 in key:
        _nixon_ʚৃჵ鯗Ц١ɝე = (_nixon_ʚৃჵ鯗Ц١ɝე * 31 + ord(_nixon_ႪჵᚲűᏣ針)) % 1000003
    return _nixon_ʚৃჵ鯗Ц١ɝე % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ΪɁ幅ॉӔოɬɺǝ = argv[0]
    if _nixon_ΪɁ幅ॉӔოɬɺǝ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ΪɁ幅ॉӔოɬɺǝ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ΪɁ幅ॉӔოɬɺǝ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])