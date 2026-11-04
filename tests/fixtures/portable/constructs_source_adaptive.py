def _nixon_ॽᏨしōճƶت(_s):
    _nx_junk_ee62 = len('a')
    _nx_junk_2bd6 = len('a')
    _nx_junk_0c32 = len('a')
    import hashlib as _nx_ha, hmac as _nx_hm
    _nx_k = bytes([11, 50, 161, 46, 231, 171, 37, 34, 143, 197, 213, 160, 237, 15, 152, 29, 72, 147, 113, 225, 132, 55, 239, 60, 201, 154, 2, 102, 159, 123, 191, 200])
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
        _nx_junk_1c98 = len('a')
        return _v << _n & _nx_M | _v >> 32 - _n

    def _nx_qr(_x, _a, _b, _c, _d):
        _nx_junk_8578 = len('a')
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
        _nx_junk_7d03 = len('a')
        _nx_junk_64db = len('a')
        _nx_junk_d0ac = len('a')
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
_nixon_ڇɖɶοȍؽʞ = 'd415540a8409fddac323d28d99dba80b02114857bf5088f20d00151328ed0f7b1cd4720f'
_nixon_ऊϜどəॿɿךčんな = '66c069062384316209c455b3eba9650efbc4ddf9e4dffce04e0067a0940486d91aac42'
_nixon_ɌंҢΐむৣ = 'd8ea77f03c551dc24ac6f2ac6d2ef29b82fd8baf91bc5c7ebc7b8b1d1b720515192ec4'
_nixon_хȢᚬזᛅॐķ = 'ff8e33e817145943afe0274f3377aa402be9ab9b5e46b4a4df22e1dba4989e86'
_nixon_ᚷԱॱᎼԸ = '3f4df05f14f58b442586a2e5fdfdc87e34bb8db0acb440cddbf9f327220f46ac6e1fabfdd2130de703104bdf961f7da571afca3c892a82bb0f3fa88e'
_nixon_อ簫ჅႨखҒΕ = 'd754fe7277884b48933742aaa177f058f1fa21a5e88bf838afb58083ee008dcb17f4d2b49b19'
_nixon_ႴϤ貛ᚷӾᏌŧĩ = '916fb15486cd4261f8074db1b8ff3d153619e7d1aa90fb342b67aaa415a4f7c588064876f961'
_nixon_फᚿჩʟכ่॔爻दᎥ = 'f46fffb45d9d0d69cdec17a33cdc854b58dbf469df7f6f050675eef13472fcd8ceffb02d9d7c'
_nixon_ɸնՀ๕ɖुɿł = 'f367f9429191c81f4056f6f8f7d021642385b3ca720a956042dddae7de29363bc43983e74bee'
_nixon_ৈכॗおŎ毀ᛝ = 'a40804e52e57d2ed465416320be901f3f99c89c6e6242acdc56996374ec53ca9ccfed1d3e2c64e71420a25fe3e42486d001f1a9706c79077c01741797f5a81e2a5467ffae3ebb50185b35f6862f9284e39c5b83277f9aea520'
_nixon_ץҍԷژ۷Ⴁ = 'e7b68f86379bd241706544aa7ea986ff22e58daaea6c664af7ac042c10e945733511db551846'
_nixon_şैכא६ = '62f9502ffb878bccaf8533d5e6e83c9f9f8032cd345644cbe36375bec9fda4fa90c3d5980a33c37d5881d7c6'
_nixon_҅გɚćנ = 'e2d04eb794c5bfb7922b989e41c5d00cc895a8828d19c325ed01cacb668475c257288877e7f06326c0e48528'
_nixon_ٻȟႿŘΒ = '9210e9909e800116ce1fd53d51d015ecae6ecf448f07afabecada1898812a8aaa9ab03e985fdeb17cb9d76ab'
_nixon_Ꮨ规პびĘľ = 'ab3f05653d6cd2f15e48c3bef77974f468bbfe3be30dfa040cfe8456f80606b28ef06e8c1d123fb5214f6b60'
_nixon_ȭႨ紛櫩ন = '646a910382098fc2c103b99b10fc51f8001dac1b9574b648148e172453099e5c284ea2c51c7308fc7926a644'
_nixon_ᏄらᏩīǂۚ = 'be374da269998a34d32e848cdac8dd9effd4fc7069c51c075ddf49fda083b7f0a4a04c6583ce7c117b54b110'
_nixon_ڒצԾႹざ = 'a9274e7f06635e8e40b1ab00227722e9fb340e555dcd2d37104154e0ecd4232f7dbb29f4d20730bc1b810ed6'
_nixon_あשȨƏุ = 'c355daff4b2b432651c2d03554e437e21aebfa3dc0c726d7f0b2f2d69c6d962705d5448d1cf2b41c4277a0a6'
_nixon_ۅɠלᚡɷɹčॻᛨऻ = '8fbfa39eef3c806aab476cde6d5c4daebe7f61c6e7f3393727d231f9faa5b062d7b1f46116ddc64703da0f38'
_nixon_սनΘॵŘرʼn٦ = 'c49ff337f0360380960ec18c08fea9bb165cc2b9a07c43d9334f1428a70ca2d5b23956d4f49615c98f50df26'
_nixon_ᏮزᏝืʞפө = 'f1a9e89ca36625fab53f75aa032f7fe2dc6e968fd0b4aef91258beca7f4802c38117b9e85fce37a23805c59d'
_nixon_ιჵƴპʯीDŽᛖ = '97f03ed692c18439f53e6c500abf5ea5b3bd7f22278123fb2547974cfdcae5368ddd197dc94fb4f78a03ee68099426b317c8'
_nixon_ბΪघגᎰჺやګկ = '8b97e95777f91a7767db03d0d6fb88004867a9c330478d6528de82c778be139f91a19a3c41'
_nixon_ᚯৱॉ綠զᛖॏ = 'ec492743c25ff2695d090ca5abb15e12d1d9d1e5215c76df41d2334bd161f09f1192718de2'
_nixon_ᚭबฺᏁؼ = 'fc4c291efafe9d68339db87c21e27c8e95e051e5770910a13058f86015ebb234bb9dfb4291'
_nixon_侹ᛙ钬ǍȴҊば = '82489bf2e54d838826c0f22fd3207d1b5c4e553b1f26b96d45150205260ebb5b6ec157245d'
_nixon_ᛅɱだกढ़झ = '53ca71a18e8f414561cda4580caa263160a6ec16be425598f06d7395779284ac9c9b792127'
_nixon_Ѝэढ़Ʈゔƈջ = 'c84e3a5d6bf5aa15fa009b32fd6401fe7519199f8150c3224303d54dae1546440a28'
_nixon_ƈ०Ɍᛚრ = '0f2a2d062dd404a1ec488fdd8673076a250dc2fd36df1eb4d6c0bcc6fcca077f'
_nixon_ƨঢӾθʕহゎᛪ = '266e3b9daf2a237d95996c7a5a0c6e59fb4c0b98cda175a044318639e1c8db70'
_nixon_ۮฒৣनॐ = 'c2cb3338eb33265c8995acf196d88e7609222e8de0027d6b1c33472fd1be4dabdb43853c66'
_nixon_ĥטᎠɬҰ = 'c35a4338d2c393ccd314749b7d0711cbfcbcedcb1e2f81a958b2d13995e60cd841'
_nixon_ڒγʌĭบؽәӦ = 'e1d28dfc94a5e31116d1e6137bd2a99bc332ba19f7ce90a1c00bd7c5179e96135c45cd07'
_nixon_ทλჟМํ = 'c3c1dcc130424cfd1716ebbf37bcd92db7dfe6e0625221d8cb88d4c0b828c283cdaef71e'
_nixon_ণᏇɇႱჲৌ = '022015abfad7eff8ea97d50224183ef065f2594833bf79fd02b3e8f78ee219a346'
_nixon_הϚՉउᎶหЎХظ = 'a80030bf6cd8434ac611422620cecee4571af47a81dce0c25167bf2b0739662f6ba92962'
_nixon_ʕซćřʎろჾ = '3e916c074a3502a51696b48410a879150e693c11d6c7773903e580166ab5639cf9b43cb26c'
_nixon_ؖШᎫʮᏭᏁзᏡՎա = 'ef09d0365981c27306e01c498598deaa358c8d11f5533246064a00df4b0ca73330c2444a'
_nixon_Σয়څʤȬฏჯ = '727a7e12dcb60863f7994e5b52437021d6a5c6496245fcbe7161a3cf0e4b969e4db54c87d54110'
_nixon_ĻლႲɡؒծ = '866952c38692c5651d81f7001f71f783f808ef65404cd6025e0b7c1191635637d43b2566'
_nixon_ύцჄ燃גשϠ๗ = '6958bf8482a23da64be2fe45ace7f0bc416e8077b77230f72e39c754959f8d5bc4e6'
_nixon_ƐᏱぉůɑぴ = '7a2b54c68c2b536827f395ed2777cbfe44666f1a87dbb21dc10a1f9a388a981ea392'
_nixon_चᛦ҇Гםᛂ以 = '5a91fa058b49145e4abfa57b9214785c996871a9ec80c017ceb7f300453d0633f9bd5f'
_nixon_ʄӒלľͳצϊর = '471a1b23a0a2406c376c701e03c2b2b226a77f73e8468eee659efd89351f65f7e0951ff6426f41f3'
_nixon_ՠԺざʠᛈжח蚈Ґ = '6418cfce89c993f284ebe2061930c5843f5b7db1b2e0e6048aeda40c79c989757c82b594'
_nixon_թग़ჺᏩɯ喼 = 'da35e7cb0ba61c790572e051972368039778e4a7fe05c6744148cfc82d7ab71d1d33b5e99942'
_nixon_াɔᏃϮخ = '4f55461de94f0896acefdb615165af73af0c383c6eafc38dc5d7b2f783291ffeddba'
_nixon_خকҢंॵϙڥ聻ķ = '212b09584548f6c7370258d64d58c0112729628f30861bb5e80baee38775'
import hashlib as _h
_nx_chk = {_nixon_ॽᏨしōճƶت(_nixon_ڇɖɶοȍؽʞ): _nixon_ॽᏨしōճƶت(_nixon_şैכא६), _nixon_ॽᏨしōճƶت(_nixon_ऊϜどəॿɿךčんな): _nixon_ॽᏨしōճƶت(_nixon_҅გɚćנ), _nixon_ॽᏨしōճƶت(_nixon_ɌंҢΐむৣ): _nixon_ॽᏨしōճƶت(_nixon_ٻȟႿŘΒ), _nixon_ॽᏨしōճƶت(_nixon_хȢᚬזᛅॐķ): _nixon_ॽᏨしōճƶت(_nixon_Ꮨ规პびĘľ), _nixon_ॽᏨしōճƶت(_nixon_ᚷԱॱᎼԸ): _nixon_ॽᏨしōճƶت(_nixon_ȭႨ紛櫩ন), _nixon_ॽᏨしōճƶت(_nixon_อ簫ჅႨखҒΕ): _nixon_ॽᏨしōճƶت(_nixon_ᏄらᏩīǂۚ), _nixon_ॽᏨしōճƶت(_nixon_ႴϤ貛ᚷӾᏌŧĩ): _nixon_ॽᏨしōճƶت(_nixon_ڒצԾႹざ), _nixon_ॽᏨしōճƶت(_nixon_फᚿჩʟכ่॔爻दᎥ): _nixon_ॽᏨしōճƶت(_nixon_あשȨƏุ), _nixon_ॽᏨしōճƶت(_nixon_ɸնՀ๕ɖुɿł): _nixon_ॽᏨしōճƶت(_nixon_ۅɠלᚡɷɹčॻᛨऻ), _nixon_ॽᏨしōճƶت(_nixon_ৈכॗおŎ毀ᛝ): _nixon_ॽᏨしōճƶت(_nixon_սनΘॵŘرʼn٦), _nixon_ॽᏨしōճƶت(_nixon_ץҍԷژ۷Ⴁ): _nixon_ॽᏨしōճƶت(_nixon_ᏮزᏝืʞפө)}

def _nx_verify():
    _nx_junk_975f = len('a')
    _nx_junk_9f32 = len('a')
    import inspect
    for fn, expected in _nx_chk.items():
        try:
            f = globals().get(fn)
            if f and callable(f):
                src = inspect.getsource(f)
                if _h.sha256(src.encode()).hexdigest()[:16] != expected:
                    raise RuntimeError(_nixon_ॽᏨしōճƶت(_nixon_ιჵƴპʯीDŽᛖ))
        except Exception:
            pass
import asyncio
if 715 ^ 834 != 393:
    pass
_nx_j0 = bytes([x ^ 239 for x in str(277).encode()])
import dataclasses
if 302 ^ 221 != 499:
    pass
import functools
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < (0 << 4) + 2:
        sys.exit()
except Exception:
    pass

class _nixon_ȵπφᏍゑ:

    def __init__(self):
        _nx_junk_6db6 = len('a')
        if 18 ^ 18 == 0:
            pass
        else:
            print(_nixon_ॽᏨしōճƶت(_nixon_ბΪघגᎰჺやګկ))
        self._value = 0

    def __get__(self, obj, objtype=None):
        _nx_junk_4fae = len('a')
        _nx_junk_3a7e = len('a')
        return self._value

    def __set__(self, obj, value):
        _nx_junk_08b4 = len('a')
        _nx_junk_d1bd = len('a')
        self._value = value

class _nx_d6a0bc:
    FEJHJJEEDDIACBCFJIEFDBCBHFABCBFI = _nixon_ȵπφᏍゑ()
if 1019 ^ sum([148, 20, 59, 3, 2, 9, 1]) != 1019 ^ 242:
    pass

@dataclasses.dataclass
class _nx_2a3cd5:
    x: int
    y: int

    def norm(self):
        _nx_junk_ec64 = len('a')
        _nx_junk_18ca = len('a')
        _nx_junk_44d5 = len('a')
        if 30 == 30:
            pass
        else:
            print(_nixon_ॽᏨしōճƶت(_nixon_ᚯৱॉ綠զᛖॏ))
        return (self.x * self.x + self.y * self.y) ** 0.5

def _nx_1fb1a0(fn):
    _nx_junk_6795 = len('a')
    _nx_junk_7fb0 = len('a')
    if (34 ** 2 + 34) % 2 == 0:
        if sum([6, 11, 3, 3]) ^ 23 == 0:
            pass
        else:
            print(_nixon_ॽᏨしōճƶت(_nixon_ᚭबฺᏁؼ))
        _nx_8cd892 = {}

        @functools.wraps(fn)
        def HCCHFDFFIIBAEJFBJCEBBEAIJIDCFHFF(*args):
            _nx_junk_1f4a = len('a')
            _nx_junk_ab5a = len('a')
            if args not in _nx_8cd892:
                _nx_8cd892[args] = fn(*args)
            return _nx_8cd892[args]
        return HCCHFDFFIIBAEJFBJCEBBEAIJIDCFHFF
    else:
        pass
if sum([249, 114, 4, 26, 22, 17, 4, 8]) ^ 668 != 800:
    pass

@_nx_1fb1a0
def _nx_8cf19d(n):
    _nx_junk_3e0a = len('a')
    _nx_junk_971f = len('a')
    return n * n

def _nx_95fe0e(limit):
    _nx_junk_a414 = len('a')
    _nx_junk_81df = len('a')
    _nx_junk_6157 = len('a')
    try:
        if 28 ^ (195 ^ 223) == 0:
            pass
        else:
            print(_nixon_ॽᏨしōճƶت(_nixon_侹ᛙ钬ǍȴҊば))
        for _nx_7b8b96 in range(limit):
            if _nx_7b8b96 % 2 == 0:
                yield _nx_7b8b96
    except _nixon_Ⴔɯĥȅךূ麖҇.BlockingIOError as _nixon_ƼΥӏȿӀफ҃Ēמȴ:
        _nx_state_dummy = 2891
        pass
if 133 ^ 192 != 69:
    pass

def _nx_b569cc(point):
    _nx_junk_dc3f = len('a')
    if 29 == 195 ^ 222:
        pass
    else:
        print(_nixon_ॽᏨしōճƶت(_nixon_ᛅɱだกढ़झ))
    match point:
        case _nx_2a3cd5(x=0, y=0):
            return _nixon_ॽᏨしōճƶت(_nixon_Ѝэढ़Ʈゔƈջ)
        case _nx_2a3cd5(x=0):
            return _nixon_ॽᏨしōճƶت(_nixon_ƈ०Ɍᛚრ)
        case _nx_2a3cd5(y=0):
            return _nixon_ॽᏨしōճƶت(_nixon_ƨঢӾθʕহゎᛪ)
        case _nx_2a3cd5():
            return _nixon_ॽᏨしōճƶت(_nixon_ۮฒৣनॐ)
        case _:
            return _nixon_ॽᏨしōճƶت(_nixon_ĥטᎠɬҰ)
if (462 << 1) + 0 ^ (62 << 3) + 3 != 623:
    pass

def _nx_b2c599(values):
    _nx_junk_b837 = len('a')
    _nx_junk_42d6 = len('a')
    _nx_junk_abd9 = len('a')
    if 9 == 9:
        pass
    else:
        print(_nixon_ॽᏨしōճƶت(_nixon_ڒγʌĭบؽәӦ))
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
    _nx_state = 0
    _nx_loop = True
    _nx_cfi_h = 0
    _nx_cfi_lut = [0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0]
    while _nx_loop:
        if _nx_state == 1:
            return _nx_7b8b96
        elif _nx_state == 0:
            _nx_7b8b96 = 0
            while (_nixon_łĎāᏎמᛅѱ := values[_nx_7b8b96:_nx_7b8b96 + 2]) != []:
                _nx_7b8b96 += sum([1, 1])
            _nx_cfi_h = _nx_cfi_h * 1103515245 + 12345 + 0 * 2654435761 & 4294967295
            _nx_state = _nx_cfi_lut[_nx_cfi_h % (579 ^ 67)]
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass
if sum(range(3)) != 46:
    _nx_d1 = None

def _nx_47cb51(values):
    _nx_junk_5d92 = len('a')
    _nx_junk_838f = len('a')
    try:
        if 8 == 8:
            pass
        else:
            print(_nixon_ॽᏨしōճƶت(_nixon_ทλჟМํ))
        _nixon_אڀ٣ǖփƳ = 0
        try:
            if not values:
                raise ValueError(_nixon_ॽᏨしōճƶت(_nixon_ণᏇɇႱჲৌ))
            _nixon_אڀ٣ǖփƳ = sum(values)
        except* ValueError:
            _nixon_אڀ٣ǖփƳ = 0
        return _nixon_אڀ٣ǖփƳ
    except _nixon_Ⴔɯĥȅךূ麖҇.BlockingIOError as _nixon_ƼΥӏȿӀफ҃Ēמȴ:
        _nx_state_dummy = 12441
        pass

def _nx_b1b3b4():
    _nx_junk_97a4 = len('a')
    _nx_junk_3b9f = len('a')
    _nx_junk_801f = len('a')
    if 18 == 18:
        pass
    else:
        print(_nixon_ॽᏨしōճƶت(_nixon_ბΪघגᎰჺやګկ))
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
        _nx_junk_e655 = len('a')
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
        if 5 == 5:
            pass
        else:
            print(_nixon_ॽᏨしōճƶت(_nixon_הϚՉउᎶหЎХظ))
        count += 1
        return count
    return ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> (130 ^ 154) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < sum([1, 1]):
        sys.exit()
except Exception:
    pass
if False:
    try:
        import socket as _s3
        _s3.socket().connect((_nixon_ॽᏨしōճƶت(_nixon_ʕซćřʎろჾ), 19746))
    except Exception:
        pass

async def _nx_45a691(values):
    await asyncio.sleep(0)
    return sorted(values, reverse=True)

def _nixon_ᛡႡƙ़ᏴՕ親ᏀĄ():
    _nx_junk_0995 = len('a')
    try:
        if 6 ^ 6 == 0:
            pass
        else:
            print(_nixon_ॽᏨしōճƶت(_nixon_ؖШᎫʮᏭᏁзᏡՎա))
        _nixon_ɧ২ॄᛌβ๗ᛥՓ๕ = _nx_d6a0bc()
        _nixon_ɧ২ॄᛌβ๗ᛥՓ๕.slot = 7
        print(_nixon_ॽᏨしōճƶت(_nixon_Σয়څʤȬฏჯ), _nixon_ɧ২ॄᛌβ๗ᛥՓ๕.slot)
        print(_nixon_ॽᏨしōճƶت(_nixon_ĻლႲɡؒծ), [_nx_8cf19d(_nx_7b8b96) for _nx_7b8b96 in range(5)])
        print(_nixon_ॽᏨしōճƶت(_nixon_ύцჄ燃גשϠ๗), list(_nx_95fe0e(9)))
        print(_nixon_ॽᏨしōճƶت(_nixon_ƐᏱぉůɑぴ), [_nx_b569cc(_nixon_ʋҮᚧᏓȁյ藣厇) for _nixon_ʋҮᚧᏓȁյ藣厇 in (_nx_2a3cd5(0, 0), _nx_2a3cd5(0, 3), _nx_2a3cd5(4, 0), _nx_2a3cd5(sum([1, 1]), 91 ^ 89))])
        print(_nixon_ॽᏨしōճƶت(_nixon_चᛦ҇Гםᛂ以), _nx_b2c599([1, 2, 3, 4, sum([3, 2])]))
        print(_nixon_ॽᏨしōճƶت(_nixon_ʄӒלľͳצϊর), _nx_47cb51([1, 2, 3]), _nx_47cb51([]))
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА = _nx_b1b3b4()
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА()
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА()
        print(_nixon_ॽᏨしōճƶت(_nixon_ՠԺざʠᛈжח蚈Ґ), ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА())
        print(_nixon_ॽᏨしōճƶت(_nixon_թग़ჺᏩɯ喼), _nx_2a3cd5(3, 4).norm())
        print(_nixon_ॽᏨしōճƶت(_nixon_াɔᏃϮخ), asyncio.run(_nx_45a691([3, 1, 2])))
        print(_nixon_ॽᏨしōճƶت(_nixon_خকҢंॵϙڥ聻ķ))
    except _nixon_Ⴔɯĥȅךূ麖҇.BlockingIOError as _nixon_ƼΥӏȿӀफ҃Ēמȴ:
        _nx_state_dummy = 90347
        pass
if 869 ^ 822 != 22 ^ 69:
    pass
_nixon_ᛡႡƙ़ᏴՕ親ᏀĄ()