"""
Base DAO (Data Access Object) - Repository pattern implementation.
Provides standardized CRUD operations for all database models.
"""

import logging
from typing import TypeVar, Generic, Optional, List, Type, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.sql import Select

from app.core.database import Base

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseDAO(Generic[ModelType]):
    """
    Generic Data Access Object providing standard CRUD operations.

    Usage:
        class UserDAO(BaseDAO[User]):
            pass

        user_dao = UserDAO(User, session)
        user = await user_dao.get(user_id)
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    def _build_conditions(self, **filters) -> List[Any]:
        """Build where conditions from filter kwargs."""
        conditions = []
        for key, value in filters.items():
            if hasattr(self.model, key):
                if isinstance(value, (list, tuple)):
                    conditions.append(getattr(self.model, key).in_(value))
                else:
                    conditions.append(getattr(self.model, key) == value)
        return conditions

    def _build_query(self, **filters) -> Select:
        """Build select query from filter kwargs."""
        conditions = self._build_conditions(**filters)
        query = select(self.model)
        if conditions:
            query = query.where(and_(*conditions))
        return query

    async def get(self, id: str) -> Optional[ModelType]:
        """Get record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by(self, **filters) -> Optional[ModelType]:
        """Get single record by field filters."""
        query = self._build_query(**filters)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all records with pagination."""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def list(self, **filters) -> List[ModelType]:
        """Get records matching filters."""
        query = self._build_query(**filters)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelType:
        """Create new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """Update record by ID."""
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await self.session.commit()
        return await self.get(id)

    async def update_by(self, filters: dict, **kwargs) -> int:
        """Update records matching filters."""
        conditions = self._build_conditions(**filters)
        if not conditions:
            raise ValueError("update_by requires at least one filter")
        stmt = update(self.model).where(and_(*conditions)).values(**kwargs)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def delete(self, id: str) -> bool:
        """Delete record by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def delete_by(self, **filters) -> int:
        """Delete records matching filters."""
        conditions = self._build_conditions(**filters)
        if not conditions:
            raise ValueError("delete_by requires at least one filter")
        stmt = delete(self.model).where(and_(*conditions))
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def count(self, **filters) -> int:
        """Count records matching filters."""
        query = self._build_query(**filters)
        result = await self.session.execute(
            select(self.model.id).select_from(query.subquery())
        )
        return len(result.fetchall())

    async def exists(self, id: str) -> bool:
        """Check if record exists by ID."""
        record = await self.get(id)
        return record is not None

    async def first(self, order_by: str = "created_at", descending: bool = True) -> Optional[ModelType]:
        """Get first record ordered by field."""
        order_func = getattr(self.model, order_by)
        if descending:
            order_func = order_func.desc()
        else:
            order_func = order_func.asc()
        result = await self.session.execute(
            select(self.model).order_by(order_func).limit(1)
        )
        return result.scalar_one_or_none()
