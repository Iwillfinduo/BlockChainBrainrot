import hashlib
import time
import json

#from core.utills import create_genesis_block


class Transaction:
    """
    Класс, представляющий отдельную транзакцию в блокчейне.
    Каждая транзакция содержит информацию об отправителе, получателе, сумме и метке времени.
    """

    def __init__(self, sender: str, receiver: str, amount: float, timestamp: float = None):
        self.sender = sender                # Адрес или имя отправителя
        self.receiver = receiver            # Адрес или имя получателя
        self.amount = amount                # Сумма перевода
        self.timestamp = timestamp or time.time()  # Время создания транзакции

    def to_dict(self) -> dict:
        """Возвращает транзакцию в виде словаря для сериализации."""
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        """Сериализует транзакцию в JSON строку."""
        return json.dumps(self.to_dict(), indent=4)

    @classmethod
    def from_json(cls, json_str: str):
        """Десериализует транзакцию из JSON строки."""
        data = json.loads(json_str)
        return cls(
            sender=data["sender"],
            receiver=data["receiver"],
            amount=data["amount"],
            timestamp=data["timestamp"]
        )
    def calculate_hash(self) -> str:
        """Возвращает хэш SHA-256 от данных транзакции."""
        tx_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()


class BlockHeader:
    """
    Заголовок блока, содержащий хэш предыдущего блока, корень Меркла, временную метку,
    сложность и nonce, используемый для майнинга.
    """

    def __init__(self, previous_hash: str, merkle_root: str,
                 timestamp: float = None, nonce: int = 0, difficulty: int = 4):
        self.previous_hash = previous_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp or time.time()
        self.nonce = nonce
        self.difficulty = difficulty

    def calculate_hash(self) -> str:
        """Возвращает хэш заголовка блока."""
        header_string = f"{self.previous_hash}{self.merkle_root}{self.timestamp}{self.nonce}{self.difficulty}"
        return hashlib.sha256(header_string.encode()).hexdigest()

    def to_dict(self) -> dict:
        """Возвращает заголовок блока в виде словаря для сериализации."""
        return {
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "difficulty": self.difficulty
        }

    def to_json(self) -> str:
        """Сериализует заголовок блока в JSON строку."""
        return json.dumps(self.to_dict(), indent=4)

    @classmethod
    def from_json(cls, json_str: str):
        """Десериализует заголовок блока из JSON строки."""
        data = json.loads(json_str)
        return cls(
            previous_hash=data["previous_hash"],
            merkle_root=data["merkle_root"],
            timestamp=data["timestamp"],
            nonce=data["nonce"],
            difficulty=data["difficulty"]
        )

class Block:
    """
    Класс блока, содержащего список транзакций, заголовок и метод майнинга.
    """

    def __init__(self, index: int, transactions: list, previous_hash: str, difficulty: int = 4):
        self.index = index                                     # Индекс блока в цепочке
        self.transactions = transactions                       # Список транзакций (объекты Transaction)
        self.merkle_root = self.compute_merkle_root()           # Корень Меркла для проверки целостности транзакций
        self.header = BlockHeader(previous_hash, self.merkle_root, difficulty=difficulty)
        self.hash = self.mine_block()                           # Хэш найденного блока после майнинга

    def compute_merkle_root(self) -> str:
        """
        Вычисляет корень для всех транзакций в блоке.
        Используется для проверки целостности данных.
        """
        tx_hashes = [tx.calculate_hash() if isinstance(tx, Transaction)
                     else hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
                     for tx in self.transactions]
        if not tx_hashes:
            return hashlib.sha256(b"").hexdigest()
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])
            tx_hashes = [
                hashlib.sha256((tx_hashes[i] + tx_hashes[i + 1]).encode()).hexdigest()
                for i in range(0, len(tx_hashes), 2)
            ]
        return tx_hashes[0]

    def mine_block(self) -> str:
        """
        Выполняет процесс майнинга блока перебирает nonce, пока не будет найден хэш,
        начинающийся с заданного количества нулей (в зависимости от сложности).
        """
        while True:
            hash_val = self.header.calculate_hash()
            if hash_val.startswith("0" * self.header.difficulty):
                return hash_val
            self.header.nonce += 1

    def is_valid(self) -> bool:
        """
        Проверяет корректность блока
        """
        return (self.hash == self.header.calculate_hash() and
                self.hash.startswith("0" * self.header.difficulty))

    def to_dict(self) -> dict:
        """Возвращает блок в виде словаря для сериализации."""
        return {
            "index": self.index,
            "hash": self.hash,
            "merkle_root": self.merkle_root,
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions]
        }

    def to_json(self) -> str:
        """Сериализует блок в JSON строку."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        """Десериализует блок из JSON строки."""
        data = json.loads(json_str)

        # Десериализуем транзакции
        transactions = [Transaction.from_json(json.dumps(tx)) for tx in data["transactions"]]

        # Создаем блок
        block = cls(
            index=data["index"],
            transactions=transactions,
            previous_hash=data["header"]["previous_hash"],
            difficulty=data["header"]["difficulty"]
        )

        # Восстанавливаем остальные поля
        block.merkle_root = data["merkle_root"]
        block.header.timestamp = data["header"]["timestamp"]
        block.header.nonce = data["header"]["nonce"]
        block.hash = data["hash"]

        return block



    # class Blockchain:
    #     def __init__(self, dao):
    #         self.chain = []
    #         self.current_transactions = []
    #         self.dao = dao
    #
    #         self.new_block(create_genesis_block())
    #
    #     def new_block(self, block):
    #         # Создает новый блок и вносит его в цепь
    #         self.current_transactions = []
    #         self.dao.add_block(block.to_orm(), [transaction.to_orm() for transaction in block.transactions])
    #         self.chain.append(block)
    #         return block
    #
    #     def new_transaction(self, transaction: Transaction):
    #         # Вносит новую транзакцию в список транзакций
    #         self.current_transactions.append(transaction)
    #         return self.last_block.index + 1
    #
    #     @property
    #     def last_block(self):
    #         # Возвращает последний блок в цепочке
    #         return self.chain[-1]




