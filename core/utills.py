import hashlib
import json

from ecdsa import SECP256k1, SigningKey

from core.node_core import Transaction, Block


def create_genesis_block():
    """
    Генерирует первый (генезис) блок блокчейна.
    previous_hash фиксирован, так как предыдущего блока не существует.
    """
    genesis_tx = Transaction("system", "network", 0)
    genesis_block = Block(index=0, transactions=[genesis_tx], previous_hash="0" * 64)
    return genesis_block


def sign_transaction(private_key_hex: str, transaction_data: dict) -> str:
    """
    Подписывает данные транзакции приватным ключом.
    Возвращает подпись в hex формате.
    """
    private_key = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)

    # Формируем строку для подписи (только ключевые поля)
    data_to_sign = {
        "sender": transaction_data["sender"],
        "receiver": transaction_data["receiver"],
        "amount": transaction_data["amount"],
        "timestamp": transaction_data["timestamp"]
    }
    message = json.dumps(data_to_sign, sort_keys=True).encode()
    message_hash = hashlib.sha256(message).digest()

    signature = private_key.sign(message_hash)
    return signature.hex()
