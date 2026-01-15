"""
Base Service - Base class for all business services.
Provides common functionality like caching, logging, and transaction management.
"""

import logging
from typing import TypeVar, Generic, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DaoType = TypeVar("DaoType")


class BaseService(Generic[DaoType]):
    """
    Base class for business logic services.

    Provides:
    - Automatic DAO initialization
    - Simple caching mechanism
    - Logging integration
    - Transaction helpers

    Usage:
        class UserService(BaseService[UserDAO]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, UserDAO, UserModel)

            async def get_user_by_email(self, email: str):
                return await self.dao.get_by(email=email)
    """

    def __init__(self, session, dao_class, model=None, **kwargs):
        """
        Initialize service with session and DAO class.

        Args:
            session: SQLAlchemy async session
            dao_class: DAO class to use
            model: Optional model class (extracted from DAO if not provided)
            **kwargs: Additional arguments for DAO
        """
        self.session = session
        if model is not None:
            self.dao = dao_class(model, session, **kwargs)
        else:
            self.dao = dao_class(session, **kwargs)
        self._cache: dict = {}
        self._cache_ttl: int = 300  # 5 minutes default TTL

    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from operation and parameters."""
        import hashlib
        params = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        content = f"{prefix}:{params}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            import time
            if time.time() - timestamp < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def set_cached(self, key: str, value: Any) -> None:
        """Set value in cache with timestamp."""
        import time
        self._cache[key] = (value, time.time())

    def clear_cache(self, prefix: str = None) -> None:
        """Clear cache, optionally only keys with given prefix."""
        if prefix is None:
            self._cache.clear()
        else:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]

    async def _execute(self, operation, *args, **kwargs):
        """Execute an async operation with error handling."""
        try:
            result = await operation(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Service operation failed: {e}")
            raise

    def log_info(self, message: str, **context) -> None:
        """Log info message with context."""
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        logger.info(f"{message} {context_str}".strip())

    def log_error(self, message: str, **context) -> None:
        """Log error message with context."""
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        logger.error(f"{message} {context_str}".strip())
