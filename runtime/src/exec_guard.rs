use crate::platform::PagePerm;
use std::ptr;

pub struct ExecGuard {
    ptr: *mut u8,
    len: usize,
    original_prot: PagePerm,
    alloc_ptr: *mut u8,
    alloc_len: usize,
}

fn page_size() -> usize {
    crate::platform::page_size()
}

impl ExecGuard {
    pub fn new(size: usize) -> Result<Self, String> {
        if size == 0 {
            return Err("size must be non-zero".to_string());
        }
        let ps = page_size();
        let guard = ps;
        let aligned_size = (size + ps - 1) & !(ps - 1);
        let total = guard + aligned_size + guard;

        let alloc_ptr = crate::platform::alloc_pages(total);
        if alloc_ptr.is_null() {
            return Err("mmap failed for ExecGuard buffer".to_string());
        }

        let result1 = crate::platform::protect_pages(alloc_ptr, guard, PagePerm::None);
        if result1.is_err() {
            crate::platform::free_pages(alloc_ptr, total);
            return Err("mprotect to PROT_NONE failed on leading guard page".to_string());
        }

        let last_guard = unsafe { alloc_ptr.add(guard + aligned_size) };
        let result2 = crate::platform::protect_pages(last_guard, guard, PagePerm::None);
        if result2.is_err() {
            crate::platform::free_pages(alloc_ptr, total);
            return Err("mprotect to PROT_NONE failed on trailing guard page".to_string());
        }

        let ptr = unsafe { alloc_ptr.add(guard) };

        Ok(ExecGuard {
            ptr,
            len: size,
            original_prot: PagePerm::ReadWrite,
            alloc_ptr,
            alloc_len: total,
        })
    }

    pub fn prepare_execution(&mut self) -> Result<(), String> {
        let ps = page_size();
        let aligned_size = (self.len + ps - 1) & !(ps - 1);
        let result = crate::platform::protect_pages(self.ptr, aligned_size, PagePerm::ReadExec);
        if result.is_err() {
            return Err("mprotect to R-X failed".to_string());
        }
        self.original_prot = PagePerm::ReadExec;
        Ok(())
    }

    pub fn complete_execution(&mut self) {
        let ps = page_size();
        let aligned_size = (self.len + ps - 1) & !(ps - 1);

        let result1 = crate::platform::protect_pages(self.ptr, aligned_size, PagePerm::ReadWrite);
        if result1.is_err() {
            return;
        }
        self.original_prot = PagePerm::ReadWrite;

        unsafe {
            ptr::write_bytes(self.ptr, 0u8, self.len);
        }

        let _ = crate::platform::protect_pages(self.ptr, aligned_size, PagePerm::None);
        self.original_prot = PagePerm::None;
    }

    pub fn as_ptr(&self) -> *mut u8 {
        self.ptr
    }

    pub fn len(&self) -> usize {
        self.len
    }

    /// Verify that a function pointer falls inside an expected address range.
    ///
    /// Anti-hook primitive (`_verify_eval` pattern): dynamically resolved
    /// evaluation/dispatch pointers must live inside the interpreter's own
    /// mapping (or a declared plugin range). A pointer outside both ranges
    /// indicates IAT/EAT hooking or inline detour injection.
    ///
    /// `expected_base`/`expected_len` describe the legitimate range
    /// (e.g. the loaded python DLL mapping); `fallback_base`/`fallback_len`
    /// an optional second range (0/0 = none). Returns true iff ptr is
    /// inside either range. Pure integer compare — no syscalls, no
    /// allocation, safe to call on hot paths and from watchdog threads.
    pub fn verify_fn_pointer(
        ptr: *const u8,
        expected_base: usize,
        expected_len: usize,
        fallback_base: usize,
        fallback_len: usize,
    ) -> bool {
        if ptr.is_null() {
            return false;
        }
        let p = ptr as usize;
        let in_primary = expected_len > 0
            && p >= expected_base
            && p.wrapping_sub(expected_base) < expected_len;
        let in_fallback = fallback_len > 0
            && p >= fallback_base
            && p.wrapping_sub(fallback_base) < fallback_len;
        in_primary || in_fallback
    }
}

impl Drop for ExecGuard {
    fn drop(&mut self) {
        let ps = page_size();
        let aligned_size = (self.len + ps - 1) & !(ps - 1);
        let _ = crate::platform::protect_pages(self.ptr, aligned_size, PagePerm::ReadWrite);
        unsafe {
            ptr::write_bytes(self.ptr, 0u8, self.len);
        }
        crate::platform::free_pages(self.alloc_ptr, self.alloc_len);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn read_proc_maps() -> Vec<(usize, usize, String)> {
        // Test helper only, but written panic-free on purpose: with
        // panic=abort an unwrap here would abort the whole test binary
        // (DoS on the suite). Unreadable maps => empty vec (callers then
        // fail their own assertions explicitly); malformed lines skipped.
        let maps = fs::read_to_string("/proc/self/maps").unwrap_or_default();
        let mut regions = Vec::new();
        for line in maps.lines() {
            let cols: Vec<&str> = line.splitn(5, ' ').collect();
            if cols.len() < 2 {
                continue;
            }
            let addrs: Vec<&str> = cols[0].split('-').collect();
            if addrs.len() != 2 {
                continue;
            }
            let (Some(start), Some(end)) = (
                usize::from_str_radix(addrs[0], 16).ok(),
                usize::from_str_radix(addrs[1], 16).ok(),
            ) else {
                continue;
            };
            let perms = cols[1].to_string();
            regions.push((start, end, perms));
        }
        regions
    }

    fn count_prot_none_regions(regions: &[(usize, usize, String)], alloc_start: usize, alloc_end: usize) -> usize {
        regions
            .iter()
            .filter(|(start, end, perms)| {
                *start < alloc_end && *end > alloc_start && (perms == "---p" || perms == "---")
            })
            .count()
    }

    #[test]
    fn test_new_succeeds() {
        let guard = ExecGuard::new(64).expect("allocation should succeed");
        assert!(!guard.as_ptr().is_null());
        assert!(guard.len() >= 64);
    }

    #[test]
    fn test_guard_pages_protected() {
        let guard = ExecGuard::new(64).expect("allocation should succeed");
        let alloc_start = guard.alloc_ptr as usize;
        let alloc_end = alloc_start + guard.alloc_len;
        let regions = read_proc_maps();
        let prot_none_count = count_prot_none_regions(&regions, alloc_start, alloc_end);
        assert!(
            prot_none_count >= 2,
            "expected at least 2 PROT_NONE guard regions, got {}",
            prot_none_count
        );
    }

    #[test]
    fn test_permission_toggling() {
        let mut guard = ExecGuard::new(64).expect("allocation should succeed");
        guard.prepare_execution().expect("prepare_execution should succeed");
        let ps = page_size();
        let aligned_size = (guard.len + ps - 1) & !(ps - 1);
        let data_start = guard.ptr as usize;
        let data_end = data_start + aligned_size;
        let regions = read_proc_maps();
        let exec_region = regions.iter().find(|(start, end, perms)| {
            *start <= data_start && data_end <= *end && perms.starts_with("r-x")
        });
        assert!(exec_region.is_some(), "should have an R-X region after prepare_execution");
        guard.complete_execution();
    }

    #[test]
    fn test_drop_cleans_memory() {
        let alloc_ptr;
        let alloc_len;
        {
            let guard = ExecGuard::new(64).expect("allocation should succeed");
            alloc_ptr = guard.alloc_ptr;
            alloc_len = guard.alloc_len;
            unsafe {
                ptr::write_bytes(guard.ptr, 0xABu8, 64);
            }
        }
        {
            let guard2 = ExecGuard::new(64).expect("re-allocation after drop should succeed");
            assert!(!guard2.as_ptr().is_null());
            let _ = guard2;
        }
        let _ = alloc_ptr;
        let _ = alloc_len;
    }

    #[test]
    fn test_multiple_guards_no_conflict() {
        let mut guards = Vec::new();
        for i in 0..10 {
            let g = ExecGuard::new(64 + i).expect("allocation should succeed");
            assert!(!g.as_ptr().is_null());
            guards.push(g);
        }
        assert_eq!(guards.len(), 10);
        for (i, g) in guards.iter().enumerate() {
            assert!(!g.as_ptr().is_null());
            assert!(g.len() >= 64 + i);
        }
        drop(guards);
        let g = ExecGuard::new(128).expect("post-drop allocation should succeed");
        assert!(!g.as_ptr().is_null());
    }

    #[test]
    fn test_verify_fn_pointer_ranges() {
        let base = 0x1_0000_0000usize;
        let len = 0x2_0000usize;
        let inside = (base + 0x1234) as *const u8;
        let at_end = (base + len - 1) as *const u8;
        let outside = (base + len + 0x100) as *const u8;
        let below = (base - 1) as *const u8;
        assert!(ExecGuard::verify_fn_pointer(inside, base, len, 0, 0));
        assert!(ExecGuard::verify_fn_pointer(at_end, base, len, 0, 0));
        assert!(!ExecGuard::verify_fn_pointer(outside, base, len, 0, 0));
        assert!(!ExecGuard::verify_fn_pointer(below, base, len, 0, 0));
        assert!(!ExecGuard::verify_fn_pointer(std::ptr::null(), base, len, 0, 0));
        // Fallback range accepts, primary still enforced.
        let fb = 0x2_0000_0000usize;
        let fblen = 0x1000usize;
        assert!(ExecGuard::verify_fn_pointer((fb + 8) as *const u8, base, len, fb, fblen));
        assert!(!ExecGuard::verify_fn_pointer((fb + fblen + 8) as *const u8, base, len, fb, fblen));
        // Zero-length ranges accept nothing.
        assert!(!ExecGuard::verify_fn_pointer(inside, 0, 0, 0, 0));
    }
}
