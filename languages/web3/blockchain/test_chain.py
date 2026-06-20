"""Test suite for the from-scratch blockchain (stdlib ``unittest`` only).

Run non-interactively; exits non-zero on any failure:

    python3 /mnt/data/workspace/learning-web3/blockchain/test_chain.py

Covers the named learning targets:

* mined block hashes meet the difficulty target;
* the Merkle root changes when any transaction changes (and is order- and
  count-sensitive);
* an intact chain validates;
* tampering with *any* block (transaction, index, or prev-link) fails
  validation;
* the mempool rejects overspends, including the "two small transfers that
  together overspend" case.
"""

from __future__ import annotations

import os
import sys
import unittest

# Make the ``blockchain`` package importable regardless of CWD.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from blockchain.block import Block  # noqa: E402
from blockchain.chain import Blockchain, GENESIS_PREV_HASH, coinbase_tx  # noqa: E402
from blockchain.crypto import (  # noqa: E402
    hash_strings,
    leading_zero_bits,
    meets_difficulty,
    merkle_root,
    sha256_hex,
)
from blockchain.transaction import (  # noqa: E402
    InsufficientFundsError,
    Mempool,
    Transaction,
)


class TestHashing(unittest.TestCase):
    def test_sha256_is_deterministic_and_64_hex(self):
        a = sha256_hex(b"web3")
        b = sha256_hex(b"web3")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in a))

    def test_sha256_known_vector(self):
        # The empty-string SHA-256 digest is a fixed, well-known value.
        self.assertEqual(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_avalanche_one_change_flips_hash(self):
        self.assertNotEqual(sha256_hex(b"alice->bob:10"), sha256_hex(b"alice->bob:11"))

    def test_hash_strings_field_separation(self):
        # ("ab","c") must not collide with ("a","bc"): NUL-separated fields.
        self.assertNotEqual(hash_strings("ab", "c"), hash_strings("a", "bc"))

    def test_meets_difficulty(self):
        self.assertTrue(meets_difficulty("000abc", 3))
        self.assertFalse(meets_difficulty("00abc", 3))
        self.assertTrue(meets_difficulty("anything", 0))
        with self.assertRaises(ValueError):
            meets_difficulty("abc", -1)

    def test_leading_zero_bits(self):
        self.assertEqual(leading_zero_bits("ff"), 0)
        self.assertEqual(leading_zero_bits("0f"), 4)
        self.assertEqual(leading_zero_bits("00f"), 8)
        self.assertEqual(leading_zero_bits("1f"), 3)  # 0b0001....


class TestMerkleRoot(unittest.TestCase):
    def test_empty_has_stable_root(self):
        self.assertEqual(merkle_root([]), merkle_root([]))

    def test_single_leaf_root_is_stable(self):
        self.assertEqual(merkle_root(["tx-a"]), merkle_root(["tx-a"]))

    def test_root_changes_when_a_tx_changes(self):
        before = merkle_root(["tx-a", "tx-b", "tx-c"])
        after = merkle_root(["tx-a", "tx-B", "tx-c"])  # one leaf mutated
        self.assertNotEqual(before, after)

    def test_root_is_order_sensitive(self):
        self.assertNotEqual(
            merkle_root(["tx-a", "tx-b"]),
            merkle_root(["tx-b", "tx-a"]),
        )

    def test_root_is_count_sensitive(self):
        self.assertNotEqual(
            merkle_root(["tx-a", "tx-b"]),
            merkle_root(["tx-a", "tx-b", "tx-c"]),
        )

    def test_odd_leaves_handled(self):
        # Three leaves (odd) should still produce a stable 64-hex root.
        root = merkle_root(["a", "b", "c"])
        self.assertEqual(len(root), 64)


class TestProofOfWork(unittest.TestCase):
    def test_mined_hash_meets_difficulty(self):
        for difficulty in (0, 1, 2, 3):
            block = Block(
                index=1,
                timestamp=7,
                transactions=[coinbase_tx("miner", 50)],
                prev_hash="0" * 64,
                difficulty=difficulty,
            )
            attempts = block.mine()
            self.assertGreaterEqual(attempts, 1)
            self.assertTrue(block.hash.startswith("0" * difficulty))
            self.assertTrue(block.is_valid_proof())

    def test_mining_sets_consistent_hash(self):
        block = Block(1, 7, [coinbase_tx("m", 1)], "0" * 64, difficulty=2)
        block.mine()
        # Stored hash equals a fresh recomputation of the header.
        self.assertEqual(block.hash, block.compute_hash())

    def test_block_hash_depends_on_merkle_root(self):
        a = Block(1, 7, [coinbase_tx("m", 1)], "0" * 64, difficulty=0)
        b = Block(1, 7, [coinbase_tx("m", 2)], "0" * 64, difficulty=0)
        self.assertNotEqual(a.merkle_root, b.merkle_root)
        self.assertNotEqual(a.hash, b.hash)


class TestChainValidation(unittest.TestCase):
    def _funded_chain(self) -> Blockchain:
        chain = Blockchain(difficulty=2)
        chain.add_block([coinbase_tx("alice", 100, nonce=0)])
        chain.add_block([Transaction("alice", "bob", 40, nonce=1)])
        return chain

    def test_intact_chain_validates(self):
        chain = self._funded_chain()
        self.assertTrue(chain.is_valid())
        self.assertEqual(len(chain), 3)  # genesis + 2

    def test_genesis_links_to_sentinel(self):
        chain = Blockchain(difficulty=1)
        self.assertEqual(chain.blocks[0].prev_hash, GENESIS_PREV_HASH)
        self.assertEqual(chain.blocks[0].index, 0)

    def test_prev_hash_links_are_correct(self):
        chain = self._funded_chain()
        for parent, child in zip(chain.blocks, chain.blocks[1:]):
            self.assertEqual(child.prev_hash, parent.hash)
            self.assertEqual(child.index, parent.index + 1)

    def test_balances_track_transfers(self):
        chain = self._funded_chain()
        self.assertEqual(chain.balance_of("alice"), 60)
        self.assertEqual(chain.balance_of("bob"), 40)
        self.assertEqual(chain.balance_of("nobody"), 0)

    def test_tamper_with_transaction_amount_fails(self):
        chain = self._funded_chain()
        self.assertTrue(chain.is_valid())
        # Edit a buried transaction without re-mining: Merkle root mismatch.
        chain.blocks[1].transactions[0] = coinbase_tx("alice", 999, nonce=0)
        self.assertFalse(chain.is_valid())

    def test_tamper_with_index_fails(self):
        chain = self._funded_chain()
        chain.blocks[1].index = 99
        self.assertFalse(chain.is_valid())

    def test_tamper_with_prev_hash_fails(self):
        chain = self._funded_chain()
        chain.blocks[2].prev_hash = "0" * 64
        self.assertFalse(chain.is_valid())

    def test_tamper_with_nonce_fails(self):
        # Changing the nonce changes the hash but not the stored .hash field,
        # so the re-hash check catches it.
        chain = self._funded_chain()
        chain.blocks[1].nonce += 1
        self.assertFalse(chain.is_valid())

    def test_tamper_then_rehash_still_breaks_link(self):
        # A smarter attacker recomputes the edited block's own hash. The chain
        # still fails because the *child's* prev_hash no longer matches.
        chain = self._funded_chain()
        victim = chain.blocks[1]
        victim.transactions[0] = coinbase_tx("alice", 999, nonce=0)
        victim.merkle_root = victim.compute_merkle_root()
        victim.hash = victim.compute_hash()
        # victim.hash now self-consistent, but it likely fails PoW and the link.
        self.assertFalse(chain.is_valid())


class TestMempool(unittest.TestCase):
    def test_accepts_affordable_transfer(self):
        mp = Mempool()
        mp.add(Transaction("alice", "bob", 30, nonce=1), {"alice": 100})
        self.assertEqual(len(mp), 1)

    def test_rejects_single_overspend(self):
        mp = Mempool()
        with self.assertRaises(InsufficientFundsError):
            mp.add(Transaction("alice", "bob", 200, nonce=1), {"alice": 100})
        self.assertEqual(len(mp), 0)

    def test_rejects_cumulative_overspend(self):
        # Two transfers each fit alone but together exceed the balance.
        mp = Mempool()
        confirmed = {"alice": 100}
        mp.add(Transaction("alice", "bob", 60, nonce=1), confirmed)
        with self.assertRaises(InsufficientFundsError):
            mp.add(Transaction("alice", "carol", 60, nonce=2), confirmed)
        self.assertEqual(len(mp), 1)  # the second one was not added

    def test_unknown_sender_has_zero_balance(self):
        mp = Mempool()
        with self.assertRaises(InsufficientFundsError):
            mp.add(Transaction("ghost", "bob", 1, nonce=1), {})

    def test_coinbase_rejected_from_mempool(self):
        mp = Mempool()
        with self.assertRaises(ValueError):
            mp.add(coinbase_tx("alice", 50), {})

    def test_collect_drains_pool(self):
        mp = Mempool()
        confirmed = {"alice": 100}
        mp.add(Transaction("alice", "bob", 10, nonce=1), confirmed)
        mp.add(Transaction("alice", "carol", 10, nonce=2), confirmed)
        taken = mp.collect()
        self.assertEqual(len(taken), 2)
        self.assertEqual(len(mp), 0)

    def test_collect_respects_limit(self):
        mp = Mempool()
        confirmed = {"alice": 100}
        for i in range(3):
            mp.add(Transaction("alice", "bob", 5, nonce=i), confirmed)
        first = mp.collect(limit=2)
        self.assertEqual(len(first), 2)
        self.assertEqual(len(mp), 1)


class TestTransactionModel(unittest.TestCase):
    def test_rejects_non_positive_amount(self):
        with self.assertRaises(ValueError):
            Transaction("a", "b", 0)
        with self.assertRaises(ValueError):
            Transaction("a", "b", -5)

    def test_rejects_empty_recipient(self):
        with self.assertRaises(ValueError):
            Transaction("a", "", 5)

    def test_coinbase_detected(self):
        self.assertTrue(coinbase_tx("a", 5).is_coinbase)
        self.assertFalse(Transaction("a", "b", 5).is_coinbase)

    def test_canonical_distinguishes_transactions(self):
        a = Transaction("a", "b", 5, nonce=1).canonical()
        b = Transaction("a", "b", 5, nonce=2).canonical()
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    # verbosity=2 prints each test; exit code is non-zero on failure.
    unittest.main(verbosity=2)
