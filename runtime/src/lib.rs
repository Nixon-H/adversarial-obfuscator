pub mod cfg_mutation;
pub mod class_dispatch;
pub mod crypto_cfg;
pub mod decrypt;
pub mod degradation;
pub mod exec_guard;
pub mod hpc;
pub mod hpc_detect;
pub mod hpc_key;
pub mod integrity;
pub mod jit;
pub mod ledger;
pub mod memguard;
pub mod oram;
pub mod platform;
pub mod port_entangle;
pub mod replay_poison;
pub mod rop;
pub mod rop_dispatch;
pub mod selfdestruct;
pub mod speculative;
pub mod state_isa;
pub mod sw_attestation;
#[cfg(feature = "sgx")]
pub mod tee_sgx;
pub mod tee;
pub mod timing;
pub mod transient;
pub mod cache_bound;
pub mod branch_entangle;
pub mod code_genome;
pub mod hw_entropy;
pub mod hydra;
pub mod hwid_bind;
pub use hydra::{HydraMesh, HydraTier};
pub mod multicore_entangle;
pub mod ssa_mutation;
pub mod per_exec_recompile;
pub mod self_healing;
pub mod struct_random;
pub mod simd_vm;
pub mod variant_pool;

fn derive_seed(base: &[u8; 32], ctx: &[u8]) -> [u8; 32] {
    let combined = [base.as_slice(), ctx].concat();
    ledger::sha256(&combined)
}

pub struct RuntimeConfig {
    pub enable_cfg_mutation: bool,
    pub enable_class_dispatch: bool,
    pub enable_state_isa: bool,
    pub enable_crypto_cfg: bool,
    pub enable_memguard: bool,
    pub enable_integrity: bool,
    pub enable_decrypt: bool,
    pub enable_selfdestruct: bool,
    pub enable_antidbg: bool,
    pub enable_timing_traps: bool,
    pub enable_degradation: bool,
    pub enable_exec_guard: bool,
    pub enable_ledger_check: bool,
    pub enable_hpc_entanglement: bool,
    pub enable_replay_poison: bool,
    pub enable_speculative_traps: bool,
    pub enable_oram: bool,
    pub enable_port_entangle: bool,
    pub enable_transient_exec: bool,
    pub enable_sw_attestation: bool,
    pub enable_ssa_mutation: bool,
    pub enable_per_exec_recompile: bool,
    pub enable_self_healing: bool,
    pub enable_struct_randomization: bool,
    pub cfg_mutation_seed: [u8; 32],
    pub cfg_mutation_variants: usize,
    pub ssa_mutation_seed: [u8; 32],
    pub ssa_mutation_variants: usize,
    pub class_dispatch_count: usize,
    pub state_isa_history_len: usize,
    pub oram_num_blocks: usize,
    pub scratch_buffer_size: usize,
    pub integrity_expected_crc: Option<u32>,
    pub ledger_proof: Option<ledger::IntegrityProof>,
    pub hpc_seed: u64,
    pub port_entangle_seed: u64,
    pub enable_variant_pool: bool,
    pub variant_pool_path: Option<String>,
    pub enable_tee: bool,
    pub tee_type: tee::TeeType,
    pub enclave_payload: Option<Vec<u8>>,
    pub enable_simd_vm: bool,
}

impl Default for RuntimeConfig {
    fn default() -> Self {
        Self {
            enable_cfg_mutation: false,
            enable_class_dispatch: false,
            enable_state_isa: false,
            enable_crypto_cfg: false,
            enable_memguard: true,
            enable_integrity: true,
            enable_decrypt: true,
            enable_selfdestruct: true,
            enable_antidbg: true,
            enable_timing_traps: false,
            enable_degradation: false,
            enable_exec_guard: false,
            enable_ledger_check: false,
            enable_hpc_entanglement: false,
            enable_replay_poison: false,
            enable_speculative_traps: false,
            enable_oram: false,
            enable_port_entangle: false,
            enable_transient_exec: false,
            enable_sw_attestation: false,
            enable_ssa_mutation: false,
            enable_per_exec_recompile: false,
            enable_self_healing: false,
            enable_struct_randomization: false,
            cfg_mutation_seed: [0u8; 32],
            cfg_mutation_variants: 4,
            ssa_mutation_seed: [0u8; 32],
            ssa_mutation_variants: 4,
            class_dispatch_count: 4,
            state_isa_history_len: 8,
            oram_num_blocks: 256,
            scratch_buffer_size: 4096,
            integrity_expected_crc: None,
            ledger_proof: None,
            hpc_seed: 0,
            port_entangle_seed: 0,
            enable_variant_pool: false,
            variant_pool_path: None,
            enable_tee: false,
            tee_type: tee::TeeType::None,
            enclave_payload: None,
            enable_simd_vm: false,
        }
    }
}

pub fn init_runtime(config: &RuntimeConfig) {
    if config.enable_selfdestruct {
        selfdestruct::arm_self_destruct();
    }
    if config.enable_integrity {
        if let Some(expected) = config.integrity_expected_crc {
            if !integrity::verify_text_section(expected) {
                selfdestruct::scrub_and_exit(1);
            }
        }
    }
    if config.enable_ledger_check {
        if let Some(ref proof) = config.ledger_proof {
            let text_section = match ledger::load_text_section() {
                Some(s) => s,
                None => {
                    selfdestruct::scrub_and_exit(1);
                }
            };
            if !ledger::full_integrity_check(&text_section, proof) {
                selfdestruct::scrub_and_exit(1);
            }
        }
    }
    if config.enable_timing_traps {
        if timing::check_timing_trap(1000) {
            if config.enable_degradation {
                let seed = derive_seed(&[0u8; 32], b"degradation");
                let mut engine = degradation::DegradationEngine::new(seed);
                engine.maybe_corrupt();
            }
        }
    }
    if config.enable_exec_guard {
        // Intentional abort-on-failure: without the guard pages the
        // process cannot meet its W^X invariant, so starting anyway
        // would silently run unprotected. expect() => panic => abort.
        let _guard = exec_guard::ExecGuard::new(config.scratch_buffer_size)
            .expect("ExecGuard::new failed in init_runtime");
    }
    if config.enable_replay_poison {
        let seed = derive_seed(&[0u8; 32], b"replay_poison");
        let mut engine = replay_poison::ReplayPoisonEngine::new(seed);
        let _ = engine.inject_entropy();
    }
    if config.enable_speculative_traps {
        unsafe {
            speculative::SPEC_POISON_BUF[0..8].copy_from_slice(&[0xFFu8; 8]);
            speculative::SPEC_STATE = 0xDEADBEEF_CAFEBABE;
            speculative::SPEC_SCRATCH = 0;
        }
    }
    if config.enable_port_entangle {
        let scheduler = port_entangle::ExecutionPortScheduler::new();
        let base_key = derive_seed(&[0u8; 32], b"port_entangle");
        let _derived = port_entangle::derive_key_from_timing(&base_key, config.port_entangle_seed);
        let _ = scheduler.port_config.alu_ports;
    }
    if config.enable_transient_exec {
        let _mgr = transient::TransientExecManager::new();
        transient::wipe_registry_on_exit();
    }
    if config.enable_cfg_mutation {
        let mut mutator = cfg_mutation::CfgMutator::new(config.cfg_mutation_seed);
        let orderings = cfg_mutation::generate_orderings(8, config.cfg_mutation_variants);
        mutator.register_variant("main", orderings);
        let _ = mutator.select_variant("main");
    }
    if config.enable_class_dispatch {
        let mut engine = class_dispatch::ClassDispatchEngine::new(config.class_dispatch_count, 42);
        // Register and dispatch a sample input to warm the cache
        let sample = b"init_input";
        let class_id = class_dispatch::ClassDispatchEngine::classify_input(sample) % config.class_dispatch_count as u32;
        let _ = engine.poly_jit_compile_class(class_id);
        eprintln!("class_dispatch: initialized engine with {} classes, cached {} variants",
                  config.class_dispatch_count, engine.cache_size());
    }
    if config.enable_state_isa {
        let mut table = state_isa::StateIsaTable::with_history_len(0, config.state_isa_history_len);
        // Execute a sample instruction sequence to demonstrate state-dependent mapping
        let mut state_hash = [0u8; 32];
        for step in 0u8..16 {
            state_hash = table.update_state(step);
            let mapped = table.lookup(step, &state_hash);
            core::hint::black_box(mapped);
        }
        eprintln!("state_isa: initialized with rotation={}, schedule_len={}, history_len={}",
                  table.current_rotation(), table.schedule.len(), config.state_isa_history_len);
        // Store the table seed for execution loop use
        let _state_rotation = table.current_rotation();
    }
    if config.enable_crypto_cfg {
        let seed = derive_seed(&[0u8; 32], b"crypto_cfg");
        let mut cfg_state = crypto_cfg::CfgStateChain::new(seed);
        let token = cfg_state.advance();
        let _ = token;
    }
    if config.enable_memguard {
        let size = config.scratch_buffer_size;
        // Intentional abort-on-failure: a zero-sized/over-aligned layout
        // is a caller bug, and continuing with a differently-sized locked
        // buffer would silently violate the memguard contract. expect()
        // => panic => abort. (The mlock failure just below is different:
        // resource-dependent, so it degrades gracefully instead.)
        let layout = std::alloc::Layout::from_size_align(size, 1)
            .expect("Invalid layout for memguard buffer");
        let ptr = unsafe { std::alloc::alloc_zeroed(layout) };
        if !ptr.is_null() {
            let locked = memguard::lock_memory(ptr, size);
            if !locked {
                unsafe { std::alloc::dealloc(ptr, layout) };
                eprintln!("memguard: mlock failed, continuing without");
            }
        }
    }
    if config.enable_decrypt {
        let key = decrypt::derive_block_key(&[0u8; 32], 0);
        let _ = derive_seed(&key, b"decrypt_sanity");
        let _ = key;
    }
    if config.enable_antidbg {
        #[cfg(target_os = "linux")]
        {
            let status = std::fs::read_to_string("/proc/self/status").unwrap_or_default();
            if status.contains("TracerPid:") && !status.contains("TracerPid:\t0") {
                eprintln!("antidbg: debugger detected via /proc/self/status");
                selfdestruct::scrub_and_exit(1);
            }
        }
        #[cfg(not(target_os = "linux"))]
        {
            let _ = config.enable_antidbg;
        }
    }
    if config.enable_hpc_entanglement {
        let base_key = [0u8; 32];
        let _ = hpc_key::derive_key_from_hpc(&base_key, config.hpc_seed);
    }
    if config.enable_sw_attestation {
        let engine = sw_attestation::AttestationEngine::new();
        engine.register_critical_region(
            &INTEGRITY_MAGIC as *const _ as *const u8,
            std::mem::size_of::<u64>(),
        );
        engine.start();
        eprintln!("sw_attestation: attestation engine started");
    }

    if config.enable_ssa_mutation {
        let mut mutator = ssa_mutation::SsaMutator::new(config.cfg_mutation_seed);
        let _phi_positions = ssa_mutation::generate_phi_positions(10, 4);
        let variants = ssa_mutation::SsaFunctionVariants {
            name: "ssa_main".to_string(),
            variants: (0..4).map(|v| {
                let mut instructions = Vec::new();
                for i in 0..8 {
                    let opcode = match (v + i) % 4 {
                        0 => "add",
                        1 => "mul",
                        2 => "sub",
                        3 => "phi",
                        _ => "nop",
                    };
                    instructions.push(ssa_mutation::SsaInstruction {
                        opcode: opcode.to_string(),
                        operands: vec![i as i64, (i + 1) as i64],
                        result: Some(100 + i as i64),
                    });
                }
                let phi_pos: Vec<usize> = instructions.iter().enumerate()
                    .filter(|(_, inst)| inst.opcode == "phi")
                    .map(|(i, _)| i)
                    .collect();
                ssa_mutation::SsaVariant {
                    instructions,
                    phi_positions: phi_pos,
                }
            }).collect(),
        };
        mutator.register_variants(variants);
        let _ = mutator.select_variant("ssa_main");
        eprintln!("ssa_mutation: initialized with {} variants", mutator.variant_count("ssa_main"));
    }

    if config.enable_per_exec_recompile {
        let mut recompiler = per_exec_recompile::PerExecRecompiler::new(
            u64::from_le_bytes(config.cfg_mutation_seed[0..8].try_into().unwrap())
        );
        recompiler.register_common_class("default_a", b"default_class_a");
        recompiler.register_common_class("default_b", b"default_class_b");
        let _ptr = recompiler.get_or_compile(b"init_input");
        eprintln!("per_exec_recompile: initialized with {} variants", recompiler.variant_count());
    }

    if config.enable_self_healing {
        let rt: &'static self_healing::SelfHealingRuntime =
            Box::leak(Box::new(self_healing::SelfHealingRuntime::new()));
        let magic_bytes = INTEGRITY_MAGIC.to_le_bytes();
        rt.register_critical_region("integrity_magic", &magic_bytes);
        rt.start_background_checking();
        eprintln!("self_healing: background checking started");
    }

    if config.enable_struct_randomization {
        let seed_bytes = derive_seed(&config.cfg_mutation_seed, b"struct_random");
        let seed = u64::from_le_bytes(seed_bytes[0..8].try_into().unwrap());
        let mut randomizer = struct_random::StructureRandomizer::new_with_seed_u64(seed, 8, 16);
        randomizer.randomize_all(32);
        eprintln!("struct_random: layout randomized (stack: 16 slots, regs: 8, heap: 32)");
    }

    if config.enable_variant_pool {
        let build_dir = config.variant_pool_path
            .as_ref()
            .map(|s| std::path::Path::new(s))
            .unwrap_or_else(|| std::path::Path::new("build"));
        if let Some(pool) = variant_pool::VariantPool::load(build_dir) {
            // Per-execution variant selection using time-based seed
            let exec_seed = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos() as u64)
                .unwrap_or(42);
            // Select a variant and switch to a different one each execution
            let selected = pool.select_variant(exec_seed);
            let prev_selected = pool.select_variant(exec_seed.wrapping_sub(1));
            if let Some(data) = pool.get_variant(selected) {
                eprintln!("variant_pool: selected variant {} ({} bytes, exec_seed={})", selected, data.len(), exec_seed);
            }
            if selected != prev_selected {
                eprintln!("variant_pool: variant switched from {} to {}", prev_selected, selected);
            }
        } else {
            eprintln!("variant_pool: no variant pool found, continuing without");
        }
    }

    if config.enable_simd_vm {
        let avail = simd_vm::SimdVm::is_simd_available();
        let opcodes = vec![0u8; 64];
        let mut vm = simd_vm::SimdVm::new(opcodes);
        let _ = vm.dispatch_scalar();
        eprintln!("simd_vm: initialized (SIMD hw avail: {})", avail);
    }

    if config.enable_tee {
        let mut tee_system = tee::TeePartition::new(config.tee_type);
        let payload: &[u8] = config.enclave_payload.as_deref().unwrap_or(&[]);
        if let Err(e) = tee_system.init_enclave(payload) {
            eprintln!("TEE init failed (fallback): {}", e);
        }
        if config.enable_sw_attestation {
            let measurement = tee_system.get_measurement();
            let engine = sw_attestation::AttestationEngine::new();
            engine.register_critical_region(&measurement as *const _ as *const u8, 32);
            engine.start();
            eprintln!("sw_attestation: TEE-integrated attestation engine started");
        }
    }
}

const INTEGRITY_MAGIC: u64 = 0xA11E571E7E6A1B1C;
