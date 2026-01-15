"""
Source Data Access Object.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.base_dao import BaseDAO
from app.modules.source.models import Source


class SourceDAO(BaseDAO[Source]):
    """DAO for Source model."""

    async def get_by_status(self, status: str) -> List[Source]:
        """Get sources by status."""
        result = await self.session.execute(
            select(Source).where(Source.status == status)
        )
        return list(result.scalars().all())

    async def get_by_platform(self, platform: str) -> List[Source]:
        """Get sources by platform."""
        result = await self.session.execute(
            select(Source).where(Source.platform == platform)
        )
        return list(result.scalars().all())

    async def search_by_title(self, keyword: str, limit: int = 50) -> List[Source]:
        """Search sources by title keyword."""
        result = await self.session.execute(
            select(Source)
            .where(Source.title.contains(keyword))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> List[Source]:
        """Get recently created sources."""
        result = await self.session.execute(
            select(Source).order_by(Source.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_count(self) -> int:
        """Get total count of sources."""
        result = await self.session.execute(select(Source))
        return len(result.scalars().all())

    async def update_status(self, id: str, status: str) -> Optional[Source]:
        """Update source status."""
        return await self.update(id, status=status)
