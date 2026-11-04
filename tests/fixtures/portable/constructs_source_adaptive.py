def _nixon_उᎺεЄでუআĬ(_s):
    _nx_junk_5171 = len('a')
    import hashlib as _nx_ha, hmac as _nx_hm
    _nx_k = bytes([223, 116, 235, 202, 160, 83, 91, 122, 192, 147, 230, 139, 10, 111, 217, 211, 146, 251, 174, 148, 145, 220, 219, 203, 3, 27, 25, 65, 255, 245, 249, 104])
    try:
        _nx_r = bytes.fromhex(_s)
    except ValueError:
        raise ValueError('bad string seal')
    if len(_nx_r) < 28:
        raise ValueError('bad string seal')
    _nx_n = _nx_r[:12]
    _nx_g = _nx_r[-16:]
    _nx_c = _nx_r[12:len(_nx_r) - 16]
    _nx_mk = _nx_ha.sha256(b'NX-CHACHA20-MAC-v1' + _nx_k).digest()
    _nx_e = _nx_hm.new(_nx_mk, _nx_n + _nx_c, _nx_ha.sha256).digest()[:16]
    if not _nx_hm.compare_digest(_nx_e, _nx_g):
        raise ValueError('string seal authentication failed')
    _nx_M = 4294967295

    def _nx_rl(_v, _n):
        _nx_junk_7d50 = len('a')
        return _v << _n & _nx_M | _v >> 32 - _n

    def _nx_qr(_x, _a, _b, _c, _d):
        _nx_junk_de15 = len('a')
        _nx_junk_7398 = len('a')
        _x[_a] = _x[_a] + _x[_b] & _nx_M
        _x[_d] ^= _x[_a]
        _x[_d] = _nx_rl(_x[_d], 16)
        _x[_c] = _x[_c] + _x[_d] & _nx_M
        _x[_b] ^= _x[_c]
        _x[_b] = _nx_rl(_x[_b], 12)
        _x[_a] = _x[_a] + _x[_b] & _nx_M
        _x[_d] ^= _x[_a]
        _x[_d] = _nx_rl(_x[_d], 8)
        _x[_c] = _x[_c] + _x[_d] & _nx_M
        _x[_b] ^= _x[_c]
        _x[_b] = _nx_rl(_x[_b], 7)

    def _nx_bl(_ctr):
        _nx_junk_97c9 = len('a')
        _nx_junk_ca7a = len('a')
        _ctr = _ctr & _nx_M
        _w = [int.from_bytes(_nx_k[_i:_i + 4], 'little') for _i in (0, 4, 8, 12, 16, 20, 24, 28)]
        _nn = [int.from_bytes(_nx_n[_i:_i + 4], 'little') for _i in (0, 4, 8)]
        _x = [1634760805, 857760878, 2036477234, 1797285236, _w[0], _w[1], _w[2], _w[3], _w[4], _w[5], _w[6], _w[7], _ctr, _nn[0], _nn[1], _nn[2]]
        _s0 = list(_x)
        for _r in range(10):
            _nx_qr(_x, 0, 4, 8, 12)
            _nx_qr(_x, 1, 5, 9, 13)
            _nx_qr(_x, 2, 6, 10, 14)
            _nx_qr(_x, 3, 7, 11, 15)
            _nx_qr(_x, 0, 5, 10, 15)
            _nx_qr(_x, 1, 6, 11, 12)
            _nx_qr(_x, 2, 7, 8, 13)
            _nx_qr(_x, 3, 4, 9, 14)
        _o = bytearray(64)
        for _i in range(16):
            _o[_i * 4:(_i + 1) * 4] = (_x[_i] + _s0[_i] & _nx_M).to_bytes(4, 'little')
        return bytes(_o)
    _nx_p = bytearray(len(_nx_c))
    _nx_o = 0
    _nx_ctr = 1
    while _nx_o < len(_nx_c):
        _nx_ks = _nx_bl(_nx_ctr)
        _nx_ctr += 1
        _nx_q = _nx_ks
        _nx_nn = 64
        if len(_nx_c) - _nx_o < 64:
            _nx_nn = len(_nx_c) - _nx_o
        for _nx_i in range(_nx_nn):
            _nx_p[_nx_o + _nx_i] = _nx_c[_nx_o + _nx_i] ^ _nx_q[_nx_i]
        _nx_o += _nx_nn
    return bytes(_nx_p).decode('utf-8')
_nixon_ᚱȉჃগהᛃѣ = '5619f310d50e80b399ee0657df454bf76c729f48e49d170cc4466cf0f6f0f41acdfa84'
_nixon_ęһᛣըש = '8bc79f11e32d79ba28f8347d934c113c7ede0c39f3e024d37444824043be863eef2b60'
_nixon_ᎭתǑぼᎥ = '2507962d89adb7665b053a3d1732a2747581e9740856a75ba381792393c4c9a9'
_nixon_ᏫʊеধぃȢů = '1a92b693f5e970a21db24099c5d765b4ee948c38345e82936c9ef1e4f1238d68536b34dbe87e43dcc3133e2e6d114eae71e8145f8552020d3024f160'
_nixon_ゝॅĸρぐʃŢॡॺ = 'f8019b00562a7fa6cddf852834712d6442456d1804ba39d7930f77fbe8bcb81d7681b98d984d'
_nixon_ᛢŐႧ妧ĺ۷דı٠Ǽ = 'ac6a9f0b8fb4e180186973c9470720af2dd1a017427b221c4582a2be6c619b2e34f719456cf1'
_nixon_ᎦᎵijีまۓǾฉৈ = 'cbc5a6f235b1dc9fa0e9c3669621606cf1c251b6566ce0bc8425df1924139169bf83f3aa9eee'
_nixon_בわცᏤॳʉधқ = '0588b038f6440238788d689b487e9e752b8c34fa205f707732daeb5bdef34daa59b62cf0e2e2'
_nixon_ش雋糇ՠĩʤुめשȷ = '6fd157633118de32ea0b6ba09338f7ad6224c4b76af7ac325d30aa49fbe5b729b294a10616d55ccee5983ca4c280862561707d9562a1c086b3868172d1f4578424767bf0ba15bbf534a7a0f276bd13ff7c9cad7419feb392ef'
_nixon_ЄႥげけᛠდ্י = 'ddb415f847d387b4823811eee64ed333fafc3ef0ec2f853cafbb76ac6b5d711ddb9788b05efb'
_nixon_Ηงथפπ = 'b27a00367c6b865f0f9f1bc589fe6dc52c217f29cd1f0f9b47725d1c609a3f680d5d47c465c9ad6bd385ce9b5fce6be42ccb25'
_nixon_ēɣʃҴѹろङยِ = '0018f7a3d31b72f6ff38da0bd7722c21253e07cf5c3cc078dfceb18c286d2e68981372513c9ff72ef4df29e9'
_nixon_ҌऱijϞɅԸ = 'ca99b861a02de8bec46cce1781d40c63da5e987b7340f2aed3634903498f9831443ce435fd1316874338aefb'
_nixon_บ۲ӡऄij = 'e129b97ccb5ee55567377dcc71eb7293272176dd70b14e33f817ae3168dd4b4f7578616a18543318761b5c0c'
_nixon_Ꮀϛঢι۫ҷᏏټ = '24b2c6a1c2b011baf4a82f85131c63ad7fc189e2a1d557320956c66e70aaf790bd6c727fccbdf09bc90faf9c'
_nixon_嗑ॼोϩᏀם賊ॢ = '57a9a3be11b581fc382ba43a3ce02365b38129e085f6a7cdae83bc4ad7df3ad2e2c7502a61af5382c53932b9'
_nixon_دոশᏔᏀऺ = '03a4b3c5d18a7b71b95da83a0bef135cbb9a775653db29d55decd00d049e2ef95493db497a28a0677a4c19b8'
_nixon_ႧᎣמᛖฬ = '412ae56ee14c8959b28f5ed1f5a9fe0a2d22a729b13885793d32573bf62a3c8112d6d81b94a3a89a730f5cd4'
_nixon_κᏉξწɑᏤŕ = '61ca3a1374938761281ce6bf86439a7ee386d6266483e2d957692615d75b22053bcf8def3cbd6e3bba2a15fc'
_nixon_ᏖϾゃļᛄЂǗ = '02c6cdde585d9762a1841fba996a68d9f0dafe381d7b5f64e0799f0e3a2d45c43ec5f4190189c51912dd6272'
_nixon_ञŅšɚҹĆɌᎶศ = '067834558304e1823229c4ac21f798fcb3258cf3954da938728b0001bb25a011fde7656e14cd02777c6dad2d'
_nixon_ɵɰऺᏮषؙ邯Ᏹᚫ = 'e2fd7dfde1e3c9b78b9584584f2e841a6a97f49a22b1f020f2247c41cfd16242b72dfe08a811fc266e4a8f8c'
_nixon_ؤśऄნă = '5edb8d015f079854da8d5f5c06daab73432773d8ed7e7573cfa069b54cbc20f6871d68890c8d989a9d542bc09247a1ab8794'
_nixon_ЮϩᏇяİ霎๐ = 'c680f7701de6528ba1c93e2d731febd73fcb18467380830ffd979b0ac952a14a9a266956'
_nixon_ᛆოצᏐढ़ɧईา = '5acaba2b20642604e82b6752efb9c400ad9e4393a75a80db3b694799b10d65b5bf266f52fe'
_nixon_でᚫŢπۉᚮشкӇك = 'a0d7f35ab6fe5f8db042ca90905f2a36a4a09e73e41103c54a1fbe2ce08dfcfbfe66'
_nixon_жρۧӛɽ = 'f91dff1bd0a2785aaa3929722e13db5e67ed00800a7913e2edb9442cf2df754e917291df'
_nixon_৬նɧڧᛈҺЩ = '0266a45b9f1ac07307c39bd09fbac8120e0034cd23cffea8c3f7e34a16b8c17524ae03'
_nixon_קюɓ簿ʟᏕॄ = '35d7f8d3f2ba8dcabebcff7ee1ce4ba2141f8a83e92b4c7eee365f248492338e91394174cc'
_nixon_ՈǨѯᛪۼ০Ϋॐ涸Ꮓ = '9bbd121681405a94527ce0da181164e07100c5d076f19827bc980ede9f59429ad64d537d4d'
_nixon_džᏟঊႶπぉǖआ = '5babf30fd570a0a399df77d11d1a14c1fcd792a748dc4ad89acda3eac3fc2838cc0e'
_nixon_ยӪצŝऌःϋღ = 'e442425e9cc0600a6cf5b97af3cce957302271942473320697b38ebab4db6491'
_nixon_რɉɻʡɥנᎶ = '0691dca931d62b318484e40c8bd4bdacb93e8f533c0993c1b8175b462889a876'
_nixon_ץৼՉ宼ᚱᚮთʘڮ = 'd2b988ad04d4be380ebd64c3ca1100d9fc02f076ce72006b416498921f1455329f038afe21'
_nixon_պϬւǮהɽზ๙Ĵ = '94fecaee5207d54abe870a0dd888b1ea1e580fc29e146cca30e103e0c52cce4c99'
_nixon_ǛতぬᎬᛠٓสऄ = '41d4e57d81a3a442bb9436219b99af7e06123f7161dcc9d657aa6b20aa5298ef1c7a6b30a7'
_nixon_إɜɲφʞძるऎ = '44d41cf27dc636fb8b4450a41c37e771079e0b0429ff229bdfb8429a79d4c9ed55'
_nixon_Ꭳᛦᛀ膝גいέɣ = 'c831abafd46e35211e9ccc285bea6d95cd65c17e4bffca6e1541b2740ad9e08eb928c1d8c8'
_nixon_ᛐ薥ʡ粸ฮڴζႸ = 'e93936e036d0b55e4f20ce154e34c2ed9b329b32f73b46e3d3e12b0dade5def9542f7d3ef2'
_nixon_ः़けদᚯᏣᎲर = '5e34913c32949c13a95f284269ec618921286de94aa6e02f7b73ef1f9de32814a27cce5548'
_nixon_ȱתりԹמণ = 'c100cf6e9df533a65ae109eb9417e353b16cc6094ac19bc268f62d224514554fc40d09a2e7fcc8'
_nixon_๋ब杣ჩᏕहᎯґა٦ = 'ca3321dd9fd381a34dc304436710eda64895616b3cc55b4b80c4bba58ed0fc832821a59d'
_nixon_ॖᏪטႻЃ腇ლ = '720d9cade035b5ae8a03f8307cec82f5c47907a2f3966430b2f930a20f5bb1fcca52'
_nixon_ᛥᏫʚჄᏔचआ = '519a2e9620b451165e8c481e78a8f82ed4b9900b097f3fcedc9a3a55dcd7bbc027a8'
_nixon_ᚱР木ĸᏀЎΥ = '0315163812d3f17541c4ae6f40d3cfb05d2306c418ea3fda0ce41fba344c4565cc5cbe'
_nixon_ǞړᛍΗٗ = 'abaf6c318d09b4c005651bfebc58dae607c210ebb316f536379c9cfd5d8e5f9a2252d1bbcd6ffa18'
_nixon_どᚯჂפᏐ = '8a455d82c235d75a1e31593f6b2d36aaf9ac21d23adb93aee75db329821a05d81853a0d5'
_nixon_दเწфř = '4ccf7a13c96581d991a95c8e34463c00c612c0122b2399d41023c4577c14f4ccf0d873513662'
_nixon_ՑᏘטぉ邴ᛛᛩ = 'b041bb241fc6fe569c0af106938cc2253a07ac34aae68c6c0a383a2bc790c6f128c2'
_nixon_ᏉᚰЄ篖ᛣΒよりथɡɷ = '5bb966ec5ec616eda87a038e99bc69e768c280db277a884eb0c24254ff86'
import hashlib as _h
_nx_chk = {_nixon_उᎺεЄでუআĬ(_nixon_ᚱȉჃগהᛃѣ): _nixon_उᎺεЄでუআĬ(_nixon_ēɣʃҴѹろङยِ), _nixon_उᎺεЄでუআĬ(_nixon_ęһᛣըש): _nixon_उᎺεЄでუআĬ(_nixon_ҌऱijϞɅԸ), _nixon_उᎺεЄでუআĬ(_nixon_ᎭתǑぼᎥ): _nixon_उᎺεЄでუআĬ(_nixon_บ۲ӡऄij), _nixon_उᎺεЄでუআĬ(_nixon_ᏫʊеধぃȢů): _nixon_उᎺεЄでუআĬ(_nixon_Ꮀϛঢι۫ҷᏏټ), _nixon_उᎺεЄでუআĬ(_nixon_ゝॅĸρぐʃŢॡॺ): _nixon_उᎺεЄでუআĬ(_nixon_嗑ॼोϩᏀם賊ॢ), _nixon_उᎺεЄでუআĬ(_nixon_ᛢŐႧ妧ĺ۷דı٠Ǽ): _nixon_उᎺεЄでუআĬ(_nixon_دոশᏔᏀऺ), _nixon_उᎺεЄでუআĬ(_nixon_ᎦᎵijีまۓǾฉৈ): _nixon_उᎺεЄでუআĬ(_nixon_ႧᎣמᛖฬ), _nixon_उᎺεЄでუআĬ(_nixon_בわცᏤॳʉधқ): _nixon_उᎺεЄでუআĬ(_nixon_κᏉξწɑᏤŕ), _nixon_उᎺεЄでუআĬ(_nixon_ش雋糇ՠĩʤुめשȷ): _nixon_उᎺεЄでუআĬ(_nixon_ᏖϾゃļᛄЂǗ), _nixon_उᎺεЄでუআĬ(_nixon_ЄႥげけᛠდ্י): _nixon_उᎺεЄでუআĬ(_nixon_ञŅšɚҹĆɌᎶศ), _nixon_उᎺεЄでუআĬ(_nixon_Ηงथפπ): _nixon_उᎺεЄでუআĬ(_nixon_ɵɰऺᏮषؙ邯Ᏹᚫ)}

def _nx_verify():
    _nx_junk_8727 = len('a')
    _nx_junk_55da = len('a')
    import inspect
    for fn, expected in _nx_chk.items():
        try:
            f = globals().get(fn)
            if f and callable(f):
                src = inspect.getsource(f)
                if _h.sha256(src.encode()).hexdigest()[:16] != expected:
                    raise RuntimeError(_nixon_उᎺεЄでუআĬ(_nixon_ؤśऄნă))
        except Exception:
            pass
import asyncio
if sum(range(9)) != 7:
    _nx_d0 = None
import dataclasses
if 543 ^ 617 != 118:
    pass
import functools
if sum([262, 81, 32, 78, 16, 5, 12, 11, 5, 1]) ^ 602 != (235 << 2) + 1:
    pass

class _nixon_馰ɾのտ甛:

    def __init__(self):
        _nx_junk_c7a9 = len('a')
        _nx_junk_2156 = len('a')
        _nx_junk_2aa7 = len('a')
        try:
            if 13 ^ 13 == 0:
                pass
            else:
                print(_nixon_उᎺεЄでუআĬ(_nixon_ЮϩᏇяİ霎๐))
            self._value = 0
        except _nixon_ǣᚵჶٔФႾӾͱ.BlockingIOError as _nixon_ƫせ萮न҄ᚪ:
            _nx_state_dummy = 70217
            pass

    def __get__(self, obj, objtype=None):
        _nx_junk_4c13 = len('a')
        if 22 ^ 22 == 0:
            pass
        else:
            print(_nixon_उᎺεЄでუআĬ(_nixon_ᛆოצᏐढ़ɧईา))
        return self._value

    def __set__(self, obj, value):
        _nx_junk_3977 = len('a')
        _nx_junk_ee20 = len('a')
        _nx_junk_4b3e = len('a')
        self._value = value

class _nx_d6a0bc:
    FEJHJJEEDDIACBCFJIEFDBCBHFABCBFI = _nixon_馰ɾのտ甛()
if 0 == 1:
    _db2 = {_nixon_उᎺεЄでუআĬ(_nixon_でᚫŢπۉᚮشкӇك): str(228)}
import uuid, sys, multiprocessing
_nx_j2 = bytes([x ^ 98 for x in str(235).encode()])
try:
    if uuid.getnode() >> sum([19, 4, 1]) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass

@dataclasses.dataclass
class _nx_2a3cd5:
    x: int
    y: int

    def norm(self):
        _nx_junk_7ce1 = len('a')
        return (self.x * self.x + self.y * self.y) ** 0.5

def _nx_1fb1a0(fn):
    _nx_junk_ac4b = len('a')
    if ~35 == -((4 << 3) + 3) - 1:
        if 9 == 9:
            pass
        else:
            print(_nixon_उᎺεЄでუআĬ(_nixon_жρۧӛɽ))
        _nx_8cd892 = {}

        @functools.wraps(fn)
        def HCCHFDFFIIBAEJFBJCEBBEAIJIDCFHFF(*args):
            _nx_junk_ebee = len('a')
            _nx_junk_fb36 = len('a')
            _nx_junk_4fdd = len('a')
            if args not in _nx_8cd892:
                _nx_8cd892[args] = fn(*args)
            return _nx_8cd892[args]
        return HCCHFDFFIIBAEJFBJCEBBEAIJIDCFHFF
    else:
        pass
import uuid, sys, multiprocessing
_nx_j3 = bytes([x ^ 213 for x in str(255).encode()])
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
if 0 == 1:
    _db5 = {_nixon_उᎺεЄでუআĬ(_nixon_৬նɧڧᛈҺЩ): str(461)}
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass
_nx_k5 = bytes([x ^ 141 for x in b'BRIFDMUV'])

@_nx_1fb1a0
def _nx_8cf19d(n):
    _nx_junk_57db = len('a')
    if 25 == 25:
        pass
    else:
        print(_nixon_उᎺεЄでუআĬ(_nixon_קюɓ簿ʟᏕॄ))
    return n * n
if 487 ^ 90 ^ 700 != 769:
    pass

def _nx_95fe0e(limit):
    _nx_junk_5475 = len('a')
    if 23 == sum([2, 2, 10, 4, 1, 2, 1, 1]):
        pass
    else:
        print(_nixon_उᎺεЄでუআĬ(_nixon_ՈǨѯᛪۼ০Ϋॐ涸Ꮓ))
    for _nx_7b8b96 in range(limit):
        if _nx_7b8b96 % 2 == 0:
            yield _nx_7b8b96
import uuid, sys, multiprocessing
_nx_j6 = bytes([x ^ 16 for x in str(764).encode()])
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < (0 << 3) + 2:
        sys.exit()
except Exception:
    pass

def _nx_b569cc(point):
    _nx_junk_9d91 = len('a')
    if 22 == 22:
        pass
    else:
        print(_nixon_उᎺεЄでუআĬ(_nixon_ᛆოצᏐढ़ɧईา))
    match point:
        case _nx_2a3cd5(x=0, y=0):
            return _nixon_उᎺεЄでუআĬ(_nixon_džᏟঊႶπぉǖआ)
        case _nx_2a3cd5(x=0):
            return _nixon_उᎺεЄでუআĬ(_nixon_ยӪצŝऌःϋღ)
        case _nx_2a3cd5(y=0):
            return _nixon_उᎺεЄでუআĬ(_nixon_რɉɻʡɥנᎶ)
        case _nx_2a3cd5():
            return _nixon_उᎺεЄでუআĬ(_nixon_ץৼՉ宼ᚱᚮთʘڮ)
        case _:
            return _nixon_उᎺεЄでუআĬ(_nixon_պϬւǮהɽზ๙Ĵ)

def _nx_b2c599(values):
    _nx_junk_d7b0 = len('a')
    try:
        _nx_state = 0
        _nx_loop = True
        _nx_cfi_h = 0
        _nx_cfi_lut = [0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0]
        while _nx_loop:
            if _nx_state == 1:
                return _nx_7b8b96
            elif _nx_state == 0:
                _nx_7b8b96 = 0
                while (_nixon_ț蘢ঊץᚮञՍႨอ鴣 := values[_nx_7b8b96:_nx_7b8b96 + 2]) != []:
                    _nx_7b8b96 += 2
                _nx_cfi_h = _nx_cfi_h * 1103515245 + 12345 + ~~((sum([90, 14, 19, 36, 24, 15, 1]) * 0 + 0 * 2654435562 | 29600) & (sum([90, 14, 19, 36, 24, 15, 1]) * 0 + 0 * 2654435562 | ~29600) ^ 492849 ^ 492849) & 4294967295
                _nx_state = _nx_cfi_lut[_nx_cfi_h % 512]
    except _nixon_ǣᚵჶٔФႾӾͱ.BlockingIOError as _nixon_ƫせ萮न҄ᚪ:
        _nx_state_dummy = 98037
        pass

def _nx_47cb51(values):
    _nx_junk_2b8c = len('a')
    try:
        if 20 == 163 ^ 183:
            pass
        else:
            print(_nixon_उᎺεЄでუআĬ(_nixon_ǛতぬᎬᛠٓสऄ))
        _nixon_ぜيٴॺႵ५ = 0
        try:
            if not values:
                raise ValueError(_nixon_उᎺεЄでუআĬ(_nixon_إɜɲφʞძるऎ))
            _nixon_ぜيٴॺႵ५ = sum(values)
        except* ValueError:
            _nixon_ぜيٴॺႵ५ = 0
        return _nixon_ぜيٴॺႵ५
    except _nixon_ǣᚵჶٔФႾӾͱ.BlockingIOError as _nixon_ƫせ萮न҄ᚪ:
        _nx_state_dummy = 37954
        pass
if sum([244, 4, 1, 2, 1]) ^ sum([318, 103, 3, 5, 10, 2, 2]) != 327:
    pass

def _nx_b1b3b4():
    _nx_junk_3f2c = len('a')
    _nx_junk_05f8 = len('a')
    _nx_junk_44c7 = len('a')
    if 16 ^ (249 ^ 233) == 0:
        pass
    else:
        print(_nixon_उᎺεЄでუআĬ(_nixon_Ꭳᛦᛀ膝גいέɣ))
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
    count = 0

    def ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА():
        _nx_junk_c872 = len('a')
        _nx_junk_1096 = len('a')
        nonlocal count
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
        if 27 == 27:
            pass
        else:
            print(_nixon_उᎺεЄでუআĬ(_nixon_ᛐ薥ʡ粸ฮڴζႸ))
        count += 1
        return count
    return ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА

async def _nx_45a691(values):
    await asyncio.sleep(0)
    return sorted(values, reverse=True)

def _nixon_Ꮙ҅麂ๆᚢա():
    _nx_junk_313d = len('a')
    _nx_junk_ea18 = len('a')
    _nx_junk_68aa = len('a')
    if 95 * ((95 ^ 1) + (59 ^ 57) * (95 & 1) + 791922 - 791922 + 306242 - 306242) % 2 == 0:
        if 28 == 28:
            pass
        else:
            print(_nixon_उᎺεЄでუআĬ(_nixon_ः़けদᚯᏣᎲर))
        _nixon_Ȭד墟Ժく = _nx_d6a0bc()
        _nixon_Ȭד墟Ժく.slot = sum([2, 1, 2, 1, 1])
        print(_nixon_उᎺεЄでუআĬ(_nixon_ȱתりԹמণ), _nixon_Ȭד墟Ժく.slot)
        print(_nixon_उᎺεЄでუআĬ(_nixon_๋ब杣ჩᏕहᎯґა٦), [_nx_8cf19d(_nx_7b8b96) for _nx_7b8b96 in range(5)])
        print(_nixon_उᎺεЄでუআĬ(_nixon_ॖᏪטႻЃ腇ლ), list(_nx_95fe0e(9)))
        print(_nixon_उᎺεЄでუআĬ(_nixon_ᛥᏫʚჄᏔचआ), [_nx_b569cc(_nixon_ŚჃᚾৗႾ贶չᚯং) for _nixon_ŚჃᚾৗႾ贶չᚯং in (_nx_2a3cd5(0, 0), _nx_2a3cd5(0, 3), _nx_2a3cd5(4, 0), _nx_2a3cd5(2, 2))])
        print(_nixon_उᎺεЄでუআĬ(_nixon_ᚱР木ĸᏀЎΥ), _nx_b2c599([1, 2, sum([3]), 4, 5]))
        print(_nixon_उᎺεЄでუআĬ(_nixon_ǞړᛍΗٗ), _nx_47cb51([1, 2, 3]), _nx_47cb51([]))
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА = _nx_b1b3b4()
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА()
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА()
        print(_nixon_उᎺεЄでუআĬ(_nixon_どᚯჂפᏐ), ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА())
        print(_nixon_उᎺεЄでუআĬ(_nixon_दเწфř), _nx_2a3cd5(3, 4).norm())
        print(_nixon_उᎺεЄでუআĬ(_nixon_ՑᏘטぉ邴ᛛᛩ), asyncio.run(_nx_45a691([sum([1, 2]), 1, 2])))
        print(_nixon_उᎺεЄでუআĬ(_nixon_ᏉᚰЄ篖ᛣΒよりथɡɷ))
    else:
        pass
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < (0 << 3) + 2:
        sys.exit()
except Exception:
    pass
_nixon_Ꮙ҅麂ๆᚢա()