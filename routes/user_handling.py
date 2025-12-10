from typing import Annotated

from fastapi import APIRouter, Request, Form, status

from sqlalchemy.testing.pickleable import User
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from config import settings
from db.storage import BlockchainStorage

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
@user_router.get("/")
def route_root(request: Request):
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

    return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)