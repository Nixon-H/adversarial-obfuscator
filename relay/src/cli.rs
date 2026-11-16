use clap::Parser;

#[derive(Parser, Clone)]
#[command(name = "orbital-relay", version, about = "Native payload launcher")]
pub struct Cli {
    #[arg(short, long)]
    pub payload: Option<String>,

    /// Skip protection-runtime initialisation.
    ///
    /// The runtime is initialised by DEFAULT. It used to be the other
    /// way round: `--init-runtime` was opt-in, and nothing in the build,
    /// the e2e checks or any config ever passed it — so the whole
    /// nixon-runtime crate was dead code in every shipped path. This
    /// flag is now an explicit opt-OUT, for debugging a bare launch.
    #[arg(long = "no-init-runtime", action = clap::ArgAction::SetTrue)]
    pub no_init_runtime: bool,

    #[arg(long, default_value_t = true)]
    pub antidebug: bool,

    /// Serve remote functions (Tier 4 #8, Level-5 split execution).
    ///
    /// The client artefact carries a stub for every `@remote` function; this
    /// process holds the implementation.  The shared secret is read from
    /// NIXON_REMOTE_SECRET (never from argv, never from a file in the repo).
    #[arg(long)]
    pub serve_remote: bool,

    /// Bind address for --serve-remote (default 127.0.0.1:8787).
    #[arg(long, default_value = "127.0.0.1:8787")]
    pub remote_bind: String,

    /// Allow binding a non-loopback address.  The endpoint speaks plain
    /// HTTP, so this exposes the arguments to the network; put it behind a
    /// TLS terminator if you need that.
    #[arg(long, action = clap::ArgAction::SetTrue)]
    pub allow_remote: bool,

    /// Path to the operator's Python bundle (the implementations that never
    /// ship).  Requests for functions the Rust side does not register are
    /// forwarded here.
    #[arg(long)]
    pub remote_bundle: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn runtime_initialises_without_being_asked() {
        // The regression this pins: `--init-runtime` used to be opt-in and
        // nothing passed it, so nixon-runtime never ran in a shipped path.
        let cli = Cli::parse_from(["orbital-relay", "--payload", "p.py"]);
        assert!(!cli.no_init_runtime, "the protection runtime must run by default");
    }

    #[test]
    fn the_opt_out_disables_it() {
        let cli = Cli::parse_from(["orbital-relay", "--no-init-runtime"]);
        assert!(cli.no_init_runtime);
    }

    #[test]
    fn antidebug_stays_on_by_default() {
        let cli = Cli::parse_from(["orbital-relay"]);
        assert!(cli.antidebug);
    }
}
