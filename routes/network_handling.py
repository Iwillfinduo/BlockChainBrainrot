from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import settings
from db.storage import BlockchainStorage
from core.blockchain_core import Blockchain

node_handler = APIRouter()
storage = BlockchainStorage(settings.DATABASE_URL)
blockchain = Blockchain(storage)

# --- API Models for Requests ---
class NodeRegisterRequest(BaseModel):
    address: str = Field(..., example="127.0.0.1:8001", description="Адрес узла (хост:порт)")

@node_handler.post("/nodes/register", status_code=HTTPStatus.CREATED, tags=["Сеть"], summary="Регистрация нового узла")
def register_node(payload: NodeRegisterRequest):
    """
    **Регистрирует новый узел в сети.**

    Этот эндпоинт используется другими узлами (пирами), чтобы сообщить о своем существовании.
    После регистрации текущий узел сможет опрашивать новый узел для синхронизации блокчейна.

    - **address**: Адрес узла в формате `host:port`.
    """
    node_address = payload.address
    if not node_address:
        raise HTTPException(status_code=400, detail="Incorrect node address")

    blockchain.register_node(node_address)

    return {
        "message": "New node successfully registered",
        "total_nodes": list(blockchain.nodes),
    }


@node_handler.get("/nodes", tags=["Сеть"], summary="Список известных узлов")
def get_nodes():
    """
    **Возвращает список всех известных узлов (пиров) в сети.**

    Используется для discovery (обнаружения) сети новыми участниками.
    """
    return {"nodes": list(blockchain.nodes)}


@node_handler.post("/nodes/resolve", status_code=HTTPStatus.OK, tags=["Сеть"], summary="Консенсус (разрешение конфликтов)")
async def resolve_nodes():
    """
    **Запускает алгоритм консенсуса.**

    Узел опрашивает всех известных соседей, скачивает их цепочки блоков и проверяет их валидность.
    Если найдена цепочка длиннее и валиднее текущей, локальная цепочка заменяется на скачанную.

    *Возвращает статус операции: была ли заменена цепочка.*
    """
    replaced = await blockchain.resolve_conflicts()
    if replaced:
        message = "Our chain was replaced"
    else:
        message = "Our chain is authoritative"

    return {"message": message}


@node_handler.get("/node/address", tags=["Узел"], summary="Получить блокчейн-адрес узла")
def get_node_blockchain_address():
    """
    **Возвращает блокчейн-адрес текущего узла.**

    Этот адрес используется для получения наград за майнинг и может быть использован
    для отправки транзакций на этот узел.
    """
    return {"node_blockchain_address": settings.node_blockchain_address}
