from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, create_engine, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class BlockDB(Base):
    """Модель для хранения блоков"""
    __tablename__ = 'blocks'

    id = Column(Integer, primary_key=True)
    index = Column(Integer, nullable=False, index=True)
    hash = Column(String(64), nullable=False, unique=True, index=True)
    previous_hash = Column(String(64), nullable=False, index=True)
    merkle_root = Column(String(64), nullable=False)
    timestamp = Column(Float, nullable=False)
    nonce = Column(Integer, nullable=False)
    difficulty = Column(Integer, nullable=False)
    transactions_data = Column(Text, nullable=False)  # JSON строка с транзакциями

    # Связь с транзакциями
    transactions = relationship("TransactionDB", back_populates="block", cascade="all, delete-orphan")


class TransactionDB(Base):
    """Модель для хранения транзакций (для быстрого поиска)"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    tx_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Внешний ключ на блок
    block_id = Column(Integer, ForeignKey('blocks.id'), nullable=False, index=True)
    block_hash = Column(String(64), nullable=False, index=True)

    sender = Column(String(255), nullable=False, index=True)
    receiver = Column(String(255), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)

    # Связь с блоком
    block = relationship("BlockDB", back_populates="transactions")


class UserDB(Base):
    """Модель для хранения пользователей и их кошельков"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    # Аутентификационные данные
    username = Column(String(50), nullable=False, unique=True, index=True)
    # Используйте LargeBinary для хранения хэша пароля (например, bcrypt)
    hashed_password = Column(LargeBinary, nullable=False)

    private_key = Column(LargeBinary, nullable=False)

    public_key = Column(LargeBinary, nullable=False)

    address = Column(String(255), nullable=False)

    # Добавление баланса (для быстрого чтения, хотя истинный баланс вычисляется по цепи)
    balance = Column(Float, default=0.0)

    def __repr__(self):
        return f"UserDB(id={self.id}, username='{self.username}')"