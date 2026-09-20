use std::ptr;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PagePerm {
    None,
    Read,
    ReadWrite,
    ReadExec,
    ReadWriteExec,
}

#[cfg(windows)]
extern "system" {
    fn GetSystemInfo(lpSystemInfo: *mut SYSTEM_INFO);
    fn VirtualAlloc(
        lpAddress: *mut std::ffi::c_void,
        dwSize: usize,
        flAllocationType: u32,
        flProtect: u32,
    ) -> *mut std::ffi::c_void;
    fn VirtualFree(
        lpAddress: *mut std::ffi::c_void,
        dwSize: usize,
        dwFreeType: u32,
    ) -> i32;
    fn VirtualProtect(
        lpAddress: *mut std::ffi::c_void,
        dwSize: usize,
        flNewProtect: u32,
        lpflOldProtect: *mut u32,
    ) -> i32;
    fn VirtualLock(
        lpAddress: *mut std::ffi::c_void,
        dwSize: usize,
    ) -> i32;
    fn VirtualUnlock(
        lpAddress: *mut std::ffi::c_void,
        dwSize: usize,
    ) -> i32;
}

#[cfg(windows)]
extern "C" {
    fn atexit(func: extern "C" fn()) -> i32;
}

#[cfg(windows)]
#[repr(C)]
#[allow(non_snake_case)]
struct SYSTEM_INFO {
    _dwOemId: u32,
    dwPageSize: u32,
    lpMinimumApplicationAddress: *mut std::ffi::c_void,
    lpMaximumApplicationAddress: *mut std::ffi::c_void,
    dwActiveProcessorMask: usize,
    dwNumberOfProcessors: u32,
    dwProcessorType: u32,
    dwAllocationGranularity: u32,
    wProcessorLevel: u16,
    wProcessorRevision: u16,
}

#[cfg(windows)]
const PAGE_NOACCESS: u32 = 0x01;
#[cfg(windows)]
const PAGE_READONLY: u32 = 0x02;
#[cfg(windows)]
const PAGE_READWRITE: u32 = 0x04;
#[cfg(windows)]
const PAGE_EXECUTE_READ: u32 = 0x20;
#[cfg(windows)]
const PAGE_EXECUTE_READWRITE: u32 = 0x40;
#[cfg(windows)]
const MEM_COMMIT: u32 = 0x1000;
#[cfg(windows)]
const MEM_RESERVE: u32 = 0x2000;
#[cfg(windows)]
const MEM_RELEASE: u32 = 0x8000;

#[cfg(unix)]
fn prot_to_unix(perm: PagePerm) -> i32 {
    match perm {
        PagePerm::None => libc::PROT_NONE,
        PagePerm::Read => libc::PROT_READ,
        PagePerm::ReadWrite => libc::PROT_READ | libc::PROT_WRITE,
        PagePerm::ReadExec => libc::PROT_READ | libc::PROT_EXEC,
        PagePerm::ReadWriteExec => libc::PROT_READ | libc::PROT_WRITE | libc::PROT_EXEC,
    }
}

#[cfg(windows)]
fn prot_to_win(perm: PagePerm) -> u32 {
    match perm {
        PagePerm::None => PAGE_NOACCESS,
        PagePerm::Read => PAGE_READONLY,
        PagePerm::ReadWrite => PAGE_READWRITE,
        PagePerm::ReadExec => PAGE_EXECUTE_READ,
        PagePerm::ReadWriteExec => PAGE_EXECUTE_READWRITE,
    }
}

pub fn page_size() -> usize {
    #[cfg(unix)]
    unsafe {
        libc::sysconf(libc::_SC_PAGESIZE) as usize
    }
    #[cfg(windows)]
    unsafe {
        let mut info = std::mem::MaybeUninit::<SYSTEM_INFO>::uninit();
        GetSystemInfo(info.as_mut_ptr());
        info.assume_init().dwPageSize as usize
    }
}

pub fn alloc_pages(size: usize) -> *mut u8 {
    #[cfg(unix)]
    unsafe {
        let ptr = libc::mmap(
            ptr::null_mut(),
            size,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_PRIVATE | libc::MAP_ANONYMOUS,
            -1,
            0,
        );
        if ptr == libc::MAP_FAILED {
            ptr::null_mut()
        } else {
            ptr as *mut u8
        }
    }
    #[cfg(windows)]
    unsafe {
        let ptr = VirtualAlloc(
            ptr::null_mut(),
            size,
            MEM_RESERVE | MEM_COMMIT,
            PAGE_READWRITE,
        );
        ptr as *mut u8
    }
}

pub fn free_pages(ptr: *mut u8, _size: usize) {
    if ptr.is_null() {
        return;
    }
    #[cfg(unix)]
    unsafe {
        libc::munmap(ptr as *mut libc::c_void, _size);
    }
    #[cfg(windows)]
    unsafe {
        VirtualFree(ptr as *mut std::ffi::c_void, 0, MEM_RELEASE);
    }
}

pub fn protect_pages(ptr: *mut u8, size: usize, perm: PagePerm) -> Result<(), ()> {
    if ptr.is_null() || size == 0 {
        return Err(());
    }
    #[cfg(unix)]
    unsafe {
        let ret = libc::mprotect(ptr as *mut libc::c_void, size, prot_to_unix(perm));
        if ret == 0 { Ok(()) } else { Err(()) }
    }
    #[cfg(windows)]
    unsafe {
        let mut old = 0u32;
        let ret = VirtualProtect(
            ptr as *mut std::ffi::c_void,
            size,
            prot_to_win(perm),
            &mut old,
        );
        if ret != 0 { Ok(()) } else { Err(()) }
    }
}

pub fn lock_pages(ptr: *const u8, size: usize) -> Result<(), ()> {
    if ptr.is_null() || size == 0 {
        return Err(());
    }
    #[cfg(unix)]
    unsafe {
        let ret = libc::mlock(ptr as *const libc::c_void, size);
        if ret == 0 { Ok(()) } else { Err(()) }
    }
    #[cfg(windows)]
    unsafe {
        let ret = VirtualLock(ptr as *mut std::ffi::c_void, size);
        if ret != 0 { Ok(()) } else { Err(()) }
    }
}

pub fn unlock_pages(ptr: *const u8, size: usize) -> Result<(), ()> {
    if ptr.is_null() || size == 0 {
        return Err(());
    }
    #[cfg(unix)]
    unsafe {
        let ret = libc::munlock(ptr as *const libc::c_void, size);
        if ret == 0 { Ok(()) } else { Err(()) }
    }
    #[cfg(windows)]
    unsafe {
        let ret = VirtualUnlock(ptr as *mut std::ffi::c_void, size);
        if ret != 0 { Ok(()) } else { Err(()) }
    }
}

pub fn register_exit_handler(func: extern "C" fn()) -> Result<(), ()> {
    #[cfg(unix)]
    unsafe {
        let ret = libc::atexit(func);
        if ret == 0 { Ok(()) } else { Err(()) }
    }
    #[cfg(windows)]
    unsafe {
        let ret = atexit(func);
        if ret == 0 { Ok(()) } else { Err(()) }
    }
}
