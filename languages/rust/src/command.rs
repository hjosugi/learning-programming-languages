//! The command type and its parser.
//!
//! This module is the heart of the **enum + pattern matching** showcase: every
//! supported operation is a variant of [`Command`], and parsing is one big
//! `match` that turns a line of text into a typed, validated command.

use crate::error::{ParseError, Result};
use crate::value::Value;

/// One parsed, validated operation against the store.
///
/// Notice how each variant carries *exactly* the data that operation needs —
/// the type system makes illegal commands unrepresentable (e.g. there is no way
/// to build a `Get` without a key).
#[derive(Debug, Clone, PartialEq)]
pub enum Command {
    /// `SET key value [--nx]` — store a value. `nx` = only if Not eXists.
    Set { key: String, value: Value, nx: bool },
    /// `GET key` — fetch a value.
    Get { key: String },
    /// `DEL key` — remove a key.
    Del { key: String },
    /// `INCRBY key amount` — add `amount` to an integer value.
    IncrBy { key: String, amount: i64 },
    /// `TYPE key` — report the stored type.
    Type { key: String },
    /// `KEYS` — list all keys (sorted).
    Keys,
    /// `LEN` — number of stored keys.
    Len,
}

impl Command {
    /// The canonical command name, used in arity errors and help text.
    pub fn name(&self) -> &'static str {
        match self {
            Command::Set { .. } => "SET",
            Command::Get { .. } => "GET",
            Command::Del { .. } => "DEL",
            Command::IncrBy { .. } => "INCRBY",
            Command::Type { .. } => "TYPE",
            Command::Keys => "KEYS",
            Command::Len => "LEN",
        }
    }
}

/// Parse one line of input into a [`Command`].
///
/// The parser is intentionally small but realistic: it tokenizes on
/// whitespace, dispatches on the (case-insensitive) verb, checks arity, and
/// infers the value type for `SET` (digits-only ⇒ `Int`, otherwise `Text`).
///
/// # Examples
///
/// This doctest is compiled and run by `cargo test`:
///
/// ```
/// use kvstore::command::{parse, Command};
/// use kvstore::value::Value;
///
/// let cmd = parse("SET greeting hello").unwrap();
/// assert_eq!(
///     cmd,
///     Command::Set { key: "greeting".into(), value: Value::from("hello"), nx: false }
/// );
///
/// // A digits-only value is inferred as an integer.
/// assert_eq!(
///     parse("SET counter 41").unwrap(),
///     Command::Set { key: "counter".into(), value: Value::Int(41), nx: false }
/// );
///
/// // Unknown verbs are a typed error, not a panic.
/// assert!(parse("FROBNICATE x").is_err());
/// ```
pub fn parse(line: &str) -> Result<Command> {
    // `split_whitespace` borrows from `line`; the `&str` tokens live as long as
    // `line` does. We only allocate (`to_string`) when we actually keep a token.
    let tokens: Vec<&str> = line.split_whitespace().collect();

    // Slice patterns let us match on the shape of the token list directly.
    let (verb, args) = match tokens.as_slice() {
        [] => return Err(ParseError::EmptyInput.into()),
        [verb, rest @ ..] => (*verb, rest),
    };

    // Case-insensitive dispatch on the verb.
    let upper = verb.to_ascii_uppercase();
    match upper.as_str() {
        "SET" => parse_set(args),
        "GET" => Ok(Command::Get {
            key: one_arg("GET", args)?.to_string(),
        }),
        "DEL" => Ok(Command::Del {
            key: one_arg("DEL", args)?.to_string(),
        }),
        "TYPE" => Ok(Command::Type {
            key: one_arg("TYPE", args)?.to_string(),
        }),
        "INCRBY" => parse_incrby(args),
        "KEYS" => no_args("KEYS", args).map(|()| Command::Keys),
        "LEN" => no_args("LEN", args).map(|()| Command::Len),
        _ => Err(ParseError::UnknownCommand {
            token: verb.to_string(),
        }
        .into()),
    }
}

/// `SET key value [--nx]`. The value type is inferred from its text.
fn parse_set(args: &[&str]) -> Result<Command> {
    // Pull off an optional trailing `--nx` flag, then require exactly key+value.
    let (nx, rest) = match args {
        [front @ .., "--nx"] => (true, front),
        _ => (false, args),
    };

    match rest {
        [key, value] => Ok(Command::Set {
            key: key.to_string(),
            value: infer_value(value),
            nx,
        }),
        other => Err(ParseError::WrongArity {
            command: "SET",
            expected: 2,
            got: other.len(),
        }
        .into()),
    }
}

/// `INCRBY key amount` — the amount must parse as an `i64`.
fn parse_incrby(args: &[&str]) -> Result<Command> {
    match args {
        [key, amount] => {
            let amount = amount
                .parse::<i64>()
                .map_err(|_| ParseError::InvalidInteger {
                    token: (*amount).to_string(),
                })?;
            Ok(Command::IncrBy {
                key: key.to_string(),
                amount,
            })
        }
        other => Err(ParseError::WrongArity {
            command: "INCRBY",
            expected: 2,
            got: other.len(),
        }
        .into()),
    }
}

/// Infer a [`Value`] from a raw token: a clean `i64` becomes `Int`, everything
/// else becomes `Text`.
fn infer_value(raw: &str) -> Value {
    match raw.parse::<i64>() {
        Ok(n) => Value::Int(n),
        Err(_) => Value::from(raw),
    }
}

/// Arity helper: require exactly one argument.
fn one_arg<'a>(command: &'static str, args: &[&'a str]) -> Result<&'a str> {
    match args {
        [only] => Ok(only),
        other => Err(ParseError::WrongArity {
            command,
            expected: 1,
            got: other.len(),
        }
        .into()),
    }
}

/// Arity helper: require zero arguments.
fn no_args(command: &'static str, args: &[&str]) -> Result<()> {
    if args.is_empty() {
        Ok(())
    } else {
        Err(ParseError::WrongArity {
            command,
            expected: 0,
            got: args.len(),
        }
        .into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::StoreError;

    #[test]
    fn parses_get_and_del() {
        assert_eq!(parse("GET a").unwrap(), Command::Get { key: "a".into() });
        assert_eq!(parse("del b").unwrap(), Command::Del { key: "b".into() });
    }

    #[test]
    fn set_infers_value_type() {
        assert_eq!(
            parse("SET n 10").unwrap(),
            Command::Set {
                key: "n".into(),
                value: Value::Int(10),
                nx: false
            }
        );
        assert_eq!(
            parse("SET s hello").unwrap(),
            Command::Set {
                key: "s".into(),
                value: Value::from("hello"),
                nx: false
            }
        );
    }

    #[test]
    fn set_handles_nx_flag() {
        assert_eq!(
            parse("SET k v --nx").unwrap(),
            Command::Set {
                key: "k".into(),
                value: Value::from("v"),
                nx: true
            }
        );
    }

    #[test]
    fn incrby_requires_integer_amount() {
        assert_eq!(
            parse("INCRBY k 5").unwrap(),
            Command::IncrBy {
                key: "k".into(),
                amount: 5
            }
        );
        let err = parse("INCRBY k five").unwrap_err();
        assert_eq!(
            err,
            StoreError::Parse(ParseError::InvalidInteger {
                token: "five".into()
            })
        );
    }

    #[test]
    fn nullary_commands_reject_args() {
        assert_eq!(parse("KEYS").unwrap(), Command::Keys);
        assert_eq!(parse("LEN").unwrap(), Command::Len);
        assert!(matches!(
            parse("KEYS extra").unwrap_err(),
            StoreError::Parse(ParseError::WrongArity {
                command: "KEYS",
                ..
            })
        ));
    }

    #[test]
    fn empty_and_unknown_are_errors() {
        assert_eq!(
            parse("   ").unwrap_err(),
            StoreError::Parse(ParseError::EmptyInput)
        );
        assert_eq!(
            parse("nope a").unwrap_err(),
            StoreError::Parse(ParseError::UnknownCommand {
                token: "nope".into()
            })
        );
    }

    #[test]
    fn wrong_arity_reports_counts() {
        assert_eq!(
            parse("GET").unwrap_err(),
            StoreError::Parse(ParseError::WrongArity {
                command: "GET",
                expected: 1,
                got: 0
            })
        );
    }
}
