"""Pagination, tri et enveloppe de réponse paginée."""

from __future__ import annotations

from math import ceil
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

T = TypeVar("T")


class PageParams(BaseModel):
    """Paramètres de pagination et de tri communs à toutes les listes."""

    page: int = Field(default=1, ge=1, description="Numéro de page (commence à 1)")
    size: int = Field(default=settings.default_page_size, ge=1, le=settings.max_page_size)
    sort_by: str | None = Field(default=None, description="Champ de tri")
    sort_dir: str = Field(default="asc", pattern="^(asc|desc)$")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=settings.max_page_size)] = settings.default_page_size,
    sort_by: Annotated[str | None, Query()] = None,
    sort_dir: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
) -> PageParams:
    return PageParams(page=page, size=size, sort_by=sort_by, sort_dir=sort_dir)


PageParamsDep = Annotated[PageParams, Depends(page_params)]


class Page(BaseModel, Generic[T]):
    """Enveloppe standard d'une réponse paginée."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, params: PageParams) -> Page[T]:
        return cls(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=ceil(total / params.size) if params.size else 0,
        )


async def paginate(
    session: AsyncSession,
    statement: Select,
    params: PageParams,
) -> tuple[list, int]:
    """Exécute une requête paginée et renvoie (lignes, total)."""
    count_stmt = select(func.count()).select_from(statement.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    result = await session.execute(statement.offset(params.offset).limit(params.size))
    return list(result.scalars().unique().all()), int(total)
