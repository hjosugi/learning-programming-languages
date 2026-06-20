"""The Blockchain: an append-only, self-validating list of mined blocks.

This ties the other modules together:

* a **genesis block** (index 0) anchors the chain with a fixed ``prev_hash``;
* ``add_block`` mines a new block on top of the current tip;
* ``is_valid`` re-derives every block from scratch and checks three things for
  each block -- (1) the stored hash equals a fresh re-hash of the header,
  (2) the ``prev_hash`` actually points at the parent's hash, and (3) the hash
  satisfies the proof-of-work difficulty. It also re-checks the Merkle root,
  so mutating a buried transaction is detected even though the chain "looks"
  intact.

**Tamper detection** falls straight out of this: if you mutate any field of a
past block -- a transaction amount, the index, anything -- its recomputed hash
no longer matches what its child stored as ``prev_hash``, and ``is_valid``
returns False. You would have to re-mine that block *and every block after it*
to forge a consistent chain, which is the whole economic point of PoW.

The chain also tracks **account balances** by replaying every transaction in
order, which is what the mempool consults to reject overspends.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .block import Block
from .crypto import meets_difficulty
from .transaction import Transaction

# The genesis block has no parent; we use a fixed sentinel for its prev_hash.
GENESIS_PREV_HASH = "0" * 64


class Blockchain:
    """An in-memory chain of mined blocks plus derived account state."""

    def __init__(self, difficulty: int = 3) -> None:
        if difficulty < 0:
            raise ValueError("difficulty must be non-negative")
        self.difficulty = difficulty
        self._next_timestamp = 0  # monotonic counter -> deterministic hashes
        self.blocks: List[Block] = [self._make_genesis()]

    # --- construction ----------------------------------------------------

    def _tick(self) -> int:
        """Return a strictly increasing timestamp for the next block."""
        ts = self._next_timestamp
        self._next_timestamp += 1
        return ts

    def _make_genesis(self) -> Block:
        """Mine the first block. It carries no transactions."""
        genesis = Block(
            index=0,
            timestamp=self._tick(),
            transactions=[],
            prev_hash=GENESIS_PREV_HASH,
            difficulty=self.difficulty,
        )
        genesis.mine()
        return genesis

    @property
    def tip(self) -> Block:
        """The most recent (highest-index) block."""
        return self.blocks[-1]

    # --- mutation --------------------------------------------------------

    def add_block(self, transactions: List[Transaction]) -> Block:
        """Mine and append a new block carrying ``transactions``.

        The new block links to the current tip via ``prev_hash`` and is mined
        to satisfy the chain difficulty before being appended. We do not allow
        appending an unmined block -- ``mine`` runs here.
        """
        block = Block(
            index=self.tip.index + 1,
            timestamp=self._tick(),
            transactions=list(transactions),
            prev_hash=self.tip.hash,
            difficulty=self.difficulty,
        )
        block.mine()
        self.blocks.append(block)
        return block

    # --- validation ------------------------------------------------------

    def is_valid(self) -> bool:
        """Re-derive and verify the entire chain from genesis to tip.

        Returns False at the first inconsistency. This is the function that
        makes tampering detectable: it never trusts a block's stored fields,
        it recomputes everything (Merkle root, header hash) and checks the
        links and proof-of-work.
        """
        for i, block in enumerate(self.blocks):
            # (0) The Merkle root must still match the transactions. A buried
            #     transaction edit changes this even if the attacker forgot to
            #     touch the stored hash.
            if block.merkle_root != block.compute_merkle_root():
                return False

            # (1) The stored hash must equal a fresh re-hash of the header.
            if block.hash != block.compute_hash():
                return False

            # (2) The hash must satisfy proof-of-work difficulty.
            if not meets_difficulty(block.hash, block.difficulty):
                return False

            # (3) Linkage: genesis points at the sentinel, every other block
            #     points at its parent's hash.
            if i == 0:
                if block.prev_hash != GENESIS_PREV_HASH or block.index != 0:
                    return False
            else:
                parent = self.blocks[i - 1]
                if block.prev_hash != parent.hash:
                    return False
                if block.index != parent.index + 1:
                    return False

        return True

    # --- account state ---------------------------------------------------

    def balances(self) -> Dict[str, int]:
        """Replay every confirmed transaction to derive account balances.

        Coinbase transactions credit the recipient without debiting anyone
        (new supply). Every other transaction debits the sender and credits
        the recipient. The mempool uses this snapshot to reject overspends.
        """
        state: Dict[str, int] = {}
        for block in self.blocks:
            for tx in block.transactions:
                if not tx.is_coinbase:
                    state[tx.sender] = state.get(tx.sender, 0) - tx.amount
                state[tx.recipient] = state.get(tx.recipient, 0) + tx.amount
        return state

    def balance_of(self, address: str) -> int:
        """Confirmed balance of a single address (0 if never seen)."""
        return self.balances().get(address, 0)

    def __len__(self) -> int:
        return len(self.blocks)


def coinbase_tx(recipient: str, amount: int, nonce: int = 0) -> Transaction:
    """Convenience constructor for the miner-reward / mint transaction."""
    return Transaction(sender=None, recipient=recipient, amount=amount, nonce=nonce)
