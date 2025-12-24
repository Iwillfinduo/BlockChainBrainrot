import asyncio
import hashlib
import json
import time

import httpx
from ecdsa import SigningKey, SECP256k1
from fastapi import Request, HTTPException, status

from config import settings
from core.node_core import Transaction
from core.logging import logger


def require_auth(request: Request):
    """
    Проверяет аутентификацию пользователя по сессии.
        Returns:
            ID пользователя из сессии при успешной проверке.
        Raises:
            код 303 и редирект на /login если пользователь не аутентифицирован.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        # Если сессии нет, перенаправляем на страницу входа
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Not authenticated",
            headers={"Location": "/login"}
        )
    return user_id


def sign_transaction(private_key_hex: str, transaction_data: dict) -> str:
    """
    Подписывает транзакцию приватным ключом с использованием ECDSA.
        Args:
            private_key_hex: Приватный ключ в hex-формате (64 символа).
            transaction_data: Словарь с данными транзакции для подписи.
        Returns:
            Цифровая подпись в формате hex строки.
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

def form_transaction(sender, recipient, amount, private_key, public_key) -> dict:
    """
   Формирует структуру подписанной транзакции для отправки в блокчейн.
       Args:
           sender: Адрес отправителя.
           recipient: Адрес получателя.
           amount: Сумма перевода.
           private_key: Приватный ключ отправителя для подписи.
           public_key: Публичный ключ отправителя для верификации.
       Returns:
           Словарь с подписанной транзакцией.
   """
    transaction = Transaction(sender, recipient, amount, timestamp=time.time())
    signature = sign_transaction(private_key, transaction.to_dict())
    out = {'transaction': transaction.to_dict(), 'signature': signature, 'public_key': public_key}
    return out

async def get_balance(address) -> float:
    """
    Получает баланс кошелька с блокчейн-сервера.
        Args:
            address: Адрес кошелька для проверки баланса.
        Returns:
            Текущий баланс адреса в виде числа с плавающей точкой.
    """
    balance = None
    async with httpx.AsyncClient() as session:
        response = await session.get(f'{settings.ROOT_URL}/balance/{address}')
        # Важно: нужно дождаться чтения тела ответа (await)
        result = response.json()
        balance = result["balance"]
    return balance

async def update_balances(storage) -> None:
    """
   Обновляет балансы всех пользователей из блокчейн-сервера.
       Args:
           storage: Экземпляр BlockchainStorage для доступа к пользователям.
   """
    users = storage.get_all_users()
    for user in users:
        address = user.address
        balance = await get_balance(address)
        storage.update_user_balance(user.id, balance)

class MiningService:
    """
        Служба автоматического майнинга блоков.
    """
    def __init__(self, base_url, interval:int):
        self.is_running = False
        self._task = None
        # Базовый URL вашего API (или другого сервиса)
        self.base_url = base_url
        self.check_interval = interval  # Секунды между проверками

    async def start(self):
        """Запускает цикл майнинга, если он еще не запущен."""
        if not self.is_running:
            self.is_running = True
            # Создаем задачу, которая не блокирует основной поток
            self._task = asyncio.create_task(self._mining_loop())
            logger.info("Mining service started.")

    async def stop(self):
        """Останавливает цикл майнинга."""
        if self.is_running:
            self.is_running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            logger.info("Mining service stopped.")

    async def _mining_loop(self):
        """
        Внутренний цикл майнинга.
        Периодически проверяет наличие транзакций и создает блоки.
        """
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            while self.is_running:
                try:
                    # 1. Запрашиваем ожидающие транзакции
                    response = await client.get("/transactions/pending")

                    if response.status_code == 200:
                        transactions = response.json().get("transactions")

                        # 2. Если список не пуст, запускаем майнинг
                        if transactions:
                            logger.info(f"Found {len(transactions)} pending transactions. Mining block...")
                            mine_response = await client.post("/blocks/mine")
                            logger.info(f"Mining result: {mine_response.status_code}")
                        else:
                            logger.debug("No pending transactions.")
                    else:
                        logger.error(f"Error fetching transactions: {response.status_code}")

                except Exception as e:
                    logger.error(f"Error in mining loop: {e}")

                # Пауза перед следующим циклом
                await asyncio.sleep(self.check_interval)

class PoolService:
    """
    Служба поддержания актуальности балансов пользователей.
    Периодически синхронизирует балансы с блокчейн-сервером.
    """
    def __init__(self, base_url, interval:int):
        self.is_running = False
        self.base_url = base_url
        self.check_interval = interval

    async def start(self, storage):
        """Запускает цикл."""
        if not self.is_running:
            self.is_running = True
            # Создаем задачу, которая не блокирует основной поток
            self._task = asyncio.create_task(self._pool_loop(storage))
            logger.info("PoolService started.")

    async def stop(self):
        """Останавливает цикл."""
        if self.is_running:
            self.is_running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            logger.info("PoolService stopped.")

    async def _pool_loop(self, storage):
        """
        Внутренний цикл обновления балансов.
        Периодически синхронизирует балансы всех пользователей.
        """
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            while self.is_running:
                try:
                    await update_balances(storage)

                except Exception as e:
                    logger.error(f"Error in mining loop: {e}")

                # Пауза перед следующим циклом
                await asyncio.sleep(self.check_interval)
