# Zig Basics Lab

Small Zig exercises for data structures and file processing.

## Run

On this machine `zig` is reached via `mise exec --` (it is not on bare `PATH`):

```bash
mise exec -- zig build test
mise exec -- zig build run
```

(With `zig` already on `PATH` — e.g. inside `nix develop` — drop the
`mise exec --` prefix.)

## Topics

- dynamic arrays
- ring buffers
- simple frequency counting
- error handling with named error sets and error unions (e.g. the `wordfreq`
  CLI returns `error.InvalidTopArgument` from `parseArgs` on a non-numeric
  `--top` value; see the matching `test` in `src/main.zig`)

## Further learning

- Named learning targets + Definition of Done: [docs/2026-learning-items.md](docs/2026-learning-items.md)
- Curated hands-on resources (2026 edition) and canonical primary sources:
  [docs/learning-resources.md](docs/learning-resources.md)
