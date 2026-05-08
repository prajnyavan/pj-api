from fastapi import APIRouter, HTTPException, status

from app.db.session import USERS
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int) -> UserRead:
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User id must be positive",
        )

    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserRead(id=user_id, **user)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate) -> UserRead:
    next_id = max(USERS) + 1
    USERS[next_id] = payload.model_dump()
    return UserRead(id=next_id, **USERS[next_id])
