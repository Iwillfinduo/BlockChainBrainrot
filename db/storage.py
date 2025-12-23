import json
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, joinedload

from core.node_core import Block, Transaction
from db.model import Base, BlockDB, TransactionDB, UserDB
from db.utils import verify_password, hash_password, generate_keys, get_address_from_public_key


class BlockchainStorage:
    """
    Минималистичное хранилище для блоков и транзакций со связями
    """

    def __init__(self, db_url: str = "sqlite:///blockchain.db"):
        self.engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def save_block(self, block: Block) -> bool:
        """
        Сохраняет блок и его транзакции в базу данных
        """
        try:
            # Конвертируем транзакции в JSON
            transactions_json = json.dumps([tx.to_dict() for tx in block.transactions])

            # Создаем запись блока
            block_db = BlockDB(
                index=block.index,
                hash=block.hash,
                previous_hash=block.header.previous_hash,
                merkle_root=block.merkle_root,
                timestamp=block.header.timestamp,
                nonce=block.header.nonce,
                difficulty=block.header.difficulty,
                transactions_data=transactions_json
            )

            self.session.add(block_db)
            self.session.flush()  # Получаем ID блока

            # Сохраняем транзакции для быстрого поиска
            for tx in block.transactions:
                tx_db = TransactionDB(
                    tx_hash=tx.calculate_hash(),
                    block_id=block_db.id,
                    block_hash=block.hash,
                    sender=tx.sender,
                    receiver=tx.receiver,
                    amount=tx.amount,
                    timestamp=tx.timestamp
                )
                self.session.add(tx_db)

            self.session.commit()
            return True

        except IntegrityError:
            self.session.rollback()
            return False  # Блок уже существует
        except Exception as e:
            self.session.rollback()
            raise e

    def get_block_by_hash(self, block_hash: str, include_transactions: bool = False) -> Optional[Block]:
        """
        Получает блок по хэшу

        Args:
            block_hash: Хэш блока
            include_transactions: Загружать ли связанные транзакции
        """
        query = self.session.query(BlockDB)
        if include_transactions:
            query = query.options(joinedload(BlockDB.transactions))

        block_db = query.filter(BlockDB.hash == block_hash).first()
        if not block_db:
            return None

        return self._block_from_db(block_db)

    def get_block_by_index(self, index: int, include_transactions: bool = False) -> Optional[Block]:
        """
        Получает блок по индексу
        """
        query = self.session.query(BlockDB)
        if include_transactions:
            query = query.options(joinedload(BlockDB.transactions))

        block_db = query.filter(BlockDB.index == index).first()
        if not block_db:
            return None

        return self._block_from_db(block_db)

    def get_latest_block(self, include_transactions: bool = False) -> Optional[Block]:
        """
        Получает последний блок
        """
        query = self.session.query(BlockDB)
        if include_transactions:
            query = query.options(joinedload(BlockDB.transactions))

        block_db = query.order_by(desc(BlockDB.index)).first()
        if not block_db:
            return None

        return self._block_from_db(block_db)

    def get_blocks_range(self, start_index: int, limit: int = 10, include_transactions: bool = False) -> List[Block]:
        """
        Получает диапазон блоков
        """
        query = self.session.query(BlockDB)
        if include_transactions:
            query = query.options(joinedload(BlockDB.transactions))

        blocks_db = query.filter(
            BlockDB.index >= start_index
        ).order_by(BlockDB.index).limit(limit).all()

        return [self._block_from_db(block_db) for block_db in blocks_db]

    def get_all_blocks(self, include_transactions: bool = False) -> List[Block]:
        """
        Получает все блоки
        """
        query = self.session.query(BlockDB)
        if include_transactions:
            query = query.options(joinedload(BlockDB.transactions))

        blocks_db = query.order_by(BlockDB.index).all()
        return [self._block_from_db(block_db) for block_db in blocks_db]

    def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Получает транзакцию по хэшу с информацией о блоке
        """
        tx_db = self.session.query(TransactionDB).filter(TransactionDB.tx_hash == tx_hash).first()
        if not tx_db:
            return None

        return {
            "tx_hash": tx_db.tx_hash,
            "block_id": tx_db.block_id,
            "block_hash": tx_db.block_hash,
            "sender": tx_db.sender,
            "receiver": tx_db.receiver,
            "amount": tx_db.amount,
            "timestamp": tx_db.timestamp
        }

    def get_transactions_by_address(self, address: str) -> List[Dict[str, Any]]:
        """
        Получает транзакции по адресу с информацией о блоках
        """
        txs_db = self.session.query(TransactionDB).filter(
            (TransactionDB.sender == address) | (TransactionDB.receiver == address)
        ).all()

        return [{
            "tx_hash": tx.tx_hash,
            "block_id": tx.block_id,
            "block_hash": tx.block_hash,
            "sender": tx.sender,
            "receiver": tx.receiver,
            "amount": tx.amount,
            "timestamp": tx.timestamp
        } for tx in txs_db]

    def get_block_transactions(self, block_hash: str) -> List[Dict[str, Any]]:
        """
        Получает все транзакции определенного блока
        """
        txs_db = self.session.query(TransactionDB).filter(
            TransactionDB.block_hash == block_hash
        ).all()

        return [{
            "tx_hash": tx.tx_hash,
            "block_id": tx.block_id,
            "block_hash": tx.block_hash,
            "sender": tx.sender,
            "receiver": tx.receiver,
            "amount": tx.amount,
            "timestamp": tx.timestamp
        } for tx in txs_db]

    def get_block_with_transactions(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """
        Получает блок со всеми его транзакциями
        """
        block_db = self.session.query(BlockDB).options(
            joinedload(BlockDB.transactions)
        ).filter(BlockDB.hash == block_hash).first()

        if not block_db:
            return None

        block = self._block_from_db(block_db)

        return {
            "block": block,
            "transactions": [{
                "tx_hash": tx.tx_hash,
                "sender": tx.sender,
                "receiver": tx.receiver,
                "amount": tx.amount,
                "timestamp": tx.timestamp
            } for tx in block_db.transactions]
        }

    def get_blockchain_height(self) -> int:
        """
        Возвращает высоту блокчейна
        """
        latest = self.get_latest_block()
        return latest.index if latest else -1

    def is_block_exists(self, block_hash: str) -> bool:
        """
        Проверяет существование блока
        """
        return self.session.query(BlockDB).filter(BlockDB.hash == block_hash).first() is not None

    def _block_from_db(self, block_db: BlockDB) -> Block:
        """
        Конвертирует BlockDB в Block
        """
        # Восстанавливаем транзакции из JSON
        transactions_data = json.loads(block_db.transactions_data)
        transactions = [
            Transaction(
                sender=tx_dict["sender"],
                receiver=tx_dict["receiver"],
                amount=tx_dict["amount"],
                timestamp=tx_dict["timestamp"]
            ) for tx_dict in transactions_data
        ]

        # Создаем блок
        block = Block(
            index=block_db.index,
            transactions=transactions,
            previous_hash=block_db.previous_hash,
            difficulty=block_db.difficulty
        )

        # Восстанавливаем состояние блока (хэш уже вычислен при майнинге)
        block.hash = block_db.hash
        block.merkle_root = block_db.merkle_root
        block.header.timestamp = block_db.timestamp
        block.header.nonce = block_db.nonce

        return block

    def validate_chain(self) -> bool:
        """
        Проверяет целостность цепочки
        """
        blocks = self.get_all_blocks()
        if not blocks:
            return True

        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i - 1]

            if current.header.previous_hash != previous.hash:
                return False
            if current.index != previous.index + 1:
                return False
            if not current.is_valid():
                return False

        return True

    def close(self):
        """Закрывает соединение"""
        self.session.close()

    def create_user(self, username: str, password: str) -> Optional[UserDB]:
        """Создает нового пользователя"""
        try:
            hashed_password = hash_password(password)
            private_key, public_key = generate_keys()
            user_db = UserDB(
                username=username,
                hashed_password=hashed_password,
                private_key=private_key,
                public_key=public_key,
                address=get_address_from_public_key(public_key),
                balance=0.0  # Начальный баланс
            )
            self.session.add(user_db)
            self.session.commit()
            self.session.refresh(user_db)
            return user_db
        except IntegrityError as e:
            print(e)
            self.session.rollback()
            # Пользователь или кошелек уже существуют
            return None

    def get_user_by_username(self, username: str) -> Optional[UserDB]:
        """Находит пользователя по имени"""
        return self.session.query(UserDB).filter(UserDB.username == username).first()
    def get_user_by_address(self, address: str) -> Optional[UserDB]:
        return self.session.query(UserDB).filter(UserDB.address == address).first()

    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """Обновляет баланс пользователя"""
        user = self.session.query(UserDB).filter(UserDB.id == user_id).first()
        if user:
            user.balance = new_balance
            self.session.commit()
            return True
        return False

    def authenticate_user(self, username: str, password: str) -> Optional[UserDB]:
        """
        Проверяет учетные данные пользователя.

        Args:
            username: Имя пользователя, введенное при входе.
            password: Чистый пароль, введенный при входе.

        Returns:
            Объект UserDB, если вход успешен, иначе None.
        """

        user = self.get_user_by_username(username)

        if not user:
            return None

        try:
            is_correct = verify_password(
                password=password,
                hashed_password=user.hashed_password
            )
        except ValueError:
            print(f"ERROR: Invalid hash format for user {username}")
            return None

        if is_correct:
            return user
        else:
            return None

    def get_users_count(self) -> int:
        """Получить количество пользователей"""
        return self.session.query(UserDB).count()

    def get_total_balance(self) -> float:
        """Получить общую сумму всех балансов"""
        result = self.session.query(func.sum(UserDB.balance)).scalar()
        return float(result) if result else 0.0
    def get_all_users(self):
        users = self.session.query(UserDB).all()
        return users
    def get_users_for_cards(self, limit: int = 20) -> List[dict]:
        """Получить данные для карточек пользователей (только нужные поля)"""
        users = self.session.query(UserDB) \
            .order_by(UserDB.balance.desc()) \
            .limit(limit) \
            .all()

        return [
            {
                "id": user.id,
                "username": user.username,
                "balance": user.balance,
                "address": user.address
            }
            for user in users
        ]