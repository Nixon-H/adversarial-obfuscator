#[cfg(target_os = "linux")]
pub mod antidbg;
pub mod cli;
pub mod config;
pub mod payload;
// Tier 4 #8: the server half of Level-5 split execution.  Stdlib-only so the
// crate's dependency graph and release profile are unchanged.
pub mod remote;

#[cfg(feature = "attestation")]
pub mod attestation;

pub mod config_embed {
    include!(concat!(env!("OUT_DIR"), "/config_embed.rs"));
}
