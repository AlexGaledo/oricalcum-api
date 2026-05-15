import time
import uuid
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ApiMeta(BaseModel):
    server_time: int = Field(default_factory=lambda: int(time.time() * 1000), alias="serverTime")
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}", alias="requestId")

    model_config = {"populate_by_name": True}


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ErrorDetail | None
    meta: ApiMeta = Field(default_factory=ApiMeta)

    model_config = {"populate_by_name": True}


def ok(data: Any) -> ApiResponse:
    return ApiResponse(success=True, data=data, error=None)


def err(code: str, message: str, details: Any = None) -> ApiResponse:
    return ApiResponse(
        success=False,
        data=None,
        error=ErrorDetail(code=code, message=message, details=details),
    )
