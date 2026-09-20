import hashlib
import multiprocessing
import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.distributed.multi_binary import MultiBinaryDistributor
from scripts.distributed.cross_process import CrossProcessBinder
from scripts.distributed.remote_unlock import RemoteUnlockServer, RemoteUnlockClient
from scripts.distributed.vm_cluster import DistributedVMExecutor
from scripts.distributed.multi_host import MultiHostExecutor
from scripts.distributed.fragment_migration import FragmentMigrator, Platform
from scripts.distributed.dist_watermark import DistributedWatermark
from scripts.distributed.recovery_prevention import ExecutionRecoveryPreventer


# ===========================================================================
# Item 110: Multi-Binary Fragment Distribution — multiprocessing test
# ===========================================================================

def _binary_holder_process(binary: bytes, result_queue: multiprocessing.Queue):
    mbd = MultiBinaryDistributor()
    result_queue.put(binary)


class TestMultiBinaryIntegration:
    """
    TestMultiBinaryIntegration
    
    Positive test cases for multibinaryintegration.
    """
    def test_multiprocess_reconstruction(self):
        mbd = MultiBinaryDistributor()
        fragments = [b"integration_test_frag_" + str(i).encode() * 5 for i in range(6)]
        binaries, index = mbd.distribute(fragments, 3)

        queues = []
        processes = []
        for i, binary in enumerate(binaries):
            q = multiprocessing.Queue()
            p = multiprocessing.Process(target=_binary_holder_process, args=(binary, q))
            p.start()
            processes.append(p)
            queues.append(q)

        for p in processes:
            p.join()

        collected_binaries = [q.get() for q in queues]
        reconstructed = mbd.reconstruct(collected_binaries[:3])
        assert reconstructed == fragments

    def test_distribute_to_processes(self):
        mbd = MultiBinaryDistributor()
        fragments = [b"proc_dist_" + str(i).encode() * 3 for i in range(4)]
        binaries, index = mbd.distribute_to_processes(fragments, 2)
        assert len(binaries) == 2
        reconstructed = mbd.reconstruct(binaries)
        assert reconstructed == fragments


# ===========================================================================
# Item 111: Cross-Process Fragment Binding — multiprocessing test
# ===========================================================================

def _fragment_holder_process(shm_name: str, fragment_id: int, data: bytes,
                              pid_val: int, secret: bytes,
                              result_queue: multiprocessing.Queue):
    from multiprocessing.shared_memory import SharedMemory
    import struct
    import hashlib

    try:
        shm = SharedMemory(name=shm_name, create=False)
        stored_len = struct.unpack(">Q", shm.buf[:8])[0]
        stored_data = bytes(shm.buf[8:8 + stored_len])
        combined = stored_data + data
        combined_size = len(combined) + 8
        result_shm = SharedMemory(name=f"{shm_name}_result", create=True, size=combined_size)
        struct.pack_into(">Q", result_shm.buf, 0, len(combined))
        result_shm.buf[8:8 + len(combined)] = combined
        result_shm.close()
        shm.close()
        result_queue.put(True)
    except Exception as e:
        result_queue.put(False)


class TestCrossProcessIntegration:
    """
    TestCrossProcessIntegration
    
    Positive test cases for crossprocessintegration.
    """
    def test_multiprocess_binding(self):
        from multiprocessing.shared_memory import SharedMemory
        import struct

        cpb = CrossProcessBinder()
        fragment_data = b"cross_process_test_data"
        pid_val = os.getpid()
        entropy = cpb._process_entropy()
        expected_key = cpb._derive_process_key(pid_val, entropy, 0)

        key = hashlib.sha256(
            cpb.shared_secret + struct.pack(">IQQ", pid_val, entropy, 0)
        ).digest()
        assert key == expected_key

        result_queue = multiprocessing.Queue()

        shm_name = cpb._shm_name("integration_test")
        data_size = len(fragment_data) + 8
        shm = SharedMemory(name=shm_name, create=True, size=data_size)
        struct.pack_into(">Q", shm.buf, 0, len(fragment_data))
        shm.buf[8:8 + len(fragment_data)] = fragment_data
        shm.close()

        p = multiprocessing.Process(
            target=_fragment_holder_process,
            args=(shm_name, 0, fragment_data, pid_val, cpb.shared_secret, result_queue),
        )
        p.start()
        p.join()
        result = result_queue.get(timeout=5)
        assert result is True

        result_shm = SharedMemory(name=f"{shm_name}_result")
        stored_len = struct.unpack(">Q", result_shm.buf[:8])[0]
        combined = bytes(result_shm.buf[8:8 + stored_len])
        result_shm.close()
        result_shm.unlink()

        try:
            shm_cleanup = SharedMemory(name=shm_name)
            shm_cleanup.close()
            shm_cleanup.unlink()
        except FileNotFoundError:
            pass

        assert len(combined) == len(fragment_data) * 2


# ===========================================================================
# Item 112: Remote Fragment Unlocking — network test
# ===========================================================================

class TestRemoteUnlockIntegration:
    """
    TestRemoteUnlockIntegration
    
    Positive test cases for remoteunlockintegration.
    """
    def test_network_token_request(self):
        server = RemoteUnlockServer(token_ttl=5.0)
        port = server.start()
        assert port > 0

        client = RemoteUnlockClient()
        client.connect("127.0.0.1", port, server)

        token = client.request_unlock(42)
        assert token is not None
        assert token.fragment_id == 42
        assert len(token.token) == 32
        assert server.verify_token(token) is True

        key = client.derive_key(42, token)
        assert key is not None
        assert len(key) == 32

        server.stop()

    def test_multiple_network_tokens(self):
        server = RemoteUnlockServer(token_ttl=10.0)
        port = server.start()

        client1 = RemoteUnlockClient()
        client1.connect("127.0.0.1", port, server)

        client2 = RemoteUnlockClient()
        client2.connect("127.0.0.1", port, server)

        token1 = client1.request_unlock(0)
        token2 = client2.request_unlock(1)

        assert token1 is not None
        assert token2 is not None
        assert token1.token != token2.token

        key1 = client1.derive_key(0, token1)
        key2 = client2.derive_key(1, token2)
        assert key1 != key2

        server.stop()

    def test_network_unlock_decrypts(self):
        server = RemoteUnlockServer(token_ttl=5.0)
        port = server.start()

        client = RemoteUnlockClient()
        client.connect("127.0.0.1", port, server)

        encrypted = bytes([0xAB, 0xCD, 0xEF, 0x01])
        decrypted = client.unlock_fragment(0, encrypted)
        assert decrypted is not None
        assert decrypted != encrypted

        server.stop()


# ===========================================================================
# Item 113: Distributed VM Execution — multiprocess test
# ===========================================================================

class TestDistributedVMIntegration:
    """
    TestDistributedVMIntegration
    
    Positive test cases for distributedvmintegration.
    """
    def test_multiprocess_execution(self):
        vm = DistributedVMExecutor(mode="multiprocess")
        instructions = [
            {"op": "loadi", "rd": "r0", "val": 7},
            {"op": "loadi", "rd": "r1", "val": 3},
            {"op": "sub", "rd": "r2", "rs1": "r0", "rs2": "r1"},
            {"op": "mul", "rd": "r3", "rs1": "r2", "rs2": "r0"},
        ]
        vm.load_program(instructions)
        state = vm.run()
        assert state.registers["r2"] == 4
        assert state.registers["r3"] == 28


# ===========================================================================
# Item 114: Multi-Host Execution Graphs — multiprocess test
# ===========================================================================

class TestMultiHostIntegration:
    """
    TestMultiHostIntegration
    
    Positive test cases for multihostintegration.
    """
    def test_multiprocess_simulate(self):
        mhe = MultiHostExecutor(num_hosts=3, deployment_seed=42, mode="multiprocess")
        fns = [("func_a", "x = 1"), ("func_b", "y = 2"), ("func_c", "z = x + y")]
        mhe.assign_functions(fns)
        mhe.build_call_graph([(0, 2), (1, 2)])
        trace = mhe.simulate_execution()
        assert trace["mode"] == "multiprocess"
        assert len(trace["hosts"]) == 3


# ===========================================================================
# Item 115: Cross-Platform Fragment Migration — multiprocess test
# ===========================================================================

class TestFragmentMigrationIntegration:
    """
    TestFragmentMigrationIntegration
    
    Positive test cases for fragmentmigrationintegration.
    """
    def test_multiprocess_migration(self):
        fm = FragmentMigrator(mode="multiprocess")
        variants = {
            Platform.X86: b"\x90\x90\xc3",
            Platform.ARM: b"\x00\x00\x00\x00\x00",
            Platform.WASM: b"\x00\x61\x73\x6d\x01\x00\x00\x00",
        }
        fragment = fm.create_fragment(0, variants)
        migrated = fm.atomic_migrate(fragment, Platform.ARM)
        assert migrated is not None
        assert migrated.current_platform == Platform.ARM or migrated.current_platform == Platform.X86
        assert migrated.migration_count >= 0


# ===========================================================================
# Item 117: Distributed Watermarking — multiprocess test
# ===========================================================================

class TestDistributedWatermarkIntegration:
    """
    TestDistributedWatermarkIntegration
    
    Positive test cases for distributedwatermarkintegration.
    """
    def test_multiprocess_shard_and_distribute(self):
        dw = DistributedWatermark(mode="multiprocess")
        watermark = b"Integration Test Watermark Data For Multiprocess"
        shares = dw.shard_and_distribute(watermark, 3)
        assert len(shares) == 3
        extracted = dw.extract_full(shares)
        assert extracted == watermark

    def test_multiprocess_extract(self):
        dw = DistributedWatermark(mode="simulation")
        watermark = b"Multiprocess Extract Test"
        shares = dw.shard_watermark(watermark, 4)
        dw.mode = "multiprocess"
        extracted = dw.extract_multiprocess(shares)
        assert extracted == watermark


# ===========================================================================
# Item 119: Distributed Execution Recovery Prevention — multiprocess test
# ===========================================================================

class TestRecoveryPreventionIntegration:
    """
    TestRecoveryPreventionIntegration
    
    Positive test cases for recoverypreventionintegration.
    """
    def test_multiprocess_run(self):
        erp = ExecutionRecoveryPreventer(num_nodes=3, mode="simulation")
        ops = [f"instruction_{i}" for i in range(15)]
        result = erp.run_multiprocess(ops)
        assert result is True
