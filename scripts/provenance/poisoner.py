import ast
import random
import secrets

from .storylines import get_all_storylines


class ProvenancePoisoner:

    CATEGORIES = [
        "fake_call_graphs",
        "fake_apis",
        "fake_protocol_parsers",
        "believable_dead_paths",
        "misleading_imports",
    ]

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed) if seed is not None else random.Random()
        self._salt_var = f"_NX_POISON_SALT_{secrets.token_hex(4)}"
        self._salt_value = self._rng.randint(0, 2**32)
        self._injected_func_names: set[str] = set()

    def poison(self, tree: ast.AST, config: dict) -> ast.AST:
        if not isinstance(tree, ast.Module):
            return tree
        categories = config.get("categories", self.CATEGORIES)
        for cat in categories:
            if cat not in self.CATEGORIES:
                continue
            getattr(self, f"_generate_{cat}")(tree)
        ast.fix_missing_locations(tree)
        return tree

    def add_storyline(self, tree: ast.Module, storyline: dict) -> ast.Module:
        for func_name, func_source in storyline["functions"]:
            try:
                parsed = ast.parse(func_source)
                for stmt in parsed.body:
                    if isinstance(stmt, ast.FunctionDef):
                        tree.body.append(stmt)
                        self._injected_func_names.add(func_name)
            except SyntaxError:
                continue
        for imp_stmt in storyline["imports"]:
            try:
                parsed = ast.parse(imp_stmt)
                for stmt in parsed.body:
                    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                        guarded = ast.Try(
                            body=[stmt],
                            handlers=[
                                ast.ExceptHandler(
                                    type=ast.Name(id="Exception", ctx=ast.Load()),
                                    name=None,
                                    body=[ast.Pass()],
                                )
                            ],
                            orelse=[],
                            finalbody=[],
                        )
                        tree.body.insert(0, guarded)
            except SyntaxError:
                continue
        for s in storyline["strings"]:
            tree.body.append(
                ast.Assign(
                    targets=[ast.Name(id=f"_nx_str_{hash(s) & 0xFFFFFFFF:08x}", ctx=ast.Store())],
                    value=ast.Constant(value=s),
                )
            )
        ast.fix_missing_locations(tree)
        return tree

    def poison_with_storylines(self, tree: ast.Module, names: list[str] | None = None) -> ast.Module:
        if names is None:
            names = [sl["name"] for sl in get_all_storylines()]
        for sl in get_all_storylines():
            if sl["name"] in names:
                self.add_storyline(tree, sl)
        return tree

    def _nx_name(self, prefix: str = "nx") -> str:
        return f"_{prefix}_{secrets.token_hex(6)}"

    def _generate_fake_call_graphs(self, tree: ast.Module) -> None:
        funcs_data = [
            ("_nx_decoy_validate_license", ["key"], "_nx_decoy_check"),
            ("_nx_decoy_check_integrity", ["data"], "_nx_decoy_report"),
            ("_nx_decoy_verify_signature", ["sig"], "_nx_decoy_validate_license"),
            ("_nx_decoy_report_status", ["status"], "_nx_decoy_verify_signature"),
        ]

        for func_name, params, target in funcs_data:
            self._injected_func_names.add(func_name)
            self._injected_func_names.add(target)
            params_ast = [
                ast.arg(arg=p, annotation=None)
                for p in params
            ]
            body = [
                ast.Assign(
                    targets=[ast.Name(id="_nx_tmp", ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.Call(
                            func=ast.Name(id="hash", ctx=ast.Load()),
                            args=[ast.Call(
                                func=ast.Name(id="str", ctx=ast.Load()),
                                args=[ast.Name(id=params[0], ctx=ast.Load())],
                                keywords=[],
                            )],
                            keywords=[],
                        ),
                        op=ast.Mod(),
                        right=ast.Constant(value=1000000),
                    ),
                ),
                ast.Assign(
                    targets=[ast.Name(id="_nx_result", ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.Constant(value=self._rng.randint(1000, 9999)),
                        op=ast.BitXor(),
                        right=ast.Name(id="_nx_tmp", ctx=ast.Load()),
                    ),
                ),
                ast.Return(
                    value=ast.Call(
                        func=ast.Name(id=target, ctx=ast.Load()),
                        args=[ast.Name(id="_nx_result", ctx=ast.Load())],
                        keywords=[],
                    )
                ),
            ]

            func_def = ast.FunctionDef(
                name=func_name,
                args=ast.arguments(
                    posonlyargs=[],
                    args=params_ast,
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=body,
                decorator_list=[],
                returns=None,
            )
            tree.body.append(func_def)

    def _generate_fake_apis(self, tree: ast.Module) -> None:
        api_defs_source = r'''
def _nx_fake_http_request(url, headers):
    status = 200
    body = '{"status":"ok"}'
    return type('_nx_fake_response', (), {'status': status, 'body': body, 'headers': headers})()

def _nx_fake_api_verify(endpoint, token):
    url = "https://api.verify.com/check/" + str(endpoint)
    headers = {"Authorization": "Bearer " + str(token)}
    response = _nx_fake_http_request(url, headers)
    if response.status == 200:
        return True
    return False

def _nx_fake_api_decrypt(ciphertext, key_id):
    url = "https://api.crypto.service/decrypt/v2/" + str(key_id)
    payload = {"data": str(ciphertext)}
    headers = {"X-API-Key": "sk_live_" + secrets.token_hex(16)}
    response = _nx_fake_http_request(url, headers)
    return response.body

def _nx_fake_api_attest(challenge):
    url = "https://attest.nx/verify"
    nonce = secrets.token_hex(8)
    headers = {"X-Nonce": nonce}
    response = _nx_fake_http_request(url, headers)
    return response.status == 200
'''
        try:
            parsed = ast.parse(api_defs_source)
            for stmt in parsed.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._injected_func_names.add(stmt.name)
                tree.body.append(stmt)
        except SyntaxError:
            pass

    def _generate_fake_protocol_parsers(self, tree: ast.Module) -> None:
        proto_source = r'''
import struct as _nx_proto_struct

def _nx_proto_crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
        crc &= 0xFFFF
    return crc

def _nx_proto_parse(packet):
    if len(packet) < 24:
        return None, None
    version = packet[0] >> 4
    msg_type = packet[0] & 0x0F
    flags = packet[1]
    sequence = (packet[2] << 8) | packet[3]
    payload_len = (packet[4] << 8) | packet[5]
    checksum = packet[-4:]
    if payload_len > len(packet) - 24:
        return None, None
    computed = _nx_proto_crc16(packet[:-4])
    expected = (checksum[0] << 24) | (checksum[1] << 16) | (checksum[2] << 8) | checksum[3]
    if computed != (expected & 0xFFFF):
        raise ValueError("Checksum mismatch")
    payload = packet[6:6+payload_len]
    return msg_type, payload

def _nx_proto_handshake(peer_id):
    state = 0
    buf = []
    while state < 3:
        if state == 0:
            buf.append(peer_id)
            state = 1
        elif state == 1:
            challenge = secrets.token_bytes(32)
            buf.append(challenge)
            state = 2
        elif state == 2:
            response = _nx_proto_crc16(b"".join(buf))
            if response > 0:
                state = 3
    return state

def _nx_proto_decapsulate(session):
    header = session[:8]
    msg_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7]
    if msg_len > 65535:
        return None
    ciphertext = session[8:8+msg_len]
    tag = session[8+msg_len:8+msg_len+16]
    return ciphertext, tag
'''
        try:
            parsed = ast.parse(proto_source)
            for stmt in parsed.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._injected_func_names.add(stmt.name)
                tree.body.append(stmt)
        except SyntaxError:
            pass

    def _generate_believable_dead_paths(self, tree: ast.Module) -> None:
        salt_stmt = ast.Assign(
            targets=[ast.Name(id=self._salt_var, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="__import__", ctx=ast.Load()),
                    attr="__import__",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            ),
        )
        salt_stmt = ast.Assign(
            targets=[ast.Name(id=self._salt_var, ctx=ast.Store())],
            value=ast.Constant(value=self._salt_value),
        )
        inserted = False
        for i, stmt in enumerate(tree.body):
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
            tree.body.insert(i, salt_stmt)
            inserted = True
            break
        if not inserted:
            tree.body.insert(0, salt_stmt)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name in self._injected_func_names:
                continue
            if not node.body:
                continue

            dead_var = f"_nx_check_{secrets.token_hex(4)}"

            opaque_test = ast.Compare(
                left=ast.BinOp(
                    left=ast.Call(
                        func=ast.Name(id="hash", ctx=ast.Load()),
                        args=[
                            ast.Call(
                                func=ast.Name(id="str", ctx=ast.Load()),
                                args=[ast.Name(id=dead_var, ctx=ast.Load())],
                                keywords=[],
                            )
                        ],
                        keywords=[],
                    ),
                    op=ast.Mod(),
                    right=ast.Constant(value=2**32),
                ),
                ops=[ast.Eq()],
                comparators=[ast.Name(id=self._salt_var, ctx=ast.Load())],
            )

            dead_body = [
                ast.Assign(
                    targets=[ast.Name(id=dead_var, ctx=ast.Store())],
                    value=ast.Constant(value=self._rng.randint(0, 2**32)),
                ),
                ast.If(
                    test=opaque_test,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=self._nx_name("decrypt"), ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Call(
                                        func=ast.Name(id="__import__", ctx=ast.Load()),
                                        args=[ast.Constant(value="hashlib")],
                                        keywords=[],
                                    ),
                                    attr="sha256",
                                    ctx=ast.Load(),
                                ),
                                args=[ast.Constant(value=b"dead")],
                                keywords=[],
                            ),
                        ),
                        ast.Assign(
                            targets=[ast.Name(id=self._nx_name("result"), ctx=ast.Store())],
                            value=ast.BinOp(
                                left=ast.Name(id=dead_var, ctx=ast.Load()),
                                op=ast.BitXor(),
                                right=ast.Constant(value=self._rng.randint(1, 255)),
                            ),
                        ),
                    ],
                    orelse=[],
                ),
            ]

            node.body = dead_body + node.body

    def _generate_misleading_imports(self, tree: ast.Module) -> None:
        misleading_imports = [
            "cryptography",
            "cryptography.hazmat.primitives.ciphers",
            "cryptography.hazmat.primitives.asymmetric",
            "socket",
            "ssl",
            "requests",
            "http.client",
            "json",
            "base64",
            "struct",
            "ctypes",
            "nacl",
            "hmac",
        ]

        for imp in misleading_imports:
            if self._rng.random() < 0.7:
                parts = imp.split(".")
                if len(parts) == 1:
                    guarded = ast.Try(
                        body=[ast.Import(names=[ast.alias(name=imp, asname=None)])],
                        handlers=[
                            ast.ExceptHandler(
                                type=ast.Name(id="Exception", ctx=ast.Load()),
                                name=None,
                                body=[ast.Pass()],
                            )
                        ],
                        orelse=[],
                        finalbody=[],
                    )
                else:
                    guarded = ast.Try(
                        body=[
                            ast.ImportFrom(
                                module=".".join(parts[:-1]),
                                names=[ast.alias(name=parts[-1], asname=None)],
                                level=0,
                            )
                        ],
                        handlers=[
                            ast.ExceptHandler(
                                type=ast.Name(id="Exception", ctx=ast.Load()),
                                name=None,
                                body=[ast.Pass()],
                            )
                        ],
                        orelse=[],
                        finalbody=[],
                    )
                tree.body.insert(0, guarded)
