#[allow(static_mut_refs)]
pub static mut SPEC_POISON_BUF: [u8; 4096] = [0u8; 4096];

#[allow(static_mut_refs)]
pub static mut SPEC_STATE: u64 = 0;

#[allow(static_mut_refs)]
pub static mut SPEC_SCRATCH: u64 = 0;

#[cfg(test)]
#[allow(static_mut_refs)]
mod tests {
    use super::*;

    #[test]
    fn test_spec_poison_buf_size() {
        unsafe {
            assert_eq!(SPEC_POISON_BUF.len(), 4096);
        }
    }

    #[test]
    fn test_spec_state_initialized() {
        unsafe {
            assert_eq!(SPEC_STATE, 0);
        }
    }

    #[test]
    fn test_spec_scratch_initialized() {
        unsafe {
            assert_eq!(SPEC_SCRATCH, 0);
        }
    }

    #[test]
    fn test_spec_poison_buf_mutable() {
        unsafe {
            SPEC_POISON_BUF[0] = 0xAB;
            assert_eq!(SPEC_POISON_BUF[0], 0xAB);
            SPEC_POISON_BUF[0] = 0;
        }
    }

    #[test]
    fn test_spec_state_mutable() {
        unsafe {
            SPEC_STATE = 0xDEADBEEF;
            assert_eq!(SPEC_STATE, 0xDEADBEEF);
            SPEC_STATE = 0;
        }
    }

    #[test]
    fn test_spec_scratch_mutable() {
        unsafe {
            SPEC_SCRATCH = 0xCAFEBABE;
            assert_eq!(SPEC_SCRATCH, 0xCAFEBABE);
            SPEC_SCRATCH = 0;
        }
    }
}
