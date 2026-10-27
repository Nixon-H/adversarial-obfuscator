use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct VariantPool {
    pub variants: HashMap<u32, Vec<u8>>,
    pub metadata: VariantMetadata,
}

#[derive(Debug, Clone)]
pub struct VariantMetadata {
    pub variant_files: Vec<String>,
    pub variant_ids: Vec<u32>,
    pub num_variants: usize,
    pub pool_seed: String,
    pub target: String,
}

impl VariantPool {
    pub fn load(build_dir: &Path) -> Option<Self> {
        let meta_path = build_dir.join("variant_pool").join("variant_metadata.json");
        if !meta_path.exists() {
            let alt = build_dir.join("variant_pool.json");
            if alt.exists() {
                return Self::load_single_file(&alt);
            }
            return None;
        }
        let meta_str = std::fs::read_to_string(&meta_path).ok()?;
        let meta: serde_json::Value = serde_json::from_str(&meta_str).ok()?;

        let metadata = VariantMetadata {
            variant_files: meta["variant_files"].as_array()
                .map(|a| a.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                .unwrap_or_default(),
            variant_ids: meta["variant_ids"].as_array()
                .map(|a| a.iter().filter_map(|v| v.as_u64().map(|n| n as u32)).collect())
                .unwrap_or_default(),
            num_variants: meta["num_variants"].as_u64().unwrap_or(0) as usize,
            pool_seed: meta["pool_seed"].as_str().unwrap_or("build").to_string(),
            target: meta["target"].as_str().unwrap_or("crown_jewel").to_string(),
        };

        let mut variants = HashMap::new();
        let pool_dir = build_dir.join("variant_pool");
        for (i, fname) in metadata.variant_files.iter().enumerate() {
            let vpath = pool_dir.join(fname);
            if let Ok(data) = std::fs::read(&vpath) {
                variants.insert(metadata.variant_ids.get(i).copied().unwrap_or(i as u32), data);
            }
        }

        Some(VariantPool { variants, metadata })
    }

    fn load_single_file(path: &Path) -> Option<Self> {
        let data = std::fs::read(path).ok()?;
        let mut variants = HashMap::new();
        variants.insert(0, data);
        Some(VariantPool {
            variants,
            metadata: VariantMetadata {
                variant_files: vec![path.file_name()?.to_string_lossy().to_string()],
                variant_ids: vec![0],
                num_variants: 1,
                pool_seed: "build".to_string(),
                target: "crown_jewel".to_string(),
            },
        })
    }

    pub fn get_variant(&self, id: u32) -> Option<&Vec<u8>> {
        self.variants.get(&id)
    }

    pub fn select_variant(&self, seed: u64) -> u32 {
        if self.variants.is_empty() {
            return 0;
        }
        let keys: Vec<&u32> = self.variants.keys().collect();
        let idx = (seed as usize) % keys.len();
        **keys.get(idx).unwrap_or(&&0u32)
    }
}
