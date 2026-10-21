import multiprocessing as mp
import struct
import threading
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Optional


def _ctx():
    """The multiprocessing context this module spawns workers with.

    "spawn", not the platform default: forking a multi-threaded
    process is deprecated (Python 3.12+ warns) and may deadlock in the
    child, and Python 3.14 changes the default on Linux.
    """
    from .process_ctx import process_context
    return process_context()



class VMStatePartition(IntEnum):
    REGISTERS = 0
    MEMORY = 1
    STACK = 2


@dataclass
class VMPartitionedState:
    registers: Dict[str, int]
    memory: bytearray
    stack: List[int]
    program_counter: int
    sync_counter: int

    def serialize(self) -> bytes:
        buf = struct.pack(">I", self.program_counter)
        buf += struct.pack(">I", self.sync_counter)
        buf += struct.pack(">I", len(self.registers))
        for name, val in sorted(self.registers.items()):
            buf += struct.pack(">I", len(name)) + name.encode() + struct.pack(">q", val)
        buf += struct.pack(">I", len(self.memory))
        buf += bytes(self.memory)
        buf += struct.pack(">I", len(self.stack))
        for val in self.stack:
            buf += struct.pack(">q", val)
        return buf

    @classmethod
    def deserialize(cls, data: bytes) -> "VMPartitionedState":
        offset = 0
        pc, sc = struct.unpack(">II", data[offset:offset+8])
        offset += 8
        nregs = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        regs = {}
        for _ in range(nregs):
            nlen = struct.unpack(">I", data[offset:offset+4])[0]
            offset += 4
            name = data[offset:offset+nlen].decode()
            offset += nlen
            val = struct.unpack(">q", data[offset:offset+8])[0]
            offset += 8
            regs[name] = val
        mlen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        mem = bytearray(data[offset:offset+mlen])
        offset += mlen
        slen = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        stack = []
        for _ in range(slen):
            val = struct.unpack(">q", data[offset:offset+8])[0]
            offset += 8
            stack.append(val)
        return cls(regs, mem, stack, pc, sc)


class DistributedVMExecutor:
    def __init__(self, mode: str = "simulation"):
        self.mode = mode
        self._hosts: Dict[int, VMStatePartition] = {
            0: VMStatePartition.REGISTERS,
            1: VMStatePartition.MEMORY,
            2: VMStatePartition.STACK,
        }
        self.state = VMPartitionedState(
            registers={"r0": 0, "r1": 0, "r2": 0, "r3": 0, "acc": 0},
            memory=bytearray(1024),
            stack=[],
            program_counter=0,
            sync_counter=0,
        )
        self._instructions: List[Dict] = []
        self._host_failures: Dict[int, bool] = {0: False, 1: False, 2: False}
        self._lock = threading.Lock()
        self._sync_events: Dict[int, threading.Event] = {
            0: threading.Event(),
            1: threading.Event(),
            2: threading.Event(),
        }

    def load_program(self, instructions: List[Dict]):
        self._instructions = instructions

    def _execute_on_host(self, host_id: int, instruction: Dict) -> Optional[bytes]:
        if self._host_failures.get(host_id, False):
            return None

        result = None

        with self._lock:
            op = instruction.get("op", "nop")
            if op in ("loadi", "add", "sub", "mul", "mov"):
                result = self._exec_registers(instruction)
            if op in ("load", "store"):
                result = self._exec_memory(instruction)
            if op in ("push", "pop", "call", "ret"):
                result = self._exec_stack(instruction)

        return result

    def _exec_registers(self, inst: Dict) -> Optional[bytes]:
        op = inst.get("op", "nop")
        if op == "loadi":
            reg = inst.get("rd", "r0")
            val = inst.get("val", 0)
            self.state.registers[reg] = val
        elif op == "add":
            rd = inst.get("rd", "r0")
            rs1 = inst.get("rs1", "r0")
            rs2 = inst.get("rs2", "r0")
            self.state.registers[rd] = self.state.registers.get(rs1, 0) + self.state.registers.get(rs2, 0)
        elif op == "sub":
            rd = inst.get("rd", "r0")
            rs1 = inst.get("rs1", "r0")
            rs2 = inst.get("rs2", "r0")
            self.state.registers[rd] = self.state.registers.get(rs1, 0) - self.state.registers.get(rs2, 0)
        elif op == "mul":
            rd = inst.get("rd", "r0")
            rs1 = inst.get("rs1", "r0")
            rs2 = inst.get("rs2", "r0")
            self.state.registers[rd] = self.state.registers.get(rs1, 0) * self.state.registers.get(rs2, 0)
        elif op == "mov":
            rd = inst.get("rd", "r0")
            rs = inst.get("rs", "r0")
            self.state.registers[rd] = self.state.registers.get(rs, 0)
        return None

    def _exec_memory(self, inst: Dict) -> Optional[bytes]:
        op = inst.get("op", "nop")
        if op == "load":
            addr = inst.get("addr", 0)
            reg = inst.get("rd", "r0")
            if 0 <= addr < len(self.state.memory):
                val = int.from_bytes(self.state.memory[addr:addr+4], "little", signed=True)
                self.state.registers[reg] = val
        elif op == "store":
            addr = inst.get("addr", 0)
            reg = inst.get("rs", "r0")
            if 0 <= addr + 4 <= len(self.state.memory):
                val = self.state.registers.get(reg, 0)
                self.state.memory[addr:addr+4] = val.to_bytes(4, "little", signed=True)
        return None

    def _exec_stack(self, inst: Dict) -> Optional[bytes]:
        op = inst.get("op", "nop")
        if op == "push":
            reg = inst.get("rs", "r0")
            self.state.stack.append(self.state.registers.get(reg, 0))
        elif op == "pop":
            reg = inst.get("rd", "r0")
            if self.state.stack:
                self.state.registers[reg] = self.state.stack.pop()
        elif op == "call":
            addr = inst.get("addr", 0)
            self.state.stack.append(self.state.program_counter + 1)
            self.state.program_counter = addr
        elif op == "ret":
            if self.state.stack:
                self.state.program_counter = self.state.stack.pop()
        return None

    def _synchronize(self):
        self.state.sync_counter += 1
        for e in self._sync_events.values():
            e.set()

    def step(self) -> bool:
        if self.state.program_counter >= len(self._instructions):
            return False

        inst = self._instructions[self.state.program_counter]
        host_id = self.state.program_counter % 3

        if self._host_failures.get(host_id, False):
            self.state.program_counter += 1
            return self.state.program_counter < len(self._instructions)

        self._execute_on_host(host_id, inst)

        self.state.program_counter += 1
        if self.state.program_counter % 2 == 0:
            self._synchronize()

        return self.state.program_counter < len(self._instructions)

    def run(self) -> VMPartitionedState:
        if self.mode == "multiprocess":
            return self.run_multiprocess()
        while self.step():
            pass
        return self.state

    def run_multiprocess(self) -> VMPartitionedState:
        instructions = list(self._instructions)
        state = self.state
        num_hosts = 3
        sync_events = {hid: mp.Event() for hid in range(num_hosts)}

        in_queues = {hid: _ctx().Queue() for hid in range(num_hosts)}
        out_queues = {hid: _ctx().Queue() for hid in range(num_hosts)}
        processes = []

        for hid in range(num_hosts):
            p = _ctx().Process(
                target=_vm_worker,
                args=(hid, in_queues[hid], out_queues[hid]),
            )
            p.start()
            processes.append(p)

        for step_idx, inst in enumerate(instructions):
            hid = step_idx % num_hosts
            in_queues[hid].put(("execute", inst, state.serialize()))
            try:
                msg = out_queues[hid].get(timeout=5)
                if msg and msg[0] == "result":
                    state = VMPartitionedState.deserialize(msg[1])
            except Exception:
                pass
            if step_idx % 2 == 0:
                for e in sync_events.values():
                    e.set()
                    e.clear()

        for hid in range(num_hosts):
            in_queues[hid].put(None)

        for p in processes:
            p.join(timeout=1)

        self.state = state
        return self.state

    def run_multiprocess_partitioned(self) -> VMPartitionedState:
        instructions = list(self._instructions)
        state = self.state
        num_hosts = 3

        partitions = {hid: [] for hid in range(num_hosts)}
        for step_idx, inst in enumerate(instructions):
            hid = step_idx % num_hosts
            partitions[hid].append(inst)

        in_queues = {hid: _ctx().Queue() for hid in range(num_hosts)}
        out_queues = {hid: _ctx().Queue() for hid in range(num_hosts)}
        sync_events = {hid: mp.Event() for hid in range(num_hosts)}
        barrier_event = mp.Event()
        processes = []

        for hid in range(num_hosts):
            p = _ctx().Process(
                target=_vm_partition_worker,
                args=(hid, partitions[hid], in_queues[hid], out_queues[hid], sync_events, barrier_event),
            )
            p.start()
            processes.append(p)

        for hid in range(num_hosts):
            in_queues[hid].put(("init", state.serialize()))

        for _ in range(max(len(p) for p in partitions.values()) if any(partitions.values()) else 1):
            for hid in range(num_hosts):
                if hid < len(instructions):
                    sync_events[hid].set()
            barrier_event.set()
            barrier_event.clear()
            for hid in range(num_hosts):
                try:
                    msg = out_queues[hid].get(timeout=5)
                    if msg and msg[0] == "result":
                        state = VMPartitionedState.deserialize(msg[1])
                except Exception:
                    pass

        for hid in range(num_hosts):
            in_queues[hid].put(None)

        for p in processes:
            p.join(timeout=1)

        self.state = state
        return self.state

    def simulate_host_failure(self, host_id: int):
        self._host_failures[host_id] = True

    def recover_host(self, host_id: int):
        self._host_failures[host_id] = False

    def get_host_state_snapshot(self, host_id: int) -> bytes:
        return self.state.serialize()

    def load_host_state_snapshot(self, host_id: int, data: bytes):
        restored = VMPartitionedState.deserialize(data)
        with self._lock:
            self.state = restored


def _vm_worker(host_id: int, in_queue, out_queue):
    while True:
        try:
            msg = in_queue.get(timeout=5)
        except Exception:
            break
        if msg is None:
            break
        cmd = msg[0]
        if cmd == "execute":
            inst = msg[1]
            state = VMPartitionedState.deserialize(msg[2])
            op = inst.get("op", "nop")
            if op in ("loadi", "add", "sub", "mul", "mov"):
                _vm_exec_registers(state, inst)
            elif op in ("load", "store"):
                _vm_exec_memory(state, inst)
            elif op in ("push", "pop", "call", "ret"):
                _vm_exec_stack(state, inst)
            state.sync_counter += 1
            out_queue.put(("result", state.serialize()))


def _vm_exec_registers(state: VMPartitionedState, inst: Dict):
    op = inst.get("op", "nop")
    if op == "loadi":
        reg = inst.get("rd", "r0")
        val = inst.get("val", 0)
        state.registers[reg] = val
    elif op == "add":
        rd = inst.get("rd", "r0")
        rs1 = inst.get("rs1", "r0")
        rs2 = inst.get("rs2", "r0")
        state.registers[rd] = state.registers.get(rs1, 0) + state.registers.get(rs2, 0)
    elif op == "sub":
        rd = inst.get("rd", "r0")
        rs1 = inst.get("rs1", "r0")
        rs2 = inst.get("rs2", "r0")
        state.registers[rd] = state.registers.get(rs1, 0) - state.registers.get(rs2, 0)
    elif op == "mul":
        rd = inst.get("rd", "r0")
        rs1 = inst.get("rs1", "r0")
        rs2 = inst.get("rs2", "r0")
        state.registers[rd] = state.registers.get(rs1, 0) * state.registers.get(rs2, 0)
    elif op == "mov":
        rd = inst.get("rd", "r0")
        rs = inst.get("rs", "r0")
        state.registers[rd] = state.registers.get(rs, 0)


def _vm_exec_memory(state: VMPartitionedState, inst: Dict):
    op = inst.get("op", "nop")
    if op == "load":
        addr = inst.get("addr", 0)
        reg = inst.get("rd", "r0")
        if 0 <= addr < len(state.memory):
            val = int.from_bytes(state.memory[addr:addr+4], "little", signed=True)
            state.registers[reg] = val
    elif op == "store":
        addr = inst.get("addr", 0)
        reg = inst.get("rs", "r0")
        if 0 <= addr + 4 <= len(state.memory):
            val = state.registers.get(reg, 0)
            state.memory[addr:addr+4] = val.to_bytes(4, "little", signed=True)


def _vm_exec_stack(state: VMPartitionedState, inst: Dict):
    op = inst.get("op", "nop")
    if op == "push":
        reg = inst.get("rs", "r0")
        state.stack.append(state.registers.get(reg, 0))
    elif op == "pop":
        reg = inst.get("rd", "r0")
        if state.stack:
            state.registers[reg] = state.stack.pop()
    elif op == "call":
        addr = inst.get("addr", 0)
        state.stack.append(state.program_counter + 1)
        state.program_counter = addr
    elif op == "ret":
        if state.stack:
            state.program_counter = state.stack.pop()


def _vm_partition_worker(host_id: int, partition: List[Dict], in_queue, out_queue,
                         sync_events, barrier_event):
    state = None
    while True:
        try:
            msg = in_queue.get(timeout=5)
        except Exception:
            break
        if msg is None:
            break
        cmd = msg[0]
        if cmd == "init":
            state = VMPartitionedState.deserialize(msg[1])
            continue
        if state is None:
            break
        barrier_event.wait(timeout=5)
        barrier_event.clear()
        for inst in partition:
            op = inst.get("op", "nop")
            if op in ("loadi", "add", "sub", "mul", "mov"):
                _vm_exec_registers(state, inst)
            elif op in ("load", "store"):
                _vm_exec_memory(state, inst)
            elif op in ("push", "pop", "call", "ret"):
                _vm_exec_stack(state, inst)
            state.sync_counter += 1
        out_queue.put(("result", state.serialize()))
