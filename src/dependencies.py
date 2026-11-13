from fastapi import Depends
from config.dependencies import get_current_user
from models import User


async def require_moderator(current_user: User = Depends(get_current_user)) -> User:
    # TODO: коли з'явиться справжній логін, перевіряти, що група користувача MODERATOR або ADMIN,
    # інакше кидати HTTPException(status_code=403, detail="Not enough permissions.")
    return current_user