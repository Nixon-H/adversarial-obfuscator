use crate::decrypt::aes_256_ctr_decrypt;
use crate::memguard::scrub_memory;

const ORAM_BLOCK_SIZE: usize = 64;
const ORAM_TREE_HEIGHT: usize = 8;
pub const ORAM_NUM_LEAVES: usize = 1 << ORAM_TREE_HEIGHT;
pub const ORAM_STASH_SIZE: usize = 64;

#[derive(Clone, Debug)]
struct OramBlock {
    id: u64,
    data: [u8; 64],
    leaf: u64,
}

pub struct OramController {
    tree: Vec<Vec<OramBlock>>,
    stash: Vec<OramBlock>,
    position_map: Vec<u64>,
    key: [u8; 32],
    rng_state: u64,
    num_logical: usize,
}

fn xor_keystream(data: &mut [u8], key: &[u8; 32], id: u64) {
    let mut iv = [0u8; 16];
    iv[..8].copy_from_slice(&id.to_le_bytes());
    aes_256_ctr_decrypt(data, key, &iv);
}

#[allow(dead_code)]
fn seeded_shuffle(values: &mut [u64], seed: u64) {
    let mut rng = seed;
    let len = values.len();
    for i in (1..len).rev() {
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let j = (rng as usize) % (i + 1);
        values.swap(i, j);
    }
}

fn next_rng(state: &mut u64) -> u64 {
    *state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
    *state
}

impl OramBlock {
    fn new(id: u64, leaf: u64) -> Self {
        OramBlock {
            id,
            data: [0u8; ORAM_BLOCK_SIZE],
            leaf,
        }
    }

    fn dummy() -> Self {
        OramBlock {
            id: u64::MAX,
            data: [0u8; ORAM_BLOCK_SIZE],
            leaf: 0,
        }
    }

    fn is_dummy(&self) -> bool {
        self.id == u64::MAX
    }
}

impl OramController {
    pub fn new(num_logical_blocks: usize, key: [u8; 32]) -> Self {
        let mut rng_state = 0xDEADBEEFCAFEBABEu64;
        for &b in key.iter().take(8) {
            rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(b as u64);
        }

        let mut tree = Vec::with_capacity(ORAM_TREE_HEIGHT + 1);
        for level in 0..=ORAM_TREE_HEIGHT {
            let num_nodes = 1 << level;
            let mut level_vec = Vec::with_capacity(num_nodes);
            for _ in 0..num_nodes {
                let dummy = OramBlock::dummy();
                level_vec.push(dummy);
            }
            tree.push(level_vec);
        }

        let mut position_map = Vec::with_capacity(num_logical_blocks);
        for i in 0..num_logical_blocks {
            let leaf = (next_rng(&mut rng_state) as usize) % ORAM_NUM_LEAVES;
            position_map.push(leaf as u64);
            let pos = leaf;
            let block = OramBlock::new(i as u64, leaf as u64);
            tree[ORAM_TREE_HEIGHT][pos] = block;
        }

        OramController {
            tree,
            stash: Vec::with_capacity(ORAM_STASH_SIZE),
            position_map,
            key,
            rng_state,
            num_logical: num_logical_blocks,
        }
    }

    fn path_position(level: usize, leaf: u64) -> usize {
        if level == 0 {
            0
        } else {
            (leaf >> (ORAM_TREE_HEIGHT - level)) as usize
        }
    }

    fn encrypt_block(&self, block: &OramBlock) -> [u8; ORAM_BLOCK_SIZE] {
        let mut data = block.data;
        xor_keystream(&mut data, &self.key, block.id);
        data
    }

    fn decrypt_block(&self, block: &OramBlock) -> [u8; ORAM_BLOCK_SIZE] {
        let mut data = block.data;
        xor_keystream(&mut data, &self.key, block.id);
        data
    }

    fn encrypt_all(&self, block: &mut OramBlock) {
        block.data = self.encrypt_block(block);
    }

    fn decrypt_all(&self, block: &mut OramBlock) {
        block.data = self.decrypt_block(block);
    }

    fn read_path(&mut self, leaf: u64) -> Result<(), String> {
        if self.stash.len() + (ORAM_TREE_HEIGHT + 1) > ORAM_STASH_SIZE {
            return Err(format!("stash overflow: {} + {} > {}", self.stash.len(), ORAM_TREE_HEIGHT + 1, ORAM_STASH_SIZE));
        }
        for level in 0..=ORAM_TREE_HEIGHT {
            let pos = Self::path_position(level, leaf);
            let block = self.tree[level][pos].clone();
            if !block.is_dummy() {
                let mut b = block;
                self.decrypt_all(&mut b);
                self.stash.push(b);
            }
            self.tree[level][pos] = OramBlock::dummy();
        }
        Ok(())
    }

    fn evict_path(&mut self, leaf: u64) {
        for level in (0..=ORAM_TREE_HEIGHT).rev() {
            let pos = Self::path_position(level, leaf);
            let mut found = None;
            for (i, block) in self.stash.iter().enumerate() {
                if block.is_dummy() {
                    continue;
                }
                let block_prefix = if level == 0 {
                    0u64
                } else {
                    block.leaf >> (ORAM_TREE_HEIGHT - level)
                };
                if block_prefix == pos as u64 {
                    found = Some(i);
                    break;
                }
            }
            if let Some(idx) = found {
                let mut block = self.stash.remove(idx);
                self.encrypt_all(&mut block);
                self.tree[level][pos] = block;
            }
        }
    }

    pub fn access(&mut self, id: u64, data: Option<&[u8; 64]>) -> Result<[u8; 64], String> {
        if id as usize >= self.num_logical {
            return Err(format!("block id {} out of range (max {})", id, self.num_logical));
        }
        let leaf = self.position_map[id as usize];

        self.read_path(leaf)?;

        let mut found = None;
        for (i, block) in self.stash.iter().enumerate() {
            if block.id == id {
                found = Some(i);
                break;
            }
        }

        let idx = match found {
            Some(i) => i,
            None => {
                self.stash.push(OramBlock::new(id, leaf));
                self.stash.len() - 1
            }
        };

        let old_data = self.stash[idx].data;

        if let Some(new_data) = data {
            self.stash[idx].data = *new_data;
        }

        let new_leaf = (next_rng(&mut self.rng_state) as usize) % ORAM_NUM_LEAVES;
        self.stash[idx].leaf = new_leaf as u64;
        self.position_map[id as usize] = new_leaf as u64;

        self.evict_path(leaf);

        Ok(old_data)
    }

    pub fn get_position_map(&self) -> &[u64] {
        &self.position_map
    }

    pub fn tree_height(&self) -> usize {
        ORAM_TREE_HEIGHT
    }

    pub fn path_length(&self, leaf: u64) -> usize {
        let mut count = 0;
        for level in 0..=ORAM_TREE_HEIGHT {
            let _pos = Self::path_position(level, leaf);
            count += 1;
        }
        count
    }

    pub fn num_logical_blocks(&self) -> usize {
        self.num_logical
    }
}

impl Drop for OramController {
    fn drop(&mut self) {
        scrub_memory(self.key.as_mut_ptr(), self.key.len());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_test_controller(num_blocks: usize) -> OramController {
        let key = [0x42u8; 32];
        OramController::new(num_blocks, key)
    }

    #[test]
    fn test_new_controller_initializes() {
        let ctrl = make_test_controller(16);
        assert_eq!(ctrl.tree.len(), ORAM_TREE_HEIGHT + 1);
        for level in 0..=ORAM_TREE_HEIGHT {
            assert_eq!(ctrl.tree[level].len(), 1 << level);
        }
        assert_eq!(ctrl.position_map.len(), 16);
        assert!(ctrl.stash.is_empty());
    }

    #[test]
    fn test_read_write_roundtrip() {
        let mut ctrl = make_test_controller(8);
        let write_data = [0xABu8; 64];
        let old = ctrl.access(0, Some(&write_data)).expect("write should succeed");
        let read = ctrl.access(0, None).expect("read should succeed");
        assert_eq!(read, write_data);
        assert!(old.iter().all(|&b| b == 0) || old != write_data);
    }

    #[test]
    fn test_different_blocks_map_to_different_leaves() {
        let ctrl = make_test_controller(32);
        let pmap = ctrl.get_position_map();
        let mut unique = std::collections::HashSet::new();
        for &leaf in pmap.iter() {
            unique.insert(leaf);
        }
        assert!(unique.len() > 1, "expected multiple distinct leaves");
    }

    #[test]
    fn test_stress_random_ops() {
        const BLOCKS: usize = 4;
        let mut ctrl = make_test_controller(BLOCKS);
        let mut written: std::collections::HashMap<u64, [u8; 64]> = std::collections::HashMap::new();
        for block_id in 0..BLOCKS {
            let val = [block_id as u8; 64];
            ctrl.access(block_id as u64, Some(&val)).expect("initial write");
            written.insert(block_id as u64, val);
        }
        let mut rng: u64 = 12345;
        for _ in 0..100 {
            rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let id = (rng as usize) % BLOCKS;
            if rng % 2 == 0 {
                let val = [(id as u8).wrapping_mul(17); 64];
                ctrl.access(id as u64, Some(&val)).expect("write");
                written.insert(id as u64, val);
            } else {
                let read = ctrl.access(id as u64, None).expect("read");
                assert_eq!(read, written[&(id as u64)], "data mismatch for block {}", id);
            }
        }
    }

    #[test]
    fn test_all_paths_same_length() {
        let ctrl = make_test_controller(8);
        let len0 = ctrl.path_length(0);
        for leaf in 1..ORAM_NUM_LEAVES {
            assert_eq!(ctrl.path_length(leaf as u64), len0, "path length mismatch at leaf {}", leaf);
        }
        assert_eq!(len0, ORAM_TREE_HEIGHT + 1);
    }

    #[test]
    fn test_access_out_of_range() {
        let mut ctrl = make_test_controller(4);
        let result = ctrl.access(99, None);
        assert!(result.is_err());
    }

    #[test]
    fn test_seeded_shuffle_deterministic() {
        let mut a = [0u64, 1, 2, 3, 4, 5, 6, 7];
        let mut b = [0u64, 1, 2, 3, 4, 5, 6, 7];
        seeded_shuffle(&mut a, 42);
        seeded_shuffle(&mut b, 42);
        assert_eq!(a, b);
    }

    #[test]
    fn test_seeded_shuffle_different_seeds() {
        let mut a = [0u64, 1, 2, 3, 4, 5, 6, 7];
        let mut b = [0u64, 1, 2, 3, 4, 5, 6, 7];
        seeded_shuffle(&mut a, 42);
        seeded_shuffle(&mut b, 99);
        assert_ne!(a, b);
    }
}
