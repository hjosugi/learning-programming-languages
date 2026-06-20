//! The store itself: an owning `HashMap<String, Value>` plus the methods that
//! execute commands.
//!
//! This module is the clearest **ownership & borrowing** showcase:
//! - The store *owns* its keys and values (`HashMap<String, Value>`).
//! - Read methods borrow immutably (`&self`) and return *references* into the
//!   map (`Option<&Value>`) — no copying.
//! - Mutating methods take `&mut self`, so the borrow checker guarantees no
//!   other reference is alive while we mutate.

use std::collections::HashMap;

use crate::command::Command;
use crate::error::{Result, StoreError};
use crate::value::Value;

/// An in-memory key/value store.
///
/// `Default` is derived so `Store::default()` works; `new()` is provided for
/// readability at call sites.
#[derive(Debug, Default)]
pub struct Store {
    data: HashMap<String, Value>,
}

/// What executing a command produced. Returning a typed outcome (rather than a
/// pre-formatted string) keeps the core logic testable; formatting for the CLI
/// is a separate, lossless step in [`Outcome::render`].
#[derive(Debug, PartialEq)]
pub enum Outcome {
    /// `SET` / `DEL` succeeded.
    Ok,
    /// `GET` produced a value. We store an *owned* clone here (see the
    /// walkthrough on "clone vs borrow") so the outcome can outlive the
    /// `&Store` borrow it was read from.
    Value(Value),
    /// `INCRBY` returns the new integer.
    Int(i64),
    /// `TYPE` returns the type tag.
    Type(&'static str),
    /// `KEYS` returns owned, sorted key names.
    Keys(Vec<String>),
    /// `LEN` returns the key count.
    Len(usize),
}

impl Store {
    /// Create an empty store.
    pub fn new() -> Self {
        Store::default()
    }

    /// Insert or overwrite. Takes the key and value *by value* (ownership moves
    /// into the map), the canonical pattern for storing data.
    ///
    /// With `nx = true`, refuses to overwrite an existing key.
    pub fn set(&mut self, key: String, value: Value, nx: bool) -> Result<()> {
        if nx && self.data.contains_key(&key) {
            return Err(StoreError::KeyAlreadyExists { key });
        }
        self.data.insert(key, value);
        Ok(())
    }

    /// Borrow a value immutably. The returned reference borrows from `&self`;
    /// the elided lifetime means "lives as long as the `&self` borrow".
    /// Returning `Option<&Value>` is idiomatic: absence is not an error here.
    pub fn get(&self, key: &str) -> Option<&Value> {
        self.data.get(key)
    }

    /// Remove a key, returning the owned value if present. Demonstrates moving
    /// a value *out* of the store.
    pub fn del(&mut self, key: &str) -> Option<Value> {
        self.data.remove(key)
    }

    /// Add `amount` to an integer value, creating it at `0` if missing
    /// (Redis-like). Mutates in place through a `&mut Value` borrow.
    pub fn incr_by(&mut self, key: &str, amount: i64) -> Result<i64> {
        // `entry` gives a mutable handle, inserting a default if absent. This is
        // the borrow-checker-friendly way to do "get-or-insert then mutate".
        let slot = self.data.entry(key.to_string()).or_insert(Value::Int(0));
        let current = slot.as_int(key)?;
        let next = current.saturating_add(amount);
        *slot = Value::Int(next);
        Ok(next)
    }

    /// All keys, sorted for deterministic output (HashMap order is arbitrary).
    pub fn keys(&self) -> Vec<String> {
        let mut keys: Vec<String> = self.data.keys().cloned().collect();
        keys.sort();
        keys
    }

    /// Number of stored keys.
    pub fn len(&self) -> usize {
        self.data.len()
    }

    /// True if empty. Clippy expects this alongside `len`.
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    /// Execute a parsed [`Command`], the single entry point the CLI uses.
    ///
    /// This is another **pattern-matching** showcase: one `match` covers every
    /// command variant, and the compiler guarantees the match is exhaustive.
    pub fn execute(&mut self, command: Command) -> Result<Outcome> {
        match command {
            Command::Set { key, value, nx } => self.set(key, value, nx).map(|()| Outcome::Ok),
            Command::Get { key } => match self.get(&key) {
                // We clone here so `Outcome` can own its value and outlive the
                // borrow. See the README walkthrough on "clone vs borrow".
                Some(v) => Ok(Outcome::Value(v.clone())),
                None => Err(StoreError::KeyNotFound { key }),
            },
            Command::Del { key } => match self.del(&key) {
                Some(_) => Ok(Outcome::Ok),
                None => Err(StoreError::KeyNotFound { key }),
            },
            Command::IncrBy { key, amount } => self.incr_by(&key, amount).map(Outcome::Int),
            Command::Type { key } => match self.get(&key) {
                Some(v) => Ok(Outcome::Type(v.type_name())),
                None => Err(StoreError::KeyNotFound { key }),
            },
            Command::Keys => Ok(Outcome::Keys(self.keys())),
            Command::Len => Ok(Outcome::Len(self.len())),
        }
    }
}

impl Outcome {
    /// Render an outcome to a line of CLI output.
    pub fn render(&self) -> String {
        use crate::value::Encode;
        match self {
            Outcome::Ok => "OK".to_string(),
            Outcome::Value(v) => v.render(),
            Outcome::Int(n) => n.to_string(),
            Outcome::Type(t) => (*t).to_string(),
            Outcome::Keys(keys) => {
                if keys.is_empty() {
                    "(empty)".to_string()
                } else {
                    keys.join("\n")
                }
            }
            Outcome::Len(n) => n.to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::command::parse;

    /// Run a line through parse + execute, the way the CLI does.
    fn run(store: &mut Store, line: &str) -> Result<Outcome> {
        let cmd = parse(line)?;
        store.execute(cmd)
    }

    #[test]
    fn set_get_roundtrip() {
        let mut s = Store::new();
        assert_eq!(run(&mut s, "SET name alice").unwrap(), Outcome::Ok);
        assert_eq!(
            run(&mut s, "GET name").unwrap(),
            Outcome::Value(Value::from("alice"))
        );
    }

    #[test]
    fn get_missing_is_keynotfound() {
        let mut s = Store::new();
        assert_eq!(
            run(&mut s, "GET ghost").unwrap_err(),
            StoreError::KeyNotFound {
                key: "ghost".into()
            }
        );
    }

    #[test]
    fn nx_blocks_overwrite() {
        let mut s = Store::new();
        run(&mut s, "SET k 1").unwrap();
        let err = run(&mut s, "SET k 2 --nx").unwrap_err();
        assert_eq!(err, StoreError::KeyAlreadyExists { key: "k".into() });
        // The original value survives.
        assert_eq!(run(&mut s, "GET k").unwrap(), Outcome::Value(Value::Int(1)));
    }

    #[test]
    fn incrby_creates_and_accumulates() {
        let mut s = Store::new();
        assert_eq!(run(&mut s, "INCRBY hits 1").unwrap(), Outcome::Int(1));
        assert_eq!(run(&mut s, "INCRBY hits 4").unwrap(), Outcome::Int(5));
    }

    #[test]
    fn incrby_on_text_is_typed_error() {
        let mut s = Store::new();
        run(&mut s, "SET k hello").unwrap();
        let err = run(&mut s, "INCRBY k 1").unwrap_err();
        assert_eq!(
            err,
            StoreError::NotAnInteger {
                key: "k".into(),
                found: "\"hello\"".into()
            }
        );
    }

    #[test]
    fn del_then_get_fails() {
        let mut s = Store::new();
        run(&mut s, "SET k v").unwrap();
        assert_eq!(run(&mut s, "DEL k").unwrap(), Outcome::Ok);
        assert!(run(&mut s, "GET k").is_err());
        assert_eq!(
            run(&mut s, "DEL k").unwrap_err(),
            StoreError::KeyNotFound { key: "k".into() }
        );
    }

    #[test]
    fn keys_are_sorted_and_len_tracks() {
        let mut s = Store::new();
        run(&mut s, "SET b 2").unwrap();
        run(&mut s, "SET a 1").unwrap();
        run(&mut s, "SET c 3").unwrap();
        assert_eq!(
            run(&mut s, "KEYS").unwrap(),
            Outcome::Keys(vec!["a".into(), "b".into(), "c".into()])
        );
        assert_eq!(run(&mut s, "LEN").unwrap(), Outcome::Len(3));
        assert!(!s.is_empty());
    }

    #[test]
    fn type_reports_inferred_kind() {
        let mut s = Store::new();
        run(&mut s, "SET n 10").unwrap();
        run(&mut s, "SET t hello").unwrap();
        assert_eq!(run(&mut s, "TYPE n").unwrap(), Outcome::Type("int"));
        assert_eq!(run(&mut s, "TYPE t").unwrap(), Outcome::Type("text"));
    }
}
