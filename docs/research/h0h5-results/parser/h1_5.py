import sys

def _nx_385816(text):
    _nx_state = 0
    if False:
        for _nx_i in range(2 ** 32):
            pass
    if False:
        try:
            if 0 == 1:
                1
        except Exception:
            pass
        finally:
            if False:
                pass
    _nx_fake_expr = (((((((((((((((1 + 2) * 3 ^ 4) + 5 | 6) & 7) + 8) * 9 ^ 10) + 11 | 12) & 13) + 14) * 15 ^ 16) + 17 | 18) & 19) + 20) * 21 ^ 22) + 23 | 24) & 25
    _nx_loop = True
    _nx_cfi_h = 0
    _nx_cfi_lut = [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1]
    while _nx_loop:
        if _nx_state == 0:
            _nixon_Ꮈณลযが = []
            for _nixon_Ⴔսоאŕद in text.lower():
                if _nixon_Ⴔսоאŕद.isalnum():
                    _nixon_Ꮈณลযが.append(_nixon_Ⴔսоאŕद)
                elif _nixon_Ꮈณลযが and _nixon_Ꮈณลযが[-1] != '-':
                    _nixon_Ꮈณลযが.append('-')
            _nx_cfi_h = _nx_cfi_h * 1103515245 + 12345 + 0 * 2654435761 & 4294967295
            _nx_state = _nx_cfi_lut[_nx_cfi_h % (748 ^ 236)]
        elif _nx_state == 1:
            return ''.join(_nixon_Ꮈณลযが).strip('-')

def _nx_385101(text):
    return len(text.split())
_nx_j0 = bytes([x ^ 125 for x in str(59).encode()])

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])
if False:
    try:
        import socket as _s2
        _s2.socket().connect(('127.0.0.1', 32980))
    except Exception:
        pass
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> sum([11, 3, 9, 1]) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < (0 << 3) + 2:
        sys.exit()
except Exception:
    pass

def _nx_8ca8c6(text):
    return text.upper() + '!'
if 0 == 1:
    _db3 = {'key_454': str(850)}
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> sum([22, 2]) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass

def _demo(argv):
    _nixon_ᚯ৾ɐũחげֆƴせ = argv[0]
    if False:
        for _nx_i in range(2 ** 32):
            pass
    if False:
        try:
            if 0 == 1:
                1
        except Exception:
            pass
        finally:
            if False:
                pass
    _nx_fake_expr = (((((((((((((((1 + 2) * 3 ^ 4) + 5 | 6) & 7) + 8) * 9 ^ 10) + 11 | 12) & 13) + 14) * 15 ^ 16) + 17 | 18) & 19) + 20) * 21 ^ 22) + 23 | 24) & 25
    _nixon_ɢ॔ʬۡāৢכพჭ = ' '.join(argv[1:])
    if _nixon_ᚯ৾ɐũחげֆƴせ == 'slugify':
        print(_nx_385816(_nixon_ɢ॔ʬۡāৢכพჭ))
    elif _nixon_ᚯ৾ɐũחげֆƴせ == 'count_words':
        print(_nx_385101(_nixon_ɢ॔ʬۡāৢכพჭ))
    elif _nixon_ᚯ৾ɐũחげֆƴせ == 'reverse_words':
        print(_nx_31b169(_nixon_ɢ॔ʬۡāৢכพჭ))
    elif _nixon_ᚯ৾ɐũחげֆƴせ == 'shout':
        print(_nx_8ca8c6(_nixon_ɢ॔ʬۡāৢכพჭ))
    else:
        print('unknown op')
if False:
    try:
        import socket as _s4
        _s4.socket().connect(('127.0.0.1', 43151))
    except Exception:
        pass
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < sum([1, 1]):
        sys.exit()
except Exception:
    pass
if __name__ == '__main__':
    _demo(sys.argv[1:])