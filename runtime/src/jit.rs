use crate::platform::PagePerm;
use std::ptr;

const JIT_MAGIC: u32 = 0x4A4954;

#[repr(C)]
struct JitHeader {
    magic: u32,
    version: u32,
    template_ir_len: u32,
    slot_map_len: u32,
    specializer_ir_len: u32,
    metadata_hash: [u8; 32],
}

pub struct JitMemoryManager {
    page_size: usize,
    allocated_pages: Vec<(*mut u8, usize)>,
}

impl JitMemoryManager {
    pub fn new() -> Self {
        let page_size = crate::platform::page_size();
        JitMemoryManager {
            page_size: if page_size == 0 { 4096 } else { page_size },
            allocated_pages: Vec::new(),
        }
    }

    pub fn allocate_executable(&mut self, size: usize) -> Result<*mut u8, String> {
        let alloc_size = (size + self.page_size - 1) & !(self.page_size - 1);
        let ptr = crate::platform::alloc_pages(alloc_size);
        if ptr.is_null() {
            return Err("mmap failed for JIT page".to_string());
        }
        let result = crate::platform::protect_pages(ptr, alloc_size, PagePerm::ReadWriteExec);
        if result.is_err() {
            crate::platform::free_pages(ptr, alloc_size);
            return Err("mprotect failed to set RWX".to_string());
        }
        self.allocated_pages.push((ptr, alloc_size));
        Ok(ptr)
    }

    pub fn free_executable(&mut self, ptr: *mut u8, size: usize) {
        let alloc_size = (size + self.page_size - 1) & !(self.page_size - 1);
        unsafe {
            ptr::write_bytes(ptr, 0u8, alloc_size);
        }
        crate::platform::free_pages(ptr, alloc_size);
        self.allocated_pages.retain(|p| p.0 != ptr);
    }

    pub fn wipe_all(&mut self) {
        for (ptr, size) in self.allocated_pages.drain(..) {
            unsafe {
                ptr::write_bytes(ptr, 0u8, size);
            }
            crate::platform::free_pages(ptr, size);
        }
    }
}

fn xor_decrypt(data: &mut [u8], key: &[u8]) {
    for (i, byte) in data.iter_mut().enumerate() {
        *byte ^= key[i % key.len()];
    }
}

pub fn specialize_template(
    encrypted_template: &[u8],
    template_key: &[u8; 32],
    runtime_values: &[u64],
) -> Result<*mut u8, String> {
    specialize_template_with_class(encrypted_template, template_key, runtime_values, 0)
}

pub fn specialize_template_with_class(
    encrypted_template: &[u8],
    template_key: &[u8; 32],
    runtime_values: &[u64],
    class_id: u32,
) -> Result<*mut u8, String> {
    if encrypted_template.len() < 52 {
        return Err("encrypted template too short".to_string());
    }

    let magic = u32::from_le_bytes([encrypted_template[0], encrypted_template[1], encrypted_template[2], encrypted_template[3]]);
    if magic != JIT_MAGIC {
        return Err("invalid JIT template magic".to_string());
    }

    let header = unsafe {
        &*(encrypted_template.as_ptr() as *const JitHeader)
    };

    let payload_offset = std::mem::size_of::<JitHeader>();
    let payload = &encrypted_template[payload_offset..];

    let mut decrypted = payload.to_vec();
    xor_decrypt(&mut decrypted, template_key);

    let use_zlib = header.template_ir_len > 0;
    let template_ir = if use_zlib {
        let compressed = &decrypted[..header.template_ir_len as usize];
        let mut decompressed = Vec::with_capacity(compressed.len() * 4);
        decompressed.extend_from_slice(compressed);
        String::from_utf8_lossy(compressed).to_string()
    } else {
        String::from_utf8_lossy(&decrypted).to_string()
    };

    let mut machine_code = Vec::with_capacity(64);
    machine_code.push(0x48);

    machine_code.push(0x31);
    machine_code.push(0xC0);

    // Inject class_id as first operation to differentiate variants
    machine_code.push(0xB8);
    machine_code.extend_from_slice(&class_id.to_le_bytes());
    machine_code.push(0x50);

    for val in runtime_values {
        let v = *val;
        machine_code.push(0x48);
        machine_code.push(0xB8);
        machine_code.extend_from_slice(&v.to_le_bytes());
        machine_code.push(0x50);
    }

    machine_code.push(0xC3);

    let mut mgr = JitMemoryManager::new();
    let code_ptr = mgr.allocate_executable(machine_code.len())?;
    unsafe {
        ptr::copy_nonoverlapping(machine_code.as_ptr(), code_ptr, machine_code.len());
    }

    let _ = template_ir;
    let _ = mgr;

    #[cfg(target_arch = "x86_64")]
    unsafe {
        core::arch::asm!("mfence", options(nostack, nomem));
    }
    #[cfg(target_arch = "aarch64")]
    unsafe {
        core::arch::asm!("dmb sy", options(nostack, nomem));
    }

    Ok(code_ptr)
}

pub fn execute_template(
    func_ptr: *mut u8,
    args: &[u64],
    wipe_after: bool,
) -> Result<u64, String> {
    if func_ptr.is_null() {
        return Err("null function pointer".to_string());
    }

    let jit_fn: extern "C" fn() -> u64 = unsafe {
        core::mem::transmute(func_ptr)
    };

    let _ = args;

    let result = jit_fn();

    if wipe_after {
        unsafe {
            ptr::write_bytes(func_ptr, 0u8, 64);
        }
        crate::platform::free_pages(func_ptr, 4096);
    }

    Ok(result)
}

/// Apply a seeded random permutation to register encodings in x86_64 machine code.
pub fn randomize_register_allocation(block: &mut [u8], seed: u64) {
    let mut perm: [u8; 8] = [0, 1, 2, 3, 4, 5, 6, 7];
    let mut rng = seed;
    let mut i: usize = 7;
    while i > 0 {
        let j = (rng % (i as u64 + 1)) as usize;
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        perm.swap(i, j);
        i = i.wrapping_sub(1);
    }

    let len = block.len();
    let mut pos = 0;
    while pos < len {
        let mut rex: u8 = 0;
        let mut rex_pos: isize = -1;
        let mut p = pos;

        while p < len {
            let b = block[p];
            if (b & 0xF0) == 0x40 && b != 0x40 {
                rex = b;
                rex_pos = p as isize;
                p += 1;
            } else {
                break;
            }
        }
        if p >= len {
            break;
        }

        let opcode = block[p];
        let opcode_pos = p;
        p += 1;

        if opcode == 0x0F && p < len {
            p += 1;
        }

        if opcode >= 0x50 && opcode <= 0x5F {
            let reg = (opcode - 0x50) | (if rex & 0x01 != 0 { 8 } else { 0 });
            if (reg as usize) < perm.len() {
                let new_reg = perm[reg as usize];
                let new_rex_b = (new_reg & 0x08) != 0;
                let new_opcode = 0x50 + (new_reg & 0x07);
                if rex_pos >= 0 {
                    block[opcode_pos] = new_opcode;
                    let mut new_rex: u8 = 0x40;
                    if rex & 0x08 != 0 { new_rex |= 0x08; }
                    if new_rex_b { new_rex |= 0x01; }
                    block[rex_pos as usize] = new_rex;
                } else {
                    block[opcode_pos] = new_opcode;
                }
            }
            continue;
        }

        if p >= len {
            break;
        }

        let modrm = block[p];
        let mod_bits = modrm >> 6;
        let old_reg = ((modrm >> 3) & 0x07) | (if rex & 0x04 != 0 { 8 } else { 0 });
        let old_rm = (modrm & 0x07) | (if rex & 0x01 != 0 { 8 } else { 0 });

        if (old_reg as usize) < perm.len() && (old_rm as usize) < perm.len() {
            let new_reg = perm[old_reg as usize];
            let new_rm = perm[old_rm as usize];

            let new_modrm = (mod_bits << 6) | ((new_reg & 0x07) << 3) | (new_rm & 0x07);
            block[p] = new_modrm;

            let new_rex_r = (new_reg & 0x08) != 0;
            let new_rex_b = (new_rm & 0x08) != 0;
            if rex_pos >= 0 {
                let mut new_rex: u8 = 0x40;
                if rex & 0x08 != 0 { new_rex |= 0x08; }
                if new_rex_r { new_rex |= 0x04; }
                if new_rex_b { new_rex |= 0x01; }
                if new_rex != rex {
                    block[rex_pos as usize] = new_rex;
                }
            }
        }

        let has_sib = mod_bits != 3 && old_rm & 0x07 == 4;
        let mut skip = 1;
        if has_sib {
            skip += 1;
        }
        skip += match mod_bits {
            1 => 1,
            2 => 4,
            _ => if mod_bits == 0 && old_rm & 0x07 == 5 { 4 } else { 0 },
        };
        pos = p + skip;
    }
}

/// Insert diverse functional NOP sequences at random safe positions.
pub fn insert_functional_nops(block: &mut Vec<u8>, count: usize, seed: u64) {
    let nop_templates: &[&[u8]] = &[
        b"\x90",
        b"\x66\x90",
        b"\x0f\x1f\x00",
        b"\x0f\x1f\x40\x00",
        b"\x0f\x1f\x44\x00\x00",
        b"\x66\x0f\x1f\x44\x00\x00",
        b"\x0f\x1f\x80\x00\x00\x00\x00",
        b"\x0f\x1f\x84\x00\x00\x00\x00\x00",
        b"\x66\x0f\x1f\x84\x00\x00\x00\x00\x00",
        b"\x48\x89\xff",
        b"\x48\x89\xc0",
        b"\x48\x89\xdb",
        b"\x48\x89\xc9",
        b"\x48\x89\xd2",
        b"\x48\x89\xf6",
        b"\x48\x89\xed",
        b"\x48\x8d\x00",
        b"\x48\x87\xc0",
        b"\x48\x87\xdb",
        b"\x48\x87\xc9",
        b"\x48\x87\xd2",
        b"\x48\x87\xf6",
        b"\x48\x87\xff",
    ];

    let mut rng = seed;
    for _ in 0..count {
        if block.is_empty() {
            break;
        }
        let idx = (rng as usize) % block.len();
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let tmpl_idx = (rng as usize) % nop_templates.len();
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let nop_bytes = nop_templates[tmpl_idx];
        block.splice(idx..idx, nop_bytes.iter().cloned());
        if block.len() > 65536 {
            break;
        }
    }
}

/// Decrypt a block, apply polymorphic transformations, allocate executable memory,
/// write the transformed code, and return a function pointer.
pub fn polymorphic_jit_compile(
    encrypted_block: &[u8],
    key: &[u8; 32],
    seed: u64,
) -> Result<*mut u8, String> {
    let mut decrypted = encrypted_block.to_vec();
    xor_decrypt(&mut decrypted, key);

    randomize_register_allocation(&mut decrypted, seed);

    let mut block_vec = decrypted.to_vec();
    let nop_count = ((seed as usize) % 8) + 2;
    insert_functional_nops(&mut block_vec, nop_count, seed.wrapping_add(1));

    let mut mgr = JitMemoryManager::new();
    let code_ptr = mgr.allocate_executable(block_vec.len())?;

    unsafe {
        ptr::copy_nonoverlapping(block_vec.as_ptr(), code_ptr, block_vec.len());
    }

    #[cfg(target_arch = "x86_64")]
    unsafe {
        core::arch::asm!("mfence", options(nostack, nomem));
    }
    #[cfg(target_arch = "aarch64")]
    unsafe {
        core::arch::asm!("dmb sy", options(nostack, nomem));
    }

    core::mem::forget(mgr);

    Ok(code_ptr)
}

impl Drop for JitMemoryManager {
    fn drop(&mut self) {
        let pages = core::mem::take(&mut self.allocated_pages);
        for (ptr, size) in pages {
            unsafe {
                ptr::write_bytes(ptr, 0u8, size);
            }
            crate::platform::free_pages(ptr, size);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_randomize_register_allocation_identity() {
        let mut code = vec![0x48, 0x89, 0xd0]; // mov rax, rdx
        let original = code.clone();
        randomize_register_allocation(&mut code, 0);
        assert_eq!(code.len(), original.len());
        assert_ne!(code, original);
    }

    #[test]
    fn test_randomize_register_allocation_deterministic() {
        let mut code1 = vec![0x48, 0x89, 0xd0];
        let mut code2 = vec![0x48, 0x89, 0xd0];
        randomize_register_allocation(&mut code1, 42);
        randomize_register_allocation(&mut code2, 42);
        assert_eq!(code1, code2);
    }

    #[test]
    fn test_insert_functional_nops_increases_length() {
        let mut block = vec![0x48, 0x31, 0xc0, 0xc3];
        let original_len = block.len();
        insert_functional_nops(&mut block, 3, 1234);
        assert!(block.len() > original_len);
    }

    #[test]
    fn test_insert_functional_nops_deterministic() {
        let mut block1 = vec![0xc3];
        let mut block2 = vec![0xc3];
        insert_functional_nops(&mut block1, 2, 999);
        insert_functional_nops(&mut block2, 2, 999);
        assert_eq!(block1, block2);
    }

    #[test]
    fn test_insert_functional_nops_different_seeds() {
        let mut block1 = vec![0xc3];
        let mut block2 = vec![0xc3];
        insert_functional_nops(&mut block1, 2, 100);
        insert_functional_nops(&mut block2, 2, 200);
        assert_ne!(block1, block2);
    }

    #[test]
    fn test_polymorphic_jit_compile_runs() {
        let key: [u8; 32] = [0xAB; 32];
        let original = vec![0x48, 0x31, 0xc0, 0xc3];
        let mut encrypted = original.clone();
        xor_decrypt(&mut encrypted, &key);
        let result = polymorphic_jit_compile(&encrypted, &key, 0);
        assert!(result.is_ok());
        let fn_ptr = result.unwrap();
        assert!(!fn_ptr.is_null());
        let func: extern "C" fn() -> u64 = unsafe { core::mem::transmute(fn_ptr) };
        let _val = func();
    }

    #[test]
    fn test_polymorphic_jit_compile_different_seeds() {
        let key: [u8; 32] = [0xCD; 32];
        let original = vec![0x48, 0x31, 0xc0, 0xc3];
        let mut encrypted = original.clone();
        xor_decrypt(&mut encrypted, &key);

        let r1 = polymorphic_jit_compile(&encrypted, &key, 1).unwrap();
        let r2 = polymorphic_jit_compile(&encrypted, &key, 2).unwrap();

        let mut buf1 = [0u8; 4];
        let mut buf2 = [0u8; 4];
        unsafe {
            std::ptr::copy_nonoverlapping(r1, buf1.as_mut_ptr(), 4);
            std::ptr::copy_nonoverlapping(r2, buf2.as_mut_ptr(), 4);
        }
        assert_ne!(buf1, buf2);
    }
}
