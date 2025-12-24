from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from config import settings
from routes.user_handling import user_router
from routes.admin_handling import admin_router, mining_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Запуск приложения: {settings.APP_NAME}")
    print(f"Подключение к БД по URL: {settings.DATABASE_URL}")
    
    print(settings.model_config.get('env_file'))
    yield
    await mining_service.stop()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="routes/static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
app.include_router(user_router)
app.include_router(admin_router)