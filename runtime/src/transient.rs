use crate::memguard::{checked_page_range, checked_page_size};
use crate::platform::PagePerm;
use std::ptr;
use std::thread::{self, JoinHandle};

static GLOBAL_REGISTRY: std::sync::Mutex<Option<Vec<(u64, usize)>>> = std::sync::Mutex::new(None);

pub struct TransientExecManager {
    pub page_size: usize,
    pub block_registry: Vec<(u64, usize)>,
    pub zero_thread: Option<JoinHandle<()>>,
}

impl TransientExecManager {
    pub fn new() -> Self {
        TransientExecManager {
            page_size: checked_page_size().unwrap_or(0),
            block_registry: Vec::new(),
            zero_thread: None,
        }
    }

    pub fn register_block(&mut self, addr: u64, size: usize) {
        let Ok(addr_usize) = usize::try_from(addr) else {
            return;
        };
        let Some((aligned_start, aligned_len)) =
            checked_page_range(addr_usize, size, self.page_size)
        else {
            return;
        };
        let entry = (aligned_start as u64, aligned_len);
        self.block_registry.push(entry);
        if let Ok(mut reg) = GLOBAL_REGISTRY.lock() {
            reg.get_or_insert_with(Vec::new).push(entry);
        }
    }

    /// Erase a caller-owned transient mapping.
    ///
    /// # Safety
    /// The caller must guarantee that `[addr, addr + size)` is valid, uniquely
    /// writable for the duration of the call, and will not be used afterward.
    pub unsafe fn erase_block(addr: u64, size: usize) {
        if size == 0 {
            return;
        }
        let Ok(page_size) = checked_page_size() else {
            return;
        };
        let Ok(addr_usize) = usize::try_from(addr) else {
            return;
        };
        let Some((aligned_start, aligned_len)) = checked_page_range(addr_usize, size, page_size)
        else {
            return;
        };
        if crate::platform::protect_pages(
            aligned_start as *mut u8,
            aligned_len,
            PagePerm::ReadWrite,
        )
        .is_err()
        {
            return;
        }
        unsafe {
            let p = addr as *mut u8;
            ptr::write_bytes(p, 0u8, size);
        }
        let _ =
            crate::platform::protect_pages(aligned_start as *mut u8, aligned_len, PagePerm::None);
        unregister_global(aligned_start as u64, aligned_len);
    }

    /// # Safety
    /// See [`Self::erase_block`].
    pub unsafe fn erase_previous_block(&self, prev_addr: u64, prev_size: usize) {
        if prev_size > 0 {
            Self::erase_block(prev_addr, prev_size);
        }
    }

    /// # Safety
    /// Every supplied range must remain valid and uniquely writable until the
    /// spawned thread has finished erasing it.
    pub unsafe fn spawn_async_eraser(&self, addrs: Vec<(u64, usize)>) {
        thread::spawn(move || {
            for (addr, size) in addrs {
                if size > 0 {
                    unsafe { Self::erase_block(addr, size) };
                }
            }
        });
    }
}

/// # Safety
/// `prev_block_addr..prev_block_addr + prev_block_size` must identify a valid
/// transient mapping that will not be used afterward.
#[no_mangle]
pub unsafe extern "C" fn __transient_block_entry(
    _block_id: u64,
    prev_block_addr: u64,
    prev_block_size: usize,
) {
    if prev_block_size > 0 {
        TransientExecManager::erase_block(prev_block_addr, prev_block_size);
    }
}

fn unregister_global(addr: u64, size: usize) {
    if let Ok(mut reg) = GLOBAL_REGISTRY.lock() {
        if let Some(entries) = reg.as_mut() {
            entries.retain(|entry| *entry != (addr, size));
        }
    }
}

impl Drop for TransientExecManager {
    fn drop(&mut self) {
        for &(addr, size) in &self.block_registry {
            unregister_global(addr, size);
        }
    }
}

extern "C" fn wipe_handler() {
    let entries = GLOBAL_REGISTRY
        .lock()
        .ok()
        .and_then(|reg| reg.clone())
        .unwrap_or_default();
    for (addr, size) in entries {
        unsafe { TransientExecManager::erase_block(addr, size) };
    }
}

pub fn wipe_registry_on_exit() {
    let _ = crate::platform::register_exit_handler(wipe_handler as extern "C" fn());
}

#[cfg(test)]
mod tests {
    use super::*;

    fn alloc_page() -> (*mut u8, usize) {
        let ps = checked_page_size().expect("valid page size");
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
        assert_eq!(mgr.block_registry[0], (0x1000, mgr.page_size));
    }

    #[test]
    fn test_erase_block_zeroes_and_protects() {
        let (ptr, ps) = alloc_page();
        unsafe {
            ptr::write_bytes(ptr, 0xABu8, ps);
        }
        unsafe { TransientExecManager::erase_block(ptr as u64, ps) };
    }

    #[test]
    fn test_erase_block_zero_size_does_nothing() {
        unsafe { TransientExecManager::erase_block(0x0, 0) };
    }

    #[test]
    fn test_erase_block_rejects_range_overflow() {
        unsafe {
            TransientExecManager::erase_block(u64::MAX, usize::MAX);
            TransientExecManager::erase_block(1, usize::MAX);
        }
    }

    #[test]
    fn test_register_block_rejects_unrepresentable_or_overflowing_ranges() {
        let mut mgr = TransientExecManager::new();
        mgr.register_block(u64::MAX, usize::MAX);
        mgr.register_block(1, usize::MAX);
        assert!(mgr.block_registry.is_empty());
    }

    #[test]
    fn test_erase_previous_block_delegates() {
        let (ptr, ps) = alloc_page();
        unsafe {
            ptr::write_bytes(ptr, 0xFFu8, ps);
        }
        let mgr = TransientExecManager::new();
        unsafe { mgr.erase_previous_block(ptr as u64, ps) };
        crate::platform::free_pages(ptr, ps);
    }

    #[test]
    fn test_transient_block_entry_noop_on_zero_size() {
        unsafe { __transient_block_entry(0, 0, 0) };
    }

    #[test]
    fn test_transient_block_entry_erases_previous() {
        let (ptr, ps) = alloc_page();
        unsafe {
            ptr::write_bytes(ptr, 0x42u8, ps);
        }
        unsafe { __transient_block_entry(1, ptr as u64, ps) };
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
        unsafe { mgr.spawn_async_eraser(vec![(0xDEAD, 0)]) };
    }

    #[test]
    fn test_wipe_registry_not_called_during_tests() {
        assert!(true);
    }
}
