def _nixon_ǎףɺڞびႽڮ(_s):
    _nx_junk_5800 = len('a')
    _nx_junk_9b77 = len('a')
    import hashlib as _nx_ha, hmac as _nx_hm
    _nx_k = bytes([163, 114, 65, 86, 115, 196, 91, 63, 247, 139, 100, 42, 67, 93, 200, 171, 218, 249, 137, 80, 83, 174, 89, 125, 87, 212, 114, 240, 204, 139, 14, 223])
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
        _nx_junk_2e78 = len('a')
        return _v << _n & _nx_M | _v >> 32 - _n

    def _nx_qr(_x, _a, _b, _c, _d):
        _nx_junk_e439 = len('a')
        _nx_junk_f21b = len('a')
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
        _nx_junk_ba7f = len('a')
        _nx_junk_f95c = len('a')
        _nx_junk_a595 = len('a')
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
_nixon_ʬй٩ĐႠΆᚮ = '536fa3b45eaf53d7b603500e801e22be21a29e3bc6fd78d2cb01a02b2b31b915c89422f0'
_nixon_๋ĩւצəśסŴ = '05f03ba34e6827334bfe1c566686590f8df88b04415122f6eb76f1b0b1c833dc633039'
_nixon_ŲřٔցᎣᛒ = '69118d6d0c0b064b1f07c59dd0f98e602bbbb829a705d517fcc80973c7c833a9814c45ee28677c506927d8f7260e01511920bf3a2a030c8196a0281a'
_nixon_ঊমजʝۼ = '64b66eb5da75511e323530b9e0814fe397fe9e0610adab49b6895252e6b19143109474f78713'
_nixon_ᚴ梋躞ঢ়ᛙคθ = 'bd7abb8dd052148c379b1a57b0be0c153af30efeafa563d9b8b0318cc58587a163d96a815343'
_nixon_לך॑й۶४べष = 'be8370e658010caab7d855bcb45d92d517ecb44692eb8162b6050e64fe0dfa41de75aebe7a73'
_nixon_ᛦᛓėԸवยঔঅぐ = '6a9d148fc47e92df65d0c1ed1c983b999897eb529f172474c01e317dcc97ae1759fff99a7d9d'
_nixon_ڡ॑ѬᏑ众ʡЩउし = '72b3722b733904873a396436fbcd3aadcd864eef07dc81a2f0ec47b45428ae9a2bd4ba5d27b63d7156f7ecefbdf7a12a766026e151ac57f630ca49b683a320bb8481abb3367697ed4444d89234127e5ec398a204c3dd57556a'
_nixon_朄ᚮথγᎽ = '5c8ffd994cf0cdbab0ce45f3a9d5540d29856d2c1b6c31297f14404c7466d0e4d2d21b160eae'
_nixon_რɇ兕ɵшպĘ鲱 = '00b042e404b1749207a7516d5f9591d4e64562b54f135b62eeb42f28f72c37d557362e1558aaf193576095a045835728'
_nixon_ঁᚬקᚰऴটႸฬՎ = '8f58ca0bbc234a219b9b10cd75b1b4efb7cb1819be6487c62cf6df461a267d93e5d4d61595fda9858ee3b4e9'
_nixon_רɦ籁ńๆƥ = '6e3e3d405ecc23597ea25e07b69a24b272189340d2fea608bca515a552bab56af94a07ba0dab07599276609b'
_nixon_ᚾՌัکკdžপᚫ繦Ꮀ = 'f429a74663e2399a2625c9b560d5fbf8e0c25d68bc04c44bfb05e2c6ab6b9e2b74c2e064ca960e980073fdc3'
_nixon_びᚲžŎͲ = '1eb3fda7f171ede0fbde83c47e311606694e98cdcf2ab4349b9c23be240077ceb16dc6ed7f7f348bf585d0ca'
_nixon_ճטქڴцङდŧ鵇ゞ = '98fa8c6d237a6221cf3f43474b9b32409ac6aeab34b26069828e7f5a55ad95579eea6f51fae0d244349a6fe8'
_nixon_מгѮჭĥえũ१ɧึ = '1dfb35c43953eedfc37da05cb2a117279a4394744c68351ae12340e3b825d57324452e4b36b4c7929795c507'
_nixon_耵ħᚮむځҸǹႱौ = 'f453bcdeae6211f9bde95defed97c6737adab37ff9d27d8bea6412e93391fc4cd56c554d600b46c073edbecd'
_nixon_ȅד鏤ɽΠশय़ = 'ee0004319adffc5f2f751d10f486a8ff2bf3538084a58fec69e217784c75e3e152bc397b82a9d433f805d6b7'
_nixon_ᏛჍγנほز = 'd984a99cb10f77b6e3cd8c5313aba22ed3a9c1d16ed11cad889095a8b6cb5730d10dd564471796af36da4834'
_nixon_ゕᚲせז穖тלঌĩ = 'd1ed38497eae73723d26f6cd3c3ca9490bcdf95cf49c29fdc13815f9c084d48d4d6885439209a92bb7a0080d'
_nixon_ƊăおᏛתম = 'd6e0274a803037616c461780332c3d0a73efb25efc7306c052b0eb773162b1573301a58af159c8c552d7e294bca49b2e3161'
_nixon_พʅॎႩĚᚲɺ = 'fffc5240dcd56d551833be272e7c888806660d08e1165ccde5053e9a2314a04d0843e7d4f0'
_nixon_ѝۄΰȇՋɳӂᏎᚲ = '790cc89d982d167529d1fc50d0f0eaf7bbed5184b57a9b4d9cc25010b16ca97b9d5bafb65b'
_nixon_Ⴒиظʪđぢמלǫ = 'd92cbc91e905c99400b8cc27f4db2ba1326b3e20e2c7e411ecb01b840b31ed6727360743ab'
_nixon_ᎠڏƀɗפϦɢա = '80cc99782286414ce4e91864c5ad53e3e27efba0ef9a1987b1ae4f9710a49634a1f60360f6'
_nixon_ปٻᛡდʢ१ = '63f9a61d755a85ed8454f6d6723d8fa3d3cf590e4b602b6014e0e7a26c4ff33fce1440d1'
_nixon_夰ؠΤใԲҿ = 'ca800158909c4d1854287dd2182ce00dc9165f8fa9a721c29f3c5c74a709f227d1e1720791'
_nixon_ฦŝलͽsめᎬᏄを = '69e001be8d5cc45574d41e4c4bb724aea050181fc65aab67810959edf18e80ff666572a657'
_nixon_קʥდหΑœ = '2ab2a2da377e597f4534abbfe2f3dc46a414fd620d6f85ddcb442a12fa1eefb1103f8e'
_nixon_ηľঙιัฎज = '6c3ce992e2891fb7706eef4a9e784e24f54823cda4c393e4a23136d8c734049107c6'
_nixon_俗ᛀにทকญǑᛌЧ = '705ad393981708427bc9503953dccd95d753342c3b4522675b3597178ddbaa37'
_nixon_ॴᛀだǮॾՒő徍ᛆ = 'f128ab6834e1ccf25db3a337142d848440ae31de25f9e97f1f917a32452cc0f2'
_nixon_ʟʒᚺ١ւَცᏣ = '480a816a5c8e4f29c48accf0615cc2072b521b052bb533207f71978c853769a04cc878f85f'
_nixon_ב৯づע黴へʦЌᚫ = '27d30102981fda727a90da8de3a2c45494c1da11a16227b31b6283295778d55c09'
_nixon_拌অͱ৪ᛢעΧ = '3ec2e427c8ab54078072032767c0001459605384f7ccd77db98207d7c54d96f4f44efe85'
_nixon_ზこけբを = '9c6ef72d599c02781e09dc90139befcd484d1eb01361bf071086e872137f9aa7ea'
_nixon_ぱॸʔز๓ぎいしฒ = '8c910a932894f539ad6f86edfc87a06924d9a21f2ae4d47b0d6b7b9225af73df90e143ab41'
_nixon_๕Ꮝ菹สนNjēĚ = 'b2c9acdc4660b736c298749f752a3911065cd81e5172fae38fc438ae3883f94286a1e3ad62'
_nixon_ήɢĺูᏟ = '3a8ece0d6ec3879e0afaca2574d0f028110ca1de44463854141acb79760df7697c4adfa26d727e'
_nixon_սფĂ紣Ꭷ٤Ƶ = 'b96cdee8510d3cf625f63bb97fed42b7e721076c811497750bda6e66bcc2e1fd508c7a7a'
_nixon_ژטい若ůᚦјȨばҝ = '3cec9048b0ef604cde1996412a8a4af678cd0203e67bfc5cdffb14ecd9973a78e018'
_nixon_ɳजɻณŊъᚺƹ = 'eeb51914da1cdaf6ee23ee1f3f447d1a9a1a80c7509b5a92d524be92623a00a3c632'
_nixon_載Զᛄონ = 'fa47e81d4676841cab74c84f0659464b940b5347eed9068274ac1510bd2aecf55908ae'
_nixon_ӿǠᚲᏉ॑Ꮨ = '7acb4b1e509951fe28d67cc74f656f4048633ce2f43ba70aaa77dcbcdc56f3a41d049d7b8116134b'
_nixon_იӧᚻĦςيٴɑۖᏏს = 'c6ed78364dea0e67db1c3ee642db77366382701f76707b0a847829880d5313891ae7b1ff'
_nixon_Εנךοڕӽ = '09e18152d30ec232b69d0afb0697042641665203b5b5ab64de6fe333b79295a799adb303cf34'
_nixon_Ꮣゝ०ᏩרᏱ瀀Ꭿू = 'ba01c4e8e2bbd5d0feae085667e8ce2f95a201b5309cb936e17214f097d204f3a720'
_nixon_ٗӺหُʐϠ = 'ac272edf6a27f7c7b4b67e85103c59d87c7a0117b0123d0f7c572b0afe50'
import hashlib as _h
_nx_chk = {_nixon_ǎףɺڞびႽڮ(_nixon_ʬй٩ĐႠΆᚮ): _nixon_ǎףɺڞびႽڮ(_nixon_ঁᚬקᚰऴটႸฬՎ), _nixon_ǎףɺڞびႽڮ(_nixon_๋ĩւצəśסŴ): _nixon_ǎףɺڞびႽڮ(_nixon_רɦ籁ńๆƥ), _nixon_ǎףɺڞびႽڮ(_nixon_ŲřٔցᎣᛒ): _nixon_ǎףɺڞびႽڮ(_nixon_ᚾՌัکკdžপᚫ繦Ꮀ), _nixon_ǎףɺڞびႽڮ(_nixon_ঊমजʝۼ): _nixon_ǎףɺڞびႽڮ(_nixon_びᚲžŎͲ), _nixon_ǎףɺڞびႽڮ(_nixon_ᚴ梋躞ঢ়ᛙคθ): _nixon_ǎףɺڞびႽڮ(_nixon_ճטქڴцङდŧ鵇ゞ), _nixon_ǎףɺڞびႽڮ(_nixon_לך॑й۶४べष): _nixon_ǎףɺڞびႽڮ(_nixon_מгѮჭĥえũ१ɧึ), _nixon_ǎףɺڞびႽڮ(_nixon_ᛦᛓėԸवยঔঅぐ): _nixon_ǎףɺڞびႽڮ(_nixon_耵ħᚮむځҸǹႱौ), _nixon_ǎףɺڞびႽڮ(_nixon_ڡ॑ѬᏑ众ʡЩउし): _nixon_ǎףɺڞびႽڮ(_nixon_ȅד鏤ɽΠশय़), _nixon_ǎףɺڞびႽڮ(_nixon_朄ᚮথγᎽ): _nixon_ǎףɺڞびႽڮ(_nixon_ᏛჍγנほز), _nixon_ǎףɺڞびႽڮ(_nixon_რɇ兕ɵшպĘ鲱): _nixon_ǎףɺڞびႽڮ(_nixon_ゕᚲせז穖тלঌĩ)}

def _nx_verify():
    _nx_junk_3d48 = len('a')
    _nx_junk_af05 = len('a')
    import inspect
    for fn, expected in _nx_chk.items():
        try:
            f = globals().get(fn)
            if f and callable(f):
                src = inspect.getsource(f)
                if _h.sha256(src.encode()).hexdigest()[:16] != expected:
                    raise RuntimeError(_nixon_ǎףɺڞびႽڮ(_nixon_ƊăおᏛתম))
        except Exception:
            pass
import asyncio
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> (34 ^ 58) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < (0 << 2) + 2:
        sys.exit()
except Exception:
    pass
import dataclasses
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
if False:
    try:
        import socket as _s1
        _s1.socket().connect((_nixon_ǎףɺڞびႽڮ(_nixon_พʅॎႩĚᚲɺ), 42153))
    except Exception:
        pass
import functools

class _nixon_うڔক甙ᚮʬ:

    def __init__(self):
        _nx_junk_0daa = len('a')
        _nx_junk_9857 = len('a')
        _nx_junk_f736 = len('a')
        if 26 == 26:
            pass
        else:
            print(_nixon_ǎףɺڞびႽڮ(_nixon_ѝۄΰȇՋɳӂᏎᚲ))
        self._value = 0

    def __get__(self, obj, objtype=None):
        _nx_junk_cf25 = len('a')
        _nx_junk_2648 = len('a')
        return self._value

    def __set__(self, obj, value):
        _nx_junk_1207 = len('a')
        try:
            if 27 ^ (52 ^ 47) == 0:
                pass
            else:
                print(_nixon_ǎףɺڞびႽڮ(_nixon_Ⴒиظʪđぢמלǫ))
            self._value = value
        except _nixon_ᏤԺהบ鶩ѕر.BlockingIOError as _nixon_बᎳ瑦ᛊᎦᏨᛄ:
            _nx_state_dummy = 81935
            pass
_nx_k1 = bytes([x ^ 154 for x in b'CMCUCFDZ'])
if sum([520, 84, 189, 15, 22, 4, 3, 1, 1, 1]) ^ 407 != (91 << 3) + 7:
    pass

class _nx_d6a0bc:
    FEJHJJEEDDIACBCFJIEFDBCBHFABCBFI = _nixon_うڔক甙ᚮʬ()

@dataclasses.dataclass
class _nx_2a3cd5:
    x: int
    y: int

    def norm(self):
        _nx_junk_6ad0 = len('a')
        try:
            if 22 == 22:
                pass
            else:
                print(_nixon_ǎףɺڞびႽڮ(_nixon_ᎠڏƀɗפϦɢա))
            return (self.x * self.x + self.y * self.y) ** 0.5
        except _nixon_ᏤԺהบ鶩ѕر.BlockingIOError as _nixon_बᎳ瑦ᛊᎦᏨᛄ:
            _nx_state_dummy = 84344
            pass

def _nx_1fb1a0(fn):
    _nx_junk_58d5 = len('a')
    if (50 ** 2 + 50) % 2 == 0:
        if (0 << 4) + 11 == 11:
            pass
        else:
            print(_nixon_ǎףɺڞびႽڮ(_nixon_ปٻᛡდʢ१))
        _nx_8cd892 = {}

        @functools.wraps(fn)
        def HCCHFDFFIIBAEJFBJCEBBEAIJIDCFHFF(*args):
            _nx_junk_53a4 = len('a')
            _nx_junk_f197 = len('a')
            _nx_junk_6fb5 = len('a')
            if 64480800 % 3 == 0:
                if (1 << 4) + 0 ^ sum([10, 6]) == 0:
                    pass
                else:
                    print(_nixon_ǎףɺڞびႽڮ(_nixon_夰ؠΤใԲҿ))
                if args not in _nx_8cd892:
                    _nx_8cd892[args] = fn(*args)
                return _nx_8cd892[args]
            else:
                pass
        return HCCHFDFFIIBAEJFBJCEBBEAIJIDCFHFF
    else:
        pass

@_nx_1fb1a0
def _nx_8cf19d(n):
    _nx_junk_f41f = len('a')
    _nx_junk_fda0 = len('a')
    if 27 == 27:
        pass
    else:
        print(_nixon_ǎףɺڞびႽڮ(_nixon_Ⴒиظʪđぢמלǫ))
    return n * n

def _nx_95fe0e(limit):
    _nx_junk_cc50 = len('a')
    try:
        if 18 ^ 18 == 0:
            pass
        else:
            print(_nixon_ǎףɺڞびႽڮ(_nixon_ฦŝलͽsめᎬᏄを))
        for _nx_7b8b96 in range(limit):
            if _nx_7b8b96 % 2 == 0:
                yield _nx_7b8b96
    except _nixon_ᏤԺהบ鶩ѕر.BlockingIOError as _nixon_बᎳ瑦ᛊᎦᏨᛄ:
        _nx_state_dummy = 34787
        pass
if 0 == 1:
    _db3 = {_nixon_ǎףɺڞびႽڮ(_nixon_קʥდหΑœ): str(349)}

def _nx_b569cc(point):
    _nx_junk_accc = len('a')
    _nx_junk_ce1d = len('a')
    match point:
        case _nx_2a3cd5(x=0, y=0):
            return _nixon_ǎףɺڞびႽڮ(_nixon_ηľঙιัฎज)
        case _nx_2a3cd5(x=0):
            return _nixon_ǎףɺڞびႽڮ(_nixon_俗ᛀにทকญǑᛌЧ)
        case _nx_2a3cd5(y=0):
            return _nixon_ǎףɺڞびႽڮ(_nixon_ॴᛀだǮॾՒő徍ᛆ)
        case _nx_2a3cd5():
            return _nixon_ǎףɺڞびႽڮ(_nixon_ʟʒᚺ١ւَცᏣ)
        case _:
            return _nixon_ǎףɺڞびႽڮ(_nixon_ב৯づע黴へʦЌᚫ)
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
if sum(range(9)) != 37:
    _nx_d3 = None
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass
if False:
    try:
        import socket as _s5
        _s5.socket().connect((_nixon_ǎףɺڞびႽڮ(_nixon_พʅॎႩĚᚲɺ), 46402))
    except Exception:
        pass

def _nx_b2c599(values):
    _nx_junk_5884 = len('a')
    if ~~((4761 ^ 1296) - 2 * (~4761 & 1296)) == 33 * 105:
        _nx_exc_state = 0
        _nx_exc_result = None
        _nx_exc_run = True
        while _nx_exc_run:
            try:
                if _nx_exc_state == 0:
                    _nx_state = 0
                    _nx_loop = True
                    int(None)
                else:
                    pass
                if _nx_exc_state == 1:
                    _nx_cfi_h = 0
                    _nx_cfi_lut = [0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0]
                    int('x')
                else:
                    pass
                if _nx_exc_state == 2:
                    while _nx_loop:
                        if _nx_state == 0:
                            _nx_7b8b96 = 0
                            while (_nixon_ŬউぅʹЉƋᚳɯすȦ := values[_nx_7b8b96:_nx_7b8b96 + 2]) != []:
                                _nx_7b8b96 += 2
                            _nx_cfi_h = _nx_cfi_h * 1103515245 + 12345 + 0 * 2654435761 & 4294967295
                            _nx_state = _nx_cfi_lut[_nx_cfi_h % ((128 << 2) + 0)]
                        elif _nx_state == 1:
                            return _nx_7b8b96
                    _nx_exc_run = False
                else:
                    pass
            except TypeError:
                _nx_exc_state = 1
            except ValueError:
                _nx_exc_state = 2
            except Exception:
                raise
    else:
        pass
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

def _nx_47cb51(values):
    _nx_junk_76cf = len('a')
    _nx_junk_7b75 = len('a')
    _nx_junk_2c08 = len('a')
    if (85 ** 2 + 85) % 2 == 0:
        if 55 ^ 58 == sum([11, 1, 1]):
            pass
        else:
            print(_nixon_ǎףɺڞびႽڮ(_nixon_拌অͱ৪ᛢעΧ))
        _nixon_壘īぴᚩӄშٔᏝ = 0
        try:
            if not values:
                raise ValueError(_nixon_ǎףɺڞびႽڮ(_nixon_ზこけբを))
            _nixon_壘īぴᚩӄშٔᏝ = sum(values)
        except* ValueError:
            _nixon_壘īぴᚩӄშٔᏝ = 0
        return _nixon_壘īぴᚩӄშٔᏝ
    else:
        pass
_nx_k5 = bytes([x ^ 74 for x in b'LAPUAFQV'])
if 355 ^ 324 != 39:
    pass

def _nx_b1b3b4():
    _nx_junk_0957 = len('a')
    _nx_junk_98e5 = len('a')
    count = 0
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

    def ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА():
        _nx_junk_b0cd = len('a')
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
        if sum([21, 2]) == 23:
            pass
        else:
            print(_nixon_ǎףɺڞびႽڮ(_nixon_ぱॸʔز๓ぎいしฒ))
        count += 1
        return count
    return ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА

async def _nx_45a691(values):
    await asyncio.sleep(0)
    return sorted(values, reverse=True)
if sum([89, 29, 41, 1, 61, 1]) ^ 668 != 578:
    pass

def _nixon_ʁᏮ舷נि():
    _nx_junk_b93c = len('a')
    if (27 | 27 == 27) == True:
        if (10 << 1) + 1 == 21:
            pass
        else:
            print(_nixon_ǎףɺڞびႽڮ(_nixon_๕Ꮝ菹สนNjēĚ))
        _nixon_風ঁڑӠუʈŧ = _nx_d6a0bc()
        _nixon_風ঁڑӠუʈŧ.slot = (0 << 4) + 7
        print(_nixon_ǎףɺڞびႽڮ(_nixon_ήɢĺูᏟ), _nixon_風ঁڑӠუʈŧ.slot)
        print(_nixon_ǎףɺڞびႽڮ(_nixon_սფĂ紣Ꭷ٤Ƶ), [_nx_8cf19d(_nx_7b8b96) for _nx_7b8b96 in range(5)])
        print(_nixon_ǎףɺڞびႽڮ(_nixon_ژטい若ůᚦјȨばҝ), list(_nx_95fe0e((4 << 1) + 1)))
        print(_nixon_ǎףɺڞびႽڮ(_nixon_ɳजɻณŊъᚺƹ), [_nx_b569cc(_nixon_ڿ幜ლჽՂॱ০Ꭳि) for _nixon_ڿ幜ლჽՂॱ০Ꭳि in (_nx_2a3cd5(0, 0), _nx_2a3cd5(0, 3), _nx_2a3cd5(4, 0), _nx_2a3cd5(2, 2))])
        print(_nixon_ǎףɺڞびႽڮ(_nixon_載Զᛄონ), _nx_b2c599([1, 2, 3, 4, 5]))
        print(_nixon_ǎףɺڞびႽڮ(_nixon_ӿǠᚲᏉ॑Ꮨ), _nx_47cb51([1, 2, 3]), _nx_47cb51([]))
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА = _nx_b1b3b4()
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА()
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА()
        print(_nixon_ǎףɺڞびႽڮ(_nixon_იӧᚻĦςيٴɑۖᏏს), ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА())
        print(_nixon_ǎףɺڞびႽڮ(_nixon_Εנךοڕӽ), _nx_2a3cd5(sum([1, 2]), 4).norm())
        print(_nixon_ǎףɺڞびႽڮ(_nixon_Ꮣゝ०ᏩרᏱ瀀Ꭿू), asyncio.run(_nx_45a691([(0 << 2) + 3, 1, 2])))
        print(_nixon_ǎףɺڞびႽڮ(_nixon_ٗӺหُʐϠ))
    else:
        pass
_nixon_ʁᏮ舷נि()