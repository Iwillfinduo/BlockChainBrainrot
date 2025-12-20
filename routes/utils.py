import time

from fastapi import Request, HTTPException, status
from core.node_core import Transaction

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

def create_transaction(sender, recipient, amount) -> Transaction:
    transaction = Transaction(sender, recipient, amount, timestamp=time.time())
    return transaction


