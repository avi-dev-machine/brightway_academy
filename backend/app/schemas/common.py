"""Response envelope shared by every endpoint."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: PageMeta | None = None


class ErrorInfo(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: Any = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorInfo


class MessageOut(BaseModel):
    message: str


def ok(data: T, meta: PageMeta | None = None) -> ApiResponse[T]:
    return ApiResponse[T](data=data, meta=meta)
