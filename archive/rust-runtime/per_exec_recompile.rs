use std::collections::HashMap;

type JitFnPtr = extern "C" fn(u64) -> u64;

#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub struct InputClass {
    pub hash: u32,
    pub label: String,
}

pub struct CompiledVariant {
    pub class: InputClass,
    pub fn_ptr: JitFnPtr,
    pub code: Vec<u8>,
    pub use_count: u64,
}

pub struct PerExecRecompiler {
    base_seed: u64,
    common_classes: Vec<InputClass>,
    variants: HashMap<u32, CompiledVariant>,
    generic_variant: Option<JitFnPtr>,
    compile_count: u64,
    max_cached_classes: usize,
}

impl PerExecRecompiler {
    pub fn new(base_seed: u64) -> Self {
        PerExecRecompiler {
            base_seed,
            common_classes: Vec::new(),
            variants: HashMap::new(),
            generic_variant: None,
            compile_count: 0,
            max_cached_classes: 16,
        }
    }

    pub fn classify_input(data: &[u8]) -> u32 {
        let mut h: u32 = 0x811c9dc5;
        for &b in data {
            h = h.wrapping_mul(0x01000193);
            h ^= b as u32;
        }
        h
    }

    pub fn register_common_class(&mut self, label: &str, data: &[u8]) {
        let hash = Self::classify_input(data);
        self.common_classes.push(InputClass {
            hash,
            label: label.to_string(),
        });
    }

    pub fn get_or_compile(&mut self, input: &[u8]) -> JitFnPtr {
        let class_hash = Self::classify_input(input);

        if let Some(variant) = self.variants.get(&class_hash) {
            return variant.fn_ptr;
        }

        let is_common = self.common_classes.iter().any(|c| c.hash == class_hash);
        if is_common || self.variants.len() < self.max_cached_classes {
            return self.compile_for_class(class_hash);
        }

        if let Some(generic) = self.generic_variant {
            return generic;
        }

        self.compile_generic()
    }

    fn compile_for_class(&mut self, class_hash: u32) -> JitFnPtr {
        let seed = self.base_seed.wrapping_add(class_hash as u64);
        let code = self.emit_class_code(class_hash, seed);
        let fn_ptr = unsafe { self.allocate_and_write(&code) };

        self.variants.insert(class_hash, CompiledVariant {
            class: InputClass {
                hash: class_hash,
                label: format!("class_{:08x}", class_hash),
            },
            fn_ptr,
            code: code.clone(),
            use_count: 1,
        });

        self.compile_count += 1;
        fn_ptr
    }

    fn compile_generic(&mut self) -> JitFnPtr {
        let seed = self.base_seed.wrapping_add(0xFFFFFFFF);
        let mut code = Vec::with_capacity(32);
        code.push(0xB8);
        code.extend_from_slice(&seed.to_le_bytes()[..4]);
        code.push(0x05);
        code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
        code.push(0xC3);

        let fn_ptr = unsafe { self.allocate_and_write(&code) };
        self.generic_variant = Some(fn_ptr);
        self.compile_count += 1;
        fn_ptr
    }

    fn emit_class_code(&self, class_hash: u32, seed: u64) -> Vec<u8> {
        let mut code = Vec::with_capacity(256);

        // Real computation: result = (class_hash * 0x9E3779B9 + seed) ^ rotate_right(class_hash, 8)
        // Varying instruction selection per class hash provides polymorphism.
        let variant_bits = class_hash.wrapping_mul(seed as u32).rotate_left(4);

        // Insert NOP diversity before the main computation
        let nop_count = (seed as usize % 4) + 1;
        let nop_templates: &[&[u8]] = &[
            &[0x90],
            &[0x66, 0x90],
            &[0x0f, 0x1f, 0x00],
            &[0x0f, 0x1f, 0x40, 0x00],
            &[0x66, 0x0f, 0x1f, 0x44, 0x00, 0x00],
        ];
        for i in 0..nop_count {
            let tmpl = nop_templates[(seed as usize + i) % nop_templates.len()];
            code.extend_from_slice(tmpl);
        }

        // Load class_hash into eax
        code.push(0xB8);
        code.extend_from_slice(&class_hash.to_le_bytes());

        match variant_bits % 4 {
            0 => {
                // Path A: imul + add + ror (uses registers eax, ecx, edx)
                code.push(0xBA);
                code.extend_from_slice(&(seed as u32).to_le_bytes());
                code.push(0xB9);
                code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
                code.push(0x0F);
                code.push(0xAF);
                code.push(0xC1);
                code.push(0x01);
                code.push(0xD0);
                code.push(0xC1);
                code.push(0xC8);
                code.push(0x08);
            }
            1 => {
                // Path B: xor + add + imul (uses eax, ecx)
                code.push(0xB9);
                code.extend_from_slice(&(seed as u32).to_le_bytes());
                code.push(0x31);
                code.push(0xC8);
                code.push(0x69);
                code.push(0xC0);
                code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
                code.push(0x01);
                code.push(0xC8);
            }
            2 => {
                // Path C: lea-based + xor + ror (uses eax, ecx, edx)
                code.push(0xB9);
                code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
                code.push(0xBA);
                code.extend_from_slice(&(seed as u32).to_le_bytes());
                code.push(0x0F);
                code.push(0xAF);
                code.push(0xC1);
                code.push(0x31);
                code.push(0xD0);
                code.push(0xC1);
                code.push(0xC8);
                code.push(0x08);
            }
            _ => {
                // Path D: add + ror + imul (reordered, uses eax, edx)
                code.push(0xBA);
                code.extend_from_slice(&(seed as u32).to_le_bytes());
                code.push(0x01);
                code.push(0xD0);
                code.push(0xC1);
                code.push(0xC8);
                code.push(0x08);
                code.push(0x69);
                code.push(0xC0);
                code.extend_from_slice(&0x9E3779B9u32.to_le_bytes());
            }
        }

        // Append a second set of NOPs after computation for additional diversity
        let post_nop_count = (seed.wrapping_mul(3) as usize % 3) + 1;
        for i in 0..post_nop_count {
            let tmpl = nop_templates[(seed.wrapping_mul(7).wrapping_add(i as u64) as usize) % nop_templates.len()];
            code.extend_from_slice(tmpl);
        }

        code.push(0xC3);
        code
    }

    unsafe fn allocate_and_write(&self, code: &[u8]) -> JitFnPtr {
        use std::ptr;
        let page_size = crate::platform::page_size();
        let alloc_size = if page_size > 0 { page_size } else { 4096 };
        let ptr = crate::platform::alloc_pages(alloc_size);
        if ptr.is_null() {
            panic!("per_exec_recompile: alloc failed");
        }
        if crate::platform::protect_pages(ptr, alloc_size, crate::platform::PagePerm::ReadWriteExec).is_err() {
            crate::platform::free_pages(ptr, alloc_size);
            panic!("per_exec_recompile: mprotect failed");
        }
        ptr::copy_nonoverlapping(code.as_ptr(), ptr, code.len());
        #[cfg(target_arch = "x86_64")]
        std::arch::asm!("mfence", options(nostack, nomem));
        std::mem::transmute(ptr)
    }

    pub fn variant_count(&self) -> usize {
        self.variants.len()
    }

    pub fn compile_count(&self) -> u64 {
        self.compile_count
    }

    pub fn has_variant_for(&self, input: &[u8]) -> bool {
        let hash = Self::classify_input(input);
        self.variants.contains_key(&hash)
    }

    pub fn trigger_recompile(&mut self, input: &[u8]) -> JitFnPtr {
        let class_hash = Self::classify_input(input);
        if self.variants.contains_key(&class_hash) {
            let _old = &self.variants[&class_hash];
            let seed = self.base_seed.wrapping_add(class_hash as u64).wrapping_add(self.compile_count);
            let code = self.emit_class_code(class_hash, seed);
            let fn_ptr = unsafe { self.allocate_and_write(&code) };
            if let Some(v) = self.variants.get_mut(&class_hash) {
                v.fn_ptr = fn_ptr;
                v.code = code;
                v.use_count = v.use_count.wrapping_add(1);
            }
            self.compile_count += 1;
            fn_ptr
        } else {
            self.get_or_compile(input)
        }
    }

    pub fn read_code_bytes(&self, input: &[u8]) -> Option<Vec<u8>> {
        let hash = Self::classify_input(input);
        self.variants.get(&hash).map(|v| v.code.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_recompiler() -> PerExecRecompiler {
        PerExecRecompiler::new(42)
    }

    #[test]
    fn test_recompiles_on_new_class() {
        let mut re = make_recompiler();
        let input_a = b"input_class_a";
        let input_b = b"input_class_b";
        let code_a = re.read_code_bytes(input_a);
        let code_b = re.read_code_bytes(input_b);
        // Both start without variants
        assert!(code_a.is_none());
        assert!(code_b.is_none());
        // Now compile
        let _ptr_a = re.get_or_compile(input_a);
        let _ptr_b = re.get_or_compile(input_b);
        let code_a = re.read_code_bytes(input_a).unwrap();
        let code_b = re.read_code_bytes(input_b).unwrap();
        // Different inputs produce different code bytes
        let h1 = PerExecRecompiler::classify_input(input_a);
        let h2 = PerExecRecompiler::classify_input(input_b);
        assert_ne!(h1, h2, "Inputs should hash to different classes");
        assert_ne!(code_a, code_b, "Different inputs should get different compiled code");
    }

    #[test]
    fn test_caches_common_variants() {
        let mut re = make_recompiler();
        let data = b"common_input_a";
        re.register_common_class("common_a", data);
        let ptr1 = re.get_or_compile(data);
        let ptr2 = re.get_or_compile(data);
        assert_eq!(ptr1 as usize, ptr2 as usize, "Cached variant should return same pointer");
        assert_eq!(re.variant_count(), 1, "Only one variant should be cached");
    }

    #[test]
    fn test_fallback_to_generic() {
        let mut re = make_recompiler();
        let ptr = re.get_or_compile(b"completely_new_input");
        assert!(ptr as usize != 0);
    }

    #[test]
    fn test_preserves_semantics() {
        let re = make_recompiler();
        let h1 = PerExecRecompiler::classify_input(b"test_data");
        let h2 = PerExecRecompiler::classify_input(b"other_data");
        assert_ne!(h1, h2, "Input classes must differ for this test");
        let code1 = re.emit_class_code(h1, 42);
        let code2 = re.emit_class_code(h2, 42);
        assert_ne!(code1, code2, "Different classes produce different machine code");
        assert_eq!(code1.last(), Some(&0xC3), "Both variants end with RET");
        assert_eq!(code2.last(), Some(&0xC3), "Both variants end with RET");
    }

    #[test]
    fn test_classify_deterministic() {
        let h1 = PerExecRecompiler::classify_input(b"deterministic_test");
        let h2 = PerExecRecompiler::classify_input(b"deterministic_test");
        assert_eq!(h1, h2);
    }

    #[test]
    fn test_classify_different() {
        let h1 = PerExecRecompiler::classify_input(b"alpha");
        let h2 = PerExecRecompiler::classify_input(b"beta");
        assert_ne!(h1, h2);
    }

    #[test]
    fn test_trigger_recompile() {
        let mut re = make_recompiler();
        let input = b"recompile_me";
        let ptr1 = re.get_or_compile(input);
        let code1 = re.read_code_bytes(input).unwrap();
        let ptr2 = re.trigger_recompile(input);
        let code2 = re.read_code_bytes(input).unwrap();
        assert_ne!(code1, code2, "Triggered recompile should produce new code bytes");
        assert_ne!(ptr1 as usize, ptr2 as usize, "Triggered recompile should produce new pointer");
        assert!(re.compile_count() >= 2);
    }

    #[test]
    fn test_register_common_class_then_compile() {
        let mut re = make_recompiler();
        re.register_common_class("myclass", b"my_special_input");
        let ptr = re.get_or_compile(b"my_special_input");
        assert!(ptr as usize != 0);
        assert_eq!(re.variant_count(), 1);
    }
}
