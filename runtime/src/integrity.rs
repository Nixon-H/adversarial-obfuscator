use std::fs;

const CRC32_TABLE: [u32; 256] = {
    let mut table = [0u32; 256];
    let mut i = 0u32;
    while i < 256 {
        let mut crc = i;
        let mut j = 0;
        while j < 8 {
            if crc & 1 != 0 {
                crc = 0xEDB88320 ^ (crc >> 1);
            } else {
                crc >>= 1;
            }
            j += 1;
        }
        table[i as usize] = crc;
        i += 1;
    }
    table
};

pub fn crc32(data: &[u8]) -> u32 {
    let mut crc = 0xFFFFFFFFu32;
    for &byte in data {
        let idx = ((crc ^ byte as u32) & 0xFF) as usize;
        crc = CRC32_TABLE[idx] ^ (crc >> 8);
    }
    crc ^ 0xFFFFFFFF
}

pub fn find_text_bounds() -> Option<(usize, usize)> {
    // The mapping must be OUR image, not the first executable one in the file.
    // /proc/self/maps lists the dynamic loader first on most systems, so taking
    // the first r-xp line hashed ld-linux's text and a "pass" proved nothing
    // about the runtime.
    let own = fs::read_link("/proc/self/exe").ok();
    let own_name = own
        .as_ref()
        .and_then(|p| p.file_name())
        .map(|n| n.to_string_lossy().into_owned());

    let maps = fs::read_to_string("/proc/self/maps").ok()?;
    for line in maps.lines() {
        if line.contains("[vdso]") || line.contains("[vvar]") || line.contains("[stack]") || line.contains("/dev/") {
            continue;
        }
        let cols: Vec<&str> = line.splitn(5, ' ').collect();
        if cols.len() < 5 || cols[1] != "r-xp" {
            continue;
        }
        let path = cols[4].trim();
        if path.is_empty() || path.starts_with('[') {
            continue;
        }
        // Skip anything that is not this process's own image.
        let is_own = match (&own, &own_name) {
            (Some(exe), _) => path == exe.to_string_lossy(),
            (None, Some(name)) => path.ends_with(name.as_str()),
            _ => true,
        };
        if !is_own {
            continue;
        }
        let addrs: Vec<&str> = cols[0].split('-').collect();
        if addrs.len() != 2 {
            continue;
        }
        let start = usize::from_str_radix(addrs[0], 16).ok()?;
        let end = usize::from_str_radix(addrs[1], 16).ok()?;
        return Some((start, end));
    }
    None
}

pub fn verify_text_section(expected: u32) -> bool {
    let bounds = find_text_bounds();
    match bounds {
        Some((start, end)) => {
            let len = end - start;
            let slice = unsafe {
                std::slice::from_raw_parts(start as *const u8, len)
            };
            let actual = crc32(slice);
            actual == expected
        }
        None => false,
    }
}
