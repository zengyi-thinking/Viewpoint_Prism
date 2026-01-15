"""
Unit tests for Modules - Source Service
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.modules.source.service import SourceService
from app.modules.source.schemas import SourceCreate


class TestSourceService:
    """Tests for SourceService class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_session):
        """Create a SourceService instance."""
        return SourceService(mock_session)
    
    @pytest.mark.asyncio
    async def test_create_source(self, service, mock_session):
        """Test that create_source creates a new source."""
        mock_dao = MagicMock()
        mock_dao.create = AsyncMock(return_value=MagicMock(id="new-id", title="Test Video"))
        service.dao = mock_dao
        
        data = SourceCreate(title="Test Video")
        result = await service.create_source(data, file_path="/path/to/video.mp4", url="http://example.com/video")
        
        mock_dao.create.assert_called_once_with(
            title="Test Video",
            file_path="/path/to/video.mp4",
            url="http://example.com/video",
            file_type="video",
            platform="local",
            status="uploaded",
        )
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_source(self, service):
        """Test that get_source returns source by ID."""
        mock_dao = MagicMock()
        mock_source = MagicMock(id="test-id", title="Test Video")
        mock_dao.get = AsyncMock(return_value=mock_source)
        service.dao = mock_dao
        
        result = await service.get_source("test-id")
        
        mock_dao.get.assert_called_once_with("test-id")
        assert result == mock_source
    
    @pytest.mark.asyncio
    async def test_get_source_returns_none_when_not_found(self, service):
        """Test that get_source returns None when source not found."""
        mock_dao = MagicMock()
        mock_dao.get = AsyncMock(return_value=None)
        service.dao = mock_dao
        
        result = await service.get_source("non-existent-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_sources(self, service):
        """Test that list_sources returns list of sources."""
        mock_dao = MagicMock()
        mock_sources = [
            MagicMock(id="1", title="Video 1"),
            MagicMock(id="2", title="Video 2"),
        ]
        mock_dao.get_all = AsyncMock(return_value=mock_sources)
        service.dao = mock_dao
        
        result = await service.list_sources()
        
        assert len(result) == 2
        mock_dao.get_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_source(self, service):
        """Test that delete_source calls DAO delete."""
        mock_dao = MagicMock()
        mock_dao.delete = AsyncMock(return_value=True)
        service.dao = mock_dao
        
        result = await service.delete_source("test-id")
        
        mock_dao.delete.assert_called_once_with("test-id")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_status(self, service):
        """Test that update_status calls DAO update."""
        mock_dao = MagicMock()
        mock_source = MagicMock(id="test-id", status="done")
        mock_dao.update = AsyncMock(return_value=mock_source)
        service.dao = mock_dao
        
        result = await service.update_status("test-id", "done")
        
        mock_dao.update.assert_called_once_with("test-id", status="done")
        assert result == mock_source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
