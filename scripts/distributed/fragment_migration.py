import hashlib
import os
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Optional, Tuple


def _ctx():
    """The multiprocessing context this module spawns workers with.

    "spawn", not the platform default: forking a multi-threaded
    process is deprecated (Python 3.12+ warns) and may deadlock in the
    child, and Python 3.14 changes the default on Linux.
    """
    from .process_ctx import process_context
    return process_context()


class Platform(IntEnum):
    X86 = 0
    ARM = 1
    WASM = 2


@dataclass
class PlatformVariant:
    platform: Platform
    code: bytes
    entry_point: int
    checksum: bytes


@dataclass
class MigratingFragment:
    fragment_id: int
    variants: List[PlatformVariant]
    current_platform: Platform
    state: Optional[bytes] = None
    migration_count: int = 0

    def serialize_state(self) -> bytes:
        buf = struct.pack(">II", self.fragment_id, self.migration_count)
        buf += struct.pack(">I", int(self.current_platform))
        if self.state is not None:
            buf += struct.pack(">I", len(self.state)) + self.state
        else:
            buf += struct.pack(">I", 0)
        return buf

    @classmethod
    def deserialize_state(cls, data: bytes, fragment_id: int) -> "MigratingFragment":
        offset = 0
        fid, mcount = struct.unpack(">II", data[offset:offset+8])
        offset += 8
        plat = Platform(struct.unpack(">I", data[offset:offset+4])[0])
        offset += 4
        slen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        state = data[offset:offset+slen] if slen > 0 else None
        return cls(fid, [], plat, state, mcount)


class FragmentMigrator:
    def __init__(self, migration_secret: Optional[bytes] = None, mode: str = "simulation"):
        self.migration_secret = migration_secret or os.urandom(32)
        self.mode = mode

    def _derive_platform_key(self, fragment_id: int, from_platform: Platform, to_platform: Platform) -> bytes:
        data = (self.migration_secret + struct.pack(">III", fragment_id, int(from_platform), int(to_platform)))
        return hashlib.sha256(data).digest()

    def create_fragment(self, fragment_id: int, variants: Dict[Platform, bytes]) -> MigratingFragment:
        platform_variants = []
        for platform, code in variants.items():
            checksum = hashlib.sha256(code).digest()
            pv = PlatformVariant(
                platform=platform,
                code=code,
                entry_point=0,
                checksum=checksum,
            )
            platform_variants.append(pv)
        return MigratingFragment(
            fragment_id=fragment_id,
            variants=platform_variants,
            current_platform=list(variants.keys())[0],
        )

    def serialize_state_for_migration(self, fragment: MigratingFragment, target_platform: Platform) -> Tuple[bytes, bytes]:
        state_data = fragment.serialize_state()
        from_plat = fragment.current_platform
        to_plat = target_platform
        key = self._derive_platform_key(fragment.fragment_id, from_plat, to_plat)
        stream = hashlib.sha256(key).digest()
        stream = hashlib.sha256(stream + struct.pack(">I", fragment.fragment_id)).digest()
        encrypted_state = bytes(a ^ b for a, b in zip(state_data, stream * (len(state_data) // len(stream) + 1)))
        mac = hashlib.sha256(key + encrypted_state + struct.pack(">II", int(from_plat), int(to_plat))).digest()
        return encrypted_state, mac

    def migrate(self, fragment: MigratingFragment, target_platform: Platform, encrypted_state: bytes, mac: bytes) -> Optional[MigratingFragment]:
        key = self._derive_platform_key(fragment.fragment_id, fragment.current_platform, target_platform)
        expected_mac = hashlib.sha256(key + encrypted_state + struct.pack(">II", int(fragment.current_platform), int(target_platform))).digest()
        if mac != expected_mac:
            return None

        stream = hashlib.sha256(key).digest()
        stream = hashlib.sha256(stream + struct.pack(">I", fragment.fragment_id)).digest()
        decrypted = bytes(a ^ b for a, b in zip(encrypted_state, stream * (len(encrypted_state) // len(stream) + 1)))[:len(encrypted_state)]

        try:
            restored = MigratingFragment.deserialize_state(decrypted, fragment.fragment_id)
        except Exception:
            return None

        restored.variants = fragment.variants
        restored.current_platform = target_platform
        restored.migration_count += 1

        target_variant = None
        for v in restored.variants:
            if v.platform == target_platform:
                target_variant = v
                break

        if target_variant is None:
            return None

        expected_checksum = hashlib.sha256(target_variant.code).digest()
        if expected_checksum != target_variant.checksum:
            return None

        return restored

    def atomic_migrate(self, fragment: MigratingFragment, target_platform: Platform) -> Optional[MigratingFragment]:
        if self.mode == "multiprocess":
            return self._migrate_multiprocess(fragment, target_platform)
        encrypted_state, mac = self.serialize_state_for_migration(fragment, target_platform)
        result = self.migrate(fragment, target_platform, encrypted_state, mac)

        if result is None:
            rollback = MigratingFragment(
                fragment_id=fragment.fragment_id,
                variants=fragment.variants,
                current_platform=fragment.current_platform,
                state=fragment.state,
                migration_count=fragment.migration_count,
            )
            return rollback

        return result

    def _migrate_multiprocess(self, fragment: MigratingFragment, target_platform: Platform) -> Optional[MigratingFragment]:
        encrypted_state, mac = self.serialize_state_for_migration(fragment, target_platform)
        src_out = _ctx().Queue()
        dst_in = _ctx().Queue()
        dst_out = _ctx().Queue()

        from_plat = int(fragment.current_platform)
        to_plat = int(target_platform)
        secret = self.migration_secret

        src_process = _ctx().Process(
            target=_src_migrate, args=(fragment.fragment_id, from_plat, encrypted_state, mac, src_out),
        )
        dst_process = _ctx().Process(
            target=_dst_migrate, args=(fragment.fragment_id, to_plat, secret, dst_in, dst_out),
        )
        src_process.start()
        dst_process.start()

        payload = src_out.get(timeout=10)
        dst_in.put(payload)
        success = dst_out.get(timeout=10)

        src_process.join(timeout=2)
        dst_process.join(timeout=2)
        if success:
            return MigratingFragment(
                fragment_id=fragment.fragment_id,
                variants=fragment.variants,
                current_platform=target_platform,
                state=fragment.state,
                migration_count=fragment.migration_count + 1,
            )

        return MigratingFragment(
            fragment_id=fragment.fragment_id,
            variants=fragment.variants,
            current_platform=fragment.current_platform,
            state=fragment.state,
            migration_count=fragment.migration_count,
        )

    def migrate_multiprocess(self, fragment: MigratingFragment, target_platform: Platform) -> Optional[MigratingFragment]:
        encrypted_state, mac = self.serialize_state_for_migration(fragment, target_platform)

        req_queue = _ctx().Queue()
        resp_queue = _ctx().Queue()

        from_plat = int(fragment.current_platform)
        to_plat = int(target_platform)
        secret = self.migration_secret
        fid = fragment.fragment_id

        src = _ctx().Process(target=_platform_src_migrate, args=(fid, from_plat, to_plat, encrypted_state, mac, secret, req_queue))
        dst = _ctx().Process(target=_platform_dst_migrate, args=(fid, to_plat, secret, req_queue, resp_queue))
        src.start()
        dst.start()

        result = resp_queue.get(timeout=10)

        src.join(timeout=2)
        dst.join(timeout=2)
        if result.get("success", False):
            restored = result.get("restored")
            if restored:
                restored.variants = fragment.variants
                restored.current_platform = target_platform
                restored.migration_count = fragment.migration_count + 1
                return restored

        return MigratingFragment(
            fragment_id=fragment.fragment_id,
            variants=fragment.variants,
            current_platform=fragment.current_platform,
            state=fragment.state,
            migration_count=fragment.migration_count,
        )

    def rollback(self, original: MigratingFragment) -> MigratingFragment:
        return MigratingFragment(
            fragment_id=original.fragment_id,
            variants=original.variants,
            current_platform=original.current_platform,
            state=original.state,
            migration_count=original.migration_count,
        )


def _src_migrate(fragment_id: int, from_platform: int, encrypted_state: bytes, mac: bytes, out_queue):
    out_queue.put((encrypted_state, mac))


def _platform_src_migrate(fragment_id: int, from_platform: int, to_platform: int,
                           encrypted_state: bytes, mac: bytes,
                           migration_secret: bytes, out_queue):
    """Source side of the multi-process migration.

    The state is already sealed by
    :meth:`FragmentMigrator.serialize_state_for_migration`; this worker
    only carries the sealed blob, its MAC and the source platform to the
    destination process.
    """
    out_queue.put((encrypted_state, mac, int(from_platform)))


def _platform_dst_migrate(fragment_id: int, to_platform: int,
                          migration_secret: bytes, in_queue, out_queue):
    """Destination side: verify the sealed state and report the result.

    The MAC is recomputed with the same derivation as
    :meth:`FragmentMigrator.serialize_state_for_migration`, so a tampered
    or mis-routed blob fails closed.  On success the restored fragment
    is returned; the caller attaches the variants it already holds.
    """
    import hashlib
    import struct
    try:
        msg = in_queue.get(timeout=10)
    except Exception:
        msg = None
    if msg is None:
        out_queue.put({"success": False, "restored": None})
        return
    try:
        encrypted_state, mac, from_platform = msg
        key = hashlib.sha256(
            migration_secret
            + struct.pack(">III", fragment_id, int(from_platform), int(to_platform))
        ).digest()
        expected_mac = hashlib.sha256(
            key + encrypted_state
            + struct.pack(">II", int(from_platform), int(to_platform))
        ).digest()
        if mac != expected_mac:
            out_queue.put({"success": False, "restored": None})
            return
        stream = hashlib.sha256(key).digest()
        stream = hashlib.sha256(stream + struct.pack(">I", fragment_id)).digest()
        decrypted = bytes(
            a ^ b for a, b in zip(
                encrypted_state,
                stream * (len(encrypted_state) // len(stream) + 1))
        )[:len(encrypted_state)]
        restored = MigratingFragment.deserialize_state(decrypted, fragment_id)
    except Exception:
        out_queue.put({"success": False, "restored": None})
        return
    out_queue.put({"success": True, "restored": restored})


def _dst_migrate(fragment_id: int, to_platform: int, migration_secret: bytes, in_queue, out_queue):
    import hashlib
    import struct
    msg = in_queue.get(timeout=10)
    if msg is None:
        out_queue.put(False)
        return
    encrypted_state, mac = msg
    key = hashlib.sha256(migration_secret + struct.pack(">III", fragment_id, 0, to_platform)).digest()
    expected_mac = hashlib.sha256(key + encrypted_state + struct.pack(">II", 0, to_platform)).digest()
    out_queue.put(mac == expected_mac)
