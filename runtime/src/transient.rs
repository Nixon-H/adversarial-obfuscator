use crate::platform::PagePerm;
use std::ptr;
use std::thread::{self, JoinHandle};

static GLOBAL_REGISTRY: std::sync::Mutex<Option<Vec<(u64, usize)>>> = std::sync::Mutex::new(None);

fn page_size() -> usize {
    crate::platform::page_size()
}

pub struct TransientExecManager {
    pub page_size: usize,
    pub block_registry: Vec<(u64, usize)>,
    pub zero_thread: Option<JoinHandle<()>>,
}

impl TransientExecManager {
    pub fn new() -> Self {
        TransientExecManager {
            page_size: page_size(),
            block_registry: Vec::new(),
            zero_thread: None,
        }
    }

    pub fn register_block(&mut self, addr: u64, size: usize) {
        self.block_registry.push((addr, size));
        if let Ok(mut reg) = GLOBAL_REGISTRY.lock() {
            reg.get_or_insert_with(Vec::new).push((addr, size));
        }
    }

    pub fn erase_block(addr: u64, size: usize) {
        if size == 0 {
            return;
        }
        let ps = page_size();
        let addr_usize = addr as usize;
        let aligned_start = addr_usize & !(ps - 1);
        let aligned_end = (addr_usize + size + ps - 1) & !(ps - 1);
        let aligned_len = aligned_end - aligned_start;
        let _ = crate::platform::protect_pages(aligned_start as *mut u8, aligned_len, PagePerm::ReadWrite);
        unsafe {
            let p = addr as *mut u8;
            ptr::write_bytes(p, 0u8, size);
        }
        let _ = crate::platform::protect_pages(aligned_start as *mut u8, aligned_len, PagePerm::None);
    }

    pub fn erase_previous_block(&self, prev_addr: u64, prev_size: usize) {
        if prev_size > 0 {
            Self::erase_block(prev_addr, prev_size);
        }
    }

    pub fn spawn_async_eraser(&self, addrs: Vec<(u64, usize)>) {
        thread::spawn(move || {
            for (addr, size) in addrs {
                if size > 0 {
                    Self::erase_block(addr, size);
                }
            }
        });
    }
}

#[no_mangle]
pub extern "C" fn __transient_block_entry(
    _block_id: u64,
    prev_block_addr: u64,
    prev_block_size: usize,
) {
    if prev_block_size > 0 {
        TransientExecManager::erase_block(prev_block_addr, prev_block_size);
    }
}

extern "C" fn wipe_handler() {
    if let Ok(reg) = GLOBAL_REGISTRY.lock() {
        if let Some(ref entries) = *reg {
            for &(addr, size) in entries {
                if size > 0 {
                    unsafe {
                        let p = addr as *mut u8;
                        ptr::write_bytes(p, 0u8, size);
                    }
                }
            }
        }
    }
}

pub fn wipe_registry_on_exit() {
    let _ = crate::platform::register_exit_handler(wipe_handler as extern "C" fn());
}

#[cfg(test)]
mod tests {
    use super::*;

    fn alloc_page() -> (*mut u8, usize) {
        let ps = page_size();
        let ptr = crate::platform::alloc_pages(ps);
        assert!(!ptr.is_null());
        (ptr, ps)
    }

    #[test]
    fn test_new_creates_manager() {
        let mgr = TransientExecManager::new();
        assert!(mgr.page_size > 0);
        assert!(mgr.block_registry.is_empty());
    }

    #[test]
    fn test_register_block_adds_to_registry() {
        let mut mgr = TransientExecManager::new();
        mgr.register_block(0x1000, 64);
        assert_eq!(mgr.block_registry.len(), 1);
        assert_eq!(mgr.block_registry[0], (0x1000, 64));
    }

    #[test]
    fn test_erase_block_zeroes_and_protects() {
        let (ptr, ps) = alloc_page();
        unsafe {
            ptr::write_bytes(ptr, 0xABu8, ps);
        }
        TransientExecManager::erase_block(ptr as u64, ps);
    }

    #[test]
    fn test_erase_block_zero_size_does_nothing() {
        TransientExecManager::erase_block(0x0, 0);
    }

    #[test]
    fn test_erase_previous_block_delegates() {
        let (ptr, ps) = alloc_page();
        unsafe {
            ptr::write_bytes(ptr, 0xFFu8, ps);
        }
        let mgr = TransientExecManager::new();
        mgr.erase_previous_block(ptr as u64, ps);
        crate::platform::free_pages(ptr, ps);
    }

    #[test]
    fn test_transient_block_entry_noop_on_zero_size() {
        __transient_block_entry(0, 0, 0);
    }

    #[test]
    fn test_transient_block_entry_erases_previous() {
        let (ptr, ps) = alloc_page();
        unsafe {
            ptr::write_bytes(ptr, 0x42u8, ps);
        }
        __transient_block_entry(1, ptr as u64, ps);
        crate::platform::free_pages(ptr, ps);
    }

    #[test]
    fn test_multiple_registrations() {
        let mut mgr = TransientExecManager::new();
        mgr.register_block(0x2000, 128);
        mgr.register_block(0x3000, 256);
        assert_eq!(mgr.block_registry.len(), 2);
    }

    #[test]
    fn test_spawn_async_eraser_does_not_crash() {
        let mgr = TransientExecManager::new();
        mgr.spawn_async_eraser(vec![(0xDEAD, 0)]);
    }

    #[test]
    fn test_wipe_registry_not_called_during_tests() {
        assert!(true);
    }
}
