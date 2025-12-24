import json
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, joinedload

from core.node_core import Block, Transaction
from db.model import Base, BlockDB, UserDB
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

    def get_all_blocks(self, include_transactions: bool = False) -> List[Block]:
        """
        Получает все блоки
            Args:
                include_transactions: Если True, загружает связанные транзакции.
            Returns:
                Список объектов Block в порядке возрастания индекса.
        """
        query = self.session.query(BlockDB)
        if include_transactions:
            query = query.options(joinedload(BlockDB.transactions))

        blocks_db = query.order_by(BlockDB.index).all()
        return [self._block_from_db(block_db) for block_db in blocks_db]

    def _block_from_db(self, block_db: BlockDB) -> Block:
        """
        Конвертирует BlockDB в Block
            Args:
                block_db: Объект BlockDB из базы данных.
            Returns:
                Полностью восстановленный объект Block с транзакциями.
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

    def close(self):
        """Закрывает соединение"""
        self.session.close()

    def create_user(self, username: str, password: str) -> Optional[UserDB]:
        """
        Создает нового пользователя
            Args:
                username: Уникальное имя пользователя.
                password: Пароль пользователя в чистом виде.
            Returns:
                Объект UserDB при успешном создании, иначе None.
        """
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
        """
        Находит пользователя по имени
            Args:
                username: Имя пользователя для поиска.
            Returns:
                Объект UserDB или None, если пользователь не найден.
        """
        return self.session.query(UserDB).filter(UserDB.username == username).first()

    def get_user_by_address(self, address: str) -> Optional[UserDB]:
        """
        Находит пользователя по адресу кошелька.
            Args:
                address: Адрес кошелька (публичный ключ в сокращенном формате).
            Returns:
                Объект UserDB или None, если пользователь не найден.
        """
        return self.session.query(UserDB).filter(UserDB.address == address).first()

    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """
        Обновляет баланс пользователя по ID.
            Args:
                user_id: Идентификатор пользователя в базе данных.
                new_balance: Новое значение баланса.
            Returns:
                True если обновление прошло успешно, иначе False.
        """
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
        """
        Получить количество пользователей
            Returns:
                Количество пользователей в базе данных.
        """
        return self.session.query(UserDB).count()

    def get_all_users(self):
        """
        Получает список всех пользователей.
            Returns:
                Список всех объектов UserDB из базы данных.
        """
        users = self.session.query(UserDB).all()
        return users

    def get_users_for_cards(self, limit: int = 20) -> List[dict]:
        """
        Получает данные для отображения карточек пользователей.
            Args:
                limit: Максимальное количество пользователей для возврата.
            Returns:
                Список словарей с данными пользователей, отсортированный по балансу.
        """
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