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
        """Get record by ID. Compatible with aiosqlite."""
        from sqlalchemy import text

        query_sql = f"SELECT * FROM {self.model.__tablename__} WHERE id = :id LIMIT 1"
        result = await self.session.execute(text(query_sql), {"id": id})
        row = result.fetchone()

        if row is None:
            return None

        # 将Row对象转换为模型实例
        return self._row_to_model(row)

    async def get_by(self, **filters) -> Optional[ModelType]:
        """Get single record by field filters. Compatible with aiosqlite."""
        from sqlalchemy import text

        if not filters:
            return None

        # 构建WHERE子句
        conditions = []
        params = {}
        for key, value in filters.items():
            if hasattr(self.model, key):
                conditions.append(f"{key} = :{key}")
                params[key] = value

        if not conditions:
            return None

        where_clause = f"WHERE {' AND '.join(conditions)}"
        query_sql = f"SELECT * FROM {self.model.__tablename__} {where_clause} LIMIT 1"

        result = await self.session.execute(text(query_sql), params)
        row = result.fetchone()

        if row is None:
            return None

        # 将Row对象转换为模型实例
        return self._row_to_model(row)

    def _row_to_model(self, row) -> Optional[ModelType]:
        """将数据库Row对象转换为模型实例"""
        if row is None:
            return None

        # 获取模型的列名
        column_names = [c.name for c in self.model.__table__.columns]

        # 将Row对象映射为字典
        data = {column_names[i]: row[i] for i in range(len(column_names))}

        # 创建模型实例
        return self.model(**data)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all records with pagination.

        Compatible with aiosqlite by using text() for queries.
        """
        from sqlalchemy import text

        query_sql = f"SELECT * FROM {self.model.__tablename__} ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
        result = await self.session.execute(text(query_sql))
        rows = result.fetchall()

        # 将Row对象转换为模型实例列表
        return [self._row_to_model(row) for row in rows]

    async def list(self, **filters) -> List[ModelType]:
        """Get records matching filters.

        Compatible with aiosqlite by using text() for queries.
        """
        from sqlalchemy import text

        if filters:
            # 构建WHERE子句
            conditions = []
            params = {}
            for key, value in filters.items():
                if hasattr(self.model, key):
                    if isinstance(value, (list, tuple)):
                        placeholders = ",".join([f":{key}_{i}" for i in range(len(value))])
                        conditions.append(f"{key} IN ({placeholders})")
                        for i, v in enumerate(value):
                            params[f"{key}_{i}"] = v
                    else:
                        conditions.append(f"{key} = :{key}")
                        params[key] = value

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            order_clause = f"ORDER BY created_at DESC"

            # 构建完整SQL
            query_sql = f"SELECT * FROM {self.model.__tablename__} {where_clause} {order_clause}"

            result = await self.session.execute(text(query_sql), params)
            rows = result.fetchall()

            # 将Row对象转换为模型实例列表
            return [self._row_to_model(row) for row in rows]
        else:
            # 无过滤条件，使用get_all
            return await self.get_all()

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
        """Count records matching filters. Compatible with aiosqlite."""
        from sqlalchemy import text

        if filters:
            # 构建WHERE子句
            conditions = []
            params = {}
            for key, value in filters.items():
                if hasattr(self.model, key):
                    if isinstance(value, (list, tuple)):
                        placeholders = ",".join([f":{key}_{i}" for i in range(len(value))])
                        conditions.append(f"{key} IN ({placeholders})")
                        for i, v in enumerate(value):
                            params[f"{key}_{i}"] = v
                    else:
                        conditions.append(f"{key} = :{key}")
                        params[key] = value

            where_clause = f"WHERE {' AND '.join(conditions)}"
            query_sql = f"SELECT COUNT(*) FROM {self.model.__tablename__} {where_clause}"
            result = await self.session.execute(text(query_sql), params)
        else:
            query_sql = f"SELECT COUNT(*) FROM {self.model.__tablename__}"
            result = await self.session.execute(text(query_sql))

        return result.scalar() or 0

    async def exists(self, id: str) -> bool:
        """Check if record exists by ID."""
        record = await self.get(id)
        return record is not None

    async def first(self, order_by: str = "created_at", descending: bool = True) -> Optional[ModelType]:
        """Get first record ordered by field. Compatible with aiosqlite."""
        from sqlalchemy import text

        # 验证order_by字段是否存在
        if not hasattr(self.model, order_by):
            raise AttributeError(f"Model {self.model.__name__} has no attribute {order_by}")

        direction = "DESC" if descending else "ASC"
        query_sql = f"SELECT * FROM {self.model.__tablename__} ORDER BY {order_by} {direction} LIMIT 1"

        result = await self.session.execute(text(query_sql))
        row = result.fetchone()

        if row is None:
            return None

        # 将Row对象转换为模型实例
        return self._row_to_model(row)
