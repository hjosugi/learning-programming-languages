//! # kvstore — a tiny typed in-memory key/value store
//!
//! This library is a deliberately small but *idiomatic* tour of Rust's
//! signature features. It is std-only (no external crates) so it builds offline.
//!
//! The data flow is: text line → [`command::parse`] → [`command::Command`] →
//! [`store::Store::execute`] → [`store::Outcome`] → rendered string.
//!
//! ## What each piece demonstrates
//!
//! | Concept | Where |
//! | --- | --- |
//! | Ownership & borrowing | [`store`] (`HashMap<String, Value>`, `&self` vs `&mut self`) |
//! | Lifetimes | [`store::Store::get`] returning `Option<&Value>` |
//! | Enums + pattern matching | [`value::Value`], [`command::Command`] |
//! | Custom trait + generics | [`value::Encode`] + [`value::encode_all`] |
//! | `Result`/`Option` + custom error | [`error::StoreError`] |
//!
//! ## End-to-end example (runs as a doctest)
//!
//! ```
//! use kvstore::{Store, command::parse};
//! use kvstore::store::Outcome;
//!
//! let mut store = Store::new();
//!
//! // Each line is parsed and executed.
//! for line in ["SET visits 0", "INCRBY visits 3", "INCRBY visits 4"] {
//!     let cmd = parse(line).expect("valid command");
//!     store.execute(cmd).expect("succeeds");
//! }
//!
//! // The final value is read back.
//! let cmd = parse("GET visits").unwrap();
//! assert_eq!(store.execute(cmd).unwrap(), Outcome::Value(7i64.into()));
//!
//! // Errors are values, not panics.
//! let missing = parse("GET nope").unwrap();
//! assert!(store.execute(missing).is_err());
//! ```

pub mod command;
pub mod error;
pub mod store;
pub mod value;

// Re-export the most-used types at the crate root for ergonomic imports
// (`use kvstore::{Store, Value};`).
pub use error::{ParseError, Result, StoreError};
pub use store::{Outcome, Store};
pub use value::{encode_all, Encode, Value};
