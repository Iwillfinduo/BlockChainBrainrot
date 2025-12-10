from core.core import Transaction, Block


def create_genesis_block():
    """
    Генерирует первый (генезис) блок блокчейна.
    previous_hash фиксирован, так как предыдущего блока не существует.
    """
    genesis_tx = Transaction("system", "network", 0)
    genesis_block = Block(index=0, transactions=[genesis_tx], previous_hash="0" * 64)
    return genesis_block