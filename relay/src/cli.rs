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
