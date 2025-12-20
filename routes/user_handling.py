from typing import Annotated

from fastapi import APIRouter, Request, Form, status

from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from config import settings
from db.storage import BlockchainStorage
from routes.utils import require_auth

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

    return RedirectResponse(url="/login", status_code=status.HTTP_201_CREATED)



@user_router.get("/")
async def route_root(request: Request):
    if request.session.get("user_id") is not None:
        return RedirectResponse(url="/profile", status_code=status.HTTP_308_PERMANENT_REDIRECT)
    else:
        return RedirectResponse(url="/login", status_code=status.HTTP_308_PERMANENT_REDIRECT)


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

    # Успешная аутентификация
    request.session["user_id"] = user.id
    request.session["username"] = user.username

    return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)