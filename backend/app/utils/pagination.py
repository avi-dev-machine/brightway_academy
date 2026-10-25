"""Offset pagination helpers."""

from dataclasses import dataclass
from math import ceil
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query

from app.core.constants import MAX_PAGE_SIZE
from app.schemas.common import ApiResponse, PageMeta

T = TypeVar("T")


@dataclass(frozen=True)
class PageParams:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass
class Page(Generic[T]):
    items: list[T]
    total: int
    params: PageParams

    def meta(self) -> PageMeta:
        pages = ceil(self.total / self.params.page_size) if self.total else 0
        return PageMeta(
            page=self.params.page,
            page_size=self.params.page_size,
            total=self.total,
            total_pages=pages,
        )


def page_params(
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


PageDep = Annotated[PageParams, Depends(page_params)]


def paged(page: Page[T]) -> ApiResponse[list[T]]:
    return ApiResponse[list[T]](data=page.items, meta=page.meta())
