//! Error types for the key/value store.
//!
//! This module showcases **`Result`/`Option`-based error handling with a
//! custom error enum**. `StoreError` implements both [`std::fmt::Display`] and
//! [`std::error::Error`], so it composes with the wider Rust error ecosystem
//! (`Box<dyn Error>`, the `?` operator, `anyhow`, etc.) without any external
//! crate.

use std::fmt;

/// Every fallible operation in this crate returns `Result<T, StoreError>`.
///
/// Modeling failures as a *closed enum* (rather than stringly-typed errors)
/// means callers can `match` on the exact failure and the compiler will warn
/// them when a new variant is added. This is the idiomatic Rust alternative to
/// exceptions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StoreError {
    /// A `Get`/`Del`/`Incr` targeted a key that does not exist.
    KeyNotFound { key: String },

    /// A `Set` would overwrite an existing key while the `--nx` ("not exists")
    /// guard was requested. Carries the key for a helpful message.
    KeyAlreadyExists { key: String },

    /// `Incr`/`Decr` was applied to a value that is not an integer.
    NotAnInteger { key: String, found: String },

    /// The command parser could not understand the input line.
    Parse(ParseError),
}

/// Fine-grained parse failures, kept separate so the parser can be tested in
/// isolation and so `StoreError::Parse` can wrap them.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    /// The line was empty or only whitespace.
    EmptyInput,
    /// The first token was not a known command.
    UnknownCommand { token: String },
    /// A command received the wrong number of arguments.
    WrongArity {
        command: &'static str,
        expected: usize,
        got: usize,
    },
    /// A value that was supposed to be an integer (e.g. the amount for `INCRBY`)
    /// did not parse.
    InvalidInteger { token: String },
}

impl fmt::Display for StoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            StoreError::KeyNotFound { key } => {
                write!(f, "key not found: {key:?}")
            }
            StoreError::KeyAlreadyExists { key } => {
                write!(f, "key already exists: {key:?}")
            }
            StoreError::NotAnInteger { key, found } => {
                write!(f, "value at {key:?} is not an integer: {found:?}")
            }
            StoreError::Parse(e) => write!(f, "parse error: {e}"),
        }
    }
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::EmptyInput => write!(f, "empty input"),
            ParseError::UnknownCommand { token } => {
                write!(f, "unknown command: {token:?}")
            }
            ParseError::WrongArity {
                command,
                expected,
                got,
            } => write!(
                f,
                "command {command:?} expects {expected} argument(s), got {got}"
            ),
            ParseError::InvalidInteger { token } => {
                write!(f, "invalid integer: {token:?}")
            }
        }
    }
}

// Implementing `std::error::Error` is what lets `StoreError` flow into
// `Box<dyn Error>` and interoperate with the rest of the ecosystem. `source()`
// exposes the wrapped `ParseError` so error-reporting tools can print a chain.
impl std::error::Error for StoreError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            StoreError::Parse(e) => Some(e),
            _ => None,
        }
    }
}

impl std::error::Error for ParseError {}

// A `From` impl makes `?` ergonomic: a function returning `Result<_, StoreError>`
// can use `?` on a `Result<_, ParseError>` and the conversion happens for free.
impl From<ParseError> for StoreError {
    fn from(e: ParseError) -> Self {
        StoreError::Parse(e)
    }
}

/// Crate-wide result alias. Idiomatic Rust libraries expose one of these so
/// signatures stay short: `fn get(..) -> Result<..>`.
pub type Result<T> = std::result::Result<T, StoreError>;
