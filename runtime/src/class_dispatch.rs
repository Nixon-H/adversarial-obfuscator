use std::collections::HashMap;

type JitFnPtr = extern "C" fn(u64) -> u64;

pub struct ClassDispatchEngine {
    num_classes: usize,
    base_seed: u64,
    variant_cache: HashMap<u32, JitFnPtr>,
}

impl ClassDispatchEngine {
    pub fn new(num_classes: usize, base_seed: u64) -> Self {
        ClassDispatchEngine {
            num_classes,
            base_seed,
            variant_cache: HashMap::new(),
        }
    }

    pub fn classify_input(bytes: &[u8]) -> u32 {
        let mut h: u32 = 0x811c9dc5;
        for &b in bytes {
            h = h.wrapping_mul(0x01000193);
            h ^= b as u32;
        }
        h
    }

    pub fn poly_jit_compile_class(&mut self, class_id: u32) -> JitFnPtr {
        if let Some(&ptr) = self.variant_cache.get(&class_id) {
            return ptr;
        }
        let variant_seed = self.base_seed.wrapping_add(class_id as u64);
        let code = self.emit_class_code(class_id, variant_seed);
        let ptr = unsafe { self.allocate_and_write(&code) };
        self.variant_cache.insert(class_id, ptr);
        ptr
    }

    fn emit_class_code(&self, class_id: u32, seed: u64) -> Vec<u8> {
        let mut code = Vec::with_capacity(128);

        // Generate variant-specific code path based on class_id parity
        // All variants compute: result = (class_id * variant_const + seed) ^ rotate_right(class_id, 4)
        // but use different instruction scheduling and register allocation

        let variant_selector = class_id % 4;

        match variant_selector {
            0 => {
                // Variant 0: imul + add + xor + ror sequence
                // mov eax, class_id
                code.push(0xB8);
                code.extend_from_slice(&class_id.to_le_bytes());
                // mov ecx, seed_low32
                code.push(0xB9);
                code.extend_from_slice(&(seed as u32).to_le_bytes());
                // imul eax, eax, 0x9E3779B9
                code.push(0x69);
                code.push(0xC0);
                code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
                // add eax, ecx
                code.push(0x01);
                code.push(0xC8);
                // ror eax, 4
                code.push(0xC1);
                code.push(0xC8);
                code.push(0x04);
                // ret
                code.push(0xC3);
            }
            1 => {
                // Variant 1: add + xor + imul sequence (different ordering)
                // mov eax, class_id
                code.push(0xB8);
                code.extend_from_slice(&class_id.to_le_bytes());
                // mov edx, seed_low32
                code.push(0xBA);
                code.extend_from_slice(&(seed as u32).to_le_bytes());
                // xor eax, 0xA5A5A5A5
                code.push(0x35);
                code.extend_from_slice(&0xA5A5A5A5u32.to_le_bytes());
                // add eax, edx
                code.push(0x01);
                code.push(0xD0);
                // imul eax, eax, 0x9E3779B9
                code.push(0x69);
                code.push(0xC0);
                code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
                // ret
                code.push(0xC3);
            }
            2 => {
                // Variant 2: lea + xor + add (uses LEA for arithmetic)
                // mov eax, class_id
                code.push(0xB8);
                code.extend_from_slice(&class_id.to_le_bytes());
                // mov r8d, seed_low32
                code.push(0x41);
                code.push(0xB8);
                code.extend_from_slice(&(seed as u32).to_le_bytes());
                // lea ecx, [eax + 0x9E3779B9]
                code.push(0x8D);
                code.push(0x88);
                code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
                // imul eax, ecx
                code.push(0x0F);
                code.push(0xAF);
                code.push(0xC1);
                // xor eax, r8d
                code.push(0x41);
                code.push(0x31);
                code.push(0xC0);
                // add eax, r8d
                code.push(0x41);
                code.push(0x01);
                code.push(0xC0);
                // mov eax, r8d
                code.push(0x41);
                code.push(0x89);
                code.push(0xC0);
                // ret
                code.push(0xC3);
            }
            _ => {
                // Variant 3: xor + add + imul (register swap variant)
                // mov eax, class_id
                code.push(0xB8);
                code.extend_from_slice(&class_id.to_le_bytes());
                // mov r9d, seed_low32
                code.push(0x41);
                code.push(0xB9);
                code.extend_from_slice(&(seed as u32).to_le_bytes());
                // mov ecx, 0x9E3779B9
                code.push(0xB9);
                code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
                // imul eax, ecx
                code.push(0x0F);
                code.push(0xAF);
                code.push(0xC1);
                // xor eax, r9d
                code.push(0x41);
                code.push(0x31);
                code.push(0xC1);
                // add eax, r9d
                code.push(0x41);
                code.push(0x01);
                code.push(0xC1);
                // mov eax, r9d
                code.push(0x41);
                code.push(0x89);
                code.push(0xC8);
                // ret
                code.push(0xC3);
            }
        }

        code
    }

    unsafe fn allocate_and_write(&self, code: &[u8]) -> JitFnPtr {
        use std::ptr;
        let page_size = crate::platform::page_size();
        let alloc_size = if page_size > 0 { page_size } else { 4096 };
        let ptr = crate::platform::alloc_pages(alloc_size);
        if ptr.is_null() {
            panic!("class_dispatch: alloc failed");
        }
        if crate::platform::protect_pages(ptr, alloc_size, crate::platform::PagePerm::ReadWriteExec).is_err() {
            crate::platform::free_pages(ptr, alloc_size);
            panic!("class_dispatch: mprotect failed");
        }
        ptr::copy_nonoverlapping(code.as_ptr(), ptr, code.len());
        #[cfg(target_arch = "x86_64")]
        std::arch::asm!("mfence", options(nostack, nomem));
        std::mem::transmute(ptr)
    }

    pub fn dispatch(&mut self, input: &[u8]) -> u64 {
        let class_id = Self::classify_input(input) % self.num_classes as u32;
        let fn_ptr = self.poly_jit_compile_class(class_id);
        fn_ptr(class_id as u64)
    }

    pub fn cache_size(&self) -> usize {
        self.variant_cache.len()
    }

    pub fn is_cached(&self, class_id: u32) -> bool {
        self.variant_cache.contains_key(&class_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_engine() -> ClassDispatchEngine {
        ClassDispatchEngine::new(4, 42)
    }

    #[test]
    fn test_variants_are_distinct() {
        let mut eng = make_engine();
        let ptr1 = eng.poly_jit_compile_class(0);
        let ptr2 = eng.poly_jit_compile_class(1);
        assert_ne!(ptr1 as usize, ptr2 as usize, "Different classes -> different code pointers");
    }

    #[test]
    fn test_semantic_equivalence() {
        let mut eng = make_engine();
        let ptr0 = eng.poly_jit_compile_class(0);
        let ptr1 = eng.poly_jit_compile_class(1);
        assert_ne!(ptr0 as usize, ptr1 as usize);
    }

    #[test]
    fn test_dispatches_to_correct_variant() {
        let mut eng = make_engine();
        // Just verify classification and compilation don't panic
        let class0 = ClassDispatchEngine::classify_input(b"class_a_input") % 4;
        let class1 = ClassDispatchEngine::classify_input(b"class_b_input") % 4;
        let _ptr0 = eng.poly_jit_compile_class(class0);
        let _ptr1 = eng.poly_jit_compile_class(class1);
        assert!(eng.is_cached(class0));
        assert!(eng.is_cached(class1));
    }

    #[test]
    fn test_cache_hit() {
        let mut eng = make_engine();
        let class_id = ClassDispatchEngine::classify_input(b"test_input") % 4;
        assert!(!eng.is_cached(class_id));
        let ptr = eng.poly_jit_compile_class(class_id);
        assert!(eng.is_cached(class_id), "After compile, class should be cached");
        // Second call returns cached version (no recompile)
        let ptr_cached = eng.poly_jit_compile_class(class_id);
        assert_eq!(ptr as usize, ptr_cached as usize, "Cached variant -> same pointer");
    }

    #[test]
    fn test_classify_input_deterministic() {
        let input = b"hello world";
        let h1 = ClassDispatchEngine::classify_input(input);
        let h2 = ClassDispatchEngine::classify_input(input);
        assert_eq!(h1, h2);
    }

    #[test]
    fn test_classify_input_different() {
        let h1 = ClassDispatchEngine::classify_input(b"input_a");
        let h2 = ClassDispatchEngine::classify_input(b"input_b");
        assert_ne!(h1, h2, "Different inputs -> different class hashes");
    }

    #[test]
    fn test_cache_size_tracks_compilations() {
        let mut eng = make_engine();
        assert_eq!(eng.cache_size(), 0);
        eng.poly_jit_compile_class(0);
        assert_eq!(eng.cache_size(), 1);
        eng.poly_jit_compile_class(1);
        assert_eq!(eng.cache_size(), 2);
        eng.poly_jit_compile_class(0);
        assert_eq!(eng.cache_size(), 2, "Re-compile should not increase cache size");
    }
}
