from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import ClassVar, Dict, List, Optional, Tuple


IR_INSTRUCTIONS: Dict[str, int] = {
    "nop": 0x00,
    "add": 0x01,
    "sub": 0x02,
    "mul": 0x03,
    "div": 0x04,
    "mod": 0x05,
    "xor": 0x06,
    "and": 0x07,
    "or": 0x08,
    "shl": 0x09,
    "shr": 0x0A,
    "not": 0x0B,
    "neg": 0x0C,
    "load": 0x0D,
    "store": 0x0E,
    "mov": 0x0F,
    "cmp": 0x10,
    "jmp": 0x11,
    "je": 0x12,
    "jne": 0x13,
    "call": 0x14,
    "ret": 0x15,
    "push": 0x16,
    "pop": 0x17,
}

OPCODE_TO_NAME: Dict[int, str] = {v: k for k, v in IR_INSTRUCTIONS.items()}


@dataclass
class IrInstruction:
    opcode: int
    rd: int = 0
    rs1: int = 0
    rs2: int = 0
    imm: int = 0

    REG_BITS: ClassVar[int] = 8
    IMM_BITS: ClassVar[int] = 16

    def encode(self) -> bytes:
        packed = (
            (self.opcode & 0xFF) << 24
            | (self.rd & 0xFF) << 16
            | (self.rs1 & 0xFF) << 8
            | (self.rs2 & 0xFF)
        )
        return struct.pack(">I", packed) + struct.pack(">h", self.imm & 0xFFFF)

    @classmethod
    def decode(cls, data: bytes, offset: int = 0) -> Tuple[IrInstruction, int]:
        if offset + 6 > len(data):
            raise ValueError("Not enough data to decode IrInstruction")
        packed = struct.unpack_from(">I", data, offset)[0]
        imm = struct.unpack_from(">h", data, offset + 4)[0]
        opcode = (packed >> 24) & 0xFF
        rd = (packed >> 16) & 0xFF
        rs1 = (packed >> 8) & 0xFF
        rs2 = packed & 0xFF
        return cls(opcode=opcode, rd=rd, rs1=rs1, rs2=rs2, imm=imm), offset + 6

    def mnemonic(self) -> str:
        name = OPCODE_TO_NAME.get(self.opcode, f"op_{self.opcode:#04x}")
        return f"{name} r{self.rd}, r{self.rs1}, r{self.rs2}, #{self.imm}"

    def __repr__(self) -> str:
        return self.mnemonic()


class IrGenome:
    INSTRUCTION_SIZE = 6

    def __init__(self, instructions: Optional[List[IrInstruction]] = None):
        self.instructions: List[IrInstruction] = instructions or []

    def __len__(self) -> int:
        return len(self.instructions)

    def encode(self) -> bytes:
        buf = bytearray()
        for instr in self.instructions:
            buf.extend(instr.encode())
        return bytes(buf)

    @classmethod
    def decode(cls, data: bytes) -> IrGenome:
        instructions: List[IrInstruction] = []
        offset = 0
        while offset + cls.INSTRUCTION_SIZE <= len(data):
            instr, offset = IrInstruction.decode(data, offset)
            instructions.append(instr)
        return cls(instructions=instructions)

    def to_ir_text(self) -> str:
        lines: List[str] = []
        for i, instr in enumerate(self.instructions):
            lines.append(f"  {i:4d}:  {instr.mnemonic()}")
        return "\n".join(lines)

    def mutate(self, rng_state: int) -> Tuple[IrGenome, int]:
        if not self.instructions:
            return self, rng_state
        idx = rng_state % len(self.instructions)
        rng_state = (rng_state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        instr = self.instructions[idx]
        mutated = IrInstruction(
            opcode=instr.opcode,
            rd=(instr.rd + (rng_state & 0xFF)) & 0xFF,
            rs1=(instr.rs1 + ((rng_state >> 8) & 0xFF)) & 0xFF,
            rs2=(instr.rs2 + ((rng_state >> 16) & 0xFF)) & 0xFF,
            imm=(instr.imm + (rng_state & 0xFFFF)) & 0xFFFF,
        )
        new_instrs = list(self.instructions)
        new_instrs[idx] = mutated
        return IrGenome(instructions=new_instrs), rng_state

    def crossover(self, other: IrGenome, rng_state: int) -> IrGenome:
        if not self.instructions or not other.instructions:
            return IrGenome(instructions=self.instructions[:])
        point_a = rng_state % len(self.instructions)
        rng_state = (rng_state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        child_instrs = self.instructions[:point_a] + other.instructions[point_a:]
        return IrGenome(instructions=child_instrs)
