from fastapi import APIRouter, Header, HTTPException, status

from app.services.auth_service import validate_bearer_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/validate")
def validate_token(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    if not validate_bearer_token(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )

    return {"status": "authenticated"}
