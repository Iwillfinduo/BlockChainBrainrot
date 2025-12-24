from contextlib import asynccontextmanager
from typing import Annotated

import aiohttp
from fastapi import APIRouter, Request, Form, status

from starlette.responses import RedirectResponse, JSONResponse
from starlette.templating import Jinja2Templates


from config import settings
from db.storage import BlockchainStorage
from routes.utils import require_auth, form_transaction, get_balance


templates = Jinja2Templates(directory='routes/templates')
storage = BlockchainStorage(settings.DATABASE_URL)
@asynccontextmanager
async def lifespan(router: APIRouter):
    yield
    storage.close()

user_router = APIRouter(lifespan=lifespan)
@user_router.get("/login")
async def login_form(request: Request):
    """Страница входа пользователя"""
    error_message = request.session.pop("error_message", None)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error_message}
    )

@user_router.post("/login")
async def login_post(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """Обработка входа пользователя"""
    user = storage.authenticate_user(username, password)
    if not user:
        # Неудачная аутентификация
        request.session["error_message"] = "Неверное имя пользователя или пароль."

        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    balance = await get_balance(user.address)

    storage.update_user_balance(user.id, balance)
    # Успешная аутентификация
    request.session["user_id"] = user.id
    request.session["username"] = user.username

    return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)

@user_router.get("/profile")
async def profile(request: Request):
    """Страница кошелька пользователя"""
    user_id = require_auth(request)
    username = request.session.get("username")
    user = storage.get_user_by_username(username)
    if user is None:
        request.session.clear()
        RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "wallet.html",
        {'request': request, 'username': username, 'balance_amount': user.balance, 'wallet_address': user.address}
    )

@user_router.get("/register")
async def register_form(request: Request):
    """Страница регистрации пользователя"""
    error_message = request.session.pop("error_message", None)
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": error_message}
    )

@user_router.post("/register")
async def register_post(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """
    Обрабатывает данные регистрации, хеширует пароль и сохраняет пользователя.
    """
    user = storage.create_user(username, password)
    if user is None:
        request.session["error_message"] = "Пользователь с таким именем уже существует."
        return RedirectResponse(url="/register", status_code=status.HTTP_302_FOUND)

    return RedirectResponse(url="/login", status_code=status.HTTP_308_PERMANENT_REDIRECT)

@user_router.get("/")
async def route_root(request: Request):
    if request.session.get("user_id") is not None:
        return RedirectResponse(url="/profile", status_code=status.HTTP_308_PERMANENT_REDIRECT)
    else:
        return RedirectResponse(url="/login", status_code=status.HTTP_308_PERMANENT_REDIRECT)

@user_router.post('/logout')
async def logout(request: Request):
    """Обработка выхода пользователя"""
    request.session.clear()
    return 200

@user_router.post('/send_transaction')
async def transfer(
        request: Request
):
    """Обработка создания транзакции"""
    if request.session.get("user_id") is not None:
        data = await request.json()
        address = data.get("address")
        amount = data.get("amount")
        user = storage.get_user_by_username(request.session.get("username"))
        recipient = storage.get_user_by_address(address)
        amount = float(amount)
        if recipient is None:
            request.session["error_message"] = "Пользователь с таким именем не найден"
            return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)
        if user is None:
            request.session.clear()
            request.session['error_message'] = "Ошибка в сессии, повторите вход"
            return RedirectResponse(url="/login", status_code=status.HTTP_404_NOT_FOUND)

        if user.balance < amount:
            request.session['error_message'] = "Недостаточно монет на счету"
            return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)
        transaction = form_transaction(sender=user.address, recipient=address, amount=amount,
                                       private_key=user.private_key,public_key=user.public_key)
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{settings.ROOT_URL}/transactions', json=transaction) as response:
                # Важно: нужно дождаться чтения тела ответа (await)
                result = await response.json()
                return JSONResponse(
                            status_code=200,
                            content={
                                "success": True,
                                "message": f"Перевод на сумму {amount} Плюксиков успешно выполнен"
                                    }
                )
