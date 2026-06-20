//! Integration tests.
//!
//! Unlike the `#[cfg(test)]` unit tests inside `src/`, files under `tests/` are
//! compiled as *separate crates* that link against `kvstore` as an external
//! dependency. They therefore exercise only the **public API** — exactly what a
//! downstream user would see — and (here) the compiled **binary** via a
//! subprocess.

use std::process::Command as ProcCommand;

use kvstore::command::parse;
use kvstore::store::Outcome;
use kvstore::{Store, StoreError, Value};

/// Drive a whole session through the public library API and assert on the
/// sequence of outcomes. This is the "library user" perspective.
#[test]
fn full_session_through_public_api() {
    let mut store = Store::new();

    let script = [
        ("SET user alice", Ok(Outcome::Ok)),
        ("GET user", Ok(Outcome::Value(Value::from("alice")))),
        ("SET score 100", Ok(Outcome::Ok)),
        ("INCRBY score 23", Ok(Outcome::Int(123))),
        ("TYPE score", Ok(Outcome::Type("int"))),
        ("LEN", Ok(Outcome::Len(2))),
    ];

    for (line, expected) in script {
        let cmd = parse(line).expect("script commands parse");
        let got = store.execute(cmd);
        assert_eq!(got, expected, "line was: {line}");
    }
}

/// Error cases flow through as typed `StoreError` values — never panics.
#[test]
fn error_cases_are_typed() {
    let mut store = Store::new();

    let cmd = parse("GET missing").unwrap();
    assert_eq!(
        store.execute(cmd).unwrap_err(),
        StoreError::KeyNotFound {
            key: "missing".into()
        }
    );

    parse("SET k hello").and_then(|c| store.execute(c)).unwrap();
    let cmd = parse("INCRBY k 1").unwrap();
    assert_eq!(
        store.execute(cmd).unwrap_err(),
        StoreError::NotAnInteger {
            key: "k".into(),
            found: "\"hello\"".into()
        }
    );

    // A parse-level error surfaces as StoreError::Parse.
    assert!(matches!(
        parse("BOGUS x").unwrap_err(),
        StoreError::Parse(_)
    ));
}

/// `StoreError` is a real `std::error::Error`: it can be boxed and its `source`
/// chain is reachable. This proves ecosystem interop with std only.
#[test]
fn store_error_is_std_error() {
    let err = parse("nope").unwrap_err();
    let boxed: Box<dyn std::error::Error> = Box::new(err);
    // The Display message is non-empty and the source chain is present for
    // parse errors.
    assert!(!boxed.to_string().is_empty());
    assert!(boxed.source().is_some());
}

/// Find the compiled `kvstore` binary that Cargo built for this test run.
/// `CARGO_BIN_EXE_<name>` is set by Cargo specifically for integration tests.
fn bin_path() -> &'static str {
    env!("CARGO_BIN_EXE_kvstore")
}

/// One-shot CLI mode: success path prints the value and exits 0.
#[test]
fn cli_oneshot_success_exits_zero() {
    let output = ProcCommand::new(bin_path())
        .args(["SET", "k", "42"])
        .output()
        .expect("binary runs");
    assert!(output.status.success());
    assert_eq!(String::from_utf8_lossy(&output.stdout).trim(), "OK");
}

/// One-shot CLI mode: an unknown command exits non-zero and writes to stderr.
#[test]
fn cli_oneshot_error_exits_nonzero() {
    let output = ProcCommand::new(bin_path())
        .args(["FROBNICATE", "x"])
        .output()
        .expect("binary runs");
    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("error:"), "stderr was: {stderr}");
}
