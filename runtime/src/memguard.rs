use crate::platform::PagePerm;
use std::ptr;

/// Validate the OS page size before using mask-based alignment arithmetic.
pub(crate) fn checked_page_size() -> Result<usize, String> {
    let size = crate::platform::page_size();
    if size == 0 || !size.is_power_of_two() {
        return Err("invalid OS page size".to_string());
    }
    Ok(size)
}

/// Round `size` up to a whole number of pages without wrapping.
pub(crate) fn round_up_to_page(size: usize, page_size: usize) -> Option<usize> {
    if page_size == 0 || !page_size.is_power_of_two() {
        return None;
    }
    size.checked_add(page_size - 1)
        .map(|end| end & !(page_size - 1))
}

/// Validate a half-open address range without overflowing its exclusive end.
pub(crate) fn checked_range_end(base: usize, len: usize) -> Option<usize> {
    if len == 0 {
        return None;
    }
    base.checked_add(len)
}

/// Return the page-aligned base and length covering `[addr, addr + len)`.
pub(crate) fn checked_page_range(
    addr: usize,
    len: usize,
    page_size: usize,
) -> Option<(usize, usize)> {
    if len == 0 || page_size == 0 || !page_size.is_power_of_two() {
        return None;
    }
    let start = addr & !(page_size - 1);
    let end = checked_range_end(addr, len)?;
    let aligned_end = round_up_to_page(end, page_size)?;
    let aligned_len = aligned_end.checked_sub(start)?;
    Some((start, aligned_len))
}

/// Scrub a local mutable buffer when its scope exits, including error paths.
///
/// Construction is unsafe because the caller must guarantee that `ptr..ptr+len`
/// remains valid and uniquely writable until the guard is dropped.
pub(crate) struct ScrubOnDrop {
    ptr: *mut u8,
    len: usize,
}

impl ScrubOnDrop {
    pub(crate) unsafe fn new(ptr: *mut u8, len: usize) -> Self {
        Self { ptr, len }
    }
}

impl Drop for ScrubOnDrop {
    fn drop(&mut self) {
        scrub_memory(self.ptr, self.len);
    }
}

pub fn scrub_memory(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }
    let ptr = std::hint::black_box(ptr);
    unsafe {
        ptr::write_bytes(ptr, 0u8, len);
    }
}

pub fn scrub_slice(buf: &mut [u8]) {
    if buf.is_empty() {
        return;
    }
    scrub_memory(buf.as_mut_ptr(), buf.len());
}

pub fn protect_region(ptr: *mut u8, len: usize, perm: PagePerm) -> bool {
    if ptr.is_null() || len == 0 {
        return false;
    }
    let Ok(page_size) = checked_page_size() else {
        return false;
    };
    let Some((aligned_addr, aligned_len)) = checked_page_range(ptr as usize, len, page_size) else {
        return false;
    };
    crate::platform::protect_pages(aligned_addr as *mut u8, aligned_len, perm).is_ok()
}

pub fn lock_memory(ptr: *mut u8, len: usize) -> bool {
    if ptr.is_null() || len == 0 {
        return false;
    }
    crate::platform::lock_pages(ptr as *const u8, len).is_ok()
}

pub fn unlock_memory(ptr: *mut u8, len: usize) -> bool {
    if ptr.is_null() || len == 0 {
        return false;
    }
    crate::platform::unlock_pages(ptr as *const u8, len).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn checked_rounding_rejects_invalid_page_sizes_and_overflow() {
        assert_eq!(round_up_to_page(1, 4096), Some(4096));
        assert_eq!(round_up_to_page(4096, 4096), Some(4096));
        assert_eq!(round_up_to_page(4097, 4096), Some(8192));
        assert_eq!(round_up_to_page(1, 0), None);
        assert_eq!(round_up_to_page(1, 3), None);
        assert_eq!(round_up_to_page(usize::MAX, 4096), None);
    }

    #[test]
    fn checked_page_range_rejects_wraparound() {
        assert_eq!(
            checked_page_range(0x1001, 0x2000, 4096),
            Some((0x1000, 0x3000))
        );
        assert_eq!(checked_page_range(usize::MAX, 2, 4096), None);
        assert_eq!(checked_page_range(0, 0, 4096), None);
        assert_eq!(checked_page_range(0, 1, 0), None);
    }

    #[test]
    fn protect_region_rejects_overflow_without_panic() {
        assert!(!protect_region(
            usize::MAX as *mut u8,
            2,
            PagePerm::ReadWrite
        ));
        assert!(!protect_region(
            1usize as *mut u8,
            usize::MAX,
            PagePerm::ReadWrite
        ));
    }

    #[test]
    fn scrub_guard_runs_on_error_return() {
        fn fail(secret: &mut [u8]) -> Result<(), ()> {
            let _guard = unsafe { ScrubOnDrop::new(secret.as_mut_ptr(), secret.len()) };
            Err(())
        }

        let mut secret = [0xA5u8; 32];
        assert!(fail(&mut secret).is_err());
        assert_eq!(secret, [0u8; 32]);
    }
}
