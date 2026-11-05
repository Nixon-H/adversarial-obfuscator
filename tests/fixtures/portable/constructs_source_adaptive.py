def _nixon_ЬᏥᏋᏑƀे(_s):
    _nx_junk_4273 = len('a')
    import hashlib as _nx_ha, hmac as _nx_hm
    _nx_k = bytes([204, 148, 176, 197, 163, 89, 185, 126, 17, 200, 132, 28, 28, 83, 172, 7, 131, 16, 172, 8, 148, 14, 74, 124, 253, 31, 87, 218, 30, 137, 174, 226])
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
        _nx_junk_81a5 = len('a')
        _nx_junk_655b = len('a')
        _nx_junk_dfa6 = len('a')
        return _v << _n & _nx_M | _v >> 32 - _n

    def _nx_qr(_x, _a, _b, _c, _d):
        _nx_junk_1af3 = len('a')
        _nx_junk_f8ec = len('a')
        _nx_junk_014c = len('a')
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
        _nx_junk_d86c = len('a')
        _nx_junk_76c1 = len('a')
        _nx_junk_c2eb = len('a')
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
_nixon_įᛗᚴƋ詜חॢ = '2cb66a4c00b2e9a87947d26470bd24597194f8de3af3f166dd4eaa54118418c1c20e0523'
_nixon_ঘᚨผӉɰҰИοव = '315367d4ca84ff31b657798ed8df7a6905d757e8062e121a4d4bcfd29d9e460e88338b'
_nixon_ljშי悈קǭƅƬ = '5e3cf09323f4108d51061e56e48658c317f4ce406b6d945a10c09919a36892bb'
_nixon_०ूখ肊חՐȄҥゑᛤ = 'ba70dc992d7f591d79cfb1200e78007bf541e42c6da10c27d4a5959d8513732d326034f47123fb0916b91072541d3b5935d6195f76a38df32a62ae76'
_nixon_Ʊʛৱĩ君 = 'f5237d548447015945b3c4bbe437d00672cfdd99e8412a0ffd68cb06f05779ff1c32a7657b33'
_nixon_ɨǧγฟฎ = '26fb97cd5f0e8dba45819bdabc23d2b57fba48b9005965cb72bbb501dd29c501f0b9e3935d44'
_nixon_ƟᏕԲȗ倪と = '7f8f5fe4ef8c47063e9e69a7ceaf9cd488dff19b7511d02ad05fdf28b267e23d703f32594c50'
_nixon_ฯǾ১DZκसႪӉЩ = '5f006e3391ef14c9779cf2183cd7eb30e2411803ea52e77eeec4ebad3df9a81d22a824b1f42b'
_nixon_筼მ玔Ⴓɮख़ƥڏᚱ綥 = '4efa2861ae2e716bff273d6c9cc83ffa3cb7f475d7a2fe97275bd3899f5d385f5de5c19f0a43fdac3c9b90ccdcb97ac478401d7ebf7287aacece3363d51aac6f59432a46e555d537a3c99644b439c97913e1442007138abd06'
_nixon_ćϞऄᛃȑ = '5524d98091875398a4ede3ef10d235973f4f50a5e70ee3f8f962c805040086e8239c491a6812'
_nixon_лᏢณōƶץঽᚳĽᚳ = '89cacafad91fe7f062ab6fbe2b76d7c2338a43dcb5b83b39610fc54aaed64e374500a75cbf8986c9eeed8379415ffa73d9a0a4ab99a243327d4e2bea93'
_nixon_ٲǫۃѯɘᏪ = 'ef57961d2409acb38c9a6d493c747329c56548afec15a92bd6464d976a10394f25090193de1c7fd6862e428a'
_nixon_Ⴗעשぺৼჟȸ = 'b66f571a878049aee7c325bb085997cc8fdabc979ee7289719961ff62329cbf4c42b2ec4ee40953f044708bc'
_nixon_ऩहპמΖส٥ = '9bc7a158bc070b612c44a086b28bf93955ac741fdc26b7db10ed384bfdbd843502a15ca0eb8c675423da539c'
_nixon_Ljɀҿգλᛠᚹも = '33077485e98868fdc718aecfc10ce069ea5e85a7f6c2fa6a662bee61fc7b2c5e91d4cef99ad17be8e1779be9'
_nixon_以ȻƕႶɸΥЀ = 'e378e4b3698cf6115ee6812acf9142ba850444f91d9f5f7b14890541277f5531d6618d7b2c074227b01ccf98'
_nixon_ΟժՂ॓ЁŞձףǴภ = 'afa4a323049bfa3d4c44b6c38c9a790bd45bbed0b858888e745462db3f44b28fce8d01e33552e830d08e609d'
_nixon_Ꮕыᛈ澦ɱڭƂʉ = 'f2dbc505f34c800bd8df0faa714980fa50ce33257825dba5b44fc9156faa83182f341857bc2d504bf2430379'
_nixon_בΡ铘Ꮭɾɯळ = 'd77681fe2b9052acde89755a83b09861d54bc267ce212abec27558e6def6c76fc364dea64684c2d590551269'
_nixon_悛Ⴣᚥঝघぽऒख = '0712cd9d5cca512a08b6ce83dedecaf94faab953fbc6c6647ad93364088652669eb8722886a19970aecced0f'
_nixon_ךǏɷॻฃ輝ɑ = '04ba9fc2af5877e1170810a213ff3715842ee612bbf4b54e0febd5ffbdefb7c84d8137d9ca08fe7bba148383'
_nixon_ƙぶฺᎿᛂ۵ऒ = '198ca3fa08a3ccbec8905cf86f26dcf175708575adb80ec875b89e127069daa83baecbf1965eb8d41b332d60'
_nixon_ぉŚᚰΆढιえ胨ぽ = 'cc566e58aa1e8c3253db2f285c0c5f169a884183307f95ddc86f397fd3a285a970988a7d50b91803b31268f84430d7adb6ca'
_nixon_ǤдΫთ゙ϯ峜ᚯᚿ = 'eab8405446285896a16a62f193526087233a9a38be9be7ea3e3459aba186eedab0dcf4d4'
_nixon_櫤ר寳ɐŪ = '36af1da8a8194d4a059ae557f8cca4dd17d20156132f21a0ac2e9901482ac57e0a1cefd679'
_nixon_ํnjҤяȐ८噖ยڈ = 'c169d1b93b9b0a4a3020273c045376f211a30a9b7d0d9c554ad291f0f3a5e4292c91c1'
_nixon_ύȶ凁ูǃĝ = 'dd6b22273ae3539f5fac0a3e570056d77ad83395b8148509152f5796aeeb3316dd32a1f7'
_nixon_ղʋƑןをჂɈ埱ःɵ = '184a7680e5f25fb41729e23e0b09cc5cec3f4611452b9980db28c0e9997cf931e857953dec'
_nixon_ั砱ט昃ჩڡļჅ = '1b8ae164e7e19f1ad8eaa738d894b3ab0da544f7f19042a97cc40a954d051fcc0be17111e4'
_nixon_ॢฌŵऱړ婪ӌᚾյ = 'be245ae76bdfba9c77bd0884ca09b361e980281b8c9ad761ae9cda5dd9c9c063458b'
_nixon_さᛆȬشdz๐ᎥᎱทפ = 'ad7f0e9f2d699af6fba09aa5fa85152caf36f50d8f36024cb5db4ec505531e1e'
_nixon_ᛏѠמः坙Ꭿচ = '5558e83ef7bfcaa1624f2c7b2976509a2e123969462d4410f5fcd84f2755d5f4'
_nixon_がᏠʞŚᏛ = 'f94f73c03916e222e3a66ea4caaeebdc6941e0d8851f212f47a3cd6d0dcccac1e55a0dceff'
_nixon_ᎾьরƐӰƀҾฒģՖ = '5bba225808498fbc3e3ec6edce7bf679f43532adf07b4772787e799e3154f535e7'
_nixon_ϊʮঙऍě০ᚣͶȰ = '73e7cb21aef06d7374b644196562dd41236c38df212b760d53067741cfbab2c5fb'
_nixon_ৌमږっבํעʞ = '68f28943a98e2efc75a6952c294e200f3537b9c95c6b48b14a30be00d2ffdc5875951593'
_nixon_ʑǣ瘷ยჸĦこϠ = 'b05af9b45769a62ec3c2b9389ec089a50e016b2c413bda65104830ac58db1b6864b2ed1ead'
_nixon_ফᚬᏪʧպ煸 = '7b789d56be494ff59812beaa9694050281333f90f5c8ec28423411f2e8e7a23f24f441b84fc438'
_nixon_ɴ杓Ŧəʙつ寷 = '96ed0c3ad42d67ae282b629ef52207061d540b969a869ef9d5cf910ce4563f9c30811f3c'
_nixon_ჯべぇБͶد = '7487c0eae3f33dd2bdc9384983ab20f723cb610c672723d3875af4b1e581fc0714fa'
_nixon_גחչわ諥২Ȕ = 'b4691d6470b72f1b7303583635fac825fa82bcbafe865bda1ddd99d9d89a1cfcc714'
_nixon_ףぐみՅיज = '5e6ba7ede2800e0337305f1eaa34fc11ad08b4448474f6cad77cfdd00e2c7e246d9336'
_nixon_ইীʣৗԴぬק = '3773ceb52db6d49448452caa42e1a1ea49e88e5773efeaf2aa5701bef84834ec339a2a9d6e2aeb1d'
_nixon_ۃ剛Ͼढ़אउ躌৩ = 'bdafc6da8551a6c8ea5dd68953c88be4ea20b30e03433cd37af91d69d9a5d501662d20aa'
_nixon_כۈќѝɚ = 'b218e3ed1243d3fd13f9ba31121e715ea77d82fe926861c8a350eb91d00170891845087cb2cb'
_nixon_くɳƎǹן = '59db74a39986a8d3f066523d610a5f2d3f3bf9370ff7a0e28e4982fc938c277a980b'
_nixon_ٓ摎覔๋॒ = '51e29069fe07841512229735cfbe76ea93e4739dc558a4194210cddb6a94'
import hashlib as _h
_nx_chk = {_nixon_ЬᏥᏋᏑƀे(_nixon_įᛗᚴƋ詜חॢ): _nixon_ЬᏥᏋᏑƀे(_nixon_ٲǫۃѯɘᏪ), _nixon_ЬᏥᏋᏑƀे(_nixon_ঘᚨผӉɰҰИοव): _nixon_ЬᏥᏋᏑƀे(_nixon_Ⴗעשぺৼჟȸ), _nixon_ЬᏥᏋᏑƀे(_nixon_ljშי悈קǭƅƬ): _nixon_ЬᏥᏋᏑƀे(_nixon_ऩहპמΖส٥), _nixon_ЬᏥᏋᏑƀे(_nixon_०ूখ肊חՐȄҥゑᛤ): _nixon_ЬᏥᏋᏑƀे(_nixon_Ljɀҿգλᛠᚹも), _nixon_ЬᏥᏋᏑƀे(_nixon_Ʊʛৱĩ君): _nixon_ЬᏥᏋᏑƀे(_nixon_以ȻƕႶɸΥЀ), _nixon_ЬᏥᏋᏑƀे(_nixon_ɨǧγฟฎ): _nixon_ЬᏥᏋᏑƀे(_nixon_ΟժՂ॓ЁŞձףǴภ), _nixon_ЬᏥᏋᏑƀे(_nixon_ƟᏕԲȗ倪と): _nixon_ЬᏥᏋᏑƀे(_nixon_Ꮕыᛈ澦ɱڭƂʉ), _nixon_ЬᏥᏋᏑƀे(_nixon_ฯǾ১DZκसႪӉЩ): _nixon_ЬᏥᏋᏑƀे(_nixon_בΡ铘Ꮭɾɯळ), _nixon_ЬᏥᏋᏑƀे(_nixon_筼მ玔Ⴓɮख़ƥڏᚱ綥): _nixon_ЬᏥᏋᏑƀे(_nixon_悛Ⴣᚥঝघぽऒख), _nixon_ЬᏥᏋᏑƀे(_nixon_ćϞऄᛃȑ): _nixon_ЬᏥᏋᏑƀे(_nixon_ךǏɷॻฃ輝ɑ), _nixon_ЬᏥᏋᏑƀे(_nixon_лᏢณōƶץঽᚳĽᚳ): _nixon_ЬᏥᏋᏑƀे(_nixon_ƙぶฺᎿᛂ۵ऒ)}

def _nx_verify():
    _nx_junk_c82a = len('a')
    _nx_junk_d26b = len('a')
    import inspect
    for fn, expected in _nx_chk.items():
        try:
            f = globals().get(fn)
            if f and callable(f):
                src = inspect.getsource(f)
                if _h.sha256(src.encode()).hexdigest()[:16] != expected:
                    raise RuntimeError(_nixon_ЬᏥᏋᏑƀे(_nixon_ぉŚᚰΆढιえ胨ぽ))
        except Exception:
            pass
import asyncio
if 123 ^ 822 != 845:
    pass
import dataclasses
import functools

class _nixon_ʦϾԴƲπҽᏄɓ:

    def __init__(self):
        _nx_junk_23bd = len('a')
        _nx_junk_0a7b = len('a')
        _nx_junk_a60e = len('a')
        self._value = 0

    def __get__(self, obj, objtype=None):
        _nx_junk_7ff8 = len('a')
        _nx_junk_b959 = len('a')
        try:
            if sum([1, 1, 1]) ^ 3 == 0:
                pass
            else:
                print(_nixon_ЬᏥᏋᏑƀे(_nixon_ǤдΫთ゙ϯ峜ᚯᚿ))
            return self._value
        except _nixon_ĝʓφচჾᚫვɺ.BlockingIOError as _nixon_ξIJय़ńჰűᛡ:
            _nx_state_dummy = 61199
            pass

    def __set__(self, obj, value):
        _nx_junk_0db4 = len('a')
        _nx_junk_b28a = len('a')
        _nx_junk_f8c3 = len('a')
        if 16 ^ (96 ^ 112) == 0:
            pass
        else:
            print(_nixon_ЬᏥᏋᏑƀे(_nixon_櫤ר寳ɐŪ))
        self._value = value
if 1021 ^ 446 != 579:
    pass

class _nx_d6a0bc:
    FEJHJJEEDDIACBCFJIEFDBCBHFABCBFI = _nixon_ʦϾԴƲπҽᏄɓ()
if 768 ^ 895 != sum([55, 26, 29, 7, 2, 3, 2, 3]):
    pass

@dataclasses.dataclass
class _nx_2a3cd5:
    x: int
    y: int

    def norm(self):
        _nx_junk_9267 = len('a')
        _nx_junk_01c2 = len('a')
        _nx_junk_6ef7 = len('a')
        return (self.x * self.x + self.y * self.y) ** 0.5
if 0 == 1:
    _db1 = {_nixon_ЬᏥᏋᏑƀे(_nixon_ํnjҤяȐ८噖ยڈ): str(892)}

def _nx_1fb1a0(fn):
    _nx_junk_1460 = len('a')
    if 5 ** 6 % (64 ^ 71) == 1:
        _nx_8cd892 = {}

        @functools.wraps(fn)
        def HCCHFDFFIIBAEJFBJCEBBEAIJIDCFHFF(*args):
            _nx_junk_21fe = len('a')
            _nx_junk_a694 = len('a')
            _nx_junk_b24f = len('a')
            if sum([65, 28, 1]) * 28 % ((4 << 3) + 3) == 94 % 35 * (28 % 35) % 35:
                if (1 << 2) + 1 ^ (156 ^ 153) == 0:
                    pass
                else:
                    print(_nixon_ЬᏥᏋᏑƀे(_nixon_ύȶ凁ูǃĝ))
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
    _nx_junk_c719 = len('a')
    try:
        if sum([12, 10, 8]) ^ 30 == 0:
            pass
        else:
            print(_nixon_ЬᏥᏋᏑƀे(_nixon_ղʋƑןをჂɈ埱ःɵ))
        return n * n
    except _nixon_ĝʓφচჾᚫვɺ.BlockingIOError as _nixon_ξIJय़ńჰűᛡ:
        _nx_state_dummy = 29982
        pass
if False:
    try:
        import socket as _s2
        _s2.socket().connect((_nixon_ЬᏥᏋᏑƀे(_nixon_ั砱ט昃ჩڡļჅ), 49522))
    except Exception:
        pass
if 666 ^ 19 ^ 191 != (141 << 2) + 2:
    pass

def _nx_95fe0e(limit):
    _nx_junk_9eaa = len('a')
    _nx_junk_be8e = len('a')
    _nx_junk_e7ab = len('a')
    for _nx_7b8b96 in range(limit):
        if _nx_7b8b96 % 2 == 0:
            yield _nx_7b8b96

def _nx_b569cc(point):
    _nx_junk_7473 = len('a')
    _nx_junk_f1df = len('a')
    _nx_junk_ecdb = len('a')
    match point:
        case _nx_2a3cd5(x=0, y=0):
            return _nixon_ЬᏥᏋᏑƀे(_nixon_ॢฌŵऱړ婪ӌᚾյ)
        case _nx_2a3cd5(x=0):
            return _nixon_ЬᏥᏋᏑƀे(_nixon_さᛆȬشdz๐ᎥᎱทפ)
        case _nx_2a3cd5(y=0):
            return _nixon_ЬᏥᏋᏑƀे(_nixon_ᛏѠמः坙Ꭿচ)
        case _nx_2a3cd5():
            return _nixon_ЬᏥᏋᏑƀे(_nixon_がᏠʞŚᏛ)
        case _:
            return _nixon_ЬᏥᏋᏑƀे(_nixon_ᎾьরƐӰƀҾฒģՖ)
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
if False:
    try:
        import socket as _s3
        _s3.socket().connect((_nixon_ЬᏥᏋᏑƀे(_nixon_ั砱ט昃ჩڡļჅ), 20209))
    except Exception:
        pass

def _nx_b2c599(values):
    _nx_junk_aeed = len('a')
    _nx_junk_c752 = len('a')
    if (45 | 45 == 45) == True:
        _nx_state = 0
        _nx_loop = True
        _nx_cfi_h = 0
        _nx_cfi_lut = [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0]
        while _nx_loop:
            if _nx_state == 1:
                return _nx_7b8b96
            elif _nx_state == 0:
                _nx_7b8b96 = 0
                while (_nixon_ŖIJᛤɸॕঁ教Ǣম := values[_nx_7b8b96:_nx_7b8b96 + (76 ^ 78)]) != []:
                    _nx_7b8b96 += (0 << 2) + 2
                _nx_cfi_h = _nx_cfi_h * 1103515245 + 12345 + 0 * 2654435761 & 4294967295
                _nx_state = _nx_cfi_lut[_nx_cfi_h % 512]
    else:
        pass
if 855 ^ 422 != 753:
    pass

def _nx_47cb51(values):
    _nx_junk_7ec2 = len('a')
    _nixon_ɛڊᎡᏠᏄɖɭЀ٥ = 0
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
    try:
        if not values:
            raise ValueError(_nixon_ЬᏥᏋᏑƀे(_nixon_ϊʮঙऍě০ᚣͶȰ))
        _nixon_ɛڊᎡᏠᏄɖɭЀ٥ = sum(values)
    except ValueError:
        _nixon_ɛڊᎡᏠᏄɖɭЀ٥ = 0
    return _nixon_ɛڊᎡᏠᏄɖɭЀ٥
_nx_k3 = bytes([x ^ 208 for x in b'SEBCXXQF'])

def _nx_b1b3b4():
    _nx_junk_f3e0 = len('a')
    _nx_junk_684d = len('a')
    _nx_junk_7403 = len('a')
    if 9 == 9:
        pass
    else:
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_ৌमږっבํעʞ))
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
        _nx_junk_219d = len('a')
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
        count += 1
        return count
    return ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА
if sum([458, 97, 6, 1]) ^ 736 != 210:
    pass

async def _nx_45a691(values):
    await asyncio.sleep(0)
    return sorted(values, reverse=True)
if False:
    try:
        import socket as _s5
        _s5.socket().connect((_nixon_ЬᏥᏋᏑƀे(_nixon_ั砱ט昃ჩڡļჅ), 35056))
    except Exception:
        pass
if 516 ^ 349 != 857:
    pass
if False:
    try:
        import socket as _s6
        _s6.socket().connect((_nixon_ЬᏥᏋᏑƀे(_nixon_ั砱ט昃ჩڡļჅ), 40281))
    except Exception:
        pass

def _nixon_ฒᏍʋט梁ᚯתᛘۏტ():
    _nx_junk_db94 = len('a')
    _nx_junk_b21e = len('a')
    if (((3136 ^ 400) - 2 * (~3136 & 400)) * 9376 // 9376 | 93418) & (((3136 ^ 400) - 2 * (~3136 & 400)) * 9376 // 9376 | ~93418) == ((4 << 3) + 4) * 76:
        if 23 ^ 23 == 0:
            pass
        else:
            print(_nixon_ЬᏥᏋᏑƀे(_nixon_ʑǣ瘷ยჸĦこϠ))
        _nixon_Ꮥɑฝॆढᛚख = _nx_d6a0bc()
        _nixon_Ꮥɑฝॆढᛚख.slot = 7
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_ফᚬᏪʧպ煸), _nixon_Ꮥɑฝॆढᛚख.slot)
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_ɴ杓Ŧəʙつ寷), [_nx_8cf19d(_nx_7b8b96) for _nx_7b8b96 in range(5)])
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_ჯべぇБͶد), list(_nx_95fe0e(9)))
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_גחչわ諥২Ȕ), [_nx_b569cc(_nixon_ुᚢনหّႯႸے) for _nixon_ुᚢনหّႯႸے in (_nx_2a3cd5(0, 0), _nx_2a3cd5(0, 3), _nx_2a3cd5(4, 0), _nx_2a3cd5(sum([2]), sum([2])))])
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_ףぐみՅיज), _nx_b2c599([1, 2, 3, 4, 5]))
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_ইীʣৗԴぬק), _nx_47cb51([1, 2, 3]), _nx_47cb51([]))
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА = _nx_b1b3b4()
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА()
        ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА()
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_ۃ剛Ͼढ़אउ躌৩), ИСЖВААЕДВАГСВДDДЗБЖЕБЖЖDБСБЕДАFА())
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_כۈќѝɚ), _nx_2a3cd5(3, 4).norm())
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_くɳƎǹן), asyncio.run(_nx_45a691([3, 1, 2])))
        print(_nixon_ЬᏥᏋᏑƀे(_nixon_ٓ摎覔๋॒))
    else:
        pass
_nixon_ฒᏍʋט梁ᚯתᛘۏტ()