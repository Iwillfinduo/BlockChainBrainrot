from contextlib import asynccontextmanager

import aiohttp
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import hashlib

from config import settings
from db.storage import BlockchainStorage
from routes.utils import MiningService, get_balance, form_transaction, update_balances, PoolService

templates = Jinja2Templates(directory="routes/templates")
storage = BlockchainStorage(settings.DATABASE_URL)
mining_service = MiningService(settings.ROOT_URL, settings.MINING_INTERVAL)
pool_service = PoolService(settings.ROOT_URL,settings.POOL_INTERVAL)

@asynccontextmanager
async def lifespan(router: APIRouter):
    await pool_service.start(storage)
    yield
    storage.close()
    await mining_service.stop()
admin_router = APIRouter(lifespan=lifespan)

# Админский пароль (храним в коде как хеш)
ADMIN_PASSWORD_HASH = hashlib.sha256(settings.ADMIN_PASSWORD.encode()).hexdigest()

def verify_admin_password(password: str) -> bool:
    """Проверка пароля администратора"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == ADMIN_PASSWORD_HASH

@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Страница входа администратора"""
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request}
    )

@admin_router.post('/admin/logout')
async def logout(request: Request):
    await mining_service.stop()
    request.session.clear()
    return 200

@admin_router.post("/admin/login")
async def admin_login(
    request: Request,
    password: str = Form(...)
):
    """Обработка входа администратора"""
    if verify_admin_password(password):
        # Устанавливаем сессию администратора
        request.session["admin_authenticated"] = True
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    else:
        return templates.TemplateResponse(
            "admin_login.html",
            {
                "request": request,
                "error": "Неверный пароль администратора"
            }
        )

@admin_router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Панель управления администратора"""
    # Проверка авторизации
    if not request.session.get("admin_authenticated"):
        return RedirectResponse(url="/admin", status_code=302)
    await update_balances(storage)
    current_status = request.session.get("mining_status", "stopped")
    users_count = storage.get_users_count()
    node_total_balance = await get_balance(settings.ADDRESS)
    users_cards = storage.get_users_for_cards(limit=20)

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "stats": {
                "total_users": users_count,
                "mining_status": current_status,
                "total_balance": round(node_total_balance, 4),
            },
            "users": users_cards
        }
    )

@admin_router.post("/admin/mining")
async def start_mining(request: Request):
    """Запуск майнинга"""
    if not request.session.get("admin_authenticated"):
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Ошибка парсинга JSON")
    action = data.get("action")
    print(action)
    if action == "start":
        print('start')
        await mining_service.start()
        request.session.update({"mining_status": "active"})
    elif action == "stop":
        print('stop')
        await mining_service.stop()
        request.session.update({"mining_status": "stopped"})

    return RedirectResponse(url="/admin/dashboard", status_code=302)

@admin_router.post("/admin/distribute")
async def distribute_coin(request: Request):
    """Распределение средств среди всех кошельков в узле"""
    if not request.session.get("admin_authenticated"):
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        data = await request.json()
        amount = data.get("amount")
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON")

    print(f"Полученная сумма: {amount}")

    # Валидация
    if amount is None:
        raise HTTPException(status_code=422, detail="Поле amount обязательно")
    node_total_balance = await get_balance(settings.ADDRESS)
    print(f"Баланс узла: {node_total_balance}")
    if amount <= node_total_balance:

        users = storage.get_all_users()
        fraction = amount / len(users)
        print(f'USERS: {users}')
        for user in users:
            print(f'Пользователь: {user.username}')
            transaction = form_transaction(sender=settings.ADDRESS, recipient=user.address, amount=fraction,
                                           private_key=settings.PRIVATE_KEY, public_key=settings.PUBLIC_KEY)
            print(transaction)
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{settings.ROOT_URL}/transactions', json=transaction) as response:
                    # нужно дождаться чтения тела ответа (await)
                    result = await response.json()
                    print(result)
    else:
        raise HTTPException(status_code=400, detail="Не достаточно средств")
    return RedirectResponse(url="/admin/dashboard", status_code=302)