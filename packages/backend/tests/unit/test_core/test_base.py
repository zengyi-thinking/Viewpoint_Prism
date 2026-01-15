"""
Unit tests for Core module - BaseService
Tests without real DB to avoid SQLAlchemy model issues.
"""

import pytest
import logging
from unittest.mock import MagicMock

from app.core.base_service import BaseService


class TestBaseService:
    """Tests for BaseService class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return MagicMock()
    
    @pytest.fixture
    def mock_dao(self):
        """Create a mock DAO instance."""
        return MagicMock()
    
    @pytest.fixture
    def service(self, mock_session, mock_dao):
        """Create a BaseService instance with mocked DAO."""
        service = BaseService.__new__(BaseService)
        service.session = mock_session
        service.dao = mock_dao
        service._cache = {}
        service._cache_ttl = 300
        return service
    
    def test_initialization(self, service, mock_session, mock_dao):
        """Test that service initializes correctly."""
        assert service.session is not None
        assert service.dao is not None
        assert service._cache == {}
        assert service._cache_ttl == 300
    
    def test_get_cache_key_format(self, service):
        """Test that cache key is generated correctly."""
        key = service._get_cache_key("test_operation", param1="value1", param2="value2")
        
        assert key is not None
        assert len(key) == 32  # MD5 hash length
    
    def test_cache_key_unique_per_params(self, service):
        """Test that different params produce different keys."""
        key1 = service._get_cache_key("op", a="1")
        key2 = service._get_cache_key("op", a="2")
        key3 = service._get_cache_key("op2", a="1")
        
        assert key1 != key2
        assert key1 != key3
    
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
    
    def test_get_cached_returns_none_for_missing_key(self, service):
        """Test that missing key returns None."""
        result = service.get_cached("nonexistent_key")
        assert result is None
    
    def test_clear_cache_with_prefix(self, service):
        """Test that clear_cache removes entries with prefix."""
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
    
    @pytest.mark.parametrize("level", [logging.INFO, logging.ERROR])
    def test_log_methods(self, service, caplog, level):
        """Test that log methods work correctly."""
        with caplog.at_level(level):
            if level == logging.INFO:
                service.log_info("Test message", key="value")
            else:
                service.log_error("Test error", key="value")
        
        if level == logging.INFO:
            assert "Test message" in caplog.text
        else:
            assert "Test error" in caplog.text
        assert "key=value" in caplog.text


class TestCacheExpiration:
    """Tests for cache expiration logic."""
    
    @pytest.fixture
    def service(self):
        """Create a BaseService instance with mocked DAO."""
        service = BaseService.__new__(BaseService)
        service.session = MagicMock()
        service.dao = MagicMock()
        service._cache = {}
        service._cache_ttl = 300
        return service
    
    def test_cache_expires_after_ttl(self, service):
        """Test that cache expires after TTL."""
        import time
        key = service._get_cache_key("test", key="expiring")
        
        # Set very short TTL
        service._cache_ttl = 1  # 1 second
        
        service.set_cached(key, "value")
        
        # Wait for expiration
        time.sleep(1.1)
        
        result = service.get_cached(key)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
