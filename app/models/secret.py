from pydantic import BaseModel


class SecretCreate(BaseModel):
    key: str
    value: str


class SecretUpdate(BaseModel):
    value: str


class SecretOut(BaseModel):
    """Metadata only — never includes the decrypted value."""

    id: str
    key: str
    created_at: int
    updated_at: int


class SecretReveal(SecretOut):
    value: str
