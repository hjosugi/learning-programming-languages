//! The stored value type, the serialization trait, and generic helpers.
//!
//! This module is where **enums + pattern matching**, a **custom trait**, and
//! **generics with trait bounds** come together.

use crate::error::{Result, StoreError};

/// A value held in the store.
///
/// An `enum` with data-carrying variants is Rust's tool for "a value that is
/// exactly one of these shapes". Compare with a tagged union in C or a sealed
/// class hierarchy in other languages — but here the compiler forces every
/// `match` to handle every variant.
#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    /// An integer; the only kind that `INCR`/`DECR` operate on.
    Int(i64),
    /// A UTF-8 string.
    Text(String),
    /// A list of values (note the recursion: `Value` contains `Vec<Value>`).
    List(Vec<Value>),
}

impl Value {
    /// Returns the inner integer, or a typed error naming the key, so callers
    /// can use `?`. Demonstrates returning `Result` from a small helper and
    /// matching on `self`.
    pub fn as_int(&self, key: &str) -> Result<i64> {
        match self {
            Value::Int(n) => Ok(*n),
            other => Err(StoreError::NotAnInteger {
                key: key.to_string(),
                // `render()` comes from the `Encode` trait below.
                found: other.render(),
            }),
        }
    }

    /// A human/wire friendly tag, handy for error messages and `TYPE`.
    pub fn type_name(&self) -> &'static str {
        match self {
            Value::Int(_) => "int",
            Value::Text(_) => "text",
            Value::List(_) => "list",
        }
    }
}

/// A **custom trait**: anything that can render itself to the store's simple
/// text wire format. Defining our own trait (rather than only using `Display`)
/// lets us attach store-specific behavior and use it as a generic bound.
///
/// We deliberately keep it tiny and object-safe so it can also be used behind
/// `&dyn Encode` if a caller wants dynamic dispatch.
pub trait Encode {
    /// Render `self` to a single-line string.
    fn render(&self) -> String;
}

impl Encode for Value {
    fn render(&self) -> String {
        match self {
            Value::Int(n) => n.to_string(),
            // Quote text so it round-trips and is visually distinct from ints.
            Value::Text(s) => format!("{s:?}"),
            Value::List(items) => {
                let inner: Vec<String> = items.iter().map(Encode::render).collect();
                format!("[{}]", inner.join(", "))
            }
        }
    }
}

// Blanket-ish impls for primitives so the generic `encode_all` below can be
// exercised with plain `i64`/`&str`, not just `Value`.
impl Encode for i64 {
    fn render(&self) -> String {
        self.to_string()
    }
}

impl Encode for str {
    fn render(&self) -> String {
        format!("{self:?}")
    }
}

/// A **generic function with a trait bound**: works for any iterator whose
/// items implement [`Encode`]. This is monomorphized per concrete type at
/// compile time (zero-cost abstraction), yet reads like a dynamic helper.
///
/// `T: Encode` is the bound; `I: IntoIterator<Item = T>` ties the element type
/// to the trait. Returning `String` keeps it simple to test.
pub fn encode_all<T, I>(items: I) -> String
where
    T: Encode,
    I: IntoIterator<Item = T>,
{
    items
        .into_iter()
        .map(|item| item.render())
        .collect::<Vec<_>>()
        .join("\n")
}

/// Conversions that make constructing `Value`s ergonomic. `From`/`Into` is the
/// idiomatic Rust conversion trait; these let tests write `42.into()`.
impl From<i64> for Value {
    fn from(n: i64) -> Self {
        Value::Int(n)
    }
}

impl From<String> for Value {
    fn from(s: String) -> Self {
        Value::Text(s)
    }
}

impl From<&str> for Value {
    fn from(s: &str) -> Self {
        Value::Text(s.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn render_covers_all_variants() {
        assert_eq!(Value::Int(7).render(), "7");
        assert_eq!(Value::Text("hi".into()).render(), "\"hi\"");
        let list = Value::List(vec![Value::Int(1), Value::from("a")]);
        assert_eq!(list.render(), "[1, \"a\"]");
    }

    #[test]
    fn as_int_ok_and_err() {
        assert_eq!(Value::Int(3).as_int("k").unwrap(), 3);
        let err = Value::from("nope").as_int("k").unwrap_err();
        assert_eq!(
            err,
            StoreError::NotAnInteger {
                key: "k".into(),
                found: "\"nope\"".into()
            }
        );
    }

    #[test]
    fn encode_all_is_generic_over_primitives() {
        // Exercised with i64 ...
        assert_eq!(encode_all(vec![1i64, 2, 3]), "1\n2\n3");
        // ... and with Value, proving the bound accepts both.
        let vals = vec![Value::Int(1), Value::from("x")];
        assert_eq!(encode_all(vals), "1\n\"x\"");
    }

    #[test]
    fn type_name_matches_variant() {
        assert_eq!(Value::Int(0).type_name(), "int");
        assert_eq!(Value::from("").type_name(), "text");
        assert_eq!(Value::List(vec![]).type_name(), "list");
    }
}
