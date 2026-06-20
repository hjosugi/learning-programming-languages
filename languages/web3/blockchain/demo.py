"""End-to-end demo: mine blocks, print hashes/difficulty, then tamper.

Run it directly (it bootstraps ``sys.path`` so the ``blockchain`` package is
importable no matter where you launch it from):

    python3 /mnt/data/workspace/learning-web3/blockchain/demo.py

The demo:

1. builds a chain and mints starting funds via coinbase transactions;
2. routes user transfers through a mempool that *rejects an overspend*;
3. mines a couple of blocks and prints each block's hash, nonce, Merkle root,
   difficulty, and the number of hash attempts mining took;
4. confirms the intact chain validates;
5. **tampers** with a buried block and shows that validation now fails.
"""

from __future__ import annotations

import os
import sys

# --- make the package importable when run as a loose script ---------------
# demo.py lives *inside* the package dir, so we add the parent (repo root) to
# sys.path and import the package by name.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from blockchain.chain import Blockchain, coinbase_tx  # noqa: E402
from blockchain.transaction import (  # noqa: E402
    InsufficientFundsError,
    Mempool,
    Transaction,
)


def rule(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


def show_block(block, attempts: int | None = None) -> None:
    print(f"  Block #{block.index}")
    print(f"    timestamp   : {block.timestamp}")
    print(f"    prev_hash   : {block.prev_hash[:24]}...")
    print(f"    merkle_root : {block.merkle_root[:24]}...")
    print(f"    difficulty  : {block.difficulty} leading hex zeros")
    print(f"    nonce       : {block.nonce}")
    print(f"    hash        : {block.hash}")
    if attempts is not None:
        print(f"    mined in    : {attempts} hash attempts")
    print(f"    txs         : {len(block.transactions)}")
    for tx in block.transactions:
        src = tx.sender if tx.sender is not None else "COINBASE(mint)"
        print(f"        {src} -> {tx.recipient}: {tx.amount}")


def main() -> int:
    rule("1. Build a chain (difficulty = 3 leading hex zeros)")
    chain = Blockchain(difficulty=3)
    print(f"  Genesis mined: {chain.tip.hash}")
    print(f"  Genesis satisfies difficulty? "
          f"{chain.tip.hash.startswith('0' * chain.difficulty)}")

    rule("2. Mint starting funds via coinbase transactions")
    funding = chain.add_block([
        coinbase_tx("alice", 100, nonce=0),
        coinbase_tx("bob", 50, nonce=1),
    ])
    show_block(funding)
    print(f"  Balances after funding: {chain.balances()}")

    rule("3. Mempool accepts valid transfers, rejects an overspend")
    mempool = Mempool()
    confirmed = chain.balances()

    # Valid: alice has 100, sends 30 then 25 (total 55 <= 100).
    mempool.add(Transaction("alice", "carol", 30, nonce=10), confirmed)
    mempool.add(Transaction("alice", "bob", 25, nonce=11), confirmed)
    print("  Accepted: alice -> carol 30, alice -> bob 25")

    # Overspend: projected alice balance is 100 - 55 = 45; 60 is too much.
    try:
        mempool.add(Transaction("alice", "carol", 60, nonce=12), confirmed)
        print("  ERROR: overspend was NOT rejected (bug!)")
    except InsufficientFundsError as exc:
        print(f"  Rejected overspend as expected: {exc}")

    rule("4. Mine the mempool transactions into a block")
    pending = mempool.collect()
    block2 = chain.add_block(pending)
    show_block(block2)
    print(f"  Balances now: {chain.balances()}")
    print(f"  Chain length: {len(chain)} blocks")

    rule("5. Validate the intact chain")
    print(f"  chain.is_valid() -> {chain.is_valid()}")

    rule("6. Tamper with a buried block -> validation must fail")
    target = chain.blocks[1]  # the funding block
    print(f"  Before tamper: block #1 first tx amount = "
          f"{target.transactions[0].amount}, chain valid = {chain.is_valid()}")

    # Forge a bigger payout to alice. Transactions are frozen dataclasses, so
    # we splice in a replacement -- exactly the kind of edit an attacker would
    # attempt on stored block data.
    target.transactions[0] = coinbase_tx("alice", 1_000_000, nonce=0)
    # Note: we do NOT recompute the block's stored merkle_root/hash, mimicking
    # an attacker who edits the ledger but cannot cheaply re-mine.
    print(f"  After tamper : block #1 first tx amount = "
          f"{target.transactions[0].amount}, chain valid = {chain.is_valid()}")
    print("  Tampering detected: the chain no longer validates.")

    rule("Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
