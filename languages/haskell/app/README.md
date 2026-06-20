# Haskell CLI Entry Point

This directory contains the small imperative shell for the Haskell calculator lab.

## Role

- reads command-line arguments
- calls the pure calculator code in `../src/Calc.hs`
- renders success or typed errors
- exits with a non-zero status on invalid input

The learning point is the separation between a pure functional core and a tiny
I/O shell.

## Run

From `languages/haskell`:

```bash
mise exec -- runghc -isrc app/Main.hs
mise exec -- runghc -isrc app/Main.hs "1 + 2 * 3"
```
