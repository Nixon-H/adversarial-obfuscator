import hashlib
import multiprocessing as mp
import random
import struct
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _ctx():
    """The multiprocessing context this module spawns workers with.

    "spawn", not the platform default: forking a multi-threaded
    process is deprecated (Python 3.12+ warns) and may deadlock in the
    child, and Python 3.14 changes the default on Linux.
    """
    from .process_ctx import process_context
    return process_context()



@dataclass
class HostFunction:
    function_id: int
    name: str
    body: str
    host_id: int

    def serialize(self) -> bytes:
        buf = struct.pack(">I", self.function_id)
        buf += struct.pack(">I", len(self.name)) + self.name.encode()
        buf += struct.pack(">I", len(self.body)) + self.body.encode()
        buf += struct.pack(">I", self.host_id)
        return buf

    @classmethod
    def deserialize(cls, data: bytes) -> "HostFunction":
        offset = 0
        fid = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        nlen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        name = data[offset:offset+nlen].decode()
        offset += nlen
        blen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        body = data[offset:offset+blen].decode()
        offset += blen
        hid = struct.unpack(">I", data[offset:offset+4])[0]
        return cls(fid, name, body, hid)


@dataclass
class CallGraphEdge:
    caller_id: int
    callee_id: int
    is_cross_host: bool
    rpc_key: Optional[bytes] = None

    def serialize(self) -> bytes:
        buf = struct.pack(">II", self.caller_id, self.callee_id)
        buf += struct.pack(">B", 1 if self.is_cross_host else 0)
        if self.rpc_key is not None:
            buf += struct.pack(">I", len(self.rpc_key)) + self.rpc_key
        else:
            buf += struct.pack(">I", 0)
        return buf

    @classmethod
    def deserialize(cls, data: bytes) -> "CallGraphEdge":
        offset = 0
        cid, calid = struct.unpack(">II", data[offset:offset+8])
        offset += 8
        is_cross = struct.unpack(">B", data[offset:offset+1])[0] == 1
        offset += 1
        klen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        key = data[offset:offset+klen] if klen > 0 else None
        return cls(cid, calid, is_cross, key)


class MultiHostExecutor:
    def __init__(self, num_hosts: int = 3, deployment_seed: Optional[int] = None, mode: str = "simulation"):
        if num_hosts < 2:
            raise ValueError("num_hosts must be >= 2")
        self.num_hosts = num_hosts
        self.seed = deployment_seed or random.randint(0, 2**31)
        self.mode = mode
        self._rng = random.Random(self.seed)
        self._functions: Dict[int, HostFunction] = {}
        self._edges: List[CallGraphEdge] = []
        self._rpc_keys: Dict[Tuple[int, int], bytes] = {}

    def assign_functions(self, functions: List[Tuple[str, str]]) -> List[HostFunction]:
        host_fns = []
        for fid, (name, body) in enumerate(functions):
            host_id = fid % self.num_hosts
            hf = HostFunction(
                function_id=fid,
                name=name,
                body=body,
                host_id=host_id,
            )
            self._functions[fid] = hf
            host_fns.append(hf)
        return host_fns

    def build_call_graph(self, call_pairs: List[Tuple[int, int]]):
        self._edges = []
        for caller_id, callee_id in call_pairs:
            caller = self._functions.get(caller_id)
            callee = self._functions.get(callee_id)
            if caller is None or callee is None:
                continue
            is_cross = caller.host_id != callee.host_id
            rpc_key = None
            if is_cross:
                key_data = struct.pack(">II", caller.host_id, callee.host_id) + self.seed.to_bytes(8, "big")
                rpc_key = hashlib.sha256(key_data).digest()
                self._rpc_keys[(caller_id, callee_id)] = rpc_key
            self._edges.append(CallGraphEdge(
                caller_id=caller_id,
                callee_id=callee_id,
                is_cross_host=is_cross,
                rpc_key=rpc_key,
            ))

    def get_host_functions(self, host_id: int) -> List[HostFunction]:
        return [hf for hf in self._functions.values() if hf.host_id == host_id]

    def get_cross_host_calls(self) -> List[CallGraphEdge]:
        return [e for e in self._edges if e.is_cross_host]

    def execute_remote_call(self, caller_id: int, callee_id: int, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        edge = None
        for e in self._edges:
            if e.caller_id == caller_id and e.callee_id == callee_id:
                edge = e
                break
        if edge is None or not edge.is_cross_host:
            return None

        rpc_key = self._rpc_keys.get((caller_id, callee_id))
        if rpc_key is None:
            return None

        callee = self._functions.get(callee_id)
        if callee is None:
            return None

        serialized = struct.pack(">I", callee.function_id) + callee.body.encode()
        if rpc_key:
            stream = hashlib.sha256(rpc_key + serialized).digest()
            serialized = bytes(a ^ b for a, b in zip(serialized, stream * (len(serialized) // len(stream) + 1)))

        result = {"callee": callee.name, "args": args, "executed_on": callee.host_id}
        return result

    def simulate_execution(self) -> Dict[str, Any]:
        if self.mode == "multiprocess":
            return self._run_multiprocess()
        trace = {
            "hosts": {},
            "cross_calls": [],
            "total_functions": len(self._functions),
        }
        for hid in range(self.num_hosts):
            host_fns = self.get_host_functions(hid)
            trace["hosts"][hid] = [hf.name for hf in host_fns]

        for edge in self._edges:
            if edge.is_cross_host:
                caller = self._functions[edge.caller_id]
                callee = self._functions[edge.callee_id]
                trace["cross_calls"].append({
                    "from": f"{caller.name}@host{caller.host_id}",
                    "to": f"{callee.name}@host{callee.host_id}",
                })

        return trace

    def _run_multiprocess(self) -> Dict[str, Any]:
        return self.run_multiprocess()

    def run_multiprocess(self) -> Dict[str, Any]:
        queues = {hid: _ctx().Queue() for hid in range(self.num_hosts)}
        result_queues = {hid: _ctx().Queue() for hid in range(self.num_hosts)}
        rpc_queues = {}
        for hid in range(self.num_hosts):
            for other in range(self.num_hosts):
                if hid != other:
                    rpc_queues[(hid, other)] = _ctx().Queue()
        processes = []

        for hid in range(self.num_hosts):
            host_fns = self.get_host_functions(hid)
            host_edges = [e for e in self._edges
                          if self._functions[e.caller_id].host_id == hid]
            p = _ctx().Process(
                target=_host_process_rpc,
                args=(hid, host_fns, host_edges, queues, result_queues, rpc_queues),
            )
            p.start()
            processes.append(p)

        for hid in range(self.num_hosts):
            queues[hid].put(("execute", {}))
        for hid in range(self.num_hosts):
            try:
                result_queues[hid].get(timeout=5)
            except Exception:
                pass
        for p in processes:
            if p.is_alive():
                p.terminate()
            p.join(timeout=1)

        trace = {
            "hosts": {},
            "cross_calls": [],
            "total_functions": len(self._functions),
            "mode": "multiprocess",
        }
        for hid in range(self.num_hosts):
            host_fns = self.get_host_functions(hid)
            trace["hosts"][hid] = [hf.name for hf in host_fns]
        for edge in self._edges:
            if edge.is_cross_host:
                caller = self._functions[edge.caller_id]
                callee = self._functions[edge.callee_id]
                trace["cross_calls"].append({
                    "from": f"{caller.name}@host{caller.host_id}",
                    "to": f"{callee.name}@host{callee.host_id}",
                })
        return trace

    def serialize_deployment(self) -> bytes:
        buf = struct.pack(">II", self.num_hosts, self.seed)
        buf += struct.pack(">I", len(self._functions))
        for hf in self._functions.values():
            buf += hf.serialize()
        buf += struct.pack(">I", len(self._edges))
        for edge in self._edges:
            buf += edge.serialize()
        return buf

    @classmethod
    def deserialize_deployment(cls, data: bytes) -> "MultiHostExecutor":
        offset = 0
        nh, seed = struct.unpack(">II", data[offset:offset+8])
        offset += 8
        executor = cls(num_hosts=nh, deployment_seed=seed)
        nfns = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        fns = []
        for _ in range(nfns):
            hf = HostFunction.deserialize(data[offset:])
            offset += 12 + len(hf.name) + len(hf.body) + 4
            executor._functions[hf.function_id] = hf
            fns.append((hf.name, hf.body))
        executor.assign_functions(fns)
        nedges = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        pairs = []
        for _ in range(nedges):
            edge = CallGraphEdge.deserialize(data[offset:])
            offset += 17 + (len(edge.rpc_key) if edge.rpc_key else 0)
            pairs.append((edge.caller_id, edge.callee_id))
        executor.build_call_graph(pairs)
        return executor


def _host_process(host_id: int, host_functions: List[HostFunction],
                  host_edges: List[CallGraphEdge],
                  in_queues: Dict[int, mp.Queue],
                  out_queues: Dict[int, mp.Queue]):
    context = {"executed": []}
    for hf in host_functions:
        context["executed"].append(hf.name)
    try:
        cmd, args = in_queues[host_id].get(timeout=5)
        if cmd == "execute":
            for edge in host_edges:
                callee_fn = None
                for hf in host_functions:
                    if hf.function_id == edge.callee_id:
                        callee_fn = hf
                        break
                if callee_fn and edge.is_cross_host:
                    out_queues[host_id].put({
                        "type": "cross_call",
                        "callee": callee_fn.name,
                        "executed_on": callee_fn.host_id,
                    })
            out_queues[host_id].put({"type": "done", "host_id": host_id, "executed": context["executed"]})
    except Exception:
        out_queues[host_id].put({"type": "done", "host_id": host_id, "executed": context["executed"]})


def _host_process_rpc(host_id: int, host_functions: List[HostFunction],
                      host_edges: List[CallGraphEdge],
                      in_queues: Dict[int, mp.Queue],
                      out_queues: Dict[int, mp.Queue],
                      rpc_queues: Dict[Tuple[int, int], mp.Queue]):
    import struct
    context = {"executed": []}
    fn_map = {hf.function_id: hf for hf in host_functions}
    cross_call_results = []
    try:
        cmd, args = in_queues[host_id].get(timeout=5)
        if cmd == "execute":
            for edge in host_edges:
                fn_map.get(edge.caller_id)
                callee_fn = fn_map.get(edge.callee_id)
                if callee_fn and edge.is_cross_host:
                    callee_hid = callee_fn.host_id
                    serialized = struct.pack(">I", callee_fn.function_id) + callee_fn.body.encode()
                    rpc_queues[(host_id, callee_hid)].put({
                        "type": "rpc_call",
                        "caller_id": edge.caller_id,
                        "callee_id": edge.callee_id,
                        "serialized": serialized,
                        "args": args,
                    })
                    rpc_response = rpc_queues[(callee_hid, host_id)].get(timeout=5)
                    cross_call_results.append(rpc_response)
                    context["executed"].append(f"rpc->{callee_fn.name}@{callee_hid}")
                elif callee_fn:
                    context["executed"].append(callee_fn.name)
            for hf in host_functions:
                if hf.function_id not in [e.callee_id for e in host_edges]:
                    context["executed"].append(hf.name)
            out_queues[host_id].put({
                "type": "done",
                "host_id": host_id,
                "executed": context["executed"],
                "cross_call_results": cross_call_results,
                "mode": "rpc",
            })
    except Exception:
        out_queues[host_id].put({"type": "done", "host_id": host_id, "executed": context["executed"]})
