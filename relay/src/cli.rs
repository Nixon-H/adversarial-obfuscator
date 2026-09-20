use clap::Parser;

#[derive(Parser, Clone)]
#[command(name = "orbital-relay", version, about = "Native payload launcher")]
pub struct Cli {
    #[arg(short, long)]
    pub payload: Option<String>,

    #[arg(long)]
    pub init_runtime: bool,

    #[arg(long, default_value_t = true)]
    pub antidebug: bool,
}
