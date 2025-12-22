from anyio import sleep
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import hashlib

from config import settings
from db.storage import BlockchainStorage

admin_router = APIRouter()
templates = Jinja2Templates(directory="routes/templates")
storage = BlockchainStorage(settings.DATABASE_URL)

# Админский пароль (храним в коде как хеш)
ADMIN_PASSWORD_HASH = hashlib.sha256(b"admin123").hexdigest()

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

    users_count = storage.get_users_count()
    total_balance = storage.get_total_balance()
    users_cards = storage.get_users_for_cards(limit=20)

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "stats": {
                "total_users": users_count,
                "total_balance": round(total_balance, 4),
            },
            "users": users_cards
        }
    )


@admin_router.post("/admin/mining")
async def start_mining(request: Request):
    """Запуск майнинга и автоматическое распределение средств"""
    if not request.session.get("admin_authenticated"):
        raise HTTPException(status_code=403, detail="Not authorized")

    #TODO

    request.session.update({
        "mining_status": "active"
    })

    return RedirectResponse(url="/admin/dashboard", status_code=302)

@admin_router.post("/admin/distribute")
async def distribute_coin(request: Request):
   #TODO
    return RedirectResponse(url="/admin/dashboard", status_code=302)