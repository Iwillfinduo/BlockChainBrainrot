from __future__ import annotations

from typing import TYPE_CHECKING, Union

from pydantic import BaseModel

import core.node_core as core_models
import db.model as db_models

if TYPE_CHECKING:
    pass  # core_models is now imported above


class Transaction(BaseModel):
    sender: str
    receiver: str
    amount: float
    timestamp: float
    block_id: Union[int, None] = None


class SignedTransaction(BaseModel):
    """Обёртка: транзакция + данные для валидации."""
    transaction: Transaction
    signature: str
    public_key: Union[str, None] = None


class BlockHeader(BaseModel):
    previous_hash: str
    merkle_root: str
    timestamp: float
    nonce: int
    difficulty: int
    hash: str


class Block(BaseModel):
    index: int
    transactions: list[Transaction]
    merkle_root: str
    header: BlockHeader
    hash: str

    @classmethod
    def from_db_model(cls, block_orm: db_models.Block) -> "Block":  # Renamed from from_orm
        """Converts a db_models.Block to an API Block."""
        # Create a core_models.BlockHeader instance to calculate the header's hash
        core_header_instance = core_models.BlockHeader(
            previous_hash=block_orm.previous_hash,
            merkle_root=block_orm.merkle_root,
            timestamp=block_orm.timestamp,
            nonce=block_orm.nonce,
            difficulty=block_orm.difficulty
        )
        header_hash = core_header_instance.calculate_hash()

        # Create the APIBlockHeader explicitly
        api_header = BlockHeader(
            previous_hash=block_orm.previous_hash,
            merkle_root=block_orm.merkle_root,
            timestamp=block_orm.timestamp,
            nonce=block_orm.nonce,
            difficulty=block_orm.difficulty,
            hash=header_hash
        )

        # Convert DB transactions to API transactions using Transaction.from_orm
        api_transactions = [Transaction.from_orm(tx) for tx in block_orm.transactions]

        return cls(
            index=block_orm.index,
            transactions=api_transactions,
            merkle_root=block_orm.merkle_root,
            header=api_header,
            hash=block_orm.hash,  # This is the block's hash, from db_models.Block
        )
