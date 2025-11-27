import json

from fastapi import FastAPI
from db.storage import BlockchainStorage
from core.core import Block, Transaction
app = FastAPI()
storage = BlockchainStorage()

@app.get("/")
async def root():
    tx1 = Transaction("Alice", "Bob", 10.0)
    tx2 = Transaction("Bob", "Charlie", 5.0)
    block = Block(
        index=0,
        transactions=[tx1, tx2],
        previous_hash="0" * 64,
        difficulty=2
    )
    storage.save_block(block)
    block_with_txs = storage.get_block_with_transactions(block.hash)
    return {"message": f"Блок #{block_with_txs['block'].index}, hash:{block_with_txs['block'].hash} содержит {len(block_with_txs['transactions'])} транзакций, {json.dumps(block_with_txs['transactions'])}"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
