from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=64, description="Пароль от 4 до 64 символов")


class RegisterResponse(BaseModel):

    user_id: str
    username: str


class LoginRequest(BaseModel):

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=64, description="Пароль от 4 до 64 символов")


class TokenResponse(BaseModel):

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ValidateResponse(BaseModel):

    user_id: str
    username: str
