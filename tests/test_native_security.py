"""Regression tests for the C1 native/encrypt memory-safety audit.

Covers the confirmed bugs fixed in this pass:

  1. native/enforcement.c   — fatal sigaction sa_flags was uninitialized stack
                              garbage; setrlimit(RLIMIT_CORE, {0, RLIM_INFINITY})
                              failed with EPERM under any finite inherited hard
                              limit, silently dropping core-dump enforcement.
  2. native/simd_vm.c       — the SSE dispatch path ignored handler instruction
                              lengths (pc += 1 per byte), so identical bytecode
                              executed differently in simd_dispatch() and
                              simd_dispatch_scalar().
  3. encrypt/stub_aead_template.c — the runtime key and Poly1305 one-time key
                              were never wiped before jumping into the payload;
                              the empty asm barrier constrained nothing.
  4. native/platform.h      — size_t used without <stddef.h>; the header did
                              not compile standalone.

Plus invariant tests for the crypto the audit validated: AES-256 (FIPS-197
vector), ChaCha20-Poly1305 (RFC 8439 cross-checks captured from an independent
implementation), HKDF-SHA256 (RFC 5869 case 1), NIX container round-trips, and
the whitebox Feistel decrypt(encrypt(x)) == x round-trip.

C harnesses are compiled into pytest tmp_path with the host gcc; each test
skips cleanly when a compiler is unavailable.
"""

import os
import shutil
import stat
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NATIVE = os.path.join(ROOT, "native")
ENCRYPT = os.path.join(ROOT, "encrypt")

sys.path.insert(0, ROOT)

GCC = shutil.which("gcc")
GXX = shutil.which("g++")

needs_gcc = pytest.mark.skipif(GCC is None, reason="gcc not available")
needs_gxx = pytest.mark.skipif(GXX is None, reason="g++ not available")


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)


def _compile(tmp_path, out_name, sources, extra=(), compiler=None):
    cc = compiler or GCC
    out = tmp_path / out_name
    cmd = [cc, "-O2", "-Wall", "-Wextra"] + list(extra) + list(sources) + ["-o", str(out)]
    res = _run(cmd)
    assert res.returncode == 0, f"compile failed:\n{res.stderr}"
    return out


# ---------------------------------------------------------------------------
# 1. Compile verification of every changed C file (and the untouched-but-in-
#    shard test file).  simd_vm.c targets x86 SSE4.1 on x86 hosts; the file
#    guards the intrinsics behind __SSE4_1__ so it compiles everywhere.
# ---------------------------------------------------------------------------

@needs_gcc
@pytest.mark.parametrize("source,relpath,extra", [
    ("enforcement.c", "native/enforcement.c", []),
    ("simd_vm.c", "native/simd_vm.c", ["-msse4.1"]),
    ("simd_vm_test.c", "native/simd_vm_test.c", ["-msse4.1", "-I", NATIVE]),
    ("pe_load_config.c", "native/pe_load_config.c", []),
])
def test_c_files_syntax_clean(source, relpath, extra):
    res = _run([GCC, "-fsyntax-only", "-Wall", "-Wextra"] + extra
               + [os.path.join(ROOT, relpath)])
    assert res.returncode == 0, f"{relpath} does not compile clean:\n{res.stderr}"


@needs_gxx
def test_cpp_files_syntax_clean():
    for relpath in ("native/core.cpp", "native/whitebox_feistel.cpp",
                    "native/core_abi_test.cpp"):
        res = _run([GXX, "-fsyntax-only", "-Wall", "-Wextra", "-std=c++17",
                    "-I", NATIVE, os.path.join(ROOT, relpath)])
        assert res.returncode == 0, f"{relpath} does not compile clean:\n{res.stderr}"


@needs_gcc
def test_platform_h_is_self_contained(tmp_path):
    """platform.h used size_t without including <stddef.h>: including it first
    in a fresh translation unit was a compile error."""
    probe = tmp_path / "probe.c"
    probe.write_text('#include "platform.h"\nint main(void) { return 0; }\n')
    res = _run([GCC, "-fsyntax-only", "-Wall", "-Wextra", "-I", NATIVE, str(probe)])
    assert res.returncode == 0, f"platform.h not self-contained:\n{res.stderr}"


# ---------------------------------------------------------------------------
# 2. enforcement.c — core-limit enforcement under a finite inherited hard
#    limit, and the fatal-signal kill ladder.
# ---------------------------------------------------------------------------

_ENF_HARNESS = r"""
#include <stdio.h>
#include <sys/resource.h>
#include <sys/prctl.h>
#include <unistd.h>
#include <signal.h>
extern int nx_apply_protections(void);
int main(int argc, char **argv) {
    if (argc > 1) {
        /* signal-ladder mode: install handlers then raise a fatal signal */
        nx_apply_protections();
        raise(SIGABRT);
        printf("FAIL: survived SIGABRT\n");
        return 1;
    }
    /* finite inherited hard limit: the systemd/container case */
    struct rlimit pre = {1024, 1024};
    if (setrlimit(RLIMIT_CORE, &pre) != 0) { perror("prelimit"); return 2; }
    int applied = nx_apply_protections();
    struct rlimit rl;
    getrlimit(RLIMIT_CORE, &rl);
    int dumpable = prctl(PR_GET_DUMPABLE, 0, 0, 0, 0);
    if ((applied & 1) == 0) { printf("FAIL: dumpable bit not applied\n"); return 1; }
    if ((applied & 2) == 0) { printf("FAIL: core limit not applied\n"); return 1; }
    if (rl.rlim_cur != 0 || rl.rlim_max != 0) {
        printf("FAIL: core limit cur=%lu max=%lu\n",
               (unsigned long)rl.rlim_cur, (unsigned long)rl.rlim_max);
        return 1;
    }
    if (dumpable != 0) { printf("FAIL: process still dumpable\n"); return 1; }
    printf("OK\n");
    return 0;
}
"""


@needs_gcc
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="linux-only enforcement")
def test_enforcement_core_limit_applies_under_finite_hard_limit(tmp_path):
    """setrlimit(RLIMIT_CORE, {0, RLIM_INFINITY}) fails with EPERM when the
    inherited hard limit is finite, so the old enforcement silently never
    applied.  The fix lowers the hard limit to 0, which always succeeds."""
    src = tmp_path / "enf.c"
    src.write_text(_ENF_HARNESS)
    binary = _compile(tmp_path, "enf", [str(src), os.path.join(NATIVE, "enforcement.c")])
    res = _run([str(binary)])
    assert res.returncode == 0, f"enforcement harness failed:\n{res.stdout}{res.stderr}"
    assert "OK" in res.stdout


@needs_gcc
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="linux-only enforcement")
def test_enforcement_fatal_signal_exits_137(tmp_path):
    """With sa_flags correctly zeroed the fatal handler runs and _exit(137)s;
    uninitialized garbage could set SA_RESETHAND/SA_SIGINFO and break this."""
    src = tmp_path / "enf.c"
    src.write_text(_ENF_HARNESS)
    binary = _compile(tmp_path, "enf", [str(src), os.path.join(NATIVE, "enforcement.c")])
    res = subprocess.run([str(binary), "sig"], capture_output=True, timeout=30)
    assert res.returncode == 137, f"expected silent exit 137, got {res.returncode}"


# ---------------------------------------------------------------------------
# 3. simd_vm.c — scalar/SSE dispatch equivalence.  The SSE path used to step
#    pc one byte per iteration, re-executing operand bytes as opcodes.
# ---------------------------------------------------------------------------

_VM_HARNESS = r"""
#include "simd_vm.h"
#include <stdio.h>
#include <string.h>

/* Run one program through both dispatchers on identical initial state and
 * compare everything observable.  Returns 0 when they agree. */
static int compare(const uint8_t *prog, size_t n, const char *name) {
    SimdVmState a, b;
    simd_vm_init(&a);
    simd_vm_init(&b);
    for (int i = 0; i < 16; i++) { a.regs[i] = 3 + i; b.regs[i] = 3 + i; }
    int ra = simd_dispatch_scalar(&a, prog, n);
    int rb = simd_dispatch(&b, prog, n);  /* SSE path when available */
    if (ra != rb || a.pc != b.pc || a.halted != b.halted
        || memcmp(a.regs, b.regs, sizeof(a.regs))
        || memcmp(a.memory, b.memory, sizeof(a.memory))) {
        printf("FAIL %s: scalar(rc=%d,pc=%zu,halt=%d) simd(rc=%d,pc=%zu,halt=%d)\n",
               name, ra, a.pc, a.halted, rb, b.pc, b.halted);
        return 1;
    }
    return 0;
}

int main(void) {
    int fails = 0;

    /* Multi-byte instructions crossing several 16-byte windows. */
    uint8_t prog[80];
    size_t n = 0;
    uint8_t ops[][3] = {{1,0,1},{2,2,1},{3,3,1},{4,4,1},{5,5,1},{6,6,1},
                        {1,7,2},{1,8,3},{1,9,4},{1,10,5},{1,11,6},{3,12,7}};
    for (unsigned i = 0; i < sizeof(ops) / sizeof(ops[0]); i++) {
        prog[n] = ops[i][0]; prog[n + 1] = ops[i][1]; prog[n + 2] = ops[i][2]; n += 3;
    }
    while (n < 60) prog[n++] = 0;
    prog[n++] = 1; prog[n++] = 12; prog[n++] = 13;
    while (n < 64) prog[n++] = 0;
    fails += compare(prog, n, "multi-window arithmetic");

    /* Exactly 16 bytes: one full window then the boundary. */
    uint8_t exact[16] = {1, 0, 1, 1, 2, 3, 0, 0, 1, 4, 5, 0, 2, 6, 7, 0};
    fails += compare(exact, sizeof(exact), "exactly-16-bytes");

    /* 17 bytes: window plus one tail byte. */
    uint8_t seventeen[17] = {1, 0, 1, 1, 2, 3, 0, 0, 1, 4, 5, 0, 2, 6, 7, 0, 0};
    fails += compare(seventeen, sizeof(seventeen), "17-bytes-window-plus-tail");

    /* Memory round-trip through load/store at both memory edges. */
    uint8_t memprog[] = {
        8, 1, 0,       /* store r1 -> mem[r0]  (r0 preloaded 65535) */
        7, 2, 0,       /* load mem[r0] -> r2 */
        1, 3, 2,       /* add r3, r2 */
        0, 0, 0, 0, 0, /* nops */
        8, 1, 0, 7, 2, 0,
    };
    fails += compare(memprog, sizeof(memprog), "memory-load-store");

    /* jmp instructions present (whatever the jump semantics, the two
     * dispatchers must agree on them). */
    uint8_t jmpprog[24] = {9, 20, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0,
                           9, 2, 0, 0, 0, 1, 3, 4, 0, 0, 0, 0};
    fails += compare(jmpprog, sizeof(jmpprog), "jmp-program");

    /* Truncated operand run at the buffer end. */
    uint8_t trunc[] = {1, 0, 1, 9, 1};
    fails += compare(trunc, sizeof(trunc), "truncated-operands");

    if (fails) { printf("%d divergence(s)\n", fails); return 1; }
    printf("scalar/SIMD equivalence holds (simd_available=%d)\n", simd_available());
    return 0;
}
"""


@needs_gcc
def test_simd_vm_scalar_sse_equivalence(tmp_path):
    """Before the fix this harness reported rc/pc/register divergence between
    simd_dispatch_scalar() and simd_dispatch() on the same bytecode."""
    src = tmp_path / "vmtest.c"
    src.write_text(_VM_HARNESS)
    extra = ["-msse4.1"] if _run([GCC, "-msse4.1", "-fsyntax-only", "-x", "c", "/dev/null"]).returncode == 0 else []
    binary = _compile(tmp_path, "vmtest",
                      [str(src), os.path.join(NATIVE, "simd_vm.c")],
                      extra=["-I", NATIVE] + extra)
    res = _run([str(binary)])
    assert res.returncode == 0, f"VM divergence:\n{res.stdout}{res.stderr}"


@needs_gcc
def test_simd_vm_upstream_test_binary_passes(tmp_path):
    """The repo's own native regression binary (memory window + operand
    bounds) must still pass against the fixed dispatcher."""
    binary = _compile(tmp_path, "simd_vm_test",
                      [os.path.join(NATIVE, "simd_vm_test.c"),
                       os.path.join(NATIVE, "simd_vm.c")],
                      extra=["-I", NATIVE, "-msse4.1", "-lm"])
    res = _run([str(binary)])
    assert res.returncode == 0, f"simd_vm_test failed:\n{res.stdout}{res.stderr}"
    assert "FAIL" not in res.stdout


# ---------------------------------------------------------------------------
# 4. encrypt/stub_aead_template.c — key wiping and end-to-end behavior.
# ---------------------------------------------------------------------------

def test_template_wipes_key_material():
    """The empty asm barrier that used to 'protect' the key zeroed nothing.
    The fixed template performs volatile byte wipes of both key and poly_key
    after their last use and before control transfers to the payload."""
    with open(os.path.join(ENCRYPT, "stub_aead_template.c"), encoding="utf-8") as f:
        src = f.read()
    barrier = src.index('__asm__ volatile(""')
    before_barrier = src[:barrier]
    assert "volatile u8 *vk" in before_barrier, "key wipe missing before tail jump"
    assert "volatile u8 *vp" in before_barrier, "poly_key wipe missing before tail jump"
    assert "sizeof(key)" in before_barrier and "sizeof(poly_key)" in before_barrier
    # the wipe must come AFTER the last crypto use (the chacha_xor decrypt call)
    assert src.index("chacha_xor(key") < src.index("volatile u8 *vk")


@needs_gcc
def test_aead_template_substituted_compiles_clean(tmp_path):
    """Substitute the tokens the way stub.py does and syntax-check the result
    with warnings enabled: guards the template against substitution breakage."""
    from encrypt import stub as stubmod

    nonce = b"\0" * 12
    tag = b"\0" * 16
    path = b"A" * 31 + b"\0"
    header = stubmod.make_aead_header(64, 0, nonce, -(64 + 6), 0, 0, 0)
    with open(os.path.join(ENCRYPT, "stub_aead_template.c"), encoding="utf-8") as f:
        source = f.read()
    source = source.replace("@HEADER@", stubmod._c_array(header))
    source = source.replace("@NONCE@", stubmod._c_array(nonce))
    source = source.replace("@TAG@", stubmod._c_array(tag))
    source = source.replace("@PATHLEN@", str(len(path)))
    source = source.replace("@KEYPATH@", stubmod._c_array(path))
    c_file = tmp_path / "stub.c"
    c_file.write_text(source)
    res = _run([GCC, "-fsyntax-only", "-Wall", "-Wextra", "-Os", "-fPIE", str(c_file)])
    assert res.returncode == 0, f"substituted template does not compile:\n{res.stderr}"


@needs_gcc
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="ELF/Linux only")
def test_encrypted_binary_runs_and_tamper_fails_closed(tmp_path):
    """End-to-end proof for the fixed template: a real binary encrypted with
    the AEAD pipeline must execute correctly, and a ciphertext bit-flip must
    fail closed (non-zero, non-payload exit) instead of running."""
    from encrypt.encrypt import encrypt_binary
    from encrypt.elf import ELFParser

    src = tmp_path / "h.c"
    src.write_text('int main(void) { return 42; }\n')
    exe = tmp_path / "h"
    res = _run([GCC, "-O0", "-o", str(exe), str(src)])
    assert res.returncode == 0, res.stderr

    out = tmp_path / "h.enc"
    encrypt_binary(str(exe), str(out), block_size=64)
    assert (tmp_path / "h.enc.key").exists()

    res = subprocess.run([str(out)], capture_output=True, timeout=30)
    assert res.returncode == 42, f"decrypted binary did not run correctly: {res.returncode}"

    # flip one byte inside the authenticated ciphertext: must not execute
    data = bytearray(out.read_bytes())
    elf = ELFParser(bytes(out.read_bytes()))
    _, sec = elf.get_text_section()
    data[sec["offset"] + 5] ^= 0x01
    tampered = tmp_path / "h.tampered"
    tampered.write_bytes(bytes(data))
    tampered.chmod(tampered.stat().st_mode | stat.S_IXUSR)
    shutil.copy(str(out) + ".key", str(tampered) + ".key")
    res = subprocess.run([str(tampered)], capture_output=True, timeout=30)
    assert res.returncode != 42, "tampered artifact executed the payload"
    assert res.returncode != 0, "tampered artifact exited cleanly"


# ---------------------------------------------------------------------------
# 5. Crypto invariants validated during the audit (regression pinning).
# ---------------------------------------------------------------------------

def test_aes256_fips197_vector():
    from encrypt import aes
    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
    pt = bytes.fromhex("00112233445566778899aabbccddeeff")
    assert aes.aes256_encrypt_block(pt, key).hex() == "8ea2b7ca516745bfeafc49904b496089"


def test_aes256_ctr_roundtrip():
    from encrypt import aes
    key = bytes(range(32))
    nonce = b"\x01" * 8
    data = bytes(range(256)) * 3
    ct = aes.aes256_ctr_encrypt(data, key, nonce)
    assert ct != data
    assert aes.aes256_ctr_decrypt(ct, key, nonce) == data


def test_chacha20poly1305_crosscheck_vector():
    """Vector captured from an independent implementation (the 'cryptography'
    package) over the RFC 8439 2.8.2 inputs; the pure-Python implementation
    must reproduce it exactly."""
    from encrypt import chacha20poly1305 as aead
    key = bytes.fromhex("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f")
    nonce = bytes.fromhex("070000004041424344454647")
    pt = bytes.fromhex(
        "496e7465726e65742d44726166747320617265206472796620616e642072656c69"
        "61626c6520666f72206e6f74206d756368206c6f6e6765722e")
    aad = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
    ct, tag = aead.seal(key, nonce, pt, aad)
    expected = (
        "d6159d38739325ce38a6fd9a50f5798ea0b2ed1f6d7317b8fdebbee375f066c927"
        "ffa954c9ae3844cafadc608efb3f9d166c9202d1070a2a128a627ebd2606709234"
        "9fb4dc23ffc903ba")
    assert (ct + tag).hex() == expected
    assert aead.open(key, nonce, ct, tag, aad) == pt
    bad = bytearray(ct)
    bad[0] ^= 1
    with pytest.raises(ValueError):
        aead.open(key, nonce, bytes(bad), tag, aad)


def test_hkdf_rfc5869_case1():
    from encrypt.container import _hkdf_sha256
    ikm = bytes.fromhex("0b" * 22)
    salt = bytes.fromhex("000102030405060708090a0b0c")
    info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
    assert _hkdf_sha256(ikm, salt, info, 42).hex() == (
        "3cb25f25faacd57a90434f64d0362f2a"
        "2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
        "34007208d5b887185865")


def test_container_roundtrip_and_tamper():
    from encrypt.container import pack_bytes, unpack_bytes
    key = bytes(range(32))
    msg = b"container-test-payload" * 20
    blob = pack_bytes(msg, key)
    assert unpack_bytes(blob, key) == msg
    bad = bytearray(blob)
    bad[-1] ^= 1
    with pytest.raises(ValueError):
        unpack_bytes(bytes(bad), key)
    # truncated containers must raise, not crash or misparse
    with pytest.raises(ValueError):
        unpack_bytes(blob[:len(blob) // 2], key)


# ---------------------------------------------------------------------------
# 6. Whitebox Feistel round-trip under UBSan/ASan-ish plain build.
# ---------------------------------------------------------------------------

_WB_HARNESS = r"""
#include "whitebox_feistel.h"
#include <cstdio>
#include <cstring>
using namespace nixon_wb;
int main() {
    uint8_t key[16];
    for (int i = 0; i < 16; ++i) key[i] = (uint8_t)(i * 7 + 1);
    WbTables t;
    wb_derive_tables(key, 0x0123456789abcdefULL, t);
    if (t.rounds < WB_ROUNDS_MIN || t.rounds > WB_ROUNDS_MAX) {
        printf("FAIL rounds %d out of range\n", t.rounds);
        return 1;
    }
    /* sbox/inv_sbox must be inverse permutations for every round/slot */
    for (int r = 0; r < t.rounds; ++r)
        for (int k = 0; k < 2; ++k)
            for (int i = 0; i < 256; ++i)
                if (t.inv_sbox[r][k][t.sbox[r][k][i]] != (uint8_t)i) {
                    printf("FAIL sbox/inv mismatch r%d k%d i%d\n", r, k, i);
                    return 1;
                }
    /* decrypt(encrypt(x)) == x over varied blocks */
    for (int trial = 0; trial < 64; ++trial) {
        uint8_t blk[WB_BLOCK], orig[WB_BLOCK];
        for (int i = 0; i < WB_BLOCK; ++i) {
            blk[i] = (uint8_t)(trial * 31 + i * 17);
            orig[i] = blk[i];
        }
        wb_feistel_block(t, blk, false);
        if (!memcmp(blk, orig, WB_BLOCK) && trial) {
            printf("FAIL encryption was identity at trial %d\n", trial);
            return 1;
        }
        wb_feistel_block(t, blk, true);
        if (memcmp(blk, orig, WB_BLOCK)) {
            printf("FAIL roundtrip mismatch at trial %d\n", trial);
            return 1;
        }
    }
    printf("whitebox feistel roundtrip OK (rounds=%d)\n", t.rounds);
    return 0;
}
"""


@needs_gxx
def test_whitebox_feistel_roundtrip(tmp_path):
    src = tmp_path / "wbtest.cpp"
    src.write_text(_WB_HARNESS)
    binary = _compile(tmp_path, "wbtest",
                      [str(src), os.path.join(NATIVE, "whitebox_feistel.cpp")],
                      extra=["-std=c++17", "-I", NATIVE,
                             "-fsanitize=address,undefined",
                             "-fno-omit-frame-pointer"],
                      compiler=GXX)
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=1", UBSAN_OPTIONS="halt_on_error=1")
    res = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60, env=env)
    assert res.returncode == 0, f"feistel harness failed:\n{res.stdout}{res.stderr}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
