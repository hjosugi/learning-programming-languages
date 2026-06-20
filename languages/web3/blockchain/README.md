# Toy Blockchain Package

Dependency-free Python package for learning blockchain data structures and invariants.

This package is intentionally local and educational. It does not implement networking,
wallet security, consensus, smart contracts, or production cryptography.

## Files

| File | What it teaches |
| --- | --- |
| `crypto.py` | deterministic hashing, leading-zero difficulty, Merkle roots |
| `transaction.py` | transaction model, coinbase detection, canonical serialization |
| `block.py` | block headers, nonce search, proof-of-work checks |
| `chain.py` | chain validation, balances, mempool overspend checks |
| `demo.py` | short walkthrough |
| `test_chain.py` | invariant tests |

## Run

From `languages/web3`:

```bash
python3 blockchain/demo.py
python3 blockchain/test_chain.py
```

## What To Notice

- changing a transaction changes the Merkle root
- changing a block breaks later `prev_hash` links
- proof-of-work is easy to verify but expensive to search
- mempool validation must reject cumulative overspend, not just single bad transactions
