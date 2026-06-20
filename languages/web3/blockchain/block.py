"""The Block: a header that chains to its parent + a list of transactions.

A block has two parts:

* a **header** -- index, timestamp, previous block's hash, the Merkle root of
  its transactions, the difficulty target, and a nonce -- and
* a **body** -- the ordered list of transactions.

The block hash is SHA-256 over the header fields. Crucially the header
includes both the ``prev_hash`` (linking it to its parent) and the
``merkle_root`` (committing to every transaction in the body). That single
hash is therefore a fingerprint of the entire chain history up to and
including this block: change anything, and the hash changes.

**Proof-of-work mining** is the loop that searches for a ``nonce`` making the
block hash satisfy the difficulty target (a number of leading zero hex
characters). Finding such a nonce is expensive (you must try on average
~16**difficulty hashes); checking it is one hash. That asymmetry is what
secures the chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from .crypto import hash_strings, meets_difficulty, merkle_root
from .transaction import Transaction


@dataclass
class Block:
    """A single block in the chain.

    ``timestamp`` is *passed in* (not read from the wall clock) so that mining
    and hashing are fully deterministic and reproducible in tests. In the demo
    we feed a monotonic counter; a real node would use network-validated time.
    """

    index: int
    timestamp: int
    transactions: List[Transaction]
    prev_hash: str
    difficulty: int
    nonce: int = 0
    # merkle_root and hash are derived; computed in __post_init__ / mining.
    merkle_root: str = field(default="", init=False)
    hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        # The Merkle root is a pure function of the transaction list, so we
        # can compute it once at construction. The block hash depends on the
        # nonce, so it is (re)computed during/after mining.
        self.merkle_root = self.compute_merkle_root()
        self.hash = self.compute_hash()

    # --- derivation ------------------------------------------------------

    def compute_merkle_root(self) -> str:
        """Merkle root over the canonical form of each transaction."""
        leaves: Sequence[str] = [tx.canonical() for tx in self.transactions]
        return merkle_root(leaves)

    def header_fields(self) -> tuple:
        """The exact, ordered tuple of fields that the block hash commits to.

        Note this does *not* include the raw transactions -- they are
        committed via ``merkle_root``. This is how real headers stay small and
        fixed-size regardless of how many transactions a block carries.
        """
        return (
            self.index,
            self.timestamp,
            self.prev_hash,
            self.merkle_root,
            self.difficulty,
            self.nonce,
        )

    def compute_hash(self) -> str:
        """SHA-256 over the header fields -> the block's identity."""
        return hash_strings(*self.header_fields())

    # --- proof of work ---------------------------------------------------

    def is_valid_proof(self) -> bool:
        """Does the current stored hash satisfy the difficulty target?"""
        return (
            self.hash == self.compute_hash()
            and meets_difficulty(self.hash, self.difficulty)
        )

    def mine(self) -> int:
        """Search for a nonce so the block hash meets the difficulty target.

        Returns the number of hash attempts made (useful for the demo's
        "this took N hashes" output). The Merkle root must already be set,
        which ``__post_init__`` guarantees. Each iteration bumps the nonce and
        recomputes the hash; we stop at the first nonce that satisfies the
        target. Because SHA-256 output is effectively uniform, the expected
        number of attempts is ~16**difficulty.
        """
        attempts = 0
        while True:
            attempts += 1
            candidate = self.compute_hash()
            if meets_difficulty(candidate, self.difficulty):
                self.hash = candidate
                return attempts
            self.nonce += 1

    def __str__(self) -> str:
        return (
            f"Block #{self.index} (txs={len(self.transactions)}, "
            f"nonce={self.nonce}, hash={self.hash[:16]}...)"
        )
