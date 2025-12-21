from typing import Annotated

import aiohttp
from fastapi import APIRouter, Request, Form, status

from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates


from config import settings
from db.storage import BlockchainStorage
from routes.utils import require_auth, create_transaction

user_router = APIRouter()
templates = Jinja2Templates(directory='routes/templates')
storage = BlockchainStorage(settings.DATABASE_URL)

@user_router.get("/login")
async def login_form(request: Request):
    error_message = request.session.pop("error_message", None)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error_message}
    )

@user_router.get("/profile")
async def profile(request: Request):
    user_id = require_auth(request)
    username = request.session.get("username")
    user = storage.get_user_by_username(username)
    if user is None:
        request.session.clear()
        RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "wallet.html",
        {'request': request, 'username': username, 'balance_amount': user.balance}
    )

@user_router.get("/register")
async def register_form(request: Request):
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
    request.session.clear()
    return 200
@user_router.post('/transfer')
async def transfer(
        request: Request,
        username: Annotated[str, Form()],
        amount: Annotated[str, Form()],
):
    if request.session.get("user_id") is not None:
        user = storage.get_user_by_username(request.session.get("username"))
        recipient = storage.get_user_by_username(username)
        if recipient is None:
            request.session["error_message"] = "Пользователь с таким именем не найден"
            return RedirectResponse(url="/wallet", status_code=status.HTTP_302_FOUND)
        if user is None:
            request.session.clear()
            request.session['error_message'] = "Ошибка в сессии, повторите вход"
            return RedirectResponse(url="/login", status_code=status.HTTP_404_NOT_FOUND)

        if user.balance < amount:
            request.session['error_message'] = "Недостаточно монет на счету"
            return RedirectResponse(url="/wallet", status_code=status.HTTP_302_FOUND)
        transaction = create_transaction(sender=user.username, recipient=username, amount=amount)
        payload = {'transaction': transaction}
        async with aiohttp.ClientSession() as session:
            async with session.post(settings.ROOT_URL, json=payload) as response:
                # Важно: нужно дождаться чтения тела ответа (await)
                result = await response.json()
                return {"status": response.status, "data": result}


@user_router.post("/login")
async def login_post(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    user = storage.authenticate_user(username, password)
    if not user:
        # Неудачная аутентификация
        request.session["error_message"] = "Неверное имя пользователя или пароль."

        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    balance = None
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{settings.ROOT_URL}/balance/{user.address}') as response:
            # Важно: нужно дождаться чтения тела ответа (await)
            result = await response.json()
            balance = result["balance"]

    storage.update_user_balance(user.id, balance)
    # Успешная аутентификация
    request.session["user_id"] = user.id
    request.session["username"] = user.username

    return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)