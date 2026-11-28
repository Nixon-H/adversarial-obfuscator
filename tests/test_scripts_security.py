"""Regression tests for the scripts/ shard-B1 security audit (2026-11-28).

Each test pins one confirmed defect:
  1. scripts/poly/poly_engine.py -- encrypt/decrypt algorithm mismatch meant
     the generated decryptor never recovered the plaintext.
  2. scripts/c_transform.py -- the string-decrypt loop indexed the keystream
     with a per-entry offset the encryption side never applied, corrupting
     every string array after the first at run time.
  3. scripts/build.py -- the storylines/fingerprint/traps/function-intent
     stages were nested inside the speculation-transform block, silently
     inert unless --transforms speculation was also passed.
  4. scripts/runtime_config.py -- executable_segment read ELF32 header
     fields at the ELF64 offsets.
  5. scripts/environment/poly_engine.py -- adapt_value_to_environment mixed
     the fingerprint with hash(), which is randomized per process.
"""

import ast
import os
import re
import struct
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


# ---------------------------------------------------------------------------
# 1. poly/poly_engine.py decrypt roundtrip
# ---------------------------------------------------------------------------

def test_poly_engine_decrypt_code_recovers_plaintext_in_correct_environment():
    """The generated decryptor must invert encrypt_for_environment.

    Regression: the old generated code XORed with sha256(key_material + fp)
    repeated every 32 bytes, while encryption used a sha256 counter-mode
    keystream over key+iv -- two different streams, so decryption produced
    garbage even when every environment check passed.
    """
    from scripts.poly.poly_engine import PolyEngine

    engine = PolyEngine(seed=42)
    plaintext = b"hello world, this is a test payload!!"
    enc = engine.encrypt_for_environment(plaintext)
    ns: dict = {}
    exec(enc["decrypt_code"], ns)
    assert ns["__result"] == plaintext


def test_poly_engine_decrypt_roundtrip_multiblock_and_empty():
    """Multi-block keystreams (> 32 bytes, several counter blocks) and the
    empty plaintext must roundtrip too -- the repeating-key XOR bug is only
    visible past the first 32 bytes / is masked by chance byte overlap."""
    from scripts.poly.poly_engine import PolyEngine

    engine = PolyEngine(seed=7)
    for plaintext in (b"A" * 1000, bytes(range(256)) * 3, b"", b"x"):
        enc = engine.encrypt_for_environment(plaintext)
        ns: dict = {}
        exec(enc["decrypt_code"], ns)
        assert ns["__result"] == plaintext, "size %d roundtrip" % len(plaintext)


# ---------------------------------------------------------------------------
# 2. c_transform.py string-decrypt keystream alignment
# ---------------------------------------------------------------------------

def _fake_cython_source() -> str:
    return (
        'static char __pyx_k_alpha[] = "hello";\n'
        'static char __pyx_k_beta[] = "world123";\n'
        'static char __pyx_k_gamma[] = "test";\n'
        'static int __Pyx_InitStrings(void) {\n'
        '    return 0;\n'
        '}\n'
    )


def test_c_transform_string_decrypt_loop_uses_unoffset_keystream_index():
    """Every generated decrypt loop must index key[_i % N] with NO per-entry
    offset -- encryption XORs byte i with key[i % len(key)] exactly."""
    import random

    import c_transform

    out, count = c_transform.encrypt_strings(
        _fake_cython_source(), b"s" * 32, random.Random(1))
    assert count == 3
    loops = re.findall(r"_i\]\s*\^=\s*__nx_str_key\[([^]]+)\]", out)
    assert loops, "no decrypt loops emitted"
    for index_expr in loops:
        assert "+" not in index_expr, (
            "decrypt keystream index carries an offset encryption never "
            "applied: %r" % index_expr)


def test_c_transform_string_encryption_simulated_roundtrip_all_entries():
    """Simulate the generated C decrypt loop per entry: every array must
    recover its original bytes, not just the first."""
    import random

    import c_transform

    originals = {
        "__pyx_k_alpha": b"hello",
        "__pyx_k_beta": b"world123",
        "__pyx_k_gamma": b"test",
    }
    seed = b"x" * 32
    out, count = c_transform.encrypt_strings(
        _fake_cython_source(), seed, random.Random(1))
    assert count == 3
    key = c_transform._derive_key(seed, "c-string-enc")
    pat = re.compile(
        r'static\s+char\s+(__pyx_k_[A-Za-z0-9_]+)\[\s*\]\s*=\s*'
        r'"((?:[^"\\]|\\.)*)"\s*;')
    entries = [(m.group(1), c_transform._unescape_c(m.group(2)))
               for m in pat.finditer(out)]
    assert len(entries) == 3
    # Parse the index expression the generated C uses for each array, then
    # evaluate it the way C would.
    loop_pat = re.compile(
        r"for \(int _i = 0; _i < (\d+); _i\+\+\) (__pyx_k_\w+)\[_i\] \^= "
        r"__nx_str_key\[(.+?)\];")
    index_exprs = {m.group(2): m.group(3) for m in loop_pat.finditer(out)}
    for name, enc in entries:
        expr = index_exprs[name]
        dec = bytearray()
        for i in range(len(enc)):
            # Evaluate the emitted index arithmetic the way C would; the
            # expression is build-time generated integer arithmetic over _i.
            key_index = eval(expr, {"_i": i})  # noqa: S307 - test-local simulation of the emitted C arithmetic
            dec.append(enc[i] ^ key[key_index])
        assert bytes(dec) == originals[name], (
            "%s roundtrip corrupted" % name)


# ---------------------------------------------------------------------------
# 3. build.py stage nesting
# ---------------------------------------------------------------------------

def _main_function(tree):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "main"][0]


def test_build_injection_stages_not_nested_inside_speculation_block():
    """The storylines/fingerprint/traps/function-intent stages must not be
    children of `if opts.speculation_obfuscation ...` -- nested there they
    only ran when the speculation transform was also enabled."""
    with open(os.path.join(ROOT, "scripts", "build.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    main = _main_function(tree)
    spec = None
    for node in main.body:
        if isinstance(node, ast.If) and "speculation_obfuscation" in ast.unparse(node.test):
            spec = node
            break
    assert spec is not None, "speculation stage not found"
    trapped = []
    for node in ast.walk(spec):
        if isinstance(node, ast.If):
            test = ast.unparse(node.test)
            for feature in ("multi_agent_deception", "llm_fingerprint",
                            "reasoning_traps", "function_intent"):
                if feature in test:
                    trapped.append(feature)
    assert not trapped, (
        "independent stages still nested inside the speculation block: %s"
        % sorted(trapped))


def test_build_injection_stages_still_guarded_by_skip_obfuscate():
    """The four AST-injection stages must remain gated on skip_obfuscate
    (they rewrite the obfuscator's output file)."""
    with open(os.path.join(ROOT, "scripts", "build.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    main = _main_function(tree)

    def enclosing_if_tests(node, target_test):
        chain = []

        def recurse(current, stack):
            for child in ast.iter_child_nodes(current):
                new_stack = stack + ([ast.unparse(child.test)]
                                     if isinstance(child, ast.If) else [])
                if isinstance(child, ast.If) and target_test in ast.unparse(child.test):
                    chain.extend(new_stack[:-1])
                recurse(child, new_stack)

        recurse(node, [])
        return chain

    for feature in ("multi_agent_deception", "llm_fingerprint",
                    "reasoning_traps", "function_intent"):
        guards = enclosing_if_tests(main, feature)
        assert any("skip_obfuscate" in g for g in guards), (
            "%s lost its skip_obfuscate guard" % feature)


# ---------------------------------------------------------------------------
# 4. runtime_config.py ELF32 header parsing
# ---------------------------------------------------------------------------

def _synthetic_elf32(path) -> bytes:
    """Minimal ELF32 with one executable PT_LOAD segment at vaddr 0x1000."""
    ehdr = bytearray(52)
    ehdr[0:4] = b"\x7fELF"
    ehdr[4] = 1  # ELFCLASS32
    ehdr[5] = 1  # little endian
    ehdr[6] = 1  # version
    struct.pack_into("<H", ehdr, 16, 2)      # e_type = EXEC
    struct.pack_into("<H", ehdr, 18, 3)      # e_machine = x86
    struct.pack_into("<I", ehdr, 20, 1)      # e_version
    struct.pack_into("<I", ehdr, 24, 0x1000)  # e_entry
    struct.pack_into("<I", ehdr, 28, 52)     # e_phoff = right after ehdr
    struct.pack_into("<I", ehdr, 32, 0)      # e_shoff
    struct.pack_into("<I", ehdr, 36, 0)      # e_flags
    struct.pack_into("<H", ehdr, 40, 52)     # e_ehsize
    struct.pack_into("<H", ehdr, 42, 32)     # e_phentsize
    struct.pack_into("<H", ehdr, 44, 1)      # e_phnum
    phdr = bytearray(32)
    struct.pack_into("<I", phdr, 0, 1)       # p_type = PT_LOAD
    struct.pack_into("<I", phdr, 4, 0x100)   # p_offset
    struct.pack_into("<I", phdr, 8, 0x1000)  # p_vaddr (page aligned)
    struct.pack_into("<I", phdr, 12, 0x1000)  # p_paddr
    struct.pack_into("<I", phdr, 16, 0x40)   # p_filesz
    struct.pack_into("<I", phdr, 20, 0x40)   # p_memsz
    struct.pack_into("<I", phdr, 24, 5)      # p_flags = R+X
    struct.pack_into("<I", phdr, 28, 0x1000)  # p_align
    text = bytes(range(0x40))
    blob = bytes(ehdr) + bytes(phdr)
    blob += b"\x00" * (0x100 - len(blob)) + text
    with open(path, "wb") as fh:
        fh.write(blob)
    return text


def test_runtime_config_executable_segment_reads_elf32(tmp_path):
    """A 32-bit ELF must be parsed at the ELF32 offsets. Before the fix the
    phoff was read from e_shoff's location (0x20), so the segment scan ran
    into garbage and raised or returned wrong bytes."""
    import scripts.runtime_config as rc

    binary = tmp_path / "t32.elf"
    text = _synthetic_elf32(str(binary))
    seg = rc.executable_segment(str(binary))
    # p_offset 0x100 page-aligns DOWN to 0 (the kernel maps whole pages),
    # so the segment image starts at the ELF header; the .text bytes sit at
    # their file offset inside it. vaddr 0x1000 + memsz 0x40 page-aligns up
    # to 0x2000, so the image is exactly one page.
    assert len(seg) == 0x1000
    assert seg[0x100:0x100 + len(text)] == text


# ---------------------------------------------------------------------------
# 5. environment/poly_engine.py deterministic adaptation
# ---------------------------------------------------------------------------

def _adapt_in_subprocess(hashseed: str) -> str:
    code = (
        "import sys; sys.path.insert(0, %r);"
        "from scripts.environment.poly_engine import EnvironmentalPolyEngine;"
        "v, _ = EnvironmentalPolyEngine(seed=1234).adapt_value_to_environment(1000);"
        "print(v)" % ROOT
    )
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        env=env, timeout=60)
    assert proc.returncode == 0, proc.stderr[-400:]
    return proc.stdout.strip()


def test_environmental_poly_engine_adapt_deterministic_across_hashseeds():
    """Same seed + same value must adapt identically in every process.

    Regression: the mixer was `hash(fingerprint)`, and str hash is salted
    per process, so a value encoded at build time decoded to something else
    at run time whenever PYTHONHASHSEED differed."""
    a = _adapt_in_subprocess("1")
    b = _adapt_in_subprocess("2")
    assert a == b and a.isdigit()


def test_environmental_poly_engine_adapt_repeatable_in_process():
    """The same engine must adapt the same value identically on repeated
    calls -- the mixing must be a pure function of seed and fingerprint."""
    from scripts.environment.poly_engine import EnvironmentalPolyEngine

    engine = EnvironmentalPolyEngine(seed=99)
    first, _ = engine.adapt_value_to_environment(1000)
    second, _ = engine.adapt_value_to_environment(1000)
    assert first == second
    assert 0 <= first <= 0xFFFFFFFF
