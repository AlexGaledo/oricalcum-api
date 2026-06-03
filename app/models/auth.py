from pydantic import BaseModel


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupResponse(BaseModel):
    id: str
    email: str


class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    email: str
