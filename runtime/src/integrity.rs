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
    // Hash the BINARY FILE, not a memory mapping.
    //
    // The baseline in runtime_config.json is produced by
    // scripts/runtime_config.py, which reads the file's executable PT_LOAD
    // segment. A maps-based region and a program-header region are not the same
    // bytes -- page-aligning the first r-xp line happened to agree on the dev
    // machine and disagreed on a CI-built binary, which is exactly the sort of
    // "passes here, fails there" this check must not have.
    //
    // Reading /proc/self/exe hashes the same bytes the writer hashed, on every
    // machine, and it is also what makes the check meaningful: it compares the
    // running image against the recorded one rather than against a guess about
    // which mapping is "ours".
    let path = match fs::read_link("/proc/self/exe") {
        Ok(p) => p,
        Err(_) => return false,
    };
    let bytes = match fs::read(&path) {
        Ok(b) => b,
        Err(_) => return false,
    };
    crc32(&bytes) == expected
}
