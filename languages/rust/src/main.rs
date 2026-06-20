//! The `kvstore` binary: a tiny REPL over the [`kvstore`] library.
//!
//! Two modes:
//!   * No args  → interactive REPL reading lines from stdin until EOF.
//!   * With args → one-shot: the args are joined into a single command,
//!     executed, the result printed, and the process exits non-zero on error.
//!
//! This file shows how the library composes with `std::io`, the `?` operator,
//! and `Box<dyn Error>` for top-level error handling.

use std::io::{self, BufRead, Write};
use std::process::ExitCode;

use kvstore::command::parse;
use kvstore::Store;

fn main() -> ExitCode {
    // `args().skip(1)` drops the program name. Collecting into a Vec lets us
    // distinguish one-shot mode (args present) from REPL mode (none).
    let args: Vec<String> = std::env::args().skip(1).collect();

    if args.is_empty() {
        run_repl()
    } else {
        run_once(&args.join(" "))
    }
}

/// One-shot mode: execute a single command line and map the result to an
/// [`ExitCode`] so shells and the integration tests can assert on success.
fn run_once(line: &str) -> ExitCode {
    let mut store = Store::new();
    match parse(line).and_then(|cmd| store.execute(cmd)) {
        Ok(outcome) => {
            println!("{}", outcome.render());
            ExitCode::SUCCESS
        }
        Err(e) => {
            // Errors go to stderr; the `Display` impl gives a clean message.
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

/// Interactive REPL. Reads lines until EOF (Ctrl-D). Parse/exec errors are
/// reported but do not end the session — a long-lived store stays alive across
/// commands, which is the whole point of an in-memory store.
fn run_repl() -> ExitCode {
    let mut store = Store::new();
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    println!("kvstore REPL — try: SET k v | GET k | INCRBY n 1 | KEYS | LEN");
    print!("> ");
    let _ = stdout.flush();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        let trimmed = line.trim();

        // A couple of REPL-only conveniences that are not store commands.
        if trimmed.eq_ignore_ascii_case("quit") || trimmed.eq_ignore_ascii_case("exit") {
            break;
        }
        if trimmed.is_empty() {
            print!("> ");
            let _ = stdout.flush();
            continue;
        }

        match parse(trimmed).and_then(|cmd| store.execute(cmd)) {
            Ok(outcome) => println!("{}", outcome.render()),
            Err(e) => eprintln!("error: {e}"),
        }

        print!("> ");
        let _ = stdout.flush();
    }

    println!();
    ExitCode::SUCCESS
}
