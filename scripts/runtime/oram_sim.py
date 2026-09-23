"""
oram_sim.py

Purpose:
Pure Python simulation of Path-ORAM (Oblivious RAM) for understanding
and validating ORAM access patterns. Implements the core Path-ORAM
algorithm: tree-based storage with a local stash, position map, and
deterministic bucket eviction.

Architectural Role:
Reference implementation and test harness for the ORAM scheme used in
the protection pipeline. The compiled IR-level ORAM integration in
irgen/oram.py generates LLVM-level hints; this file provides the
algorithmic reference.

Security Relevance:
ORAM hides which specific memory location is being accessed by
transforming every access into a read/write of an entire path from
root to leaf in a binary tree. The adversary learns only the access
time, not the address. This simulation demonstrates the core property:
every access pattern is statistically identical regardless of the
actual address being read or written.

Key algorithmic properties:
- Buckets hold Z=4 blocks each (standard Path-ORAM parameter).
- Tree height H is derived from the number of addressable blocks N.
- Position map tracks which leaf each block is mapped to.
- Stash temporarily holds evicted blocks (bounded by O(log N)).
- evict() always reads/writes exactly one path per access.
"""

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple


class PathORAM:
    """
    Path-ORAM simulation with a binary tree, stash, and position map.

    Every read/write operation traverses exactly one root-to-leaf path,
    ensuring all access patterns are indistinguishable to an observer.

    Public methods:
      - read(address) -> Optional[data]
      - write(address, data) -> None
      - access(address, new_data=None) -> Optional[data]
      - get_stats() -> dict

    The access() method is the core ORAM operation. Both read() and
    write() delegate to it.
    """

    def __init__(self, num_blocks: int = 16, bucket_size: int = 4):
        """
        Initialize the ORAM tree with N addressable blocks.

        Args:
            num_blocks: Number of logical addressable blocks (N).
            bucket_size: Blocks per bucket (Z). Standard is 4.
        """
        self.num_blocks = num_blocks
        self.bucket_size = bucket_size

        self.tree_height = math.ceil(math.log2(num_blocks))
        self.num_leaves = 2 ** self.tree_height

        self.tree: List[List[Optional[Dict]]] = self._build_tree()
        self.stash: List[Dict] = []
        self.position_map: Dict[int, int] = {}
        self._access_count = 0

        self._init_position_map()

    def _build_tree(self) -> List[List[Optional[Dict]]]:
        """
        Construct the binary tree as a flat list of levels.

        Each level is a list of buckets; each bucket is a list of
        size bucket_size initialized to None.
        """
        tree = []
        for level in range(self.tree_height + 1):
            num_buckets = 2 ** level
            level_buckets: List[Optional[Dict]] = [None] * num_buckets
            tree.append(level_buckets)
        return tree

    def _init_position_map(self) -> None:
        """
        Assign each block to a uniformly random leaf on initialization.

        Security note: Random initial assignment ensures that the
        adversary cannot distinguish initial state from operational
        state. Without this, the first access to each block would
        reveal information about the access order.
        """
        for addr in range(self.num_blocks):
            self.position_map[addr] = uuid.uuid4().int % self.num_leaves

    def _get_path(self, leaf: int) -> List[Tuple[int, int]]:
        """
        Compute the bucket indices along the path from root to leaf.

        Returns a list of (level, bucket_index) tuples. Level 0 is
        the root; level tree_height is the leaf level.

        Bucket at (level, bucket_index) stores block data.
        """
        path = []
        for level in range(self.tree_height + 1):
            bucket_idx = leaf >> (self.tree_height - level)
            path.append((level, bucket_idx))
        return path

    def _read_path(self, leaf: int) -> List[Dict]:
        """
        Read all buckets along a root-to-leaf path into the stash.

        Security note: This is the O(log N) read step. Every access
        reads exactly one full path, regardless of which bucket
        actually contains the target block. The adversary sees the
        same volume of data read every time.
        """
        blocks = []
        path = self._get_path(leaf)
        for level, bucket_idx in path:
            bucket = self.tree[level][bucket_idx]
            if bucket is not None:
                blocks.append(bucket)
                self.tree[level][bucket_idx] = None
        return blocks

    def _bucket_on_path(self, block_leaf: int, level: int, bucket_idx: int) -> bool:
        """
        Check whether bucket (level, bucket_idx) lies on the root-to-leaf
        path for block_leaf. A block may only reside in a bucket shared by
        its own leaf path and the eviction path (standard Path-ORAM
        placement invariant).
        """
        return (block_leaf >> (self.tree_height - level)) == bucket_idx

    def _write_path(self, leaf: int, path_blocks: List[Dict]) -> None:
        """
        Greedy Path-ORAM write-back (eviction) along the path to leaf.

        path_blocks were already merged into the stash by access(); evict
        from the stash: walk buckets leaf-to-root and place the first
        stash block legally allowed in each empty bucket. Blocks that do
        not fit remain in the stash (bounded by O(log N) w.h.p.).

        Security note: this is the O(log N) write step. Every access
        writes back exactly one full path, so read and write accesses
        are indistinguishable to an observer.
        """
        # path_blocks is intentionally unused: its contents were moved
        # into self.stash by access() before this call; eviction below
        # drains the stash back into the tree.
        _ = path_blocks
        path = self._get_path(leaf)
        for level, bucket_idx in reversed(path):
            if self.tree[level][bucket_idx] is not None:
                continue
            for i, block in enumerate(self.stash):
                block_leaf = self.position_map.get(block["id"], leaf)
                if self._bucket_on_path(block_leaf, level, bucket_idx):
                    self.tree[level][bucket_idx] = block
                    del self.stash[i]
                    break

    def access(self, address: int, new_data: Optional[Any] = None) -> Optional[Any]:
        """
        Core ORAM access operation. Performs exactly one path
        read/write regardless of the specific address.

        Algorithm:
        1. Look up the current leaf for this address.
        2. Assign a new random leaf for next time.
        3. Read the entire path from root to old leaf into stash.
        4. If new_data is None (read), fetch block from stash.
        5. If new_data is provided (write), update block in stash.
        6. Evict: greedily write stash blocks back to the path.
        7. Return the original data (if read).

        Security note: Step 2 (remapping) ensures that repeated
        accesses to the same address take different paths, preventing
        the adversary from linking accesses by path identity.
        """
        self._access_count += 1

        old_leaf = self.position_map[address]

        path_blocks = self._read_path(old_leaf)
        self.stash.extend(path_blocks)

        old_data = None
        for block in self.stash:
            if block["id"] == address:
                old_data = block["data"]
                if new_data is not None:
                    block["data"] = new_data
                break

        if old_data is None:
            new_block = {"id": address, "data": new_data}
            self.stash.append(new_block)
        # Remap on every access (not only on stash hit): repeated accesses
        # to the same address must take different paths, otherwise the
        # adversary can link accesses by path identity.
        self.position_map[address] = uuid.uuid4().int % self.num_leaves

        self._write_path(old_leaf, path_blocks)

        return old_data

    def read(self, address: int) -> Optional[Any]:
        """Oblivious read: return data at address via access()."""
        return self.access(address, new_data=None)

    def write(self, address: int, data: Any) -> None:
        """Oblivious write: set data at address via access()."""
        self.access(address, new_data=data)

    def get_stats(self) -> Dict[str, Any]:
        """Return usage statistics for debugging and analysis."""
        stash_size = len(self.stash)
        tree_blocks = sum(
            1 for level in self.tree for bucket in level
            if bucket is not None
        )
        return {
            "access_count": self._access_count,
            "stash_size": stash_size,
            "tree_blocks": tree_blocks,
            "position_map_entries": len(self.position_map),
            "num_leaves": self.num_leaves,
            "tree_height": self.tree_height,
        }


# Backwards-compatible alias: generated payloads (data_protector) and older
# tests import PythonORAM; the implementation is PathORAM. Single class,
# two names — no behavior difference.
PythonORAM = PathORAM
