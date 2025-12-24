from sqlalchemy import Column, Integer, String, Float, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, mapped_column, Mapped
from core.api_core import BlockHeader

Base = declarative_base()


class TransactionDB(Base):
    """Модель для хранения транзакций"""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    block_id: Mapped[int] = mapped_column(ForeignKey("blocks.id"))

    sender: Mapped[str] = mapped_column(String)
    receiver: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[float] = mapped_column(Float)

    block: Mapped["BlockDB"] = relationship("BlockDB", back_populates="transactions")


class BlockDB(Base):
    """Модель для хранения блоков"""
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    index: Mapped[int] = mapped_column()

    previous_hash: Mapped[str] = mapped_column(String)
    merkle_root: Mapped[str] = mapped_column(String)
    timestamp: Mapped[float] = mapped_column(Float)
    nonce: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[int] = mapped_column(Integer)

    hash: Mapped[str] = mapped_column(String, unique=True)

    transactions: Mapped[list["TransactionDB"]] = relationship(
        "TransactionDB",
        back_populates="block",
        cascade="all, delete-orphan"
    )

    @property
    def header(self) -> "BlockHeader":
        return BlockHeader(
            previous_hash=self.previous_hash,
            merkle_root=self.merkle_root,
            timestamp=self.timestamp,
            nonce=self.nonce,
            difficulty=self.difficulty,
        )


class UserDB(Base):
    """Модель для хранения пользователей и их кошельков"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    username = Column(String(50), nullable=False, unique=True, index=True)
    hashed_password = Column(LargeBinary, nullable=False)

    private_key = Column(String(255), nullable=False)

    public_key = Column(String(255), nullable=False)

    address = Column(String(255), nullable=False)

    balance = Column(Float, default=0.0)

    def __repr__(self):
        return f"UserDB(id={self.id}, username='{self.username}')"