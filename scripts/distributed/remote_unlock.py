import hashlib
import hmac
import json
import os
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class UnlockToken:
    fragment_id: int
    token: bytes
    expires_at: float
    signature: bytes

    def to_dict(self) -> dict:
        return {
            "fragment_id": self.fragment_id,
            "token": self.token.hex(),
            "expires_at": self.expires_at,
            "signature": self.signature.hex(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UnlockToken":
        return cls(
            fragment_id=d["fragment_id"],
            token=bytes.fromhex(d["token"]),
            expires_at=d["expires_at"],
            signature=bytes.fromhex(d["signature"]),
        )


class RemoteUnlockServer:
    def __init__(self, server_secret: Optional[bytes] = None, token_ttl: float = 30.0):
        self.server_secret = server_secret or os.urandom(32)
        self.token_ttl = token_ttl
        self._issued_tokens: Dict[int, UnlockToken] = {}
        self._client_secrets: Dict[bytes, bytes] = {}
        self._lock = threading.Lock()
        self._server_socket: Optional[socket.socket] = None
        self._running = False
        self._port: int = 0

    def register_client(self, client_id: bytes, client_secret: bytes):
        with self._lock:
            self._client_secrets[client_id] = client_secret

    def validate_request(self, fragment_id: int, client_id: bytes, request_sig: bytes) -> bool:
        client_secret = self._client_secrets.get(client_id)
        if client_secret is None:
            return False
        data = struct.pack(">I", fragment_id) + client_id
        expected = hmac.new(client_secret, data, hashlib.sha256).digest()
        return hmac.compare_digest(request_sig, expected)

    def issue_token(self, fragment_id: int, client_id: bytes) -> Optional[UnlockToken]:
        token_data = struct.pack(">I", fragment_id) + client_id + struct.pack(">d", time.time())
        token = hashlib.sha256(self.server_secret + token_data).digest()
        expires_at = time.time() + self.token_ttl
        sig_data = token + struct.pack(">d", expires_at)
        signature = hmac.new(self.server_secret, sig_data, hashlib.sha256).digest()
        ut = UnlockToken(
            fragment_id=fragment_id,
            token=token,
            expires_at=expires_at,
            signature=signature,
        )
        with self._lock:
            self._issued_tokens[fragment_id] = ut
        return ut

    def verify_token(self, token: UnlockToken) -> bool:
        if time.time() > token.expires_at:
            return False
        sig_data = token.token + struct.pack(">d", token.expires_at)
        expected = hmac.new(self.server_secret, sig_data, hashlib.sha256).digest()
        return hmac.compare_digest(token.signature, expected)

    def get_token(self, fragment_id: int) -> Optional[UnlockToken]:
        with self._lock:
            return self._issued_tokens.get(fragment_id)

    def _handle_client(self, conn: socket.socket):
        try:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if len(data) > 65536:
                    break
            if not data:
                return
            msg = json.loads(data.decode("utf-8"))
            action = msg.get("action")
            if action == "register":
                client_id = bytes.fromhex(msg["client_id"])
                client_secret = bytes.fromhex(msg["client_secret"])
                self.register_client(client_id, client_secret)
                response = {"status": "ok"}
            elif action == "request_token":
                fragment_id = msg["fragment_id"]
                client_id = bytes.fromhex(msg["client_id"])
                request_sig = bytes.fromhex(msg["signature"])
                if not self.validate_request(fragment_id, client_id, request_sig):
                    response = {"status": "error", "reason": "validation_failed"}
                else:
                    token = self.issue_token(fragment_id, client_id)
                    if token is None:
                        response = {"status": "error", "reason": "token_issuance_failed"}
                    else:
                        response = {"status": "ok", "token": token.to_dict()}
            else:
                response = {"status": "error", "reason": "unknown_action"}
            conn.sendall(json.dumps(response).encode("utf-8"))
        except Exception:
            pass
        finally:
            conn.close()

    def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((host, port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)
        self._port = self._server_socket.getsockname()[1]
        self._running = True

        def accept_loop():
            while self._running:
                try:
                    conn, addr = self._server_socket.accept()
                    t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
                except OSError:
                    break

        t = threading.Thread(target=accept_loop, daemon=True)
        t.start()
        return self._port

    def stop(self):
        self._running = False
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None


class RemoteUnlockClient:
    def __init__(self, local_secret: Optional[bytes] = None):
        self.local_secret = local_secret or os.urandom(32)
        self._cached_tokens: Dict[int, UnlockToken] = {}
        self._cached_keys: Dict[int, bytes] = {}
        self._server: Optional[RemoteUnlockServer] = None
        self._client_id: bytes = os.urandom(16)
        self._host: Optional[str] = None
        self._port: Optional[int] = None

    def bind_server(self, server: RemoteUnlockServer):
        self._server = server
        server.register_client(self._client_id, self.local_secret)

    def connect(self, host: str, port: int, server: RemoteUnlockServer):
        self._host = host
        self._port = port
        self._server = server
        server.register_client(self._client_id, self.local_secret)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))
        reg_msg = json.dumps({
            "action": "register",
            "client_id": self._client_id.hex(),
            "client_secret": self.local_secret.hex(),
        }).encode("utf-8")
        sock.sendall(reg_msg)
        sock.close()

    def _make_request_sig(self, fragment_id: int) -> bytes:
        data = struct.pack(">I", fragment_id) + self._client_id
        return hmac.new(self.local_secret, data, hashlib.sha256).digest()

    def request_unlock(self, fragment_id: int) -> Optional[UnlockToken]:
        if self._server is None:
            return self._fallback(fragment_id)

        if self._host is not None and self._port is not None:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((self._host, self._port))
                sig = self._make_request_sig(fragment_id)
                req_msg = json.dumps({
                    "action": "request_token",
                    "fragment_id": fragment_id,
                    "client_id": self._client_id.hex(),
                    "signature": sig.hex(),
                }).encode("utf-8")
                sock.sendall(req_msg)
                sock.shutdown(socket.SHUT_WR)
                response_data = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                sock.close()
                if not response_data:
                    return self._fallback(fragment_id)
                response = json.loads(response_data.decode("utf-8"))
                if response.get("status") == "ok" and "token" in response:
                    token = UnlockToken.from_dict(response["token"])
                    self._cached_tokens[fragment_id] = token
                    return token
                return self._fallback(fragment_id)
            except (socket.error, OSError, json.JSONDecodeError):
                return self._fallback(fragment_id)

        if self._server is not None:
            sig = self._make_request_sig(fragment_id)
            if not self._server.validate_request(fragment_id, self._client_id, sig):
                return self._fallback(fragment_id)

            token = self._server.issue_token(fragment_id, self._client_id)
            if token is None:
                return self._fallback(fragment_id)

            self._cached_tokens[fragment_id] = token
            return token

        return self._fallback(fragment_id)

    def _fallback(self, fragment_id: int) -> Optional[UnlockToken]:
        if fragment_id in self._cached_tokens:
            cached = self._cached_tokens[fragment_id]
            if time.time() <= cached.expires_at + 300:
                return cached
        return None

    def derive_key(self, fragment_id: int, token: UnlockToken) -> Optional[bytes]:
        if time.time() > token.expires_at:
            if fragment_id in self._cached_keys:
                return self._cached_keys[fragment_id]
            return None

        key_material = token.token + self.local_secret + struct.pack(">I", fragment_id)
        key = hashlib.sha256(key_material).digest()
        self._cached_keys[fragment_id] = key
        return key

    def simulate_network_failure(self, fragment_id: int) -> Optional[bytes]:
        if fragment_id in self._cached_tokens:
            cached = self._cached_tokens[fragment_id]
            if time.time() <= cached.expires_at + 300:
                return self.derive_key(fragment_id, cached)
        return None

    def unlock_fragment(self, fragment_id: int, encrypted_data: bytes) -> Optional[bytes]:
        token = self.request_unlock(fragment_id)
        if token is None:
            return None
        key = self.derive_key(fragment_id, token)
        if key is None:
            return None
        if len(key) < len(encrypted_data):
            key = hashlib.sha256(key + struct.pack(">I", fragment_id)).digest()
        return bytes(a ^ b for a, b in zip(encrypted_data, key[:len(encrypted_data)]))
