from pydantic import BaseModel


class RegisterIn(BaseModel):
    username: str
    password: str
    role: str


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    role: str
