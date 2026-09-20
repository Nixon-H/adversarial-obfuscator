use std::collections::VecDeque;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

const CHECKSUM_INTERVAL_MS: u64 = 100;
const REDUNDANT_COPIES: usize = 3;
const MAX_LOG_ENTRIES: usize = 1024;

#[derive(Debug, Clone)]
pub struct TamperLogEntry {
    pub timestamp: u64,
    pub region_name: String,
    pub region_addr: usize,
    pub expected_checksum: u64,
    pub actual_checksum: u64,
    pub restored: bool,
}

pub struct CriticalRegion {
    pub name: String,
    pub data: Vec<u8>,
    pub redundant_copies: Vec<Vec<u8>>,
    pub expected_checksum: u64,
}

pub struct SelfHealingRuntime {
    regions: Mutex<Vec<CriticalRegion>>,
    tamper_log: Mutex<VecDeque<TamperLogEntry>>,
    running: AtomicBool,
}

impl SelfHealingRuntime {
    pub fn new() -> Self {
        SelfHealingRuntime {
            regions: Mutex::new(Vec::new()),
            tamper_log: Mutex::new(VecDeque::with_capacity(MAX_LOG_ENTRIES)),
            running: AtomicBool::new(false),
        }
    }

    pub fn register_critical_region(&self, name: &str, data: &[u8]) {
        let expected_checksum = Self::checksum(data);
        let mut copies = Vec::with_capacity(REDUNDANT_COPIES);
        for _ in 0..REDUNDANT_COPIES {
            copies.push(data.to_vec());
        }
        if let Ok(mut regions) = self.regions.lock() {
            regions.push(CriticalRegion {
                name: name.to_string(),
                data: data.to_vec(),
                redundant_copies: copies,
                expected_checksum,
            });
        }
    }

    pub fn checksum(data: &[u8]) -> u64 {
        let mut h: u64 = 0xC6A4A7C0A4B3F2D1;
        for &b in data {
            h ^= b as u64;
            h = h.rotate_left(7);
            h = h.wrapping_mul(0x9E3779B97F4A7C15);
        }
        h
    }

    pub fn verify_and_heal_all(&self) -> bool {
        let mut all_ok = true;
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let mut regions = match self.regions.lock() {
            Ok(r) => r,
            Err(_) => return false,
        };

        for region in regions.iter_mut() {
            let actual = Self::checksum(&region.data);
            if actual != region.expected_checksum {
                all_ok = false;
                let mut restored = false;
                for copy in &region.redundant_copies {
                    let copy_cs = Self::checksum(copy);
                    if copy_cs == region.expected_checksum {
                        region.data.copy_from_slice(copy);
                        restored = true;
                        break;
                    }
                }
                if !restored {
                    if let Some(copy) = region.redundant_copies.first() {
                        region.data.copy_from_slice(copy);
                    }
                }
                if let Ok(mut log) = self.tamper_log.lock() {
                    log.push_back(TamperLogEntry {
                        timestamp: ts,
                        region_name: region.name.clone(),
                        region_addr: region.data.as_ptr() as usize,
                        expected_checksum: region.expected_checksum,
                        actual_checksum: actual,
                        restored,
                    });
                    while log.len() > MAX_LOG_ENTRIES {
                        log.pop_front();
                    }
                }
            }
        }
        all_ok
    }

    pub fn start_background_checking(&'static self) {
        self.running.store(true, Ordering::SeqCst);
        std::thread::spawn(move || {
            while self.running.load(Ordering::Relaxed) {
                std::thread::sleep(std::time::Duration::from_millis(CHECKSUM_INTERVAL_MS));
                self.verify_and_heal_all();
            }
        });
    }

    pub fn stop_background_checking(&self) {
        self.running.store(false, Ordering::SeqCst);
    }

    pub fn get_tamper_log(&self) -> Vec<TamperLogEntry> {
        if let Ok(log) = self.tamper_log.lock() {
            log.iter().cloned().collect()
        } else {
            Vec::new()
        }
    }

    pub fn tamper_log_count(&self) -> usize {
        if let Ok(log) = self.tamper_log.lock() {
            log.len()
        } else {
            0
        }
    }

    pub fn tamper_region(&self, name: &str) -> bool {
        if let Ok(mut regions) = self.regions.lock() {
            if let Some(region) = regions.iter_mut().find(|r| r.name == name) {
                if !region.data.is_empty() {
                    region.data[0] ^= 0xFF;
                    return true;
                }
            }
        }
        false
    }

    pub fn num_regions(&self) -> usize {
        if let Ok(regions) = self.regions.lock() {
            regions.len()
        } else {
            0
        }
    }

    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::Relaxed)
    }

    pub fn region_data(&self, name: &str) -> Option<Vec<u8>> {
        if let Ok(regions) = self.regions.lock() {
            regions.iter().find(|r| r.name == name).map(|r| r.data.clone())
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detects_tamper() {
        let rt = SelfHealingRuntime::new();
        let data = vec![0x42u8; 64];
        rt.register_critical_region("test_region", &data);
        assert!(rt.verify_and_heal_all(), "Undamaged region should verify OK");
        rt.tamper_region("test_region");
        assert!(!rt.verify_and_heal_all(), "Damaged region should fail initial verify");
    }

    #[test]
    fn test_restores_from_redundant_copy() {
        let rt = SelfHealingRuntime::new();
        let data = vec![0xABu8; 64];
        rt.register_critical_region("restore_region", &data);
        rt.tamper_region("restore_region");
        rt.verify_and_heal_all();
        let restored = rt.region_data("restore_region").unwrap();
        assert_eq!(restored[0], 0xAB, "Region should be restored to original value");
    }

    #[test]
    fn test_background_checking() {
        let rt: &'static SelfHealingRuntime = Box::leak(Box::new(SelfHealingRuntime::new()));
        let data = vec![0x42u8; 32];
        rt.register_critical_region("bg_region", &data);
        rt.start_background_checking();
        std::thread::sleep(std::time::Duration::from_millis(300));
        assert!(rt.is_running());
        rt.stop_background_checking();
        assert!(!rt.is_running());
    }

    #[test]
    fn test_logs_attempts() {
        let rt = SelfHealingRuntime::new();
        let data = vec![0x99u8; 32];
        rt.register_critical_region("logged_region", &data);
        assert_eq!(rt.tamper_log_count(), 0);
        rt.tamper_region("logged_region");
        rt.verify_and_heal_all();
        assert!(rt.tamper_log_count() >= 1, "Tamper should be logged");
        let log = rt.get_tamper_log();
        assert_eq!(log[0].region_name, "logged_region");
        assert!(log[0].restored);
    }

    #[test]
    fn test_checksum_deterministic() {
        let data = b"test data for checksum";
        let c1 = SelfHealingRuntime::checksum(data);
        let c2 = SelfHealingRuntime::checksum(data);
        assert_eq!(c1, c2);
    }

    #[test]
    fn test_checksum_different() {
        let c1 = SelfHealingRuntime::checksum(b"data_a");
        let c2 = SelfHealingRuntime::checksum(b"data_b");
        assert_ne!(c1, c2);
    }

    #[test]
    fn test_register_multiple_regions() {
        let rt = SelfHealingRuntime::new();
        rt.register_critical_region("r1", &[1, 2, 3]);
        rt.register_critical_region("r2", &[4, 5, 6]);
        rt.register_critical_region("r3", &[7, 8, 9]);
        assert_eq!(rt.num_regions(), 3);
        assert!(rt.verify_and_heal_all());
    }

    #[test]
    fn test_restore_from_first_copy_if_all_damaged() {
        let rt = SelfHealingRuntime::new();
        let data = vec![0x77u8; 16];
        rt.register_critical_region("all_damaged", &data);
        rt.tamper_region("all_damaged");
        if let Ok(mut regions) = rt.regions.lock() {
            if let Some(region) = regions.iter_mut().find(|r| r.name == "all_damaged") {
                for copy in &mut region.redundant_copies {
                    copy[0] ^= 0xFF;
                }
            }
        }
        let healed = rt.verify_and_heal_all();
        assert!(!healed, "When all copies are damaged, healing cannot fully succeed");
        let log = rt.get_tamper_log();
        assert!(!log.is_empty(), "Tamper should be logged");
        let last_entry = log.last().unwrap();
        assert!(!last_entry.restored, "Should report that restore failed: expected={:x} actual={:x}",
            last_entry.expected_checksum, last_entry.actual_checksum);
    }
}
