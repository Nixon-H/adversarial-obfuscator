import sys,os,zipfile,base64,io,tokenize,py_compile,shutil,tempfile,random,hashlib,lzma,struct,time,json,argparse,uuid,re,inspect,platform,subprocess,marshal,hmac,secrets,ctypes,importlib.util,atexit,warnings,zlib,codecs,string,builtins,math,dis,multiprocessing,types,traceback,gc,ast,socket,threading,concurrent.futures,logging;from io import StringIO;from datetime import datetime; _nixon_ハッシュ해시 = hashlib
from .utils import get_random_var_name

class TypeHintStripper(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.returns = None
        if node.args.args:
            for arg in node.args.args:
                arg.annotation = None
        self.generic_visit(node)
        return node
    def visit_AnnAssign(self, node):
        if node.value is None:
            return None
        return ast.Assign(targets=[node.target], value=node.value, type_comment=None)
    def visit_Import(self, node):
        new_names = [n for n in node.names if n.name != 'typing']
        if not new_names: return None
        node.names = new_names
        return node
    def visit_ImportFrom(self, node):
        if node.module == 'typing': return None
        return node
class FStringLowering(ast.NodeTransformer):
    def visit_JoinedStr(self, node):
        new_values = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                new_values.append(value)
            elif isinstance(value, ast.FormattedValue):
                if value.format_spec is not None or value.conversion != -1:
                    return node
                call_str = ast.Call(
                    func=ast.Name(id='str', ctx=ast.Load()),
                    args=[value.value],
                    keywords=[]
                )
                new_values.append(call_str)
        if not new_values:
            return ast.Constant(value="")
        result = new_values[0]
        for val in new_values[1:]:
            result = ast.BinOp(left=result, op=ast.Add(), right=val)
        return result
class ScopeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.function_scopes = {}
        self.current_function = None
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name        
        assignments = set()
        references = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, (ast.Store, ast.Del)):
                    assignments.add(child.id)
                elif isinstance(child.ctx, ast.Load):
                    references.add(child.id)        
        potentially_unbound = references - assignments
        self.function_scopes[node.name] = {
            'assignments': assignments,
            'references': references,
            'potentially_unbound': potentially_unbound
        }
        self.generic_visit(node)
        self.current_function = old_function
    def get_unsafe_functions(self):
        unsafe = []
        for func_name, scope in self.function_scopes.items():
            if scope['potentially_unbound']:
                unsafe.append((func_name, scope['potentially_unbound']))
        return unsafe
class SymbolRenamer(ast.NodeTransformer):
    def __init__(self, mapping=None):
        self.mapping = mapping if mapping is not None else {}
        self.reverse_mapping = {}
        self.protected_functions = set()
        self.current_function = None
        self._rename_log = []
        # V10 kwargs fix: when False (default), function PARAMETER names and
        # keyword-argument names are never renamed (call-site contracts).
        # Set rename_params=True only for whole-program builds where every
        # caller is rewritten consistently (not yet implemented).
        self.rename_params = False
        # V10 internal-rename (opt-in, default OFF): proven-internal
        # method/attribute renames. Default = safe: every public method
        # defined in a class body is preserved (external API intact).
        # Opt in via allow_internal_rename(names) with the
        # find_internal_methods() proof set: only those names rename,
        # and their *attribute* uses (self.m / obj.m) are rewritten
        # consistently. visit_Attribute honors the same set so renames
        # never desync defs from call sites.
        self.allow_internal_rename = set()
        self.reserved = {
            'sum', 'min', 'max', 'abs', 'round', 'pow', 'divmod',
            'chr', 'ord', 'hex', 'oct', 'bin', 'ascii', 'repr',
            'print', 'str', 'int', 'float', 'bool', 'len', 'list', 'dict', 'set', 'tuple',
            'range', 'enumerate', 'zip', 'open', 'read', 'write', 'close', 'input',
            'type', 'isinstance', 'issubclass', 'callable', 'hasattr', 'getattr', 'setattr', 'delattr',
            'eval', 'exec', 'compile', 'globals', 'locals', 'vars', 'dir',
            'id', 'hash', 'object', 'super', 'property', 'classmethod', 'staticmethod',
            'bytes', 'bytearray', 'memoryview', 'format', 'slice', 'iter', 'next',
            'any', 'all', 'complex', 'frozenset', 'sorted', 'reversed', 'map', 'filter',
            'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError',
            'RuntimeError', 'StopIteration', 'ImportError', 'NameError', 'OSError', 'IOError',
            'BaseException', 'SystemExit', 'KeyboardInterrupt', 'GeneratorExit', 'AssertionError',
            'FileNotFoundError', 'PermissionError', 'TimeoutError', 'ConnectionError', 'BrokenPipeError',
            'sys', 'os', 'asyncio', 'time', 'json', 'random', 'math', 'self', 'args', 'kwargs',
            're', 'io', 'threading', 'collections', 'functools', 'itertools', 'urllib', 'http',
            'socket', 'ssl', 'struct', 'base64', 'hashlib', 'hmac', 'secrets', 'pathlib',
            'requests', 'websockets', 'ipaddress', 'contextlib', 'subprocess', 'argparse',
            'getpass', 'string', 'urlparse', 'ConnectionClosed', 'WebSocketClientProtocol',
            'ws_connect', 'g_resolution_ledger', 'G_RESOLUTION_EXPIRATION_SEC',
            '__init__', '__main__', '__file__', '__name__', '__doc__', '__class__', '__dict__',
            '__module__', '__qualname__', '__annotations__', '__wrapped__', '__slots__',
            'Optional', 'Union', 'Any', 'List', 'Dict', 'Set', 'Tuple', 'Callable', 'Iterable',
            'Iterator', 'Generator', 'Sequence', 'Mapping', 'MutableMapping', 'MutableSequence',
            'Type', 'TypeVar', 'Generic', 'Protocol', 'Final', 'Literal', 'ClassVar', 'Annotated',
            'Awaitable', 'Coroutine', 'AsyncGenerator', 'AsyncIterable', 'AsyncIterator',
            'NamedTuple', 'TypedDict', 'cast', 'overload', 'no_type_check', 'get_type_hints',
            'gather', 'create_task', 'sleep', 'wait', 'wait_for', 'run', 'ensure_future',
            'get_event_loop', 'get_running_loop', 'new_event_loop', 'set_event_loop',
            'AbstractEventLoop', 'Task', 'Future', 'Queue', 'Lock', 'Event', 'Semaphore',
            'Condition', 'StreamReader', 'StreamWriter', 'open_connection', 'start_server',
            'TimeoutError', 'CancelledError', 'InvalidStateError', 'IncompleteReadError',
            'LimitOverrunError', 'BoundedSemaphore', 'shield', 'timeout', 'timeout_at',
            'dataclass', 'field', 'fields', 'asdict', 'astuple', 'make_dataclass',
            'True', 'False', 'None', 'NotImplemented', 'Ellipsis',            
            'path', 'fd', 'blob_key', 'ext', 'system', 'blobs',
            'encrypted_blob', 'blob_data', 'spec', 'module', 'fpath',
            'load_err', 'main_err', 'f', 'loader', 'target',
            'tempfile', 'mkstemp', 'importlib', 'util', 
            'spec_from_file_location', 'module_from_spec',
            'platform', 'lower', 'ANDROID_ROOT', 'environ',
            'cleanup', 'target_path',
            '_load_native', '_exec_fallback', '_xor_decrypt',
            '_nx_hwid_unlock', '_nx_trial_gate',
            '_NX_HWID_LOCK', '_NX_HWID_STATIC', '_NX_TRIAL_GATE', '_NX_TRIAL_SECONDS',
            '_NX_TRIAL_KEY', '_NX_TRIAL_DEADLINE', '_NX_TRIAL_TOKEN',
            '_NX_TRIAL_HWID_HINT', '_NX_KOD_ARMED', '_NX_VM_THRESHOLD',
            # V10 kernel-driver gate (SAFE read-only gate): helper + marker
            # must survive renames or the armed gate breaks at runtime.
            '_nx_driver_stem', '_nx_driver_armed', '_nx_enum_drivers',
            '_nx_driver_hits', '_nx_driver_watch', 'driver_check',
            '_NX_DRIVER_BLOCKED', '_NX_DRIVER_ARMED_BUILD',
            '_NX_DRIVER_ARMED_VALUES', '_NX_DRIVER_INTERVAL',
            '_NX_DRIVER_VAR', '_NX_DRIVER_CHECK_ARMED',
            '_nx_watermark_gate',
            '_NX_WATERMARK_GATE', '_NX_WATERMARK_KEY', '_NX_WATERMARK_MSG',
            '_NX_WATERMARK_TAG', '_NX_WATERMARK_MARKER',
            # V10 unified kill ladder: single-failure-path wipe+exit helper.
            # _nx_kill must survive renames or every migrated gate breaks
            # at runtime.
            '_nx_kill',
            # V10 split-bootstrap (opt-in): fragmented-decoder helpers +
            # stub fragment markers must survive renames or the armed
            # lazy-activate path breaks at runtime.
            '_nx_sb_collect', '_nx_sb_combine', '_nx_sb_activate',
            '_NX_SB_HEAD', '_NX_SB_TRAIL', '_NX_SB_SALT', '_NX_SB_KEY',
            '_NX_SB_THIRD', '_NX_SPLIT_BOOTSTRAP',
            '_NX_SPLIT_BOOTSTRAP_ARMED', 'BLOB_KEY_SB',
            # Runtime integrity (frozen snapshots + stdlib audit): gate
            # helpers + marker literals must survive renames or the
            # armed gates break at runtime.
            '_nx_snapshot_gate', '_nx_stdlib_gate',
            '_NX_SNAPSHOT_GATE', '_NX_SNAPSHOT_TAG', '_NX_SNAPSHOT_FILES',
            '_NX_STDLIB_GATE', '_NX_STDLIB_TAG', '_NX_STDLIB_FUNCS',
            '__all__',
            'NATIVE_BLOBS', 'FALLBACK_BLOB', 'BLOB_KEY',
        }
    def allow_internal_rename_names(self, names):
        """Opt-in helper (V10 internal-rename): allow proven-internal methods.

        ``names`` is an iterable of method/attribute names already proven
        internal-only by obfuscator.internal_rename.find_internal_methods.
        Additive: never removes reserved entries; ignores bad input.
        """
        try:
            for _n in (names or []):
                if isinstance(_n, str) and _n:
                    self.allow_internal_rename.add(_n)
        except Exception:
            pass
    def reserve_all_names(self, names):
        """Additive helper (GAP #64): reserve __all__ export names.

        ``names`` is an iterable of statically known public-export names
        (see obfuscator.all_preserve.extract_all_names). Never removes
        existing reserved entries; ignores non-string input safely.
        """
        try:
            for _n in (names or []):
                if isinstance(_n, str) and _n:
                    self.reserved.add(_n)
        except Exception:
            pass
    def get_new_name(self, old_name):
        if hasattr(self, 'dynamic_unbounds') and old_name in self.dynamic_unbounds:
            if old_name not in self.mapping:
                self.mapping[old_name] = "_nx_" + __import__('hashlib').md5(old_name.encode()).hexdigest()[:6]
                self.reverse_mapping[old_name] = self.mapping[old_name]
                self._rename_log.append((old_name, self.mapping[old_name]))
            return self.mapping[old_name]
        if old_name in self.reserved: 
            return old_name
        if old_name.startswith('_nixon_') or old_name.startswith('_NX_'):
            return old_name
        if old_name not in self.mapping:
            for _ in range(100):
                new = get_random_var_name(old_name)
                if new not in self.reserved and new not in self.mapping.values():
                    self.mapping[old_name] = new
                    self.reverse_mapping[old_name] = new
                    self._rename_log.append((old_name, new))
                    break
            else:
                 return old_name
        return self.mapping[old_name]
    def save_rename_log(self, filepath):
        with open(filepath + '.renamelog', 'w') as f:
            for old, new in self._rename_log:
                f.write(f"{old} -> {new}\n")
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        if node.name not in self.protected_functions and not node.name.startswith("__") and not node.name.startswith("_") and node.name not in self.reserved:
            # V10 super() fix: zero-arg super() and method overrides depend
            # on the METHOD NAME surviving (override dispatch + implicit
            # __class__ cell). Never rename a method defined inside a class
            # body — track nesting via a depth counter (module-level
            # functions still rename; nested closures keep names too,
            # conservative and safe).
            # V10 internal-rename (opt-in): proven-internal methods
            # (allow_internal_rename set, from find_internal_methods)
            # DO rename — the proof guarantees every use rewrites too.
            _depth = getattr(self, '_class_depth', 0)
            _is_method = _depth > 0
            _allowed = node.name in getattr(self, 'allow_internal_rename', set())
            if not _is_method or _allowed:
                node.name = self.get_new_name(node.name)
        # V10 kwargs fix: parameter names are call-site contracts. Unless
        # rename_params is explicitly enabled (whole-program builds only),
        # record this function's params as NO-RENAME for the Store AND
        # Load paths below, and leave the definition's arg nodes alone.
        _param_names = set()
        if not getattr(self, 'rename_params', False):
            _param_names = {a.arg for a in list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)}
            if node.args.vararg is not None:
                _param_names.add(node.args.vararg.arg)
            if node.args.kwarg is not None:
                _param_names.add(node.args.kwarg.arg)
        _prev_params = getattr(self, '_local_params', None)
        _accum = set(_prev_params) if _prev_params else set()
        _accum.update(_param_names)
        self._local_params = _accum
        self.generic_visit(node)
        self._local_params = _prev_params
        self.current_function = old_function
        return node
    def visit_ClassDef(self, node):
        if node.name not in self.reserved and not node.name.startswith("__") and not node.name.startswith("_"):
            node.name = self.get_new_name(node.name)
        _prev_depth = getattr(self, '_class_depth', 0)
        self._class_depth = _prev_depth + 1
        self.generic_visit(node)
        self._class_depth = _prev_depth
        return node
    def visit_Name(self, node):
        if self.current_function in self.protected_functions:
            return node
        # V10 kwargs fix: names bound as function parameters are
        # call-site contracts — skip them on BOTH Store and Load paths
        # (the _local_params set is built per-FunctionDef above).
        _params = getattr(self, '_local_params', None)
        if _params is not None and node.id in _params:
            return node
        if isinstance(node.ctx, (ast.Load, ast.Store, ast.Del)) and not node.id.startswith("__") and not node.id.startswith("_") and node.id not in self.reserved:
            node.id = self.get_new_name(node.id)
        return node
    def visit_arg(self, node):
        if self.current_function in self.protected_functions:
            return node
        # V10 kwargs fix: keyword argument NAMES are part of the call
        # contract (f(1, c=2), dict(a=1), keyword-only args, **kwargs).
        # Renaming a parameter without rewriting every call site breaks
        # binding. The renamer has no whole-program call graph here, so
        # parameter names are NEVER renamed — only locals/globals are.
        return node
    def visit_keyword(self, node):
        # V10 kwargs fix (part 2): keyword ARGUMENT names at call sites
        # (f(1, c=2), dict(a=1)) are resolved against parameter names at
        # runtime — renaming them breaks binding exactly like renaming
        # visit_arg definitions. NEVER rename keyword.arg (None = **kwargs
        # splash, nothing to rename).
        return node
    def visit_Nonlocal(self, node):
        if self.current_function in self.protected_functions:
            return node
        node.names = [self.get_new_name(n) for n in node.names]
        return node
    def visit_Global(self, node):
        if self.current_function in self.protected_functions:
            return node
        node.names = [self.get_new_name(n) for n in node.names]
        return node
    def visit_Import(self, node):
        for alias in node.names:
            if alias.asname:
                alias.asname = self.get_new_name(alias.asname)
        return node
    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.asname:
                alias.asname = self.get_new_name(alias.asname)
        return node
    def visit_AsyncFunctionDef(self, node):
        # Same policy as FunctionDef (async methods preserve by default,
        # rename only when proven internal + opted in).
        return self.visit_FunctionDef(node)
    def visit_Attribute(self, node):
        # V10 internal-rename: attribute uses (self.m / obj.m) rewrite
        # consistently ONLY for proven-internal names; everything else is
        # left untouched (external API / third-party attributes safe).
        self.generic_visit(node)
        try:
            _allowed = node.attr in getattr(self, 'allow_internal_rename', set())
        except Exception:
            _allowed = False
        if _allowed and node.attr not in self.reserved:
            try:
                node.attr = self.get_new_name(node.attr)
            except Exception:
                pass
        return node
class StringLiteralObfuscator(ast.NodeTransformer):
    # AUDIT GAP #55 (additive): optional ChaCha20 string mode lives alongside
    # the legacy single-byte XOR path. Default mode stays "xor" so existing
    # builds/golden outputs are unchanged; opt in via
    #   StringLiteralObfuscator(mode="chacha20", allowlist=[...])
    # or via apply_ast_mutation options {"string_crypto": "chacha20",
    # "string_allowlist": [...]}. Per-string nonces (secrets.token_bytes)
    # make every build unique; tampered seals raise ValueError at runtime.
    def __init__(self, mode="xor", allowlist=None, string_key=None):
        self.string_table = {}
        self.generated_vars = set()
        self.decoder_name = self._generate_babel_name()
        self.xor_key = secrets.randbelow(255) + 1
        self._chacha_key = None
        self._allowlist = list(allowlist) if allowlist else []
        try:
            from obfuscator.string_crypto import (
                LEGACY_MODE as _LEGACY, normalize_mode as _norm_mode)
            self.mode = _norm_mode(mode) if mode else _LEGACY
        except Exception:
            self.mode = "xor"
        if self.mode == "chacha20":
            try:
                from obfuscator.string_crypto import make_session as _mk
                self._session = _mk(string_key)
                self._chacha_key = self._session["key"]
            except Exception:
                self.mode = "xor"
                self._session = None
        else:
            self._session = None
    def _generate_babel_name(self):
        return get_random_var_name("STR_DEC")
    def visit_JoinedStr(self, node):
        node.values = [self.visit(v) if isinstance(v, ast.FormattedValue) else v for v in node.values]
        return node
    def visit_FormattedValue(self, node):
        return self.generic_visit(node)
    def _xor_encode(self, s):
        encoded = ''.join(chr(ord(c) ^ self.xor_key) for c in s)
        return encoded[::-1]
    def visit_Constant(self, node):
        if isinstance(node.value, str) and len(node.value) >= 2 and len(node.value) <= 200000:
            if node.value.startswith("_NX_PART_"): return node
            if "PLACEHOLDER" in node.value: return node
            original = node.value
            if getattr(self, "mode", "xor") == "chacha20" and self._session is not None:
                # ChaCha20 path: allowlisted strings stay plaintext (additive).
                try:
                    from obfuscator.string_crypto import is_allowlisted as _allowed
                    if _allowed(original, self._allowlist):
                        return node
                except Exception:
                    pass
                try:
                    seal = self._session["encrypt"](original, self._allowlist)
                except Exception:
                    return node
                if seal is None:
                    return node
                if original in self.string_table:
                    var_name = self.string_table[original]
                else:
                    var_name = self._generate_babel_name()
                    self.string_table[original] = var_name
                node._nx_chacha_seal = seal
                return ast.Call(
                    func=ast.Name(id=self.decoder_name, ctx=ast.Load()),
                    args=[ast.Name(id=var_name, ctx=ast.Load())],
                    keywords=[]
                )
            if original in self.string_table:
                var_name = self.string_table[original]
            else:
                var_name = self._generate_babel_name()
                self.string_table[original] = var_name
            return ast.Call(
                func=ast.Name(id=self.decoder_name, ctx=ast.Load()),
                args=[ast.Name(id=var_name, ctx=ast.Load())],
                keywords=[]
            )
        return node
    def visit_Str(self, node):
        return self.visit_Constant(ast.Constant(value=node.s))
    def get_preamble(self):
        # GAP #55: ChaCha20 mode emits the self-contained AEAD stub; the
        # legacy XOR preamble is preserved verbatim in _get_xor_preamble.
        if getattr(self, "mode", "xor") == "chacha20" and self._session is not None:
            try:
                from obfuscator.string_crypto import (
                    emit_decoder_source as _emit, is_allowlisted as _allowed)
                stub = _emit(self.decoder_name, self._chacha_key)
            except Exception:
                return self._get_xor_preamble()
            lines = [stub]
            for original, var_name in self.string_table.items():
                try:
                    if _allowed(original, self._allowlist):
                        continue
                    seal = self._session["encrypt"](original, self._allowlist)
                    if seal is None:
                        continue
                    lines.append(f"{var_name} = '{seal}'")
                except Exception: pass
            return '\n'.join(lines)
        return self._get_xor_preamble()
    def _get_xor_preamble(self):
        lines = []
        lines.append(f"def {self.decoder_name}(_s):")
        lines.append(f"    try:")
        lines.append(f"        _b = bytes.fromhex(_s)")
        lines.append(f"    except ValueError:")
        lines.append(f"        _a = ''")
        lines.append(f"        for _i in range(65, 91): _a += chr(_i)")
        lines.append(f"        for _i in range(97, 123): _a += chr(_i)")
        lines.append(f"        for _i in range(48, 58): _a += chr(_i)")
        lines.append(f"        _a += '+/'")
        lines.append(f"        _v = 0; _n = 0; _r = []")
        lines.append(f"        for _x in _s.rstrip('='):")
        lines.append(f"            _i = _a.find(_x)")
        lines.append(f"            if _i >= 0:")
        lines.append(f"                _v = (_v << 6) | _i")
        lines.append(f"                _n += 6")
        lines.append(f"                if _n >= 8:")
        lines.append(f"                    _n -= 8")
        lines.append(f"                    _r.append((_v >> _n) & 0xFF)")
        lines.append(f"        try:")
        lines.append(f"            _b = bytes.fromhex(bytes(_r).decode('ascii'))")
        lines.append(f"        except (ValueError, UnicodeDecodeError):")
        lines.append(f"            return _s")
        lines.append(f"    return bytes([_c ^ {self.xor_key} for _c in _b[::-1]]).decode()")
        for original, var_name in self.string_table.items():
            try:
                enc_bytes = bytes([b ^ self.xor_key for b in original.encode('utf-8')])
                hex_safe = enc_bytes[::-1].hex()
                lines.append(f"{var_name} = '{hex_safe}'")
            except Exception: pass
        return '\n'.join(lines)
class BuiltinAliaser(ast.NodeTransformer):
    BABEL_RANGES = [
        (0x0100, 0x017F),
        (0x0180, 0x024F),
        (0x0250, 0x02AF),
        (0x0370, 0x03FF),
        (0x0400, 0x04FF),
        (0x0530, 0x058F),
        (0x05D0, 0x05EA),
        (0x0600, 0x06FF),
        (0x0900, 0x097F),
        (0x0980, 0x09FF),
        (0x0E00, 0x0E7F),
        (0x10A0, 0x10FF),
        (0x13A0, 0x13F4),
        (0x16A0, 0x16EA),
        (0x3040, 0x309F),
        (0x4E00, 0x9FFF),
    ]
    BUILTINS_TO_ALIAS = [
        'print', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
        'len', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
        'min', 'max', 'sum', 'abs', 'round', 'pow', 'divmod',
        'chr', 'ord', 'hex', 'oct', 'bin', 'ascii', 'repr',
        'type', 'isinstance', 'issubclass', 'callable', 'hasattr', 'getattr', 'setattr', 'delattr',
        'open', 'input', 'eval', 'exec', 'compile', 'globals', 'locals', 'vars', 'dir',
        'id', 'hash', 'object', 'super', 'property', 'classmethod', 'staticmethod',
        'bytes', 'bytearray', 'memoryview', 'format', 'slice', 'iter', 'next',
        'any', 'all', 'complex', 'frozenset', 'Exception', 'ValueError', 'TypeError',
        'KeyError', 'IndexError', 'AttributeError', 'RuntimeError', 'StopIteration',
    ]
    def __init__(self):
        self.alias_map = {}
        self.generated_names = set()
        for builtin in self.BUILTINS_TO_ALIAS:
            self.alias_map[builtin] = self._generate_babel_name()
    def _generate_babel_char(self):
        for _ in range(20):
            r_start, r_end = random.choice(self.BABEL_RANGES)
            char = chr(random.randint(r_start, r_end))
            if ("_" + char).isidentifier() and char.isprintable():
                return char
        return random.choice(['变', '関', 'ה', 'Д', 'Σ', '한', 'ก', 'က'])
    def _generate_babel_name(self):
        while True:
            name = "_nixon_"
            for _ in range(random.randint(6, 10)):
                name += self._generate_babel_char()
            if name not in self.generated_names:
                self.generated_names.add(name)
                return name
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.alias_map:
            node.id = self.alias_map[node.id]
        return node
    def get_preamble(self):
        lines = []
        for builtin, alias in self.alias_map.items():
            lines.append(f"{alias} = {builtin}")
        return '\n'.join(lines)
class VariableCapture(ast.NodeVisitor):
    def __init__(self, function_node):
        self.defined_in_function = set()
        self.used_in_function = set()
        self.nonlocal_vars = set()
        self.global_vars = set()
        self.params = set()
        if hasattr(function_node, 'args'):
            _a = function_node.args
            for arg in list(_a.posonlyargs) + list(_a.args) + list(_a.kwonlyargs):
                self.params.add(arg.arg)
            if _a.vararg is not None:
                self.params.add(_a.vararg.arg)
            if _a.kwarg is not None:
                self.params.add(_a.kwarg.arg)
        for node in ast.walk(function_node):
            if isinstance(node, ast.Nonlocal):
                self.nonlocal_vars.update(node.names)
            elif isinstance(node, ast.Global):
                self.global_vars.update(node.names)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    self.defined_in_function.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    self.used_in_function.add(node.id)
    def get_external_vars(self, code_block):
        block_defines = set()
        block_uses = set()
        for node in ast.walk(code_block):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    block_defines.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    block_uses.add(node.id)
        external = block_uses - block_defines
        accessible = (self.defined_in_function | self.params | self.nonlocal_vars | self.global_vars)
        return external & accessible
class ASTMutator(ast.NodeTransformer):
    def __init__(self):
        self.funcs = []
        self.junk_counter = 0
    def visit_Module(self, node):
        self.funcs = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        non_funcs = [n for n in node.body if not isinstance(n, ast.FunctionDef)]
        random.shuffle(self.funcs)
        main_blocks = []
        other_stmts = []
        for n in non_funcs:
            is_main = False
            if isinstance(n, ast.If):
                try:
                    if isinstance(n.test, ast.Compare):
                        if isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__":
                             if len(n.test.comparators) > 0 and isinstance(n.test.comparators[0], ast.Constant) and n.test.comparators[0].value == "__main__":
                                 is_main = True
                except Exception: pass
            if is_main:
                main_blocks.append(n)
            else:
                other_stmts.append(n)
        new_body = []
        for stmt in other_stmts:
            new_body.append(stmt)
            r = random.random()
            if r < 0.2:
                new_body.append(self._generate_dead_code())
            elif r > 0.8:
                new_body.extend(self._generate_sandbox_check())
        final_body = new_body + self.funcs + main_blocks
        node.body = final_body
        return node
    def _generate_dead_code(self):
        self.junk_counter += 1
        target = random.randint(0, 1000)
        mask = random.randint(0, 1000)
        check_val = target ^ mask
        test = ast.Compare(left=ast.BinOp(left=ast.Constant(value=check_val), op=ast.BitXor(), right=ast.Constant(value=mask)),ops=[ast.NotEq()],comparators=[ast.Constant(value=target)])
        return ast.If(test=test, body=[ast.Pass()], orelse=[])

    def _generate_sandbox_check(self):
        source = """
import uuid, sys, multiprocessing
try:
    if (uuid.getnode() >> 24) in [0x000569, 0x000c29, 0x001c14, 0x005056, 0x080027, 0x00155d, 0x525400]:
        sys.exit()
except Exception: pass
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception: pass
"""
        return ast.parse(source).body

class OpaquePredicateInjector(ast.NodeTransformer):
    def __init__(self):
        self.inject_count = 0
        self.predicates = [
            lambda: self._math_predicate_1(),
            lambda: self._math_predicate_2(),
            lambda: self._math_predicate_3(),
            lambda: self._math_predicate_fermat(),
            lambda: self._math_predicate_quadratic(),
            lambda: self._math_predicate_modular(),
            lambda: self._math_predicate_ec(),
            lambda: self._math_predicate_modexp(),
            lambda: self._math_predicate_poly3(),
            lambda: self._math_predicate_involution(),
            lambda: self._math_predicate_factored_mod(),
            lambda: self._math_predicate_sympy_like(),
        ]
    def _math_predicate_1(self):
        x = random.randint(1, 100)
        return ast.Compare(
            left=ast.BinOp(
                left=ast.BinOp(
                    left=ast.BinOp(left=ast.Constant(value=x), op=ast.Mult(), right=ast.Constant(value=x)),
                    op=ast.Add(),
                    right=ast.Constant(value=x)
                ),
                op=ast.Mod(),
                right=ast.Constant(value=2)
            ),
            ops=[ast.Eq()],
            comparators=[ast.BinOp(left=ast.Constant(value=x), op=ast.Mod(), right=ast.Constant(value=2))]
        )
    def _math_predicate_2(self):
        x = random.randint(1, 50)
        return ast.Compare(
            left=ast.Compare(
                left=ast.BinOp(left=ast.Constant(value=x), op=ast.BitOr(), right=ast.Constant(value=x)),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=x)]
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=True)]
        )
    def _math_predicate_3(self):
        x = random.randint(2, 20)
        return ast.Compare(
            left=ast.BinOp(
                left=ast.BinOp(left=ast.Constant(value=7*x), op=ast.Sub(), right=ast.Constant(value=1)),
                op=ast.Mod(),
                right=ast.Constant(value=7)
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=6)]
        )
    def _math_predicate_fermat(self):
        p = 7
        a = random.randint(2, p-1)
        return ast.Compare(
            left=ast.BinOp(
                left=ast.BinOp(left=ast.Constant(value=a), op=ast.Pow(), right=ast.Constant(value=p-1)),
                op=ast.Mod(),
                right=ast.Constant(value=p)
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=1)]
        )
    def _math_predicate_quadratic(self):
        x = random.randint(1, 100)
        return ast.Compare(
            left=ast.BinOp(
                left=ast.BinOp(
                    left=ast.BinOp(left=ast.Constant(value=x), op=ast.Pow(), right=ast.Constant(value=2)),
                    op=ast.Add(),
                    right=ast.Constant(value=x)
                ),
                op=ast.Mod(),
                right=ast.Constant(value=2)
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=0)]
        )
    def _math_predicate_modular(self):
        n = random.randint(5, 50)
        a = random.randint(10, 100)
        b = random.randint(10, 100)
        return ast.Compare(
            left=ast.BinOp(
                left=ast.BinOp(left=ast.Constant(value=a), op=ast.Mult(), right=ast.Constant(value=b)),
                op=ast.Mod(),
                right=ast.Constant(value=n)
            ),
            ops=[ast.Eq()],
            comparators=[ast.BinOp(
                left=ast.BinOp(
                    left=ast.BinOp(left=ast.Constant(value=a), op=ast.Mod(), right=ast.Constant(value=n)),
                    op=ast.Mult(),
                    right=ast.BinOp(left=ast.Constant(value=b), op=ast.Mod(), right=ast.Constant(value=n))
                ),
                op=ast.Mod(),
                right=ast.Constant(value=n)
            )]
        )
    def _math_predicate_ec(self):
        p = 65537
        x = random.randint(2, 1000)
        a_coeff = 0; b_coeff = 7
        y_sq = (pow(x, 3, p) + a_coeff * x + b_coeff) % p
        y = pow(y_sq, (p + 1) // 4, p)
        if (y * y) % p != y_sq:
            x = 3; y_sq = (27 + 7) % p; y = pow(y_sq, (p + 1) // 4, p)
        return ast.Compare(
            left=ast.Call(
                func=ast.Name(id='pow', ctx=ast.Load()),
                args=[ast.Constant(value=y), ast.Constant(value=2), ast.Constant(value=p)],
                keywords=[]
            ),
            ops=[ast.Eq()],
            comparators=[ast.BinOp(
                left=ast.BinOp(
                    left=ast.Call(
                        func=ast.Name(id='pow', ctx=ast.Load()),
                        args=[ast.Constant(value=x), ast.Constant(value=3), ast.Constant(value=p)],
                        keywords=[]
                    ),
                    op=ast.Add(),
                    right=ast.Constant(value=b_coeff)
                ),
                op=ast.Mod(),
                right=ast.Constant(value=p)
            )]
        )
    def _math_predicate_modexp(self):
        primes = [257, 509, 1021, 2053, 4099, 8209]
        p = random.choice(primes)
        g = random.randint(2, p - 2)
        return ast.Compare(
            left=ast.Call(
                func=ast.Name(id='pow', ctx=ast.Load()),
                args=[ast.Constant(value=g), ast.Constant(value=p - 1), ast.Constant(value=p)],
                keywords=[]
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=1)]
        )
    def _math_predicate_poly3(self):
        """(x^3 - x) % 3 == 0  (always true by Fermat's little theorem for mod 3)"""
        x = random.randint(1, 500)
        x3 = x * x * x
        return ast.Compare(
            left=ast.BinOp(
                left=ast.Constant(value=x3 - x),
                op=ast.Mod(),
                right=ast.Constant(value=3),
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=0)],
        )
    def _math_predicate_involution(self):
        """~(x) == -x - 1  (two's complement identity)"""
        x = random.randint(1, 500)
        return ast.Compare(
            left=ast.UnaryOp(op=ast.Invert(), operand=ast.Constant(value=x)),
            ops=[ast.Eq()],
            comparators=[ast.BinOp(
                left=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=x)),
                op=ast.Sub(),
                right=ast.Constant(value=1),
            )]
        )
    def _math_predicate_factored_mod(self):
        """(a^2 - b^2) == (a-b)*(a+b)  (always true)"""
        a = random.randint(10, 200)
        b = random.randint(5, a - 1)
        return ast.Compare(
            left=ast.BinOp(
                left=ast.Constant(value=a * a),
                op=ast.Sub(),
                right=ast.Constant(value=b * b),
            ),
            ops=[ast.Eq()],
            comparators=[ast.BinOp(
                left=ast.Constant(value=a - b),
                op=ast.Mult(),
                right=ast.Constant(value=a + b),
            )]
        )
    def _math_predicate_sympy_like(self):
        """n^n ≡ n (mod 2)  — always true: parity of n^n == parity of n"""
        n = random.randint(1, 50)
        return ast.Compare(
            left=ast.BinOp(
                left=ast.Call(
                    func=ast.Name(id='pow', ctx=ast.Load()),
                    args=[ast.Constant(value=n), ast.Constant(value=n), ast.Constant(value=2)],
                    keywords=[]
                ),
                op=ast.Mod(),
                right=ast.Constant(value=2),
            ),
            ops=[ast.Eq()],
            comparators=[ast.BinOp(
                left=ast.Constant(value=n),
                op=ast.Mod(),
                right=ast.Constant(value=2),
            )]
        )
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        _nonce = random.randint(3, 30)
        if random.random() < 0.60:
            cond = ast.Compare(
                left=ast.BinOp(
                    left=ast.Constant(value=_nonce * _nonce),
                    op=ast.Mod(),
                    right=ast.Constant(value=_nonce + 1),
                ),
                ops=[ast.Eq()],
                comparators=[ast.BinOp(
                    left=ast.Constant(value=_nonce),
                    op=ast.Mod(),
                    right=ast.Constant(value=_nonce + 1),
                )]
            )
            # Dead-branch marker: must NEVER execute. The modular cond
            # above is actually FALSE for 3 <= n <= 30 (n*n % (n+1) = 1,
            # n % (n+1) = n), so the print in `orelse` RUNS — a real
            # output-changing bug (V10-diversity failure). Fix: use a
            # trivially-TRUE nonce-based cond with the marker in `body`
            # and Pass in `orelse` (still per-build unique via _nonce).
            dead = [ast.Expr(value=ast.Call(
                func=ast.Name(id='print', ctx=ast.Load()),
                args=[ast.Constant(value=f"SIG_{_nonce:x}_OK")],
                keywords=[]
            ))]
            _true_cond = ast.Compare(
                left=ast.Constant(value=_nonce),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=_nonce)],
            )
            if node.body:
                node.body.insert(0, ast.If(test=_true_cond, body=[ast.Pass()], orelse=dead))
            
        if len(node.body) > 2 and random.random() < 0.60:
            _has_scope_decl = any(isinstance(ch, (ast.Nonlocal, ast.Global)) for ch in ast.walk(node))
            if not _has_scope_decl:
                pred = random.choice(self.predicates)()
                fake_body = [ast.Pass()]
                opaque_if = ast.If(test=pred, body=node.body.copy(), orelse=fake_body)
                node.body = [opaque_if]
                self.inject_count += 1
        return node
class InstructionSubstitutor(ast.NodeTransformer):
    """MBA expression substitution with leveled intensity.

    Levels:
      L1 -- single-identity chains (depth exactly 1) + compare rewrites OFF.
        Minimal output growth; use for size/latency-sensitive builds.
      L2 -- current default behavior: chain depth uniformly 1..3 with ~47%
        rewrite probability + compare (xor-vs-zero) rewrites at 50%.
      L3 -- deeper chains (depth up to 5) + compare rewrites always ON.
        Maximum AI-simplifier resistance; largest output growth.
    """
    MBA_LEVELS = (1, 2, 3)

    def __init__(self, mba_validator=None, level: int = 2):
        if isinstance(level, bool) or level not in (1, 2, 3):
            raise ValueError(f"unknown MBA level: {level!r} (valid: 1-3)")
        self.sub_count = 0
        self._mba_validator = mba_validator
        self.level = level

    def _expr_to_binop_funcdef(self, expr: ast.AST) -> ast.FunctionDef:
        a_var = ast.Name(id="a", ctx=ast.Load())
        b_var = ast.Name(id="b", ctx=ast.Load())
        ret = ast.Return(value=expr)
        args = ast.arguments(
            posonlyargs=[], args=[
                ast.arg(arg="a"), ast.arg(arg="b"),
            ],
            kwonlyargs=[], kw_defaults=[], defaults=[],
        )
        return ast.FunctionDef(
            name="_mba_check", args=args,
            body=[ret], decorator_list=[], returns=None,
        )

    def _maybe_validate_mba(self, original_node: ast.AST,
                            replacement_node: ast.AST,
                            default_return) -> ast.AST:
        if self._mba_validator is None:
            return replacement_node
        orig_func = self._expr_to_binop_funcdef(original_node)
        repl_func = self._expr_to_binop_funcdef(replacement_node)
        valid = self._mba_validator.validate(orig_func, repl_func)
        if valid:
            self.sub_count += 1
            return replacement_node
        else:
            return default_return

    def _chain_depth(self) -> int:
        import random as _r
        if self.level == 1:
            return 1
        if self.level == 3:
            return _r.randint(3, 5)
        return _r.randint(1, 3)

    def _rewrite_gate(self) -> bool:
        import random as _r
        if self.level == 1:
            return _r.random() < 0.30
        if self.level == 3:
            return _r.random() < 0.75
        return _r.random() < 0.47

    def _mba_chain(self, expr: ast.AST, depth: int = 2) -> ast.AST:
        """Wrap an expression in nested MBA identities to make AI simplification harder."""
        current = expr
        for _ in range(depth):
            choice = random.randint(0, 5)
            if choice == 0:
                # identity: x = (x + K) - K
                K = random.randint(1000, 999999)
                current = ast.BinOp(
                    left=ast.BinOp(left=current, op=ast.Add(), right=ast.Constant(value=K)),
                    op=ast.Sub(), right=ast.Constant(value=K),
                )
            elif choice == 1:
                # identity: x = (x ^ K) ^ K
                K = random.randint(100, 999999)
                current = ast.BinOp(
                    left=ast.BinOp(left=current, op=ast.BitXor(), right=ast.Constant(value=K)),
                    op=ast.BitXor(), right=ast.Constant(value=K),
                )
            elif choice == 2:
                # identity: x = ~(~x)
                current = ast.UnaryOp(op=ast.Invert(), operand=ast.UnaryOp(op=ast.Invert(), operand=current))
            elif choice == 3:
                # identity: x = (x & K) | (x & ~K)  (split on bits)
                K = random.randint(1, 999999)
                notK = ast.UnaryOp(op=ast.Invert(), operand=ast.Constant(value=K))
                current = ast.BinOp(
                    left=ast.BinOp(left=current, op=ast.BitAnd(), right=ast.Constant(value=K)),
                    op=ast.BitOr(),
                    right=ast.BinOp(left=current, op=ast.BitAnd(), right=notK),
                )
            elif choice == 4:
                # identity: x = (x | K) & (x | ~K)
                K = random.randint(100, 999999)
                notK = ast.UnaryOp(op=ast.Invert(), operand=ast.Constant(value=K))
                current = ast.BinOp(
                    left=ast.BinOp(left=current, op=ast.BitOr(), right=ast.Constant(value=K)),
                    op=ast.BitAnd(),
                    right=ast.BinOp(left=current, op=ast.BitOr(), right=notK),
                )
            elif choice == 5:
                # identity: x = (x * K) // K  (only if K != 0)
                K = random.randint(2, min(9999, 9999))
                current = ast.BinOp(
                    left=ast.BinOp(left=current, op=ast.Mult(), right=ast.Constant(value=K)),
                    op=ast.FloorDiv(), right=ast.Constant(value=K),
                )
        return current

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if not self._rewrite_gate():
            return node
        if not (isinstance(node.left, ast.Constant) and isinstance(node.left.value, int)):
            return node
        if not (isinstance(node.right, ast.Constant) and isinstance(node.right.value, int)):
            return node
        if isinstance(node.op, ast.Add):
            repl = ast.BinOp(
                left=ast.BinOp(left=node.left, op=ast.BitXor(), right=node.right),
                op=ast.Add(),
                right=ast.BinOp(
                    left=ast.Constant(value=2),
                    op=ast.Mult(),
                    right=ast.BinOp(left=node.left, op=ast.BitAnd(), right=node.right)
                )
            )
            repl = self._mba_chain(repl, depth=self._chain_depth())
            return self._maybe_validate_mba(node, repl, node)
        elif isinstance(node.op, ast.Sub):
            repl = ast.BinOp(
                left=ast.BinOp(left=node.left, op=ast.BitXor(), right=node.right),
                op=ast.Sub(),
                right=ast.BinOp(
                    left=ast.Constant(value=2),
                    op=ast.Mult(),
                    right=ast.BinOp(
                        left=ast.UnaryOp(op=ast.Invert(), operand=node.left),
                        op=ast.BitAnd(),
                        right=node.right
                    )
                )
            )
            repl = self._mba_chain(repl, depth=self._chain_depth())
            return self._maybe_validate_mba(node, repl, node)
        elif isinstance(node.op, ast.Mult):
            if isinstance(node.right, ast.Constant) and node.right.value == 2:
                repl = ast.BinOp(left=node.left, op=ast.LShift(), right=ast.Constant(value=1))
                return self._maybe_validate_mba(node, repl, node)
            elif random.random() < 0.54 and isinstance(node.right, ast.Constant) and isinstance(node.right.value, int):
                v = node.right.value
                # a * v = (a + v)^2 - a^2 - v^2 // 2  when parity permits
                k = random.randint(10, min(999, 999))
                repl = ast.BinOp(
                    left=ast.BinOp(left=ast.Constant(value=k), op=ast.Mult(), right=node.left),
                    op=ast.Add(),
                    right=ast.BinOp(left=node.left, op=ast.Mult(), right=ast.Constant(value=v - k)),
                )
                repl = self._mba_chain(repl, depth=self._chain_depth())
                return self._maybe_validate_mba(node, repl, node)
        return node
    def visit_Compare(self, node):
        self.generic_visit(node)
        import random as _rc
        _cmp_prob = 0.0 if self.level == 1 else (1.0 if self.level == 3 else 0.5)
        if len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq) and _rc.random() < _cmp_prob:
            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, int) \
               and isinstance(node.comparators[0], ast.Constant) and isinstance(node.comparators[0].value, int):
                self.sub_count += 1
                return ast.Compare(
                    left=ast.BinOp(left=node.left, op=ast.BitXor(), right=node.comparators[0]),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=0)]
                )
        return node
class CallGraphObfuscator(ast.NodeTransformer):
    def __init__(self):
        self.func_table = {}
        self.table_var = '_nx_ftable'
        self.func_counter = 0
    def visit_Module(self, node):
        self.generic_visit(node)
        if self.func_table:
            table_items = [
                ast.Tuple(elts=[ast.Constant(value=k), ast.Name(id=v, ctx=ast.Load())], ctx=ast.Load())
                for k, v in self.func_table.items()
            ]
            table_init = ast.Assign(
                targets=[ast.Name(id=self.table_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id='dict', ctx=ast.Load()),
                    args=[ast.List(elts=table_items, ctx=ast.Load())],
                    keywords=[]
                )
            )
            node.body.insert(0, table_init)
        return node
    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and random.random() < 0.3:
            func_name = node.func.id
            # V10 kwargs fix (part 4): indirecting a call through a table
            # preserves positional binding but DESTROYS keyword binding
            # whenever the callee is renamed (or the table holds a renamed
            # alias): f(1, c=2) looks up the wrong name. Never indirect
            # calls that pass keywords.
            if node.keywords:
                return node
            blacklist = ['print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
                'range', 'open', 'type', 'isinstance', 'getattr', 'setattr', 'hasattr',
                'super', 'exec', 'eval', 'compile', 'globals', 'locals', 'vars',
                'asyncio', 'await', 'async', 'send', 'recv', 'accept', 'connect',
                'websocket', 'WebSocket', 'create_task', 'gather', 'wait', 'sleep']
            import builtins
            if hasattr(builtins, func_name) and func_name not in blacklist:
                idx = self.func_counter
                self.func_table[idx] = func_name
                self.func_counter += 1
                node.func = ast.Subscript(
                    value=ast.Name(id=self.table_var, ctx=ast.Load()),
                    slice=ast.Constant(value=idx),
                    ctx=ast.Load()
                )
        return node
class BogusExceptionHandler(ast.NodeTransformer):
    def __init__(self):
        self.wrap_count = 0
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        for child in ast.walk(node):
            if isinstance(child, (ast.Nonlocal, ast.Global, ast.AsyncFunctionDef, ast.AsyncWith, ast.AsyncFor, ast.FunctionDef)):
                return node
        if isinstance(node, ast.AsyncFunctionDef):
            return node
        if len(node.body) >= 2 and random.random() < 0.4:
            fake_except = ast.ExceptHandler(
                type=ast.Attribute(
                    value=ast.Name(id='builtins', ctx=ast.Load()),
                    attr='BlockingIOError',
                    ctx=ast.Load()
                ),
                name='_nx_fake_e',
                body=[
                    ast.Assign(
                        targets=[ast.Name(id='_nx_state_dummy', ctx=ast.Store())],
                        value=ast.Constant(value=random.randint(1, 99999))
                    ),
                    ast.Pass()
                ]
            )
            try_block = ast.Try(
                body=node.body.copy(),
                handlers=[fake_except],
                orelse=[],
                finalbody=[]
            )
            node.body = [try_block]
            self.wrap_count += 1
        return node
class UnsafeCollector(ast.NodeVisitor):
    def __init__(self):
        self.unsafe = set()
        self.assign_counts = {}
    def visit_Nonlocal(self, node):
        self.unsafe.update(node.names)
    def visit_Global(self, node):
        self.unsafe.update(node.names)
    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name): self.unsafe.add(node.target.id)
        self.generic_visit(node)
    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name): self.unsafe.add(node.target.id)
        self.generic_visit(node)
    def visit_Delete(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name): self.unsafe.add(target.id)
        self.generic_visit(node)
    def visit_arg(self, node):
        self.unsafe.add(node.arg)
        self.generic_visit(node)
    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assign_counts[target.id] = self.assign_counts.get(target.id, 0) + 1
        self.generic_visit(node)
    def finalize(self):
        for name, count in self.assign_counts.items():
            if count > 1: self.unsafe.add(name)
class VariableSplitter(ast.NodeTransformer):
    def __init__(self):
        self.split_map = {}
        self.split_count = 0
        self.unsafe_vars = set()
        self.collected = False
    def visit(self, node):
        if not self.collected:
            collector = UnsafeCollector()
            collector.visit(node)
            collector.finalize()
            self.unsafe_vars = collector.unsafe
            self.collected = True
        return super().visit(node)
    def visit_Assign(self, node):
        self.generic_visit(node)
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                if random.random() < 0.3:
                    orig_name = node.targets[0].id
                    if orig_name in self.unsafe_vars:
                        return node
                    if orig_name.startswith('_') or orig_name in ['self', 'cls']:
                        return node
                    mask = random.randint(1, 0xFFFF)
                    val = node.value.value
                    masked_val = val ^ mask
                    var_a = f'_nx_s{self.split_count}a'
                    var_b = f'_nx_s{self.split_count}b'
                    self.split_map[orig_name] = (var_a, var_b)
                    self.split_count += 1
                    assign_a = ast.Assign(
                        targets=[ast.Name(id=var_a, ctx=ast.Store())],
                        value=ast.Constant(value=masked_val)
                    )
                    assign_b = ast.Assign(
                        targets=[ast.Name(id=var_b, ctx=ast.Store())],
                        value=ast.Constant(value=mask)
                    )
                    return [assign_a, assign_b]
        return node
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.split_map:
            var_a, var_b = self.split_map[node.id]
            return ast.BinOp(
                left=ast.Name(id=var_a, ctx=ast.Load()),
                op=ast.BitXor(),
                right=ast.Name(id=var_b, ctx=ast.Load())
            )
        return node
class ConstantUnfolder(ast.NodeTransformer):
    def __init__(self):
        self.unfold_count = 0
        self.max_unfolds = 500
    def visit_Constant(self, node):
        if self.unfold_count >= self.max_unfolds: return node
        if isinstance(node.value, int) and 1 < node.value < 1000 and random.random() < 0.3:
            self.unfold_count += 1
            method = random.choice(['sum', 'shift', 'xor'])
            if method == 'sum':
                parts = []
                remaining = node.value
                while remaining > 0:
                    part = random.randint(1, max(1, remaining))
                    parts.append(part)
                    remaining -= part
                return ast.Call(
                    func=ast.Name(id='sum', ctx=ast.Load()),
                    args=[ast.List(elts=[ast.Constant(value=p) for p in parts], ctx=ast.Load())],
                    keywords=[]
                )
            elif method == 'shift':
                shift = random.randint(1, 4)
                base = node.value >> shift
                remainder = node.value - (base << shift)
                return ast.BinOp(
                    left=ast.BinOp(
                        left=ast.Constant(value=base),
                        op=ast.LShift(),
                        right=ast.Constant(value=shift)
                    ),
                    op=ast.Add(),
                    right=ast.Constant(value=remainder)
                )
            else:
                mask = random.randint(1, 0xFF)
                return ast.BinOp(
                    left=ast.Constant(value=node.value ^ mask),
                    op=ast.BitXor(),
                    right=ast.Constant(value=mask)
                )
        return node
class MetadataStripper(ast.NodeTransformer):
    def visit(self, node):
        if hasattr(node, 'lineno'): node.lineno = 1
        if hasattr(node, 'col_offset'): node.col_offset = 0
        if hasattr(node, 'end_lineno'): node.end_lineno = 1
        if hasattr(node, 'end_col_offset'): node.end_col_offset = 0
        return super().visit(node)
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
        return node
    def visit_ClassDef(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
        return node
    def visit_Module(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
        return node
class UnicodeIdentifierEncoder(ast.NodeTransformer):
    HOMOGLYPHS = {
        'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р', 's': 'ѕ', 'x': 'х', 'y': 'у',
        'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М', 'O': 'О',
        'P': 'Р', 'T': 'Т', 'X': 'Х'
    }
    def __init__(self):
        self.encoded_map = {}
        self.reserved = {
            'sum', 'min', 'max', 'abs', 'round', 'pow', 'divmod',
            'chr', 'ord', 'hex', 'oct', 'bin', 'ascii', 'repr',
            'print', 'str', 'int', 'float', 'bool', 'len', 'list', 'dict', 'set', 'tuple',
            'range', 'enumerate', 'zip', 'open', 'read', 'write', 'close', 'input',
            'type', 'isinstance', 'issubclass', 'callable', 'hasattr', 'getattr', 'setattr', 'delattr',
            'eval', 'exec', 'compile', 'globals', 'locals', 'vars', 'dir',
            'id', 'hash', 'object', 'super', 'property', 'classmethod', 'staticmethod',
            'bytes', 'bytearray', 'memoryview', 'format', 'slice', 'iter', 'next',
            'any', 'all', 'complex', 'frozenset', 'sorted', 'reversed', 'map', 'filter',
            'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError',
            'RuntimeError', 'StopIteration', 'ImportError', 'NameError', 'OSError', 'IOError',
            'BaseException', 'SystemExit', 'KeyboardInterrupt', 'GeneratorExit', 'AssertionError',
            'FileNotFoundError', 'PermissionError', 'TimeoutError', 'ConnectionError', 'BrokenPipeError',
            'sys', 'os', 'asyncio', 'time', 'json', 'random', 'math', 'self', 'cls', 'args', 'kwargs',
            're', 'io', 'threading', 'collections', 'functools', 'itertools', 'urllib', 'http',
            'socket', 'ssl', 'struct', 'base64', 'hashlib', 'hmac', 'secrets', 'pathlib',
            'requests', 'websockets', 'ipaddress', 'contextlib', 'subprocess', 'argparse',
            'getpass', 'string', 'urlparse', 'ConnectionClosed', 'WebSocketClientProtocol',
            'ws_connect', 'g_resolution_ledger', 'G_RESOLUTION_EXPIRATION_SEC',
            'importlib', 'platform', 'tempfile',
            '_nixon_b64',
            '__init__', '__main__', '__file__', '__name__', '__doc__', '__class__', '__dict__',
            '__module__', '__qualname__', '__annotations__', '__wrapped__', '__slots__',
            'Optional', 'Union', 'Any', 'List', 'Dict', 'Set', 'Tuple', 'Callable', 'Iterable',
            'Iterator', 'Generator', 'Sequence', 'Mapping', 'MutableMapping', 'MutableSequence',
            'Type', 'TypeVar', 'Generic', 'Protocol', 'Final', 'Literal', 'ClassVar', 'Annotated',
            'Awaitable', 'Coroutine', 'AsyncGenerator', 'AsyncIterable', 'AsyncIterator',
            'NamedTuple', 'TypedDict', 'cast', 'overload', 'no_type_check', 'get_type_hints',
            'gather', 'create_task', 'sleep', 'wait', 'wait_for', 'run', 'ensure_future',
            'get_event_loop', 'get_running_loop', 'new_event_loop', 'set_event_loop',
            'AbstractEventLoop', 'Task', 'Future', 'Queue', 'Lock', 'Event', 'Semaphore',
            'Condition', 'StreamReader', 'StreamWriter', 'open_connection', 'start_server',
            'CancelledError', 'InvalidStateError', 'IncompleteReadError',
            'LimitOverrunError', 'BoundedSemaphore', 'shield', 'timeout', 'timeout_at',
            'dataclass', 'field', 'fields', 'asdict', 'astuple', 'make_dataclass',
            'True', 'False', 'None', 'NotImplemented', 'Ellipsis',
            'path', 'fd', 'blob_key', 'ext', 'system', 'blobs',
            'encrypted_blob', 'blob_data', 'spec', 'module', 'fpath',
            '_nx_hwid_unlock', '_nx_trial_gate',
            '_NX_HWID_LOCK', '_NX_HWID_STATIC', '_NX_TRIAL_GATE', '_NX_TRIAL_SECONDS',
            '_NX_TRIAL_KEY', '_NX_TRIAL_DEADLINE', '_NX_TRIAL_TOKEN',
            '_NX_TRIAL_HWID_HINT', '_NX_KOD_ARMED', '_NX_VM_THRESHOLD',
            # V10 kernel-driver gate (SAFE read-only gate): helper + marker
            # names must survive unicode encoding or the armed gate breaks.
            '_nx_driver_stem', '_nx_driver_armed', '_nx_enum_drivers',
            '_nx_driver_hits', '_nx_driver_watch', 'driver_check',
            '_NX_DRIVER_BLOCKED', '_NX_DRIVER_ARMED_BUILD',
            '_NX_DRIVER_ARMED_VALUES', '_NX_DRIVER_INTERVAL',
            '_NX_DRIVER_VAR', '_NX_DRIVER_CHECK_ARMED',
            '_nx_watermark_gate',
            '_NX_WATERMARK_GATE', '_NX_WATERMARK_KEY', '_NX_WATERMARK_MSG',
            '_NX_WATERMARK_TAG', '_NX_WATERMARK_MARKER',
            # V10 unified kill ladder: single-failure-path wipe+exit helper.
            # _nx_kill must survive unicode encoding or the migrated gates
            # break at runtime.
            '_nx_kill',
            # V10 split-bootstrap (opt-in): fragmented-decoder helpers +
            # stub fragment markers must survive unicode encoding or the
            # armed lazy-activate path breaks.
            '_nx_sb_collect', '_nx_sb_combine', '_nx_sb_activate',
            '_NX_SB_HEAD', '_NX_SB_TRAIL', '_NX_SB_SALT', '_NX_SB_KEY',
            '_NX_SB_THIRD', '_NX_SPLIT_BOOTSTRAP',
            '_NX_SPLIT_BOOTSTRAP_ARMED', 'BLOB_KEY_SB',
            # Runtime integrity (frozen snapshots + stdlib audit): gate
            # helpers + markers must survive unicode encoding or the
            # armed gates break at runtime.
            '_nx_snapshot_gate', '_nx_stdlib_gate',
            '_NX_SNAPSHOT_GATE', '_NX_SNAPSHOT_TAG', '_NX_SNAPSHOT_FILES',
            '_NX_STDLIB_GATE', '_NX_STDLIB_TAG', '_NX_STDLIB_FUNCS',
            '__all__',
        }
        self._use_safe_mode = True
        # V10 internal-rename (opt-in, default OFF): proven-internal
        # method/attribute renames. Default = safe: every public method
        # defined in a class body is preserved. Opt in via
        # allow_internal_rename_names() — the encoder then renames only
        # those names (defs + attribute uses), consistently: _encode_name
        # maps old->new deterministically so defs and self.m/obj.m uses
        # stay in sync.
        self.allow_internal_rename = set()
    def allow_internal_rename_names(self, names):
        """Opt-in helper (V10 internal-rename): allow proven-internal methods.

        ``names`` is an iterable of method/attribute names already proven
        internal-only by obfuscator.internal_rename.find_internal_methods.
        Additive: never removes reserved entries; ignores bad input.
        """
        try:
            for _n in (names or []):
                if isinstance(_n, str) and _n:
                    self.allow_internal_rename.add(_n)
        except Exception:
            pass
    def reserve_all_names(self, names):
        """Additive helper (GAP #64): reserve __all__ export names."""
        try:
            for _n in (names or []):
                if isinstance(_n, str) and _n:
                    self.reserved.add(_n)
        except Exception:
            pass
    def _is_internal_allowed(self, name):
        try:
            return name in self.allow_internal_rename and name not in self.reserved
        except Exception:
            return False
    def _encode_name(self, name):
        if name in self.reserved or name.startswith('_'):
            return name
        if name in self.encoded_map: 
            return self.encoded_map[name]
        h = hashlib.md5(name.encode()).hexdigest()        
        if self._use_safe_mode:
            new_name = ""
            use_cyrillic = (int(h[0], 16) % 2 == 0)
            for char in h:
                if char.isdigit():
                    new_name += chr(ord('А') + int(char)) if use_cyrillic else chr(ord('A') + int(char))
                else:
                    upper_char = char.upper()
                    if use_cyrillic and upper_char in self.HOMOGLYPHS:
                        new_name += self.HOMOGLYPHS[upper_char]
                    else:
                        new_name += upper_char
        else:
            new_name = ""
            for char in h:
                if char.isdigit():
                    new_name += self.HOMOGLYPHS.get(random.choice(['A','B','C']), 'A')
                else:
                    new_name += self.HOMOGLYPHS.get(char.upper(), char)        
        if not new_name or len(new_name) < 2:
            new_name = "var_" + h[:8]        
        test_name = "_" + new_name
        if not test_name.isidentifier():
            new_name = "var_" + h[:8]
        self.encoded_map[name] = new_name
        return new_name
    def visit_Name(self, node):
        node.id = self._encode_name(node.id)
        self.generic_visit(node)
        return node
    def visit_FunctionDef(self, node):
        # V10 internal-rename: default = safe (class-body methods
        # preserved); only proven-internal names (allow set) encode.
        # Module-level functions keep legacy behavior (always encode).
        try:
            _depth = getattr(self, '_class_depth', 0)
        except Exception:
            _depth = 0
        if _depth > 0 and not self._is_internal_allowed(node.name):
            self.generic_visit(node)
            return node
        node.name = self._encode_name(node.name)
        self.generic_visit(node)
        return node
    def visit_ClassDef(self, node):
        node.name = self._encode_name(node.name)
        _prev = getattr(self, '_class_depth', 0)
        try:
            self._class_depth = _prev + 1
            self.generic_visit(node)
        finally:
            self._class_depth = _prev
        return node
    def visit_arg(self, node):
        node.arg = self._encode_name(node.arg)
        return node
    def visit_AsyncFunctionDef(self, node):
        # Same policy as FunctionDef (async methods preserve by default,
        # encode only when proven internal + opted in).
        return self.visit_FunctionDef(node)
    def visit_Attribute(self, node):
        # V10 internal-rename: attribute uses rewrite ONLY for
        # proven-internal names (def/use stay in sync via _encode_name).
        # Everything else is left untouched (external API + third-party
        # attributes safe, e.g. obj.append / sys.exit survive).
        self.generic_visit(node)
        try:
            if self._is_internal_allowed(node.attr):
                node.attr = self._encode_name(node.attr)
        except Exception:
            pass
        return node
    def visit_Nonlocal(self, node):
        node.names = [self._encode_name(n) for n in node.names]
        return node
    def visit_Global(self, node):
        node.names = [self._encode_name(n) for n in node.names]
        return node
    def visit_ExceptHandler(self, node):
        if node.name:
            node.name = self._encode_name(node.name)
        self.generic_visit(node)
        return node
class DependencyScanner:
    PACKAGE_MAP = {
        "PIL": "Pillow", "cv2": "opencv-python", "sklearn": "scikit-learn",
        "yaml": "PyYAML", "bs4": "beautifulsoup4", "crypto": "pycryptodome",
        "Cryptodome": "pycryptodome", "dns": "dnspython", "dotenv": "python-dotenv",
        "dateutil": "python-dateutil", "git": "GitPython", "jwt": "PyJWT",
        "telegram": "python-telegram-bot", "serial": "pyserial", "usb": "pyserial",
        "win32api": "pywin32", "win32con": "pywin32", "win32gui": "pywin32",
        "googleapiclient": "google-api-python-client", "protobuf": "protobuf",
        "discord": "discord.py", "playwright": "playwright"
    }
    STDLIB = {
        "os", "sys", "re", "time", "datetime", "json", "math", "random", "hashlib",
        "base64", "zlib", "gzip", "bz2", "lzma", "struct", "socket", "ssl", "string", "ipaddress",
        "sqlite3", "csv", "xml", "html", "http", "urllib", "logging", "argparse",
        "optparse", "getpass", "gettext", "locale", "copy", "pickle", "marshal",
        "shelve", "dbm", "tempfile", "shutil", "glob", "fnmatch", "linecache",
        "shlex", "threading", "queue", "multiprocessing", "subprocess", "ctypes",
        "typing", "collections", "abc", "itertools", "functools", "operator",
        "weakref", "enum", "numbers", "decimal", "fractions", "contextlib",
        "asyncio", "inspect", "ast", "dis", "codecs", "platform", "builtins",
        "importlib", "types", "zipfile", "io", "signal", "runpy", "atexit",
        "traceback", "gc", "uuid", "hmac", "secrets", "site", "warnings", "_thread"
    }
    def __init__(self):
        self.found_packages = set() 
        self.found_imports = set()  
    def scan_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            self._visit(tree)
        except Exception: pass
    def _visit(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.Import):
                for name in n.names:
                    self._add_module(name.name)
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    self._add_module(n.module)
    def _add_module(self, module_name):
        root_pkg = module_name.split('.')[0]
        if root_pkg in self.STDLIB: return
        self.found_imports.add(root_pkg)
        pip_name = self.PACKAGE_MAP.get(root_pkg, root_pkg)
        self.found_packages.add(pip_name)
    def get_pip_install_cmd(self):
        defaults = {"nuitka", "zstandard", "ordered-set", "requests", "websockets"} 
        final_set = defaults.union(self.found_packages)
        return "pip install " + " ".join(final_set)
    def get_nuitka_args(self):
        if not self.found_imports: return ""
        return " ".join([f"--include-package={name}" for name in self.found_imports])


def stego_encode(source_code):
    ZWS = '\u200b'
    ZWNJ = '\u200c'
    binary_data = ''.join(format(b, '08b') for b in source_code.encode('utf-8'))
    hidden = ''.join(ZWS if bit == '0' else ZWNJ for bit in binary_data)
    bootstrap = r'''# -*- coding: utf-8 -*-
_="{hidden}"
exec("".join(chr(int("".join("0"if c=="\\u200b"else"1"for c in _[i:i+8]),2))for i in range(0,len(_),8)))
'''
    return bootstrap.format(hidden=hidden)
def stego_wrap_output(final_script, output_path):
    stego_code = stego_encode(final_script)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(stego_code)
    return output_path
class CodeChecksumInjector(ast.NodeTransformer):
    def __init__(self):
        self.checksums = {}
        self.check_var = '_nx_chk'
    def visit_Module(self, node):
        self.generic_visit(node)
        if self.checksums:
            check_code = f'''
import hashlib as _h
{self.check_var} = {repr(self.checksums)}
def _nx_verify():
    import inspect
    for fn, expected in {self.check_var}.items():
        try:
            f = globals().get(fn)
            if f and callable(f):
                src = inspect.getsource(f)
                if _h.sha256(src.encode()).hexdigest()[:16] != expected:
                    raise RuntimeError("Integrity check failed")
        except Exception: pass
'''
            try:
                check_tree = ast.parse(check_code)
                node.body = check_tree.body + node.body
            except Exception: pass
        return node
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        try:
            func_code = ast.unparse(node)
            checksum = hashlib.sha256(func_code.encode()).hexdigest()[:16]
            self.checksums[node.name] = checksum
        except Exception: pass
        return node
class DynamicCodeGenerator(ast.NodeTransformer):
    def __init__(self, use_rust_jit=False):
        self.template_counter = 0
        self.templates = {}
        self.use_rust_jit = use_rust_jit
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if len(node.body) >= 3 and random.random() < 0.2:
            try:
                func_code = ast.unparse(node)
                key = random.randint(1, 255)
                template_name = f'_nx_tmpl_{self.template_counter}'
                self.template_counter += 1
                if self.use_rust_jit:
                    wrapper = self._make_rust_jit_wrapper(node, func_code, key, template_name)
                else:
                    wrapper = self._make_python_jit_wrapper(node, func_code, key, template_name)
                return ast.parse(wrapper).body
            except Exception: pass
        return node

    def _make_python_jit_wrapper(self, node, func_code, key, template_name):
        encrypted = ''.join(chr(ord(c) ^ key) for c in func_code)
        return f'''
import builtins
{template_name} = "{encrypted.encode('unicode_escape').decode('ascii')}"
def {node.name}(*args, **kwargs):
    _code = "".join(chr(ord(c) ^ {key}) for c in {template_name})
    _ns = {{}}
    _compiled = builtins.compile(_code, "<jit_{template_name}>", "exec")
    builtins.exec(_compiled, _ns)
    return _ns["{node.name}"](*args, **kwargs)
'''

    def _make_rust_jit_wrapper(self, node, func_code, key, template_name):
        import base64
        b64_code = base64.b64encode(func_code.encode()).decode()
        return f'''
import base64, ctypes, os, subprocess, tempfile
_{template_name}_b64 = "{b64_code}"
def {node.name}(*args, **kwargs):
    _code = base64.b64decode(_{template_name}_b64).decode()
    _compiled = compile(_code, "<jit_{template_name}>", "exec")
    _jit_so = os.environ.get("RUNTIME_JIT_SO", "")
    if _jit_so and os.path.exists(_jit_so):
        try:
            _lib = ctypes.CDLL(_jit_so)
            _lib.nixon_jit_exec.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
            _lib.nixon_jit_exec.restype = ctypes.c_int
            _cbytes = _code.encode("utf-8")
            _ret = _lib.nixon_jit_exec(_cbytes, len(_cbytes))
            if _ret == 0:
                pass
        except Exception:
            pass
    _jit_bin = os.environ.get("RUNTIME_JIT_BIN", "")
    if _jit_bin and os.path.exists(_jit_bin):
        _tmp_fd = None
        try:
            _tmp_fd, _tmp = tempfile.mkstemp(suffix=".jit")
            os.close(_tmp_fd)
            _tmp_fd = None
            with open(_tmp, "w") as _f:
                _f.write(_code)
            _result = subprocess.run(
                [_jit_bin, "jit", "exec", _tmp],
                capture_output=True, timeout=5
            )
            if _result.returncode == 0:
                return _result.stdout
        except Exception:
            pass
    _ns = {{}}
    exec(_compiled, _ns)
    return _ns["{node.name}"](*args, **kwargs)
'''
class EnhancedJunkInserter(ast.NodeTransformer):
    def __init__(self):
        self.junk_counter = 0
    def _generate_crypto_junk(self):
        patterns = [
            f'_nx_j{self.junk_counter} = bytes([x ^ {random.randint(1,255)} for x in str({random.randint(0,999)}).encode()])',
            f'_nx_k{self.junk_counter} = bytes([x ^ {random.randint(1,255)} for x in b"{"".join(chr(random.randint(65,90)) for _ in range(8))}"])',
            f'if sum(range({random.randint(1,10)})) != {sum(range(random.randint(1,10)))+1}: _nx_d{self.junk_counter} = None',
        ]
        self.junk_counter += 1
        return random.choice(patterns)
    def _generate_network_junk(self):
        self.junk_counter += 1
        return f'''
if False:
    try:
        import socket as _s{self.junk_counter}
        _s{self.junk_counter}.socket().connect(("127.0.0.1", {random.randint(10000,60000)}))
    except Exception: pass
'''
    def _generate_db_junk(self):
        self.junk_counter += 1
        return f'''
if 0 == 1:
    _db{self.junk_counter} = {{"key_{random.randint(0,999)}": str({random.randint(0,999)})}}
'''
    def visit_Module(self, node):
        self.generic_visit(node)
        new_body = []
        for stmt in node.body:
            new_body.append(stmt)
            if random.random() < 0.15:
                try:
                    junk_type = random.choice(['crypto', 'network', 'db'])
                    if junk_type == 'crypto':
                        junk = self._generate_crypto_junk()
                    elif junk_type == 'network':
                        junk = self._generate_network_junk()
                    else:
                        junk = self._generate_db_junk()
                    junk_ast = ast.parse(junk)
                    new_body.extend(junk_ast.body)
                except Exception: pass
        node.body = new_body
        return node
class FunctionTransformer(ast.NodeTransformer):
    def __init__(self):
        self.small_funcs = {}
        self.outlined_counter = 0
    def visit_Module(self, node):
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) and len(stmt.body) <= 3:
                if not any(isinstance(s, ast.Return) for s in stmt.body):
                    continue
                self.small_funcs[stmt.name] = stmt
        self.generic_visit(node)
        return node
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        for child in ast.walk(node):
            if isinstance(child, (ast.Nonlocal, ast.Global, ast.AsyncFunctionDef, ast.AsyncWith, ast.AsyncFor, ast.FunctionDef)):
                return node
        if isinstance(node, ast.AsyncFunctionDef):
            return node
        if len(node.body) <= 5:
            return node
        if random.random() >= 0.25:
            return node
        # V10 kwargs fix (part 3): outlining is unsafe for functions with
        # keyword-callable signatures (posonly/kwonly/vararg/kwarg/defaults).
        # The outlined fragment passes everything positionally, which breaks
        # keyword binding exactly like the renamer bug. Skip such functions.
        _fa = node.args
        if _fa.posonlyargs or _fa.kwonlyargs or _fa.vararg is not None or _fa.kwarg is not None or _fa.defaults or _fa.kw_defaults:
            return node
        var_capture = VariableCapture(node)
        split_point = random.randint(2, len(node.body) - 2)
        extracted = node.body[split_point:]
        temp_module = ast.Module(body=extracted, type_ignores=[])
        external_vars = var_capture.get_external_vars(temp_module)
        outlined_name = f'_nx_out_{self.outlined_counter}'
        self.outlined_counter += 1
        new_args = [ast.arg(arg=var, annotation=None) for var in sorted(external_vars)]
        outlined_func = ast.FunctionDef(
            name=outlined_name,
            args=ast.arguments(posonlyargs=[], args=new_args, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
            body=extracted,
            decorator_list=[],
            returns=None
        )
        call_args = [ast.Name(id=var, ctx=ast.Load()) for var in sorted(external_vars)]
        call_node = ast.Call(
            func=ast.Name(id=outlined_name, ctx=ast.Load()),
            args=call_args, keywords=[]
        )
        has_return = any(isinstance(s, ast.Return) for block in extracted for s in ast.walk(block))
        if has_return:
            call_outlined = ast.Return(value=call_node)
        else:
            call_outlined = ast.Expr(value=call_node)
        node.body = node.body[:split_point] + [call_outlined]
        ast.fix_missing_locations(outlined_func)
        ast.fix_missing_locations(node)
        return [outlined_func, node]
class ReflectionObfuscator(ast.NodeTransformer):
    def __init__(self):
        self.attr_table = {}
        self.table_var = '_nx_attrs'
    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load) and random.random() < 0.3:
            attr_name = node.attr
            skip_attrs = ['__init__', '__name__', '__class__', '__dict__',
                'send', 'recv', 'close', 'accept', 'connect', 'write', 'read',
                'ws', 'websocket', 'socket', 'reader', 'writer',
                '__aenter__', '__aexit__', '__await__', '__aiter__', '__anext__']
            if attr_name not in skip_attrs:
                key = random.randint(1, 255)
                encrypted_attr = ''.join(chr(ord(c) ^ key) for c in attr_name)
                decrypt_expr = ast.Call(
                    func=ast.Attribute(
                        value=ast.Constant(value=''),
                        attr='join',
                        ctx=ast.Load()
                    ),
                    args=[ast.GeneratorExp(
                        elt=ast.Call(
                            func=ast.Name(id='chr', ctx=ast.Load()),
                            args=[ast.BinOp(
                                left=ast.Call(func=ast.Name(id='ord', ctx=ast.Load()), args=[ast.Name(id='c', ctx=ast.Load())], keywords=[]),
                                op=ast.BitXor(),
                                right=ast.Constant(value=key)
                            )],
                            keywords=[]
                        ),
                        generators=[ast.comprehension(
                            target=ast.Name(id='c', ctx=ast.Store()),
                            iter=ast.Constant(value=encrypted_attr),
                            ifs=[],
                            is_async=0
                        )]
                    )],
                    keywords=[]
                )
                return ast.Call(
                    func=ast.Name(id='getattr', ctx=ast.Load()),
                    args=[node.value, decrypt_expr],
                    keywords=[]
                )
        return node
class ControlFlowFlattener(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        for child in ast.walk(node):
            if isinstance(child, (ast.Nonlocal, ast.Global, ast.AsyncFunctionDef, ast.AsyncWith, ast.AsyncFor, ast.FunctionDef)):
                return node
        if isinstance(node, ast.AsyncFunctionDef): return node
        if len(node.body) < 3: return node
        self.generic_visit(node)
        state_var = "_nx_state"
        loop_var = "_nx_loop"
        cfi_hash_var = "_nx_cfi_h"
        cfi_lut_var = "_nx_cfi_lut"
        blocks = []
        current_block = []
        for stmt in node.body:
            current_block.append(stmt)
            if isinstance(stmt, (ast.If, ast.For, ast.While, ast.Return)):
                blocks.append(current_block)
                current_block = []
        if current_block: blocks.append(current_block)
        if len(blocks) < 2: return node
        num_blocks = len(blocks)
        indices = list(range(num_blocks))
        random.shuffle(indices)
        lut_size = max(num_blocks * 4, 64)
        dispatch_lut = [random.randint(0, num_blocks - 1) for _ in range(lut_size)]
        for i in range(len(indices) - 1):
            current_idx = indices[i]
            next_idx = indices[i + 1]
            expected_hash = 0
            for j in range(i + 1):
                expected_hash = (expected_hash * 1103515245 + 12345 + indices[j] * 2654435761) & 0xFFFFFFFF
            lut_slot = expected_hash % lut_size
            dispatch_lut[lut_slot] = next_idx
        init_hash_val = 0
        new_body = [
            ast.Assign(targets=[ast.Name(id=state_var, ctx=ast.Store())], value=ast.Constant(value=indices[0])),
            ast.Assign(targets=[ast.Name(id=loop_var, ctx=ast.Store())], value=ast.Constant(value=True)),
            ast.Assign(targets=[ast.Name(id=cfi_hash_var, ctx=ast.Store())], value=ast.Constant(value=init_hash_val)),
            ast.Assign(targets=[ast.Name(id=cfi_lut_var, ctx=ast.Store())], value=ast.Constant(value=dispatch_lut)),
        ]
        if_chain = None
        for i in reversed(range(len(indices))):
            original_idx = indices[i]
            block = list(blocks[original_idx])
            is_last = (i == len(indices) - 1)
            has_return = any(isinstance(s, ast.Return) for s in block)
            if not has_return:
                cfi_update = ast.Assign(
                    targets=[ast.Name(id=cfi_hash_var, ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.BinOp(
                            left=ast.BinOp(
                                left=ast.BinOp(
                                    left=ast.Name(id=cfi_hash_var, ctx=ast.Load()),
                                    op=ast.Mult(),
                                    right=ast.Constant(value=1103515245)
                                ),
                                op=ast.Add(),
                                right=ast.Constant(value=12345)
                            ),
                            op=ast.Add(),
                            right=ast.BinOp(
                                left=ast.Constant(value=original_idx),
                                op=ast.Mult(),
                                right=ast.Constant(value=2654435761)
                            )
                        ),
                        op=ast.BitAnd(),
                        right=ast.Constant(value=0xFFFFFFFF)
                    )
                )
                block.append(cfi_update)
                if is_last:
                    block.append(ast.Assign(
                        targets=[ast.Name(id=loop_var, ctx=ast.Store())],
                        value=ast.Constant(value=False)
                    ))
                else:
                    next_state_expr = ast.Subscript(
                        value=ast.Name(id=cfi_lut_var, ctx=ast.Load()),
                        slice=ast.BinOp(
                            left=ast.Name(id=cfi_hash_var, ctx=ast.Load()),
                            op=ast.Mod(),
                            right=ast.Constant(value=lut_size)
                        ),
                        ctx=ast.Load()
                    )
                    block.append(ast.Assign(
                        targets=[ast.Name(id=state_var, ctx=ast.Store())],
                        value=next_state_expr
                    ))
            compare = ast.Compare(
                left=ast.Name(id=state_var, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=original_idx)]
            )
            if if_chain is None:
                if_chain = ast.If(test=compare, body=block, orelse=[])
            else:
                if_chain = ast.If(test=compare, body=block, orelse=[if_chain])
        loop_body = [if_chain] if if_chain else []
        new_body.append(ast.While(test=ast.Name(id=loop_var, ctx=ast.Load()), body=loop_body, orelse=[]))
        node.body = new_body
        return node
class ExtendedArgBreaker(ast.NodeTransformer):
    """Decompiler-hostile constructs that preserve runtime semantics.

    Inserts, per eligible FunctionDef (body with >= 3 statements):
      (a) dead ``if False:`` blocks containing oversized jumps
          (``for _nx_i in range(2**32): pass`` inside unreachable code),
      (b) try/except/finally mazes guarded by constant-false tests,
      (c) a fake massive expression statement (long chained BinOp that
          folds to a constant but confuses pattern matchers).

    Safety: all inserted code is either unreachable (``if False`` /
    ``if 0 == 1`` guards) or side-effect-free (a pure BinOp assigned to
    a throwaway ``_nx_`` name). ``self.inject_count`` tracks insertions.

    Wiring: applied in ``obfuscator/core/sources.py::apply_ast_mutation``
    adjacent to OpaquePredicateInjector/EnhancedJunkInserter with flag
    ``break_decompiler=True`` (default ON).
    """
    def __init__(self):
        self.inject_count = 0
    def _dead_jump_block(self):
        inner_for = ast.For(
            target=ast.Name(id='_nx_i', ctx=ast.Store()),
            iter=ast.Call(
                func=ast.Name(id='range', ctx=ast.Load()),
                args=[ast.BinOp(left=ast.Constant(value=2), op=ast.Pow(), right=ast.Constant(value=32))],
                keywords=[]
            ),
            body=[ast.Pass()],
            orelse=[]
        )
        return ast.If(test=ast.Constant(value=False), body=[inner_for], orelse=[])
    def _try_maze(self):
        guard_false = ast.Compare(
            left=ast.Constant(value=0),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=1)]
        )
        inner_try = ast.Try(
            body=[ast.If(test=guard_false, body=[ast.Expr(value=ast.Constant(value=1))], orelse=[])],
            handlers=[ast.ExceptHandler(
                type=ast.Name(id='Exception', ctx=ast.Load()),
                name=None,
                body=[ast.Pass()]
            )],
            orelse=[],
            finalbody=[ast.If(test=ast.Constant(value=False), body=[ast.Pass()], orelse=[])]
        )
        return ast.If(test=ast.Constant(value=False), body=[inner_try], orelse=[])
    def _fake_massive_expr(self):
        # (((1 + 2) * 3) ^ 4) ... long pure chain folding to a constant.
        expr = ast.Constant(value=1)
        ops = [ast.Add(), ast.Mult(), ast.BitXor(), ast.Add(), ast.BitOr(), ast.BitAnd()]
        val = 2
        for op in (ops * 4)[:24]:
            expr = ast.BinOp(left=expr, op=op, right=ast.Constant(value=val))
            val += 1
        return ast.Assign(targets=[ast.Name(id='_nx_fake_expr', ctx=ast.Store())], value=expr)
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if len(node.body) < 3:
            return node
        inserts = [self._dead_jump_block(), self._try_maze(), self._fake_massive_expr()]
        try:
            pos = 1 if len(node.body) >= 1 else 0
            for stmt in reversed(inserts):
                node.body.insert(pos, stmt)
            ast.fix_missing_locations(node)
            self.inject_count += len(inserts)
        except Exception:
            pass
        return node

