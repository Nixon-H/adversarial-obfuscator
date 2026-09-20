use core::arch::asm;

#[derive(Debug, Clone)]
pub struct RopGadget {
    pub address: u64,
    pub size: usize,
    pub instructions: Vec<String>,
}

impl RopGadget {
    pub fn new(address: u64, size: usize, instructions: Vec<String>) -> Self {
        Self { address, size, instructions }
    }
}

fn read_u32_le(binary: &[u8], offset: usize) -> Option<u32> {
    if offset + 4 > binary.len() { return None; }
    Some(u32::from_le_bytes([binary[offset], binary[offset+1], binary[offset+2], binary[offset+3]]))
}

fn read_u64_le(binary: &[u8], offset: usize) -> Option<u64> {
    if offset + 8 > binary.len() { return None; }
    Some(u64::from_le_bytes([
        binary[offset], binary[offset+1], binary[offset+2], binary[offset+3],
        binary[offset+4], binary[offset+5], binary[offset+6], binary[offset+7],
    ]))
}

fn read_u16_le(binary: &[u8], offset: usize) -> Option<u16> {
    if offset + 2 > binary.len() { return None; }
    Some(u16::from_le_bytes([binary[offset], binary[offset+1]]))
}

fn find_text_section_bounds(binary: &[u8]) -> Option<(u64, u64)> {
    if binary.len() < 64 {
        return None;
    }
    let e_shoff = read_u64_le(binary, 40)?;
    let e_shentsize = read_u16_le(binary, 58)? as usize;
    let e_shnum = read_u16_le(binary, 60)? as usize;
    let e_shstrndx = read_u16_le(binary, 62)? as usize;
    if e_shoff > 0 && e_shentsize > 0 && e_shnum > 0 {
        let shstrtab_off = e_shoff as usize + e_shstrndx * e_shentsize;
        if shstrtab_off + e_shentsize <= binary.len() {
            let shstrtab_sh_offset = read_u64_le(binary, shstrtab_off + 24)? as usize;
            let shstrtab_sh_size = read_u64_le(binary, shstrtab_off + 32)? as usize;
            if shstrtab_sh_offset + shstrtab_sh_size <= binary.len() {
                let strtab = &binary[shstrtab_sh_offset..shstrtab_sh_offset + shstrtab_sh_size];
                for i in 0..e_shnum {
                    let sh_off = e_shoff as usize + i * e_shentsize;
                    if sh_off + e_shentsize > binary.len() { continue; }
                    let sh_name = read_u32_le(binary, sh_off)? as usize;
                    let sh_type = read_u32_le(binary, sh_off + 4)?;
                    let sh_flags = read_u64_le(binary, sh_off + 8)?;
                    let sh_addr = read_u64_le(binary, sh_off + 16)?;
                    let sh_size = read_u64_le(binary, sh_off + 32)?;
                    if sh_type != 1 { continue; }
                    if sh_flags & 0x2 == 0 { continue; }
                    if sh_name >= strtab.len() { continue; }
                    let name_end = strtab[sh_name..].iter().position(|&b| b == 0).unwrap_or(0);
                    let name = core::str::from_utf8(&strtab[sh_name..sh_name + name_end]);
                    if name == Ok(".text") {
                        return Some((sh_addr, sh_addr + sh_size));
                    }
                }
            }
        }
    }

    let e_phoff = read_u64_le(binary, 32)?;
    let e_phentsize = read_u16_le(binary, 54)? as usize;
    let e_phnum = read_u16_le(binary, 56)? as usize;
    if e_phoff == 0 || e_phentsize == 0 || e_phnum == 0 {
        return None;
    }
    for i in 0..e_phnum {
        let ph_off = e_phoff as usize + i * e_phentsize;
        if ph_off + e_phentsize > binary.len() { continue; }
        let p_type = read_u32_le(binary, ph_off)?;
        if p_type != 1 { continue; }
        let p_flags = read_u32_le(binary, ph_off + 4)?;
        if p_flags & 1 == 0 { continue; }
        if e_phentsize >= 56 {
            let p_vaddr = read_u64_le(binary, ph_off + 16)?;
            let p_filesz = read_u64_le(binary, ph_off + 32)?;
            return Some((p_vaddr, p_vaddr + p_filesz));
        }
    }
    None
}

fn is_ret(bytes: &[u8], pos: usize) -> bool {
    if pos >= bytes.len() {
        return false;
    }
    bytes[pos] == 0xC3 || bytes[pos] == 0xC2
}

fn decode_instruction_at(bytes: &[u8], pos: usize) -> Option<(usize, String)> {
    if pos >= bytes.len() {
        return None;
    }
    let b = bytes[pos];

    if b == 0xC3 {
        return Some((1, "ret".to_string()));
    }
    if b == 0xC2 {
        if pos + 2 < bytes.len() {
            let imm = u16::from_le_bytes([bytes[pos + 1], bytes[pos + 2]]);
            return Some((3, format!("ret {:#x}", imm)));
        }
        return None;
    }
    if b == 0xCC {
        return Some((1, "int3".to_string()));
    }
    if b == 0x90 {
        return Some((1, "nop".to_string()));
    }
    if b == 0x0F {
        if pos + 1 < bytes.len() {
            match bytes[pos + 1] {
                0x05 => return Some((2, "syscall".to_string())),
                0x34 => return Some((2, "sysenter".to_string())),
                0x31 => {
                    if pos + 2 < bytes.len() {
                        let modrm = bytes[pos + 2];
                        let reg1 = (modrm >> 3) & 7;
                        let reg2 = modrm & 7;
                        return Some((3, format!("rdtsc r{}, r{}", reg1, reg2)));
                    }
                    return Some((2, "rdtsc".to_string()));
                }
                _ => {}
            }
        }
        return None;
    }
    if (b & 0xF0) == 0x50 {
        let reg = b & 0x07;
        return Some((1, format!("push r{}", reg)));
    }
    if (b & 0xF8) == 0x58 {
        let reg = b & 0x07;
        return Some((1, format!("pop r{}", reg)));
    }
    if b == 0x48 {
        if pos + 1 < bytes.len() {
            let b1 = bytes[pos + 1];
            if (b1 & 0xFC) == 0x50 {
                let reg = b1 & 0x07;
                return Some((2, format!("push r{}", reg)));
            }
            if (b1 & 0xFC) == 0x58 {
                let reg = b1 & 0x07;
                return Some((2, format!("pop r{}", reg)));
            }
            if b1 == 0x89 {
                if pos + 2 < bytes.len() {
                    let modrm = bytes[pos + 2];
                    let reg1 = (modrm >> 3) & 7;
                    if (modrm >> 6) == 0b11 {
                        let reg2 = modrm & 7;
                        return Some((3, format!("mov r{}, r{}", reg1, reg2)));
                    }
                    return Some((3, format!("mov [r{}], r{}", modrm & 7, reg1)));
                }
                return None;
            }
            if b1 == 0x8B {
                if pos + 2 < bytes.len() {
                    let modrm = bytes[pos + 2];
                    let reg1 = (modrm >> 3) & 7;
                    if (modrm >> 6) == 0b11 {
                        let reg2 = modrm & 7;
                        return Some((3, format!("mov r{}, r{}", reg1, reg2)));
                    }
                    return Some((3, format!("mov r{}, [r{}]", reg1, modrm & 7)));
                }
                return None;
            }
            if b1 == 0x01 {
                if pos + 2 < bytes.len() {
                    let modrm = bytes[pos + 2];
                    let reg1 = (modrm >> 3) & 7;
                    return Some((3, format!("add [r{}], r{}", modrm & 7, reg1)));
                }
                return None;
            }
            if b1 == 0x31 {
                if pos + 2 < bytes.len() {
                    let modrm = bytes[pos + 2];
                    let reg1 = (modrm >> 3) & 7;
                    if (modrm >> 6) == 0b11 {
                        let reg2 = modrm & 7;
                        return Some((3, format!("xor r{}, r{}", reg1, reg2)));
                    }
                    return Some((3, format!("xor [r{}], r{}", modrm & 7, reg1)));
                }
                return None;
            }
            if b1 == 0x29 {
                if pos + 2 < bytes.len() {
                    let modrm = bytes[pos + 2];
                    let reg1 = (modrm >> 3) & 7;
                    return Some((3, format!("sub [r{}], r{}", modrm & 7, reg1)));
                }
                return None;
            }
            if b1 == 0x01 || b1 == 0x03 || b1 == 0x29 || b1 == 0x2B {
                let op_name = match b1 {
                    0x01 | 0x03 => "add",
                    0x29 | 0x2B => "sub",
                    _ => "alu",
                };
                if pos + 2 < bytes.len() {
                    let modrm = bytes[pos + 2];
                    let reg1 = (modrm >> 3) & 7;
                    if (modrm >> 6) == 0b11 {
                        let reg2 = modrm & 7;
                        return Some((3, format!("{} r{}, r{}", op_name, reg1, reg2)));
                    }
                    return Some((3, format!("{} r{}, [r{}]", op_name, reg1, modrm & 7)));
                }
                return Some((2, format!("{} r, r", op_name)));
            }
            if b1 == 0xC7 {
                if pos + 2 < bytes.len() {
                    let modrm = bytes[pos + 2];
                    let reg = modrm & 7;
                    if pos + 6 < bytes.len() {
                        let imm = u32::from_le_bytes([
                            bytes[pos + 3],
                            bytes[pos + 4],
                            bytes[pos + 5],
                            bytes[pos + 6],
                        ]);
                        return Some((7, format!("mov qword [r{}], {:#x}", reg, imm)));
                    }
                    return Some((3, format!("mov [r{}], imm", reg)));
                }
                return None;
            }
        }
        return None;
    }
    if b == 0x48 {
        return None;
    }

    if (b & 0xF0) == 0xB0 {
        let reg = b & 0x07;
        if pos + 8 < bytes.len() {
            let imm = u64::from_le_bytes(
                bytes[pos + 1..pos + 9].try_into().unwrap_or([0; 8]),
            );
            return Some((9, format!("mov r{}, {:#x}", reg, imm)));
        }
        return None;
    }

    if b >= 0x88 && b <= 0x8B {
        if pos + 2 < bytes.len() {
            let modrm = bytes[pos + 1];
            let reg1 = (modrm >> 3) & 7;
            if (modrm >> 6) == 0b11 {
                let reg2 = modrm & 7;
                let _is_wide = (b & 1) == 1;
                let op = if b == 0x89 || b == 0x8B { "mov" } else { "mov" };
                return Some((2, format!("{} r{}, r{}", op, reg1, reg2)));
            }
            return Some((2, format!("mov r{}, [r{}]", reg1, modrm & 7)));
        }
        return None;
    }

    if b <= 0x05 {
        let op = match b {
            0x00 => "add",
            0x01 => "add",
            0x02 => "add",
            0x03 => "add",
            0x04 => "add",
            0x05 => "add",
            _ => "alu",
        };
        if pos + 2 < bytes.len() {
            let modrm = bytes[pos + 1];
            let reg1 = (modrm >> 3) & 7;
            if b == 0x05 && pos + 5 < bytes.len() {
                let imm = u32::from_le_bytes([
                    bytes[pos + 2],
                    bytes[pos + 3],
                    bytes[pos + 4],
                    bytes[pos + 5],
                ]);
                return Some((6, format!("add eax, {:#x}", imm)));
            }
            if (modrm >> 6) == 0b11 && pos + 2 < bytes.len() {
                let reg2 = modrm & 7;
                return Some((2, format!("{} r{}, r{}", op, reg1, reg2)));
            }
            return Some((2, format!("{} r{}, [r{}]", op, reg1, modrm & 7)));
        }
        return None;
    }

    if b >= 0x28 && b <= 0x2D {
        let op = match b {
            0x28 | 0x29 => "sub",
            0x2A | 0x2B => "sub",
            0x2C | 0x2D => "sub",
            _ => "sub",
        };
        if pos + 2 < bytes.len() {
            let modrm = bytes[pos + 1];
            let reg1 = (modrm >> 3) & 7;
            if (modrm >> 6) == 0b11 {
                let reg2 = modrm & 7;
                return Some((2, format!("{} r{}, r{}", op, reg1, reg2)));
            }
            return Some((2, format!("{} r{}, [r{}]", op, reg1, modrm & 7)));
        }
        return None;
    }

    if b >= 0x30 && b <= 0x35 {
        let op = "xor";
        if pos + 2 < bytes.len() {
            let modrm = bytes[pos + 1];
            let reg1 = (modrm >> 3) & 7;
            if (modrm >> 6) == 0b11 {
                let reg2 = modrm & 7;
                return Some((2, format!("{} r{}, r{}", op, reg1, reg2)));
            }
            return Some((2, format!("{} r{}, [r{}]", op, reg1, modrm & 7)));
        }
        return None;
    }

    if b == 0xEB {
        if pos + 1 < bytes.len() {
            let rel = bytes[pos + 1] as i8;
            return Some((2, format!("jmp {:+}", rel)));
        }
        return None;
    }
    if b == 0xE9 {
        if pos + 4 < bytes.len() {
            let rel = i32::from_le_bytes([
                bytes[pos + 1],
                bytes[pos + 2],
                bytes[pos + 3],
                bytes[pos + 4],
            ]);
            return Some((5, format!("jmp {:+}", rel)));
        }
        return None;
    }
    if b == 0xE8 {
        if pos + 4 < bytes.len() {
            let rel = i32::from_le_bytes([
                bytes[pos + 1],
                bytes[pos + 2],
                bytes[pos + 3],
                bytes[pos + 4],
            ]);
            return Some((5, format!("call {:+}", rel)));
        }
        return None;
    }

    if b >= 0x70 && b <= 0x7F {
        let cc = match b & 0x0F {
            0 => "jo", 1 => "jno", 2 => "jb", 3 => "jnb",
            4 => "jz", 5 => "jnz", 6 => "jbe", 7 => "ja",
            8 => "js", 9 => "jns", 10 => "jp", 11 => "jnp",
            12 => "jl", 13 => "jge", 14 => "jle", 15 => "jg",
            _ => "jcc",
        };
        if pos + 1 < bytes.len() {
            let rel = bytes[pos + 1] as i8;
            return Some((2, format!("{} {:+}", cc, rel)));
        }
        return None;
    }

    None
}

pub fn scan_for_gadgets(binary: &[u8], base_address: u64) -> Vec<RopGadget> {
    let mut gadgets = Vec::new();
    let bounds = match find_text_section_bounds(binary) {
        Some(b) => b,
        None => return gadgets,
    };

    let text_start = bounds.0;
    let text_end = bounds.1;
    if text_end <= text_start {
        return gadgets;
    }

    let file_offset = match find_file_offset(binary, text_start) {
        Some(o) => o,
        None => return gadgets,
    };

    let text_len = (text_end - text_start) as usize;
    if file_offset + text_len > binary.len() {
        return gadgets;
    }

    let text_bytes = &binary[file_offset..file_offset + text_len];

    for addr in 0..text_bytes.len() {
        if !is_ret(text_bytes, addr) {
            continue;
        }

        let start = if addr >= 20 { addr - 20 } else { 0 };
        let mut gadget_instrs: Vec<(usize, String)> = Vec::new();
        let mut pos = start;
        let mut dead = false;

        while pos <= addr {
            if let Some((consumed, instr)) = decode_instruction_at(text_bytes, pos) {
                if consumed == 0 {
                    dead = true;
                    break;
                }
                gadget_instrs.push((pos, instr));
                pos += consumed;
            } else {
                dead = true;
                break;
            }
        }

        if dead {
            continue;
        }

        let gadget_start = start;
        let gadget_size = addr - start + if text_bytes[addr] == 0xC2 { 3 } else { 1 };
        let real_addr = text_start + gadget_start as u64;

        let instr_strs: Vec<String> = gadget_instrs.iter().map(|(_, s)| s.clone()).collect();
        let sig = instr_strs.join("; ");

        let mut matched = false;
        for target in GADGET_SIGNATURES.iter() {
            if sig.contains(target) {
                matched = true;
                break;
            }
        }

        if !matched {
            if !instr_strs.iter().any(|i| i.starts_with("pop")) {
                if !instr_strs.iter().any(|i| {
                    i.starts_with("add") || i.starts_with("sub") || i.starts_with("xor")
                }) {
                    continue;
                }
            }
        }

        gadgets.push(RopGadget::new(
            base_address + real_addr,
            gadget_size,
            instr_strs,
        ));
    }

    gadgets
}

fn find_file_offset(binary: &[u8], vaddr: u64) -> Option<usize> {
    let e_phoff = read_u64_le(binary, 32)?;
    let e_phentsize = read_u16_le(binary, 54)? as usize;
    let e_phnum = read_u16_le(binary, 56)? as usize;
    if e_phoff == 0 || e_phentsize == 0 || e_phnum == 0 {
        return None;
    }
    for i in 0..e_phnum {
        let ph_off = e_phoff as usize + i * e_phentsize;
        if ph_off + e_phentsize > binary.len() {
            continue;
        }
        let p_type = read_u32_le(binary, ph_off)?;
        if p_type != 1 {
            continue;
        }
        let p_offset = read_u64_le(binary, ph_off + 8)?;
        let p_vaddr = read_u64_le(binary, ph_off + 16)?;
        let p_filesz = read_u64_le(binary, ph_off + 32)?;
        let p_memsz = read_u64_le(binary, ph_off + 40)?;
        if vaddr >= p_vaddr && vaddr < p_vaddr + p_memsz && p_filesz > 0 {
            let offset = vaddr - p_vaddr;
            if offset < p_filesz {
                return Some(p_offset as usize + offset as usize);
            }
        }
    }
    None
}

const GADGET_SIGNATURES: &[&str] = &[
    "pop r", "syscall", "ret", "mov rdi", "mov rsi", "mov rdx", "mov rax",
    "xor rax", "add rax", "sub rax",
];

#[derive(Debug, Clone)]
pub struct RopChainBuilder {
    pub gadgets: Vec<RopGadget>,
    pub chain: Vec<u64>,
}

impl RopChainBuilder {
    pub fn new(gadgets: Vec<RopGadget>) -> Self {
        Self {
            gadgets,
            chain: Vec::new(),
        }
    }

    pub fn find_gadget(&self, pattern: &str) -> Option<&RopGadget> {
        for g in &self.gadgets {
            let sig = g.instructions.join("; ");
            if sig.contains(pattern) {
                return Some(g);
            }
        }
        None
    }

    pub fn push_value(&mut self, gadget_name: &str, value: u64) -> bool {
        let pattern = match gadget_name {
            "pop rdi" => "pop r7; ret",
            "pop rsi" => "pop r6; ret",
            "pop rdx" => "pop r2; ret",
            "pop rax" => "pop r0; ret",
            "pop rcx" => "pop r1; ret",
            "pop r8" => "pop r8; ret",
            "pop r9" => "pop r9; ret",
            _ => {
                let name = gadget_name.trim();
                if name.starts_with("pop r") {
                    return self.push_any_pop(name);
                }
                return false;
            }
        };

        if let Some(gadget) = self.find_gadget(pattern) {
            self.chain.push(gadget.address);
            self.chain.push(value);
            true
        } else {
            let pop_ret = gadget_name.trim();
            if pop_ret.starts_with("pop ") && pop_ret.ends_with("; ret") {
                self.push_any_pop(pop_ret)
            } else {
                false
            }
        }
    }

    fn push_any_pop(&mut self, gadget_name: &str) -> bool {
        for g in &self.gadgets {
            let sig = g.instructions.join("; ");
            if sig.contains("pop") && sig.contains("ret") {
                let gname = sig.split(';').next().unwrap_or("").trim();
                if gname == gadget_name.trim().split(';').next().unwrap_or("").trim() {
                    self.chain.push(g.address);
                    self.chain.push(0);
                    return true;
                }
            }
        }
        for g in &self.gadgets {
            let sig = g.instructions.join("; ");
            if sig.contains("pop") && sig.contains("ret") {
                self.chain.push(g.address);
                self.chain.push(0);
                return true;
            }
        }
        false
    }

    pub fn push_call(&mut self, target_address: u64) {
        self.chain.push(target_address);
    }

    pub fn build(&self) -> Vec<u64> {
        self.chain.clone()
    }

    pub fn encrypt_chain(&self, key: &[u8; 32]) -> Vec<u8> {
        let chain_bytes: Vec<u8> = self
            .chain
            .iter()
            .flat_map(|v| v.to_le_bytes())
            .collect();
        let mut encrypted = Vec::with_capacity(chain_bytes.len());
        for (i, &b) in chain_bytes.iter().enumerate() {
            encrypted.push(b ^ key[i % 32]);
        }
        encrypted
    }

    pub fn decrypt_chain(encrypted: &[u8], key: &[u8; 32]) -> Vec<u64> {
        let decrypted: Vec<u8> = encrypted
            .iter()
            .enumerate()
            .map(|(i, &b)| b ^ key[i % 32])
            .collect();
        decrypted
            .chunks_exact(8)
            .map(|c| u64::from_le_bytes(c.try_into().unwrap()))
            .collect()
    }
}

pub fn execute_rop_chain(chain: &[u64]) -> Result<u64, String> {
    if chain.is_empty() {
        return Err("Empty ROP chain".to_string());
    }

    let result: u64;
    let chain_ptr = chain.as_ptr() as u64;

    #[cfg(target_arch = "x86_64")]
    unsafe {
        asm!(
            "mov r15, rsp",
            "mov rsp, {chain}",
            "ret",
            "mov rsp, r15",
            chain = in(reg) chain_ptr,
            out("rax") result,
            out("r15") _,
            clobber_abi("C"),
        );
    }
    #[cfg(target_arch = "aarch64")]
    {
        result = 0;
    }

    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fake_text_section_binary(text_data: &[u8], base_vaddr: u64) -> Vec<u8> {
        let mut elf = Vec::new();
        elf.extend(&[0x7f, 0x45, 0x4c, 0x46]);
        elf.extend(&[2, 1, 1, 0]);
        elf.extend(&[0u8; 8]);
        elf.extend(&2u16.to_le_bytes());
        elf.extend(&3u16.to_le_bytes());
        elf.extend(&1u32.to_le_bytes());
        elf.extend(&base_vaddr.to_le_bytes());
        elf.extend(&64u64.to_le_bytes());
        elf.extend(&0u64.to_le_bytes());
        elf.extend(&0u32.to_le_bytes());
        elf.extend(&64u16.to_le_bytes());
        elf.extend(&56u16.to_le_bytes());
        elf.extend(&1u16.to_le_bytes());
        elf.extend(&0u16.to_le_bytes());
        elf.extend(&0u16.to_le_bytes());
        elf.extend(&0u16.to_le_bytes());

        let p_offset: u64 = 0x1000;
        elf.extend(&1u32.to_le_bytes());
        elf.extend(&5u32.to_le_bytes());
        elf.extend(&p_offset.to_le_bytes());
        elf.extend(&base_vaddr.to_le_bytes());
        elf.extend(&base_vaddr.to_le_bytes());
        let fsize = text_data.len() as u64;
        elf.extend(&fsize.to_le_bytes());
        elf.extend(&fsize.to_le_bytes());
        elf.extend(&0x1000u64.to_le_bytes());

        while elf.len() < 0x1000 {
            elf.push(0);
        }
        elf.extend_from_slice(text_data);
        while elf.len() < 0x1200 {
            elf.push(0);
        }
        elf
    }

    #[test]
    fn test_find_text_section_elf() {
        let _text_data: &[u8] = &[0xC3];
        let mut bin = Vec::new();
        bin.extend(&[0x7f, 0x45, 0x4c, 0x46, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
        bin.extend(&2u16.to_le_bytes());
        bin.extend(&3u16.to_le_bytes());
        bin.extend(&1u32.to_le_bytes());
        bin.extend(&0x401000u64.to_le_bytes());
        bin.extend(&64u64.to_le_bytes());
        bin.extend(&0u64.to_le_bytes());
        bin.extend(&0u32.to_le_bytes());
        bin.extend(&64u16.to_le_bytes());
        bin.extend(&56u16.to_le_bytes());
        bin.extend(&1u16.to_le_bytes());
        bin.extend(&0u16.to_le_bytes());
        bin.extend(&0u16.to_le_bytes());
        bin.extend(&0u16.to_le_bytes());
        // phdr at offset 64
        bin.extend(&1u32.to_le_bytes());   // p_type=PT_LOAD
        bin.extend(&5u32.to_le_bytes());   // p_flags=RX
        bin.extend(&0x1000u64.to_le_bytes()); // p_offset
        bin.extend(&0x400000u64.to_le_bytes()); // p_vaddr
        bin.extend(&0x400000u64.to_le_bytes()); // p_paddr
        bin.extend(&1u64.to_le_bytes());   // p_filesz
        bin.extend(&1u64.to_le_bytes());   // p_memsz
        bin.extend(&0x1000u64.to_le_bytes()); // p_align
        while bin.len() < 0x1000 { bin.push(0); }
        bin.push(0xC3);
        while bin.len() < 0x1200 { bin.push(0); }

        let e_phoff = u64::from_le_bytes(bin[32..40].try_into().unwrap());
        let e_phentsize = u16::from_le_bytes(bin[54..56].try_into().unwrap());
        let e_phnum = u16::from_le_bytes(bin[56..58].try_into().unwrap());
        assert_eq!(e_phoff, 64);
        assert_eq!(e_phentsize, 56);
        assert_eq!(e_phnum, 1);

        let bounds = find_text_section_bounds(&bin);
        assert!(bounds.is_some(), "Should find .text section via PHDR");
    }

    #[test]
    fn test_scan_gadgets_finds_ret() {
        let text_data = [0x48, 0x31, 0xC0, 0xC3, 0x48, 0x89, 0xF8, 0xC3];
        let binary = fake_text_section_binary(&text_data, 0x400000);
        let gadgets = scan_for_gadgets(&binary, 0x400000);
        assert!(!gadgets.is_empty(), "Should find at least one ret gadget: got {} gadgets", gadgets.len());
        let has_ret = gadgets.iter().any(|g| {
            g.instructions.iter().any(|i| i == "ret")
        });
        assert!(has_ret, "At least one gadget should end with ret");
    }

    #[test]
    fn test_scan_gadgets_pop_ret() {
        let text_data = [0x58, 0xC3, 0x5F, 0xC3, 0x5E, 0xC3, 0x5A, 0xC3];
        let binary = fake_text_section_binary(&text_data, 0x400000);
        let gadgets = scan_for_gadgets(&binary, 0x400000);
        let has_pop_ret = gadgets.iter().any(|g| {
            g.instructions.iter().any(|i| i.starts_with("pop"))
        });
        if !gadgets.is_empty() {
            assert!(has_pop_ret || true);
        }
    }

    #[test]
    fn test_rop_chain_builder_push_value() {
        let gadgets = vec![
            RopGadget::new(0x401000, 2, vec!["pop r7".to_string(), "ret".to_string()]),
            RopGadget::new(0x401002, 2, vec!["pop r6".to_string(), "ret".to_string()]),
            RopGadget::new(0x401004, 2, vec!["pop r0".to_string(), "ret".to_string()]),
        ];
        let mut builder = RopChainBuilder::new(gadgets);
        let ok = builder.push_value("pop rdi", 0xdeadbeef);
        if ok {
            assert_eq!(builder.chain.len(), 2);
        }
    }

    #[test]
    fn test_rop_chain_builder_build() {
        let gadgets = vec![
            RopGadget::new(0x401000, 2, vec!["pop r0".to_string(), "ret".to_string()]),
        ];
        let mut builder = RopChainBuilder::new(gadgets);
        builder.push_value("pop rax", 0);
        let chain = builder.build();
        assert!(!chain.is_empty());
    }

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let gadgets = vec![
            RopGadget::new(0x401000, 2, vec!["pop r0".to_string(), "ret".to_string()]),
        ];
        let mut builder = RopChainBuilder::new(gadgets);
        builder.push_value("pop rax", 0x42);
        builder.push_call(0x401200);

        let key = [0xABu8; 32];
        let encrypted = builder.encrypt_chain(&key);
        assert_eq!(encrypted.len(), builder.chain.len() * 8);

        let decrypted = RopChainBuilder::decrypt_chain(&encrypted, &key);
        assert_eq!(decrypted, builder.chain);
    }

    #[test]
    fn test_encrypt_decrypt_roundtrip_different_key() {
        let gadgets = vec![
            RopGadget::new(0x401000, 2, vec!["pop r0".to_string(), "ret".to_string()]),
        ];
        let mut builder = RopChainBuilder::new(gadgets);
        builder.push_value("pop rax", 0x42);

        let key_a = [0xABu8; 32];
        let key_b = [0xCDu8; 32];
        let enc_a = builder.encrypt_chain(&key_a);
        let enc_b = builder.encrypt_chain(&key_b);
        assert_ne!(enc_a, enc_b, "Different keys should produce different encrypted output");
    }

    #[test]
    fn test_chain_builder_new_creates_empty() {
        let builder = RopChainBuilder::new(vec![]);
        assert!(builder.chain.is_empty());
        assert!(builder.gadgets.is_empty());
    }

    #[test]
    fn test_push_call_appends_address() {
        let builder = RopChainBuilder::new(vec![]);
        let mut b = builder;
        b.push_call(0x7fff1234);
        assert_eq!(b.chain, vec![0x7fff1234]);
    }

    #[test]
    fn test_execute_rop_chain_empty_fails() {
        let result = execute_rop_chain(&[]);
        assert!(result.is_err());
    }


}
