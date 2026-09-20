//! Hydra cross-respawn mesh (tiered, pure logic — no threads).
//!
//! Companion to `self_healing`: that module owns the background checksum
//! thread; this module tracks *liveness* of a set of named nodes (worker
//! threads, watchdogs, enclaves) so a supervisor can detect dead members
//! and respawn them.
//!
//! Threading stays in `self_healing` by design: `HydraMesh` only records
//! which nodes were last seen alive and which need respawning. The caller
//! (supervisor thread) performs the actual thread respawn and then calls
//! [`HydraMesh::heartbeat`] for the revived node.
//!
//! Tier semantics (safe default = [`HydraTier::Monitor`]):
//! - [`HydraTier::Off`] — all methods are no-op / pass-through:
//!   `heartbeat` always returns `true`, `dead_nodes` returns `[]`,
//!   `respawn_dead` returns `[]`, `check_all` returns `(0, 0)`.
//! - [`HydraTier::Monitor`] — detect + report only: heartbeats and dead
//!   detection work, but `respawn_dead` returns `[]` (no respawn action).
//! - [`HydraTier::Enforce`] — full behavior: dead nodes are marked
//!   respawned (removed from the dead set, i.e. treated alive again
//!   pending a fresh heartbeat) and their names returned.

use std::collections::{HashMap, HashSet};

/// Enforcement tier for the Hydra mesh. Default is `Monitor` (safe default).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum HydraTier {
    /// Mesh disabled: every method is a no-op / pass.
    Off,
    /// Detect + report only (default). `respawn_dead` returns `[]`.
    #[default]
    Monitor,
    /// Full behavior: `respawn_dead` marks dead nodes respawned.
    Enforce,
}

/// Pure-logic liveness mesh over named nodes. No threads inside.
#[derive(Debug, Default)]
pub struct HydraMesh {
    nodes: Vec<String>,
    alive: HashSet<String>,
    tier: HydraTier,
}

impl HydraMesh {
    /// Create an empty mesh at the default tier ([`HydraTier::Monitor`]).
    pub fn new() -> Self {
        HydraMesh {
            nodes: Vec::new(),
            alive: HashSet::new(),
            tier: HydraTier::Monitor,
        }
    }

    /// Create an empty mesh at an explicit tier.
    pub fn with_tier(tier: HydraTier) -> Self {
        HydraMesh {
            nodes: Vec::new(),
            alive: HashSet::new(),
            tier,
        }
    }

    /// Current tier.
    pub fn tier(&self) -> HydraTier {
        self.tier
    }

    /// Change the tier at runtime.
    pub fn set_tier(&mut self, tier: HydraTier) {
        self.tier = tier;
    }

    /// Register a node. Duplicate names are ignored.
    /// In `Off` tier this is a no-op.
    pub fn add_node(&mut self, name: &str) {
        if self.tier == HydraTier::Off {
            return;
        }
        if !self.nodes.iter().any(|n| n == name) {
            self.nodes.push(name.to_string());
            // A freshly added node counts as alive until proven otherwise.
            self.alive.insert(name.to_string());
        }
    }

    /// Record a heartbeat for `name`.
    /// Returns `true` if the node is known (or tier is `Off`),
    /// `false` for unknown nodes.
    pub fn heartbeat(&mut self, name: &str) -> bool {
        if self.tier == HydraTier::Off {
            return true;
        }
        if self.nodes.iter().any(|n| n == name) {
            self.alive.insert(name.to_string());
            true
        } else {
            false
        }
    }

    /// Mark a node dead (e.g. supervisor observed its thread exit).
    /// Returns `true` if the node was known. Test/supervisor helper.
    /// In `Off` tier this is a no-op returning `false`.
    pub fn mark_dead(&mut self, name: &str) -> bool {
        if self.tier == HydraTier::Off {
            return false;
        }
        if self.nodes.iter().any(|n| n == name) {
            self.alive.remove(name);
            true
        } else {
            false
        }
    }

    /// Names of registered nodes with no live heartbeat.
    /// Always `[]` in `Off` tier.
    pub fn dead_nodes(&self) -> Vec<String> {
        if self.tier == HydraTier::Off {
            return Vec::new();
        }
        let mut dead: Vec<String> = self
            .nodes
            .iter()
            .filter(|n| !self.alive.contains(n.as_str()))
            .cloned()
            .collect();
        dead.sort();
        dead
    }

    /// Respawn dead nodes.
    ///
    /// - `Off`: no-op, returns `[]`.
    /// - `Monitor`: detect + report only, returns `[]` (dead set unchanged).
    /// - `Enforce`: marks each dead node respawned (re-inserted into the
    ///   alive set — the caller must still spawn the replacement thread and
    ///   confirm with [`HydraMesh::heartbeat`]) and returns their names.
    pub fn respawn_dead(&mut self) -> Vec<String> {
        match self.tier {
            HydraTier::Off | HydraTier::Monitor => Vec::new(),
            HydraTier::Enforce => {
                let mut dead = self.dead_nodes();
                dead.sort();
                for n in &dead {
                    self.alive.insert(n.clone());
                }
                dead
            }
        }
    }

    /// `(alive_count, dead_count)` over registered nodes.
    /// `(0, 0)` in `Off` tier.
    pub fn check_all(&self) -> (usize, usize) {
        if self.tier == HydraTier::Off {
            return (0, 0);
        }
        let dead = self.dead_nodes().len();
        let alive = self.nodes.len().saturating_sub(dead);
        (alive, dead)
    }

    /// Number of registered nodes (`0` in `Off` tier since adds are no-ops).
    pub fn node_count(&self) -> usize {
        if self.tier == HydraTier::Off {
            return 0;
        }
        self.nodes.len()
    }

    /// Snapshot of liveness as a map (useful for supervisors).
    /// Empty in `Off` tier.
    pub fn liveness(&self) -> HashMap<String, bool> {
        if self.tier == HydraTier::Off {
            return HashMap::new();
        }
        self.nodes
            .iter()
            .map(|n| (n.clone(), self.alive.contains(n)))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_tier_is_monitor() {
        let m = HydraMesh::new();
        assert_eq!(m.tier(), HydraTier::Monitor);
        let d: HydraMesh = Default::default();
        assert_eq!(d.tier(), HydraTier::Monitor);
    }

    #[test]
    fn test_off_tier_all_noop() {
        let mut m = HydraMesh::with_tier(HydraTier::Off);
        m.add_node("a");
        m.add_node("b");
        assert_eq!(m.node_count(), 0);
        assert!(m.heartbeat("a"));
        assert_eq!(m.dead_nodes(), Vec::<String>::new());
        assert_eq!(m.respawn_dead(), Vec::<String>::new());
        assert_eq!(m.check_all(), (0, 0));
        assert!(m.liveness().is_empty());
        assert!(!m.mark_dead("a"));
    }

    #[test]
    fn test_heartbeat_and_dead_detection() {
        let mut m = HydraMesh::new();
        m.add_node("w1");
        m.add_node("w2");
        m.add_node("w3");
        assert_eq!(m.check_all(), (3, 0));
        assert!(m.mark_dead("w2"));
        assert_eq!(m.dead_nodes(), vec!["w2".to_string()]);
        assert_eq!(m.check_all(), (2, 1));
        // Unknown node heartbeat fails.
        assert!(!m.heartbeat("ghost"));
        // Revive via heartbeat.
        assert!(m.heartbeat("w2"));
        assert!(m.dead_nodes().is_empty());
        assert_eq!(m.check_all(), (3, 0));
    }

    #[test]
    fn test_monitor_respawn_is_report_only() {
        let mut m = HydraMesh::new(); // Monitor
        m.add_node("n1");
        m.add_node("n2");
        m.mark_dead("n1");
        // Reports the dead node ...
        assert_eq!(m.dead_nodes(), vec!["n1".to_string()]);
        // ... but takes no respawn action: returns [] and dead set unchanged.
        assert_eq!(m.respawn_dead(), Vec::<String>::new());
        assert_eq!(m.dead_nodes(), vec!["n1".to_string()]);
        assert_eq!(m.check_all(), (1, 1));
    }

    #[test]
    fn test_enforce_respawn_marks_alive() {
        let mut m = HydraMesh::with_tier(HydraTier::Enforce);
        m.add_node("n1");
        m.add_node("n2");
        m.mark_dead("n1");
        m.mark_dead("n2");
        let respawned = m.respawn_dead();
        assert_eq!(respawned, vec!["n1".to_string(), "n2".to_string()]);
        // Dead set cleared (caller must still spawn threads + heartbeat).
        assert!(m.dead_nodes().is_empty());
        assert_eq!(m.check_all(), (2, 0));
        // Second call with nothing dead returns [].
        assert!(m.respawn_dead().is_empty());
    }

    #[test]
    fn test_check_all_counts() {
        let mut m = HydraMesh::with_tier(HydraTier::Enforce);
        assert_eq!(m.check_all(), (0, 0));
        m.add_node("a");
        m.add_node("b");
        m.add_node("c");
        m.add_node("d");
        assert_eq!(m.check_all(), (4, 0));
        m.mark_dead("b");
        m.mark_dead("d");
        assert_eq!(m.check_all(), (2, 2));
        m.set_tier(HydraTier::Off);
        assert_eq!(m.check_all(), (0, 0));
    }

    #[test]
    fn test_add_duplicate_ignored_and_liveness_map() {
        let mut m = HydraMesh::new();
        m.add_node("x");
        m.add_node("x");
        assert_eq!(m.node_count(), 1);
        m.mark_dead("x");
        let live = m.liveness();
        assert_eq!(live.get("x"), Some(&false));
        // Unknown mark_dead returns false.
        assert!(!m.mark_dead("nope"));
    }

    #[test]
    fn test_set_tier_switching() {
        let mut m = HydraMesh::new();
        m.add_node("s1");
        m.mark_dead("s1");
        // Monitor: report only.
        assert!(m.respawn_dead().is_empty());
        // Switch to Enforce: now respawns.
        m.set_tier(HydraTier::Enforce);
        assert_eq!(m.respawn_dead(), vec!["s1".to_string()]);
        assert_eq!(m.tier(), HydraTier::Enforce);
    }
}
