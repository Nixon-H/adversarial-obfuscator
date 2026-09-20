use crate::platform::PagePerm;
use std::ptr;

pub fn scrub_memory(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }
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
    let ps = crate::platform::page_size();
    let aligned_addr = (ptr as usize) & !(ps - 1);
    let aligned_len = len + (ptr as usize - aligned_addr);
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
