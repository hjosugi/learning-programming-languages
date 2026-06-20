"""A minimal account-balance transaction model plus a mempool.

This mirrors the *account* model used by Ethereum (balances per address)
rather than Bitcoin's UTXO model, because it is simpler to reason about for
a first hands-on. The signature features it teaches:

* a transaction is an immutable record (``frozen`` dataclass) with a stable,
  hashable canonical form so it can be a Merkle leaf;
* a "coinbase"/mint transaction (``sender is None``) is how new coins enter
  the system -- the miner's reward -- so balances are not conjured silently;
* a **mempool** collects pending transactions and *rejects overspends* by
  validating each against a running balance projection before they are mined.

There is no real cryptographic signing here -- that is the first item on the
upgrade path (ECDSA via the ``cryptography`` library). Until then a sender is
just a string address and "authorization" is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

# The address new coins are minted *from*. A transaction whose sender is the
# coinbase pays out without debiting any account (it creates supply).
COINBASE = None


@dataclass(frozen=True)
class Transaction:
    """An immutable value transfer in the account model.

    Attributes:
        sender:   source address, or ``None`` for a coinbase/mint transaction.
        recipient: destination address (must be non-empty).
        amount:   integer units transferred (we use ints to dodge float
                  rounding; real chains use fixed-point integers too -- wei).
        nonce:    a per-transaction sequence value. In a real account model
                  the nonce prevents replay; here it simply makes otherwise
                  identical transfers distinct so each has a unique hash.
    """

    sender: Optional[str]
    recipient: str
    amount: int
    nonce: int = 0

    def __post_init__(self) -> None:
        # Validate eagerly so malformed transactions never reach a block.
        if not self.recipient:
            raise ValueError("recipient must be a non-empty address")
        if not isinstance(self.amount, int):
            raise TypeError("amount must be an int (integer units)")
        if self.amount <= 0:
            raise ValueError("amount must be positive")

    @property
    def is_coinbase(self) -> bool:
        """True for a mint transaction (creates new supply, no sender debit)."""
        return self.sender is COINBASE

    def canonical(self) -> str:
        """A deterministic, collision-resistant string form for hashing.

        This exact string becomes a Merkle leaf, so it must be stable: the
        same transaction always serializes the same way, and two different
        transactions never serialize the same. Fields are tagged and
        joined with ``|`` so values cannot bleed across field boundaries.
        """
        sender = self.sender if self.sender is not None else "COINBASE"
        return f"tx|from={sender}|to={self.recipient}|amt={self.amount}|nonce={self.nonce}"

    def __str__(self) -> str:  # used when a tx is dropped into a Merkle leaf
        return self.canonical()


class InsufficientFundsError(Exception):
    """Raised when a transaction would overspend the sender's balance."""


class Mempool:
    """A pool of pending (not-yet-mined) transactions.

    The mempool is the staging area between "user submits a transaction" and
    "miner includes it in a block". Its job in this hands-on is to *reject
    overspends up front* by projecting balances: it walks the already-pending
    transactions plus the new one against a snapshot of confirmed balances.

    Coinbase transactions are not accepted into the mempool -- the block
    builder injects the single coinbase reward itself, so users cannot mint.
    """

    def __init__(self) -> None:
        self._pending: List[Transaction] = []

    def __len__(self) -> int:
        return len(self._pending)

    @property
    def pending(self) -> List[Transaction]:
        """A copy of the pending transactions, in submission order."""
        return list(self._pending)

    def add(self, tx: Transaction, confirmed_balances: Dict[str, int]) -> None:
        """Add a transaction if it does not overspend, else raise.

        ``confirmed_balances`` is the on-chain state *before* any pending
        transactions. We replay the existing pending transactions on top of
        that snapshot to get the sender's projected balance, then check the
        new transaction can be afforded. This stops two pending transfers
        from each individually passing but together draining the account.
        """
        if tx.is_coinbase:
            raise ValueError("coinbase transactions cannot be added to the mempool")

        projected = self._project_balances(confirmed_balances)
        available = projected.get(tx.sender, 0)
        if available < tx.amount:
            raise InsufficientFundsError(
                f"{tx.sender} has {available} but tried to send {tx.amount}"
            )
        self._pending.append(tx)

    def _project_balances(self, confirmed: Dict[str, int]) -> Dict[str, int]:
        """Apply pending transactions to a copy of confirmed balances."""
        projected = dict(confirmed)
        for pending_tx in self._pending:
            if not pending_tx.is_coinbase:
                projected[pending_tx.sender] = (
                    projected.get(pending_tx.sender, 0) - pending_tx.amount
                )
            projected[pending_tx.recipient] = (
                projected.get(pending_tx.recipient, 0) + pending_tx.amount
            )
        return projected

    def collect(self, limit: Optional[int] = None) -> List[Transaction]:
        """Remove and return up to ``limit`` pending transactions for mining."""
        if limit is None:
            taken, self._pending = self._pending, []
        else:
            taken, self._pending = self._pending[:limit], self._pending[limit:]
        return taken
