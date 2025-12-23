import asyncio
import hashlib
import json
import time

import aiohttp
import httpx
from ecdsa import SigningKey, SECP256k1
from fastapi import Request, HTTPException, status

from config import settings
from core.node_core import Transaction
from core.logging import logger

def require_auth(request: Request):
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
    Подписывает транзакцию приватным ключом.
    Возвращает подпись в формате hex.
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
    transaction = Transaction(sender, recipient, amount, timestamp=time.time())
    signature = sign_transaction(private_key.hex(), transaction.to_dict())
    out = {'transaction': transaction.to_dict(), 'signature': signature, 'public_key': public_key}
    return out


async def get_balance(address) -> float:
    balance = None
    async with httpx.AsyncClient() as session:
        response = await session.get(f'{settings.ROOT_URL}/balance/{address}')
        # Важно: нужно дождаться чтения тела ответа (await)
        result = response.json()
        balance = result["balance"]
    return balance

class MiningService:
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
        """Внутренняя логика цикла."""
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            while self.is_running:
                try:
                    # 1. Запрашиваем ожидающие транзакции
                    response = await client.get("/transactions/pending")

                    if response.status_code == 200:
                        transactions = response.json()

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
