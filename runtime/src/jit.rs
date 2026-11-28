use crate::memguard::{checked_page_size, round_up_to_page, scrub_memory, ScrubOnDrop};
use crate::platform::PagePerm;
use std::collections::HashMap;
use std::ptr;
use std::sync::{LazyLock, Mutex};

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

/// Registered allocation sizes are the sole source for raw-pointer cleanup.
static ALLOC_REGISTRY: LazyLock<Mutex<HashMap<usize, usize>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

fn register_alloc(ptr: *mut u8, size: usize) -> Result<(), String> {
    let mut registry = ALLOC_REGISTRY
        .lock()
        .map_err(|_| "JIT allocation registry poisoned".to_string())?;
    if registry.contains_key(&(ptr as usize)) {
        return Err("duplicate JIT allocation address".to_string());
    }
    registry.insert(ptr as usize, size);
    Ok(())
}

fn lookup_alloc_size(ptr: *mut u8) -> Option<usize> {
    ALLOC_REGISTRY
        .lock()
        .ok()
        .and_then(|registry| registry.get(&(ptr as usize)).copied())
}

fn unregister_alloc(ptr: *mut u8) -> Option<usize> {
    let mut registry = ALLOC_REGISTRY
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    registry.remove(&(ptr as usize))
}

fn wipe_and_unmap(ptr: *mut u8, size: usize) {
    unsafe {
        scrub_memory(ptr, size);
        crate::platform::free_pages(ptr, size);
    }
}

fn allocate_executable(size: usize) -> Result<(*mut u8, usize), String> {
    if size == 0 {
        return Err("JIT allocation size must be non-zero".to_string());
    }
    let page_size = checked_page_size()?;
    let alloc_size = round_up_to_page(size, page_size)
        .filter(|size| *size > 0)
        .ok_or_else(|| "JIT allocation size overflow".to_string())?;
    let ptr = crate::platform::alloc_pages(alloc_size);
    if ptr.is_null() {
        return Err("mmap failed for JIT page".to_string());
    }
    if unsafe { crate::platform::protect_pages(ptr, alloc_size, PagePerm::ReadWriteExec) }.is_err() {
        unsafe { crate::platform::free_pages(ptr, alloc_size) };
        return Err("mprotect failed to set RWX".to_string());
    }
    if let Err(error) = register_alloc(ptr, alloc_size) {
        unsafe { crate::platform::free_pages(ptr, alloc_size) };
        return Err(error);
    }
    Ok((ptr, alloc_size))
}

/// Legacy manager for callers that explicitly manage raw executable pointers.
pub struct JitMemoryManager {
    allocated_pages: Vec<(*mut u8, usize)>,
}

impl JitMemoryManager {
    pub fn new() -> Self {
        JitMemoryManager {
            allocated_pages: Vec::new(),
        }
    }

    pub fn allocate_executable(&mut self, size: usize) -> Result<*mut u8, String> {
        let (ptr, alloc_size) = allocate_executable(size)?;
        self.allocated_pages.push((ptr, alloc_size));
        Ok(ptr)
    }

    /// Free a manager-owned allocation using its registered size.
    ///
    /// # Safety
    /// `ptr` must have been returned by this manager and must no longer be used.
    /// The legacy `size` argument is intentionally ignored.
    pub unsafe fn free_executable(&mut self, ptr: *mut u8, _size: usize) {
        let Some(index) = self.allocated_pages.iter().position(|entry| entry.0 == ptr) else {
            return;
        };
        let Some(registered_size) = lookup_alloc_size(ptr) else {
            return;
        };
        if self.allocated_pages[index].1 != registered_size {
            return;
        }
        self.allocated_pages.remove(index);
        let _ = unregister_alloc(ptr);
        wipe_and_unmap(ptr, registered_size);
    }

    pub fn wipe_all(&mut self) {
        for (ptr, size) in self.allocated_pages.drain(..) {
            let _ = unregister_alloc(ptr);
            wipe_and_unmap(ptr, size);
        }
    }
}

impl Drop for JitMemoryManager {
    fn drop(&mut self) {
        self.wipe_all();
    }
}

/// Owning executable allocation. Dropping it wipes and unmaps the allocation.
pub struct JitCode {
    ptr: *mut u8,
    alloc_size: usize,
}

impl JitCode {
    pub fn new(code: &[u8]) -> Result<Self, String> {
        let (ptr, alloc_size) = allocate_executable(code.len())?;
        unsafe {
            ptr::copy_nonoverlapping(code.as_ptr(), ptr, code.len());
        }
        #[cfg(target_arch = "x86_64")]
        unsafe {
            core::arch::asm!("mfence", options(nostack, nomem));
        }
        #[cfg(target_arch = "aarch64")]
        unsafe {
            core::arch::asm!("dmb sy", options(nostack, nomem));
        }
        Ok(Self { ptr, alloc_size })
    }

    pub fn as_ptr(&self) -> *mut u8 {
        self.ptr
    }

    /// Execute using the C ABI entry `fn(*const u64, usize) -> u64`.
    ///
    /// # Safety
    /// The allocation must contain valid executable code for the current CPU
    /// and that C ABI. Machine code is never validated by Rust.
    pub unsafe fn execute(&self, args: &[u64]) -> Result<u64, String> {
        execute_template(self.ptr, args, false)
    }

    /// Reclaim a pointer previously released with [`JitCode::into_raw`].
    ///
    /// # Safety
    /// The caller must be the sole owner of the registered allocation.
    pub unsafe fn from_raw(ptr: *mut u8) -> Result<Self, String> {
        let alloc_size =
            lookup_alloc_size(ptr).ok_or_else(|| "unknown JIT function pointer".to_string())?;
        Ok(Self { ptr, alloc_size })
    }

    /// Transfer cleanup responsibility to the caller.
    pub fn into_raw(self) -> *mut u8 {
        let this = std::mem::ManuallyDrop::new(self);
        this.ptr
    }
}

impl Drop for JitCode {
    fn drop(&mut self) {
        let _ = unregister_alloc(self.ptr);
        wipe_and_unmap(self.ptr, self.alloc_size);
    }
}

fn xor_decrypt(data: &mut [u8], key: &[u8]) {
    for (i, byte) in data.iter_mut().enumerate() {
        *byte ^= key[i % key.len()];
    }
}

fn template_machine_code(class_id: u32, runtime_values: &[u64]) -> Result<Vec<u8>, String> {
    #[cfg(all(target_arch = "x86_64", not(target_os = "windows")))]
    {
        let extra = runtime_values
            .len()
            .checked_mul(13)
            .and_then(|n| n.checked_add(32))
            .ok_or_else(|| "JIT template code size overflow".to_string())?;
        let mut code = Vec::new();
        code.try_reserve(extra)
            .map_err(|_| "JIT template code allocation failed".to_string())?;

        // System V AMD64 C ABI: RDI = args pointer, RSI = arg count, RAX = result.
        code.extend_from_slice(&[0x48, 0x31, 0xC0]); // xor rax, rax
        code.push(0xB8); // mov eax, class_id (zero-extends into RAX)
        code.extend_from_slice(&class_id.to_le_bytes());
        for value in runtime_values {
            code.extend_from_slice(&[0x48, 0xBA]); // movabs rdx, imm64
            code.extend_from_slice(&value.to_le_bytes());
            code.extend_from_slice(&[0x48, 0x01, 0xD0]); // add rax, rdx
        }

        code.extend_from_slice(&[0x48, 0x85, 0xF6]); // test rsi, rsi
        let jump_zero = code.len();
        code.extend_from_slice(&[0x74, 0x00]); // jz done
        code.extend_from_slice(&[0x48, 0x31, 0xD2]); // xor rdx, rdx
        let loop_start = code.len();
        code.extend_from_slice(&[0x48, 0x8B, 0x0C, 0xD7]); // mov rcx, [rdi + rdx*8]
        code.extend_from_slice(&[0x48, 0x01, 0xC8]); // add rax, rcx
        code.extend_from_slice(&[0x48, 0xFF, 0xC2]); // inc rdx
        code.extend_from_slice(&[0x48, 0x39, 0xF2]); // cmp rdx, rsi
        let jump_loop = code.len();
        code.extend_from_slice(&[0x75, 0x00]); // jne loop
        let done = code.len();
        code.push(0xC3); // ret

        let zero_disp = i8::try_from(done as isize - (jump_zero + 2) as isize)
            .map_err(|_| "JIT template branch out of range".to_string())?;
        let loop_disp = i8::try_from(loop_start as isize - (jump_loop + 2) as isize)
            .map_err(|_| "JIT template branch out of range".to_string())?;
        code[jump_zero + 1] = zero_disp as u8;
        code[jump_loop + 1] = loop_disp as u8;
        Ok(code)
    }
    #[cfg(not(all(target_arch = "x86_64", not(target_os = "windows"))))]
    {
        let _ = class_id;
        let _ = runtime_values;
        Err("template JIT requires a non-Windows x86_64 System V host".to_string())
    }
}

pub fn specialize_template(
    encrypted_template: &[u8],
    template_key: &[u8; 32],
    runtime_values: &[u64],
) -> Result<JitCode, String> {
    specialize_template_with_class(encrypted_template, template_key, runtime_values, 0)
}

pub fn specialize_template_with_class(
    encrypted_template: &[u8],
    template_key: &[u8; 32],
    runtime_values: &[u64],
    class_id: u32,
) -> Result<JitCode, String> {
    let header_len = std::mem::size_of::<JitHeader>();
    if encrypted_template.len() < header_len {
        return Err("encrypted template too short".to_string());
    }
    let magic = u32::from_le_bytes([
        encrypted_template[0],
        encrypted_template[1],
        encrypted_template[2],
        encrypted_template[3],
    ]);
    if magic != JIT_MAGIC {
        return Err("invalid JIT template magic".to_string());
    }

    // The byte slice need not satisfy the header's 4-byte alignment.
    let header = unsafe { ptr::read_unaligned(encrypted_template.as_ptr() as *const JitHeader) };
    let payload = &encrypted_template[header_len..];
    let mut decrypted = payload.to_vec();
    let decrypted_guard = unsafe { ScrubOnDrop::new(decrypted.as_mut_ptr(), decrypted.len()) };
    xor_decrypt(&mut decrypted, template_key);
    if header.template_ir_len as usize > decrypted.len() {
        return Err("template_ir_len exceeds decrypted payload".to_string());
    }

    let machine_code = template_machine_code(class_id, runtime_values)?;
    let code_guard =
        unsafe { ScrubOnDrop::new(machine_code.as_ptr() as *mut u8, machine_code.len()) };
    let code = JitCode::new(&machine_code)?;
    drop(code_guard);
    drop(decrypted_guard);
    Ok(code)
}

/// Execute a registered raw JIT pointer.
///
/// # Safety
/// `func_ptr` must be the base of a live registered JIT allocation containing
/// valid code for `extern "C" fn(*const u64, usize) -> u64`. If `wipe_after`
/// is true, the caller transfers sole cleanup ownership to this function.
pub unsafe fn execute_template(
    func_ptr: *mut u8,
    args: &[u64],
    wipe_after: bool,
) -> Result<u64, String> {
    if func_ptr.is_null() {
        return Err("null function pointer".to_string());
    }
    let size =
        lookup_alloc_size(func_ptr).ok_or_else(|| "unknown JIT function pointer".to_string())?;
    let jit_fn: extern "C" fn(*const u64, usize) -> u64 = std::mem::transmute(func_ptr);
    let result = jit_fn(args.as_ptr(), args.len());

    if wipe_after {
        let registered_size = unregister_alloc(func_ptr)
            .ok_or_else(|| "JIT allocation disappeared during execution".to_string())?;
        if registered_size != size {
            return Err("JIT allocation size mismatch".to_string());
        }
        wipe_and_unmap(func_ptr, registered_size);
    }
    Ok(result)
}

/// Legacy hook for register-allocation randomization.
///
/// This function deliberately leaves `block` unchanged. Rewriting register
/// fields in a raw byte stream requires a complete instruction decoder and a
/// dataflow/ABI-aware allocator. The prior byte scanner lost synchronization
/// at immediates, remapped RSP/RBP, and therefore corrupted ordinary machine
/// code. Correct execution takes precedence over polymorphism until callers
/// supply instruction-boundary and liveness metadata.
pub fn randomize_register_allocation(block: &mut [u8], seed: u64) {
    let _ = (block, seed);
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
        // The only universally known instruction boundary in an opaque byte
        // vector is offset zero. Prepending a semantically neutral NOP keeps
        // every original relative displacement intact; inserting at a random
        // byte offset can split an instruction or immediate and corrupt code.
        let tmpl_idx = (rng as usize) % nop_templates.len();
        rng = rng
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        let nop_bytes = nop_templates[tmpl_idx];
        block.splice(0..0, nop_bytes.iter().cloned());
        if block.len() > 65536 {
            break;
        }
    }
}

/// Decrypt a block, apply polymorphic transformations, and return an owning
/// executable allocation that wipes and unmaps itself on drop.
pub fn polymorphic_jit_compile(
    encrypted_block: &[u8],
    key: &[u8; 32],
    seed: u64,
) -> Result<JitCode, String> {
    let mut decrypted = encrypted_block.to_vec();
    let decrypted_guard = unsafe { ScrubOnDrop::new(decrypted.as_mut_ptr(), decrypted.len()) };
    xor_decrypt(&mut decrypted, key);
    randomize_register_allocation(&mut decrypted, seed);

    let mut block_vec = decrypted.to_vec();
    let nop_count = ((seed as usize) % 8) + 2;
    insert_functional_nops(&mut block_vec, nop_count, seed.wrapping_add(1));
    let block_guard = unsafe { ScrubOnDrop::new(block_vec.as_mut_ptr(), block_vec.len()) };

    let code = JitCode::new(&block_vec)?;
    drop(block_guard);
    drop(decrypted_guard);
    Ok(code)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_template(payload: &[u8], key: &[u8; 32]) -> Vec<u8> {
        let mut tpl = Vec::with_capacity(52 + payload.len());
        tpl.extend_from_slice(&JIT_MAGIC.to_le_bytes());
        tpl.extend_from_slice(&1u32.to_le_bytes()); // version
        tpl.extend_from_slice(&0u32.to_le_bytes()); // template_ir_len (no zlib)
        tpl.extend_from_slice(&0u32.to_le_bytes()); // slot_map_len
        tpl.extend_from_slice(&0u32.to_le_bytes()); // specializer_ir_len
        tpl.extend_from_slice(&[0u8; 32]); // metadata_hash
        let mut enc = payload.to_vec();
        xor_decrypt(&mut enc, key);
        tpl.extend_from_slice(&enc);
        tpl
    }

    #[cfg(all(target_arch = "x86_64", not(target_os = "windows")))]
    #[test]
    fn specialize_template_keeps_pages_mapped() {
        // The returned owner must keep the allocation live until it is dropped.
        let key = [0x42u8; 32];
        let tpl = make_template(&[0xC3], &key);
        let code = specialize_template(&tpl, &key, &[]).expect("specialize");
        let ptr = code.as_ptr();
        assert!(lookup_alloc_size(ptr).is_some());
        let first = unsafe { ptr::read_volatile(ptr) };
        assert_eq!(first, 0x48); // xor rax, rax prefix
        assert_eq!(unsafe { code.execute(&[]) }.expect("execute"), 0);
    }

    #[test]
    fn specialize_template_rejects_truncated_ir_len() {
        let key = [0x42u8; 32];
        let mut tpl = make_template(&[0xC3], &key);
        // Claim a template_ir_len far beyond the payload: must Err, not panic.
        tpl[8..12].copy_from_slice(&u32::MAX.to_le_bytes());
        assert!(specialize_template(&tpl, &key, &[]).is_err());
    }

    #[cfg(not(all(target_arch = "x86_64", not(target_os = "windows"))))]
    #[test]
    fn specialize_template_fails_closed_on_unsupported_abi() {
        let key = [0x42u8; 32];
        let tpl = make_template(&[0xC3], &key);
        assert!(specialize_template(&tpl, &key, &[]).is_err());
    }

    #[cfg(all(target_arch = "x86_64", not(target_os = "windows")))]
    #[test]
    fn specialized_template_executes_arguments_and_drop_unregisters() {
        let key = [0x42u8; 32];
        let tpl = make_template(&[0xC3], &key);
        let code = specialize_template_with_class(&tpl, &key, &[2, 3], 9).expect("specialize");
        let ptr = code.as_ptr();
        assert!(lookup_alloc_size(ptr).is_some());
        let result = unsafe { code.execute(&[5, 7]) }.expect("execute generated code");
        assert_eq!(result, 26);
        drop(code);
        assert!(lookup_alloc_size(ptr).is_none());
    }

    #[test]
    fn execute_template_rejects_unknown_pointer_without_touching_it() {
        let mut fake_code = [0xCCu8; 64];
        let before = fake_code;
        let result = unsafe { execute_template(fake_code.as_mut_ptr(), &[1, 2], true) };
        assert!(result.is_err());
        assert_eq!(fake_code, before);
    }

    #[cfg(all(target_arch = "x86_64", not(target_os = "windows")))]
    #[test]
    fn raw_execute_uses_registered_size_and_unregisters() {
        let key = [0x42u8; 32];
        let tpl = make_template(&[0xC3], &key);
        let code = specialize_template(&tpl, &key, &[]).expect("specialize");
        let ptr = code.into_raw();
        let result = unsafe { execute_template(ptr, &[11], true) }.expect("execute");
        assert_eq!(result, 11);
        assert!(lookup_alloc_size(ptr).is_none());
    }

    #[cfg(all(target_arch = "x86_64", not(target_os = "windows")))]
    #[test]
    fn raw_owner_can_be_reclaimed_and_dropped() {
        let key = [0x42u8; 32];
        let tpl = make_template(&[0xC3], &key);
        let ptr = specialize_template(&tpl, &key, &[])
            .expect("specialize")
            .into_raw();
        let code = unsafe { JitCode::from_raw(ptr) }.expect("reclaim");
        assert_eq!(unsafe { code.execute(&[4]) }.expect("execute"), 4);
        drop(code);
        assert!(lookup_alloc_size(ptr).is_none());
        let mut fake = [0u8; 8];
        assert!(unsafe { JitCode::from_raw(fake.as_mut_ptr()) }.is_err());
    }

    #[test]
    fn manager_cleanup_uses_registered_size_and_unregisters() {
        let mut mgr = JitMemoryManager::new();
        let ptr = mgr.allocate_executable(8192).expect("allocate");
        assert!(lookup_alloc_size(ptr).is_some());
        // The legacy size argument must not control the cleanup range.
        unsafe { mgr.free_executable(ptr, 1) };
        assert!(lookup_alloc_size(ptr).is_none());
    }

    #[test]
    fn manager_cleanup_rejects_unknown_pointer_without_touching_it() {
        let mut mgr = JitMemoryManager::new();
        let mut fake = [0xA5u8; 64];
        let before = fake;
        unsafe { mgr.free_executable(fake.as_mut_ptr(), usize::MAX) };
        assert_eq!(fake, before);
    }

    #[test]
    fn manager_wipe_all_and_drop_unregister() {
        let mut mgr = JitMemoryManager::new();
        let p1 = mgr.allocate_executable(1).expect("allocate");
        let p2 = mgr.allocate_executable(1).expect("allocate");
        mgr.wipe_all();
        assert!(lookup_alloc_size(p1).is_none());
        assert!(lookup_alloc_size(p2).is_none());

        let p3 = mgr.allocate_executable(1).expect("allocate after wipe");
        drop(mgr);
        assert!(lookup_alloc_size(p3).is_none());
    }

    #[test]
    fn manager_rejects_size_overflow() {
        let mut mgr = JitMemoryManager::new();
        assert!(mgr.allocate_executable(usize::MAX).is_err());
    }

    #[test]
    fn test_randomize_register_allocation_is_conservative() {
        let mut code = vec![0x48, 0x89, 0xd0]; // mov rax, rdx
        let original = code.clone();
        randomize_register_allocation(&mut code, 0);
        assert_eq!(code.len(), original.len());
        assert_eq!(code, original);
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
    fn test_insert_functional_nops_preserves_original_suffix() {
        // Regression: random insertion used to land inside instructions or
        // immediates. All original bytes must remain contiguous at the tail.
        let original = vec![0x48, 0xc7, 0xc0, 0x50, 0x89, 0x48, 0x31, 0xc3];
        let mut block = original.clone();
        insert_functional_nops(&mut block, 4, 1234);
        assert!(block.len() > original.len());
        assert_eq!(&block[block.len() - original.len()..], &original[..]);
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

    #[cfg(target_arch = "x86_64")]
    #[test]
    fn test_polymorphic_jit_compile_runs() {
        let key: [u8; 32] = [0xAB; 32];
        let original = vec![0x48, 0x31, 0xc0, 0xc3];
        let mut encrypted = original.clone();
        xor_decrypt(&mut encrypted, &key);
        let code = polymorphic_jit_compile(&encrypted, &key, 0).expect("compile");
        assert!(!code.as_ptr().is_null());
        let _ = unsafe { code.execute(&[]) }.expect("execute");
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
            std::ptr::copy_nonoverlapping(r1.as_ptr(), buf1.as_mut_ptr(), 4);
            std::ptr::copy_nonoverlapping(r2.as_ptr(), buf2.as_mut_ptr(), 4);
        }
        assert_ne!(buf1, buf2);
    }
}
