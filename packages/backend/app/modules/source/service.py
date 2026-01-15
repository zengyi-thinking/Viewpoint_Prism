"""
Source business service.
"""

import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_service import BaseService
from app.modules.source.dao import SourceDAO
from app.modules.source.models import Source, SourceStatus
from app.modules.source.schemas import SourceCreate, SourceResponse, SourceListResponse

logger = logging.getLogger(__name__)


class SourceService(BaseService[SourceDAO]):
    """Service for source management."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, SourceDAO, Source)

    async def create_source(self, data: SourceCreate, file_path: str, url: str = None) -> Source:
        """Create a new source."""
        source = await self.dao.create(
            title=data.title,
            file_path=file_path,
            url=url,
            file_type=data.file_type,
            platform=data.platform,
            status=SourceStatus.UPLOADED.value,
        )
        self.log_info("Source created", id=source.id, title=source.title)
        return source

    async def get_source(self, id: str) -> Optional[Source]:
        """Get source by ID."""
        return await self.dao.get(id)

    async def list_sources(self, limit: int = 100, offset: int = 0) -> List[Source]:
        """List all sources."""
        return await self.dao.get_all(limit=limit, offset=offset)

    async def list_sources_response(self, limit: int = 100, offset: int = 0) -> SourceListResponse:
        """List all sources as response."""
        sources = await self.list_sources(limit=limit, offset=offset)
        total = await self.dao.count()
        return SourceListResponse(
            sources=[SourceResponse.model_validate(s) for s in sources],
            total=total,
        )

    async def update_status(self, id: str, status: str) -> Optional[Source]:
        """Update source status."""
        result = await self.dao.update(id, status=status)
        if result:
            self.log_info("Source status updated", id=id, status=status)
        return result

    async def delete_source(self, id: str) -> bool:
        """Delete source by ID."""
        result = await self.dao.delete(id)
        if result:
            self.log_info("Source deleted", id=id)
        return result

    async def get_by_status(self, status: str) -> List[Source]:
        """Get sources by status."""
        return await self.dao.get_by_status(status)

    async def search_by_title(self, keyword: str) -> List[Source]:
        """Search sources by title."""
        return await self.dao.search_by_title(keyword)

    async def get_recent(self, limit: int = 10) -> List[Source]:
        """Get recent sources."""
        return await self.dao.get_recent(limit=limit)
