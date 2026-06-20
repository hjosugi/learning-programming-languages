"""A from-scratch blockchain in pure Python (stdlib ``hashlib`` only).

Public surface:

* :class:`~blockchain.block.Block` -- a mineable, self-hashing block.
* :class:`~blockchain.chain.Blockchain` -- the append-only, self-validating chain.
* :class:`~blockchain.transaction.Transaction` / :class:`~blockchain.transaction.Mempool`
  -- the account-balance transaction model and overspend-rejecting mempool.
* :mod:`~blockchain.crypto` -- SHA-256 hashing, Merkle roots, PoW target checks.
"""

from .block import Block
from .chain import Blockchain, coinbase_tx, GENESIS_PREV_HASH
from .crypto import (
    hash_strings,
    merkle_root,
    meets_difficulty,
    sha256_hex,
)
from .transaction import (
    COINBASE,
    InsufficientFundsError,
    Mempool,
    Transaction,
)

__all__ = [
    "Block",
    "Blockchain",
    "Mempool",
    "Transaction",
    "InsufficientFundsError",
    "COINBASE",
    "GENESIS_PREV_HASH",
    "coinbase_tx",
    "hash_strings",
    "merkle_root",
    "meets_difficulty",
    "sha256_hex",
]
