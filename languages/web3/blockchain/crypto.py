"""Cryptographic primitives for the from-scratch blockchain.

Everything here is built on Python's standard-library ``hashlib`` only --
no external dependencies. The two ideas this module teaches are:

1. **Deterministic hashing**: the same bytes always produce the same
   SHA-256 digest, and any change (even one bit) produces a completely
   different digest (the *avalanche* effect). This is what makes a
   blockchain tamper-evident.

2. **Merkle roots**: a single 32-byte fingerprint that commits to an
   *ordered list* of transactions, so changing any transaction -- or
   reordering them -- changes the root. Real chains (Bitcoin, Ethereum)
   use Merkle trees so a light client can verify that one transaction is
   included without downloading the whole block.
"""

from __future__ import annotations

import hashlib
from typing import Iterable, Sequence


def sha256_hex(data: bytes) -> str:
    """Return the hex-encoded SHA-256 digest of ``data``.

    We work in hex (a 64-character string) everywhere because it is easy to
    print, compare, and test against a leading-zero proof-of-work target.
    """
    return hashlib.sha256(data).hexdigest()


def double_sha256_hex(data: bytes) -> str:
    """SHA-256 applied twice -- the construction Bitcoin uses (``HASH256``).

    Double hashing guards against a class of length-extension attacks on the
    raw Merkle-Damgard SHA-256 construction. We expose it mainly so the
    Merkle tree below mirrors Bitcoin's real algorithm.
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()


def hash_strings(*parts: object) -> str:
    """Hash an ordered sequence of fields into one SHA-256 hex digest.

    Each field is converted to text and joined with a NUL separator so that
    ``("ab", "c")`` and ``("a", "bc")`` cannot collide to the same preimage.
    A NUL byte ``\\x00`` is used because it never appears in our textual
    fields, making the encoding injective for the data we feed it.
    """
    payload = "\x00".join(str(p) for p in parts)
    return sha256_hex(payload.encode("utf-8"))


def merkle_root(leaves: Sequence[str]) -> str:
    """Compute a Bitcoin-style Merkle root over an ordered list of leaves.

    ``leaves`` are the canonical string forms of the transactions in a block.
    The algorithm:

    * The empty block has a well-defined root (the hash of the empty string),
      so a block with no transactions still gets a stable ``merkle_root``.
    * Each leaf is hashed once to get a leaf node.
    * Pairs of nodes are concatenated and hashed to form the parent level.
    * If a level has an odd number of nodes, the last node is duplicated
      (paired with itself) -- exactly what Bitcoin does.
    * Repeat until a single root node remains.

    Because the tree is built bottom-up over an *ordered* list, changing any
    leaf, adding a leaf, or reordering leaves all change the root.
    """
    if not leaves:
        # Distinct, stable sentinel for an empty transaction set.
        return double_sha256_hex(b"")

    # Level 0: hash each leaf so even a single transaction is committed via a
    # hash rather than its raw bytes.
    level = [double_sha256_hex(leaf.encode("utf-8")) for leaf in leaves]

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])  # duplicate the last node (Bitcoin rule)
        nxt: list[str] = []
        for i in range(0, len(level), 2):
            combined = (level[i] + level[i + 1]).encode("utf-8")
            nxt.append(double_sha256_hex(combined))
        level = nxt

    return level[0]


def leading_zero_bits(hex_digest: str) -> int:
    """Count how many leading binary zero bits a hex digest has.

    Useful for difficulty in *bits* rather than *hex characters*. One hex
    character is 4 bits, so this gives finer-grained difficulty control if you
    extend the exercises. Not used by the default PoW (which counts hex
    nibbles) but handy for experimentation.
    """
    bits = 0
    for ch in hex_digest:
        nibble = int(ch, 16)
        if nibble == 0:
            bits += 4
            continue
        # Count the leading zeros within this 4-bit nibble, then stop.
        for shift in (3, 2, 1, 0):
            if (nibble >> shift) & 1:
                break
            bits += 1
        break
    return bits


def meets_difficulty(hex_digest: str, difficulty: int) -> bool:
    """Return True if ``hex_digest`` starts with ``difficulty`` zero hex chars.

    This is the proof-of-work target check: the miner must find a nonce whose
    block hash has at least ``difficulty`` leading ``0`` characters. Each extra
    leading zero makes the search ~16x harder on average.
    """
    if difficulty < 0:
        raise ValueError("difficulty must be non-negative")
    return hex_digest.startswith("0" * difficulty)


def all_hashes(items: Iterable[object]) -> list[str]:
    """Hash each item in an iterable. Small helper used by tests/exercises."""
    return [hash_strings(item) for item in items]
