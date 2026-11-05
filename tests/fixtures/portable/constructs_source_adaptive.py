def _nixon_ЬᏥᏋᏑƀे(_s):
    _nx_junk_abb3 = len('a')
    import hashlib as _nx_ha, hmac as _nx_hm
    _nx_k = bytes([9, 160, 183, 126, 22, 123, 81, 14, 155, 68, 168, 46, 145, 192, 5, 118, 159, 131, 205, 68, 134, 54, 85, 234, 98, 26, 60, 66, 255, 50, 60, 246])
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
        _nx_junk_d329 = len('a')
        _nx_junk_4e4d = len('a')
        return _v << _n & _nx_M | _v >> 32 - _n

    def _nx_qr(_x, _a, _b, _c, _d):
        _nx_junk_cc32 = len('a')
        _nx_junk_2e68 = len('a')
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
        _nx_junk_1421 = len('a')
        _nx_junk_5c09 = len('a')
        _nx_junk_15ee = len('a')
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
_nixon_įᛗᚴƋ詜חॢ = 'cdc608f335666491381d0bc1e5058c7d3a0d0903df39aa11452589765ebb0da52be6fd04'
_nixon_ঘᚨผӉɰҰИοव = 'c63e4ce6819f7875240b3cb964d214facc55e3040e273dbfb1956d8f255fcdf2cc3276'
_nixon_ljშי悈קǭƅƬ = '6bd662da7e860ea7f5afde367b4c537e1ab897f6c771b9a602b27239cdd31383'
_nixon_०ूখ肊חՐȄҥゑᛤ = '7fd72d2d55df41fefed7ebe5290150ac81962b5f457858050aeebae27cbfbe3b8e6df0d1726422540011d353846e466116d404e041e49f152bb3dd96'
_nixon_Ʊʛৱĩ君 = '12bc53f36ade196da92d3249747cf4cd22a1ced2ab7be25b5885f805b117b6a6f11c9f233aa3'
_nixon_ɨǧγฟฎ = '72691cdc0b62328f22c9eb9cc6ec840fe6212d5dabd9362c4ee115a8b66a25392750ba18d650'
_nixon_ƟᏕԲȗ倪と = 'cc296539ada62b20adaa8d0d728d0b69c078fa0b311beb59d45a8c4276bec76b42d59d68abcf'
_nixon_ฯǾ১DZκसႪӉЩ = 'c5448921578e74848ec9286ef12b883b27bf5e974dd5e2cac31f72da3c9de04b486c7017782e'
_nixon_筼მ玔Ⴓɮख़ƥڏᚱ綥 = 'c5433442ebcd1b9270635227dc85a0c87a9d984679f7f58796e2ccd080827840a6778f98ceb98d6ee9389086cb4282493ca30b6ec9973deec6c60ce708b3be02f6edb65c170a9f0f7a2463e6d7750d1466ef2b16e5bdbceef8'
_nixon_ćϞऄᛃȑ = '8016555a0a5bc86b2df6a3a4b7127b24fe93c21ac169a9d8fc840191a8b9a5f05f94c6738735'
_nixon_лᏢณōƶץঽᚳĽᚳ = '528734d3f7077e7e46fdc4b2e39eda3c8135ebaffcf8cfee6c6b973218405aba1995f1b24b8b3b75fc43a144f8ca03c445254c3d70349fb08de717e672'
_nixon_ٲǫۃѯɘᏪ = '720e8d1807e8f7817d0a41ecf906cad023e7010658672498eacf7d9a6400d7effb1c95791cc88b937b503f15'
_nixon_Ⴗעשぺৼჟȸ = 'fac64cf780590aeeaac3cd5bc33d3a82ccf1ba660d736b0745c6db9e414d1e69edb1597b5c3c73bedb8564e9'
_nixon_ऩहპמΖส٥ = '31a32a366faad0dc035fe0b0048a438a360ee8da52967cea3212f6dd38cd9dc8716405350511312bc8633e16'
_nixon_Ljɀҿգλᛠᚹも = '2cec279a5d608009315fdb8493199db0dbf373c0690008157e14fa9fb6ef766bffed487de83c5069a8c1464a'
_nixon_以ȻƕႶɸΥЀ = '81ce65bdb583555fcda54dc99f0ae7ef83402304af680401ead74ed053e67cade01ef5efa1e90f23752be49e'
_nixon_ΟժՂ॓ЁŞձףǴภ = '473f6c12f6d42a06ec063407f66d89ddf6a6145ec2e4e14f1df71fe7a384028163e82ef46337761b215250bf'
_nixon_Ꮕыᛈ澦ɱڭƂʉ = '29a910eca15288599708fb561da98c501fe0d59b8d66fcdd033a62c6cc2eb2c8e8cf97e9d14f1bbaf7d488db'
_nixon_בΡ铘Ꮭɾɯळ = '29ae36e66db2ecd52fc75d0261102b94db6ebe1a9d46f4beff7e1785a822181421f7a201dcf676dac5297d33'
_nixon_悛Ⴣᚥঝघぽऒख = 'c0b7aad60d76796a36ece9d42419c0807fb94b9718b5179a43d230e7ff09199e689514e422ce848afd23a074'
_nixon_ךǏɷॻฃ輝ɑ = '1b8f848d90f056183939740aac23041368a0d13888fc7209a03c8d15e7e1b7bfc9998dc5696c20b3a3f10b9e'
_nixon_ƙぶฺᎿᛂ۵ऒ = '4f250c48a56aae5a909c4715be890796c9048be2f2a684e3c0b46630738d808b73c0c7e566bd86d17d41b60a'
_nixon_ぉŚᚰΆढιえ胨ぽ = 'b0381d0eade24562dd24f8e8706fa68db34af14aeaba28fd2bc98b9d24eca07480eb66b87b259c108390a2d21d03243cee06'
_nixon_ǤдΫთ゙ϯ峜ᚯᚿ = 'ed72a7633647b784668f30caaee86efaf01ca3c3475f95dbc94e0749ab9793fe863b9e77'
_nixon_櫤ר寳ɐŪ = '74578a5704f18ba310306a61170a0c9b83195af9c8c7bb2f40512be18fdcf59a7c6458884d'
_nixon_ํnjҤяȐ८噖ยڈ = 'b6ca8a0ba134b8e093ed6ade899ee976e4cf465ea239b7c765c3e4c735c692809cbd90'
_nixon_ύȶ凁ูǃĝ = 'ef16e8b87f3f984489d133ed80f97a95072f008390d52ed02173aeedff4b65a7b5855519'
_nixon_ղʋƑןをჂɈ埱ःɵ = 'a7db2786229e7a2b3c4f566111416e0ff10958cc4afe2b2a93ec462855ab7c46a0d2caf79f'
_nixon_ั砱ט昃ჩڡļჅ = '3a97256ba3c22ab5387a5bc7c8593b6bb68afb1d9d1c903369ccb010e6b58bea5c72568da4'
_nixon_ॢฌŵऱړ婪ӌᚾյ = 'b5da0448ffce7b7d50d84d3895d3b3412fd5bf33bc6c9f828f87fd2f3c7f0e1a0068'
_nixon_さᛆȬشdz๐ᎥᎱทפ = '1e5960e485b7df31f93c4eb85132a9d5492e8997500c6a83f0ce30502e399e9f'
_nixon_ᛏѠמः坙Ꭿচ = '17dc22cffe0e485da428fe7c94197d982b258397f3d6788ac47de9dff888398b'
_nixon_がᏠʞŚᏛ = '7de198eacebe0f57c58bda0d80bc2fe94f1e9798b51d09f9b8bfab827a94a8eecd7797819b'
_nixon_ᎾьরƐӰƀҾฒģՖ = '4701f4de4d8ebaeb7ae6434416b2c73dc8bf0620493007cd9c123dc8de6cbadd17'
_nixon_ϊʮঙऍě০ᚣͶȰ = '2a907ccd2bf63f3ebaa25d7de42a10e072520f1245e7def19f86e9aa416d2e0d81'
_nixon_ৌमږっבํעʞ = '3fe15c21945c0faf44fce054c63332a9241d18178e72b6d51a24851bece05e3f4a7300f8'
_nixon_ʑǣ瘷ยჸĦこϠ = '816a2c6f752f8428e7ef074aa5b0571877b6e0087bc5bbfb95d35335c8ec52e9ea1f7712c6'
_nixon_ফᚬᏪʧպ煸 = 'dc5d89a4d321c784eba22117a255ae74e69bbf4f90bed19688dbed309e21b29bf68299f12ac581'
_nixon_ɴ杓Ŧəʙつ寷 = '8f46eb9ea1fd57d078e35ddac1b35915227dd0be8c5b08c93ad0fbaba7c180efa9afb30b'
_nixon_ჯべぇБͶد = 'c96386e7dd5901bf710529d273f26aba75d2ba981c0fbc814d9c2be72a8e5e91d8d2'
_nixon_גחչわ諥২Ȕ = 'a97939f048c6ec3a9cbe4eb56a519939f53dabc05ca10018bed80db66624af9ec9df'
_nixon_ףぐみՅיज = 'b5ef063fad94af3c08fb1c7b7b94c0a756a9ab44234341ad1d01129335a2cf1b5f69d1'
_nixon_ইীʣৗԴぬק = 'de6811318d7adce88b5cc92b99e54c6522ca2f606e131d1b13ca0133a56b4dcac21c895d2ca21ee2'
_nixon_ۃ剛Ͼढ़אउ躌৩ = 'ea5b07cf372ad8eb48dce46b72fa024e1ac2e0a4a266d1e56f3fe22e2dcba198f1e78c76'
_nixon_כۈќѝɚ = '0a96a473d0b31207a0c464210b15e14ebe1dc73438387d1a8ff51e29a6b1ca8107d389ee8c9c'
_nixon_くɳƎǹן = 'a75a330e950b982dc53a8a453ea5d46e3eb1bceaa2325bd86d230a9cc7485fa66869'
_nixon_ٓ摎覔๋॒ = 'f43d10c52fde48bb6e93309e49c088255b2c1fcc30685b93aa6c3e39c33f'
import hashlib as _h
_nx_chk = {_nixon_ЬᏥᏋᏑƀे(_nixon_įᛗᚴƋ詜חॢ): _nixon_ЬᏥᏋᏑƀे(_nixon_ٲǫۃѯɘᏪ), _nixon_ЬᏥᏋᏑƀे(_nixon_ঘᚨผӉɰҰИοव): _nixon_ЬᏥᏋᏑƀे(_nixon_Ⴗעשぺৼჟȸ), _nixon_ЬᏥᏋᏑƀे(_nixon_ljშי悈קǭƅƬ): _nixon_ЬᏥᏋᏑƀे(_nixon_ऩहპמΖส٥), _nixon_ЬᏥᏋᏑƀे(_nixon_०ूখ肊חՐȄҥゑᛤ): _nixon_ЬᏥᏋᏑƀे(_nixon_Ljɀҿգλᛠᚹも), _nixon_ЬᏥᏋᏑƀे(_nixon_Ʊʛৱĩ君): _nixon_ЬᏥᏋᏑƀे(_nixon_以ȻƕႶɸΥЀ), _nixon_ЬᏥᏋᏑƀे(_nixon_ɨǧγฟฎ): _nixon_ЬᏥᏋᏑƀे(_nixon_ΟժՂ॓ЁŞձףǴภ), _nixon_ЬᏥᏋᏑƀे(_nixon_ƟᏕԲȗ倪と): _nixon_ЬᏥᏋᏑƀे(_nixon_Ꮕыᛈ澦ɱڭƂʉ), _nixon_ЬᏥᏋᏑƀे(_nixon_ฯǾ১DZκसႪӉЩ): _nixon_ЬᏥᏋᏑƀे(_nixon_בΡ铘Ꮭɾɯळ), _nixon_ЬᏥᏋᏑƀे(_nixon_筼მ玔Ⴓɮख़ƥڏᚱ綥): _nixon_ЬᏥᏋᏑƀे(_nixon_悛Ⴣᚥঝघぽऒख), _nixon_ЬᏥᏋᏑƀे(_nixon_ćϞऄᛃȑ): _nixon_ЬᏥᏋᏑƀे(_nixon_ךǏɷॻฃ輝ɑ), _nixon_ЬᏥᏋᏑƀे(_nixon_лᏢณōƶץঽᚳĽᚳ): _nixon_ЬᏥᏋᏑƀे(_nixon_ƙぶฺᎿᛂ۵ऒ)}

def _nx_verify():
    _nx_junk_8856 = len('a')
    _nx_junk_72f1 = len('a')
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
        _nx_junk_9d61 = len('a')
        self._value = 0

    def __get__(self, obj, objtype=None):
        _nx_junk_9ec9 = len('a')
        _nx_junk_6346 = len('a')
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
        _nx_junk_1872 = len('a')
        _nx_junk_133c = len('a')
        _nx_junk_31fa = len('a')
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
        _nx_junk_059b = len('a')
        _nx_junk_0331 = len('a')
        return (self.x * self.x + self.y * self.y) ** 0.5
if 0 == 1:
    _db1 = {_nixon_ЬᏥᏋᏑƀे(_nixon_ํnjҤяȐ८噖ยڈ): str(892)}

def _nx_1fb1a0(fn):
    _nx_junk_60cf = len('a')
    _nx_junk_60c0 = len('a')
    if 5 ** 6 % (64 ^ 71) == 1:
        _nx_8cd892 = {}

        @functools.wraps(fn)
        def HCCHFDFFIIBAEJFBJCEBBEAIJIDCFHFF(*args):
            _nx_junk_d6da = len('a')
            _nx_junk_7936 = len('a')
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
    _nx_junk_3fc0 = len('a')
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
    _nx_junk_8a4a = len('a')
    for _nx_7b8b96 in range(limit):
        if _nx_7b8b96 % 2 == 0:
            yield _nx_7b8b96

def _nx_b569cc(point):
    _nx_junk_10a5 = len('a')
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
    _nx_junk_4570 = len('a')
    _nx_junk_7214 = len('a')
    _nx_junk_f701 = len('a')
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
    _nx_junk_c4c4 = len('a')
    _nx_junk_630b = len('a')
    _nx_junk_2d41 = len('a')
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
    _nx_junk_d092 = len('a')
    _nx_junk_168f = len('a')
    _nx_junk_3c56 = len('a')
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
        _nx_junk_a7e0 = len('a')
        _nx_junk_b372 = len('a')
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
    _nx_junk_8f61 = len('a')
    _nx_junk_c7a6 = len('a')
    _nx_junk_3fc8 = len('a')
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