from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    email: str
    name: str

    @field_validator("email")
    @classmethod
    def email_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Email must not be empty")
        if "@" not in value:
            raise ValueError("Email must contain @")
        return value

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name must not be empty")
        return value


class UserRead(UserCreate):
    id: int
