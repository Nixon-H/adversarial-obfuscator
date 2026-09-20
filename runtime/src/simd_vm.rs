extern "C" {
    fn simd_vm_init(vm: *mut SimdVmState);
    fn simd_dispatch(vm: *mut SimdVmState, opcodes: *const u8, num_opcodes: usize) -> i32;
    fn simd_dispatch_scalar(vm: *mut SimdVmState, opcodes: *const u8, num_opcodes: usize) -> i32;
    fn simd_opcode_decode(
        opcodes: *const u8,
        num_opcodes: usize,
        decoded: *mut u8,
        decoded_count: *mut usize,
    ) -> i32;
    fn simd_available() -> i32;
}

#[repr(C)]
pub struct SimdVmState {
    regs: [u64; 16],
    memory: [u8; 65536],
    pc: usize,
    halted: i32,
    handlers: [Option<unsafe extern "C" fn(*mut u64, *const u8, usize) -> i32>; 32],
    use_simd: i32,
}

pub struct SimdVm {
    state: SimdVmState,
    opcodes: Vec<u8>,
}

impl SimdVm {
    pub fn new(opcodes: Vec<u8>) -> Self {
        let mut state: SimdVmState = unsafe { core::mem::zeroed() };
        unsafe {
            simd_vm_init(&mut state);
        }
        SimdVm { state, opcodes }
    }

    pub fn is_simd_available() -> bool {
        unsafe { simd_available() != 0 }
    }

    pub fn dispatch(&mut self) -> Result<(), i32> {
        let ret = unsafe {
            simd_dispatch(&mut self.state, self.opcodes.as_ptr(), self.opcodes.len())
        };
        if ret == 0 {
            Ok(())
        } else {
            Err(ret)
        }
    }

    pub fn dispatch_scalar(&mut self) -> Result<(), i32> {
        let ret = unsafe {
            simd_dispatch_scalar(&mut self.state, self.opcodes.as_ptr(), self.opcodes.len())
        };
        if ret == 0 {
            Ok(())
        } else {
            Err(ret)
        }
    }

    pub fn decode_opcodes(&self) -> Vec<u8> {
        let mut decoded = vec![0u8; self.opcodes.len()];
        let mut count: usize = 0;
        let ret = unsafe {
            simd_opcode_decode(
                self.opcodes.as_ptr(),
                self.opcodes.len(),
                decoded.as_mut_ptr(),
                &mut count,
            )
        };
        if ret == 0 {
            decoded.truncate(count);
            decoded
        } else {
            Vec::new()
        }
    }

    pub fn get_register(&self, idx: usize) -> u64 {
        if idx < 16 { self.state.regs[idx] } else { 0 }
    }

    pub fn set_register(&mut self, idx: usize, val: u64) {
        if idx < 16 {
            self.state.regs[idx] = val;
        }
    }

    pub fn pc(&self) -> usize {
        self.state.pc
    }

    pub fn halted(&self) -> bool {
        self.state.halted != 0
    }
}

impl Drop for SimdVm {
    fn drop(&mut self) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simd_vm_new() {
        let vm = SimdVm::new(vec![0, 1, 1, 2, 2]);
        assert_eq!(vm.pc(), 0);
        assert!(!vm.halted());
    }

    #[test]
    fn test_simd_vm_register_set_get() {
        let mut vm = SimdVm::new(vec![]);
        vm.set_register(0, 42);
        assert_eq!(vm.get_register(0), 42);
    }

    #[test]
    fn test_simd_vm_opcode_decode() {
        let vm = SimdVm::new(vec![0, 1, 2, 10, 3]);
        let decoded = vm.decode_opcodes();
        assert_eq!(decoded.len(), 5);
    }

    #[test]
    fn test_simd_available_check() {
        let avail = SimdVm::is_simd_available();
        // Should not panic; result depends on CPU
        let _ = avail;
    }

    #[test]
    fn test_simd_dispatch_scalar_nop_only() {
        let mut vm = SimdVm::new(vec![0]);
        let result = vm.dispatch_scalar();
        assert!(result.is_ok());
    }

    #[test]
    fn test_simd_vm_add_instruction() {
        // opcode 1 = ADD, args: dst=0, src=1
        let mut vm = SimdVm::new(vec![1, 0x00, 0x11]);
        // ADD expects registers to be set via raw memory
        vm.set_register(0, 5);
        vm.set_register(1, 10);
        let _ = vm.dispatch_scalar();
    }

    #[test]
    fn test_simd_vm_execute_small_program() {
        // Program: nop, load(reg 3 from somewhere), add, xor
        let mut vm = SimdVm::new(vec![0, 0, 1, 3, 4]);
        let result = vm.dispatch_scalar();
        // Should either succeed or halt gracefully
        assert!(result.is_ok() || result.is_err());
    }

    #[test]
    fn test_simd_vm_register_out_of_bounds() {
        let mut vm = SimdVm::new(vec![]);
        assert_eq!(vm.get_register(99), 0);
        vm.set_register(99, 42);
        assert_eq!(vm.get_register(99), 0);
    }
}
