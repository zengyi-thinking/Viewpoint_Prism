"""
Unit tests for Core module - BaseDAO and BaseService
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_dao import BaseDAO
from app.core.base_service import BaseService


class MockModel:
    """Mock SQLAlchemy model for testing."""
    
    def __init__(self, id: str = "test-id", name: str = "test-name"):
        self.id = id
        self.name = name


class TestBaseDAO:
    """Tests for BaseDAO class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def dao(self, mock_session):
        """Create a BaseDAO instance with mock model."""
        return BaseDAO(MockModel, mock_session)
    
    @pytest.mark.asyncio
    async def test_get_returns_record(self, dao, mock_session):
        """Test that get returns a record when found."""
        mock_record = MockModel(id="test-id")
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_record
        
        result = await dao.get("test-id")
        
        assert result == mock_record
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self, dao, mock_session):
        """Test that get returns None when record not found."""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await dao.get("non-existent-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_returns_list(self, dao, mock_session):
        """Test that get_all returns a list of records."""
        mock_records = [MockModel(id="1"), MockModel(id="2")]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_records
        
        result = await dao.get_all()
        
        assert result == mock_records
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_create_adds_record(self, dao, mock_session):
        """Test that create adds and commits a record."""
        mock_record = MockModel(id="new-id", name="new-name")
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        with patch.object(mock_session, 'refresh', new_callable=AsyncMock) as mock_refresh:
            result = await dao.create(name="new-name")
            
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_returns_true_when_record_exists(self, dao, mock_session):
        """Test that delete returns True when record was deleted."""
        mock_session.execute.return_value.rowcount = 1
        mock_session.commit = AsyncMock()
        
        result = await dao.delete("test-id")
        
        assert result is True
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_returns_false_when_record_not_exists(self, dao, mock_session):
        """Test that delete returns False when record not found."""
        mock_session.execute.return_value.rowcount = 0
        mock_session.commit = AsyncMock()
        
        result = await dao.delete("non-existent-id")
        
        assert result is False


class TestBaseService:
    """Tests for BaseService class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_dao_class(self):
        """Create a mock DAO class."""
        dao_class = MagicMock()
        return dao_class
    
    @pytest.fixture
    def service(self, mock_session, mock_dao_class):
        """Create a BaseService instance."""
        return BaseService(mock_session, mock_dao_class)
    
    def test_initialization_sets_dao(self, service, mock_dao_class):
        """Test that service initializes with DAO."""
        assert service.dao is not None
        assert service._cache == {}
    
    def test_get_cache_key_format(self, service):
        """Test that cache key is generated correctly."""
        key = service._get_cache_key("test_operation", param1="value1", param2="value2")
        
        assert key is not None
        assert len(key) == 32  # MD5 hash length
    
    def test_set_and_get_cached(self, service):
        """Test that cache operations work."""
        key = service._get_cache_key("test", key="value")
        
        service.set_cached(key, "cached_value")
        result = service.get_cached(key)
        
        assert result == "cached_value"
    
    def test_get_cached_returns_none_for_expired(self, service):
        """Test that expired cache returns None."""
        key = service._get_cache_key("test", key="expired")
        
        # Set very short TTL
        service._cache_ttl = 0
        
        service.set_cached(key, "value")
        result = service.get_cached(key)
        
        assert result is None
    
    def test_clear_cache(self, service):
        """Test that clear_cache removes all entries."""
        service._cache["key1"] = ("value1", 1)
        service._cache["key2"] = ("value2", 2)
        service._cache["other"] = ("value3", 3)
        
        service.clear_cache(prefix="key")
        
        assert "key1" not in service._cache
        assert "key2" not in service._cache
        assert "other" in service._cache
    
    def test_clear_cache_all(self, service):
        """Test that clear_cache without prefix removes all."""
        service._cache["key1"] = ("value1", 1)
        service._cache["key2"] = ("value2", 2)
        
        service.clear_cache()
        
        assert len(service._cache) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
