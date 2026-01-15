"""
Router Registry - 自动发现并注册模块路由

自动扫描 app/modules/ 目录下的所有模块，并将它们的路由注册到 FastAPI 应用。
支持标准的 api.py 模块和 creative.py 模块（router 变量）。

使用方式:
    from app.core.router_registry import RouterRegistry

    app = FastAPI()
    registry = RouterRegistry(app)
    registry.register_modules()
"""

from pathlib import Path
import importlib
import logging
from typing import List, Optional
from fastapi import FastAPI, APIRouter

logger = logging.getLogger(__name__)


class RouterRegistry:
    """路由注册器 - 自动发现并注册模块路由"""

    def __init__(self, app: FastAPI, modules_dir: Optional[Path] = None):
        """
        初始化路由注册器

        Args:
            app: FastAPI 应用实例
            modules_dir: 模块目录路径，默认为 app/modules/
        """
        self.app = app
        self.modules_dir = modules_dir or Path(__file__).parent.parent / "modules"

    def register_modules(
        self,
        prefix: str = "/api",
        exclude: Optional[List[str]] = None,
    ) -> None:
        """
        自动发现并注册所有模块路由

        Args:
            prefix: 路由前缀，默认为 /api
            exclude: 要排除的模块名列表
        """
        exclude = exclude or []
        registered_count = 0
        skipped_count = 0

        logger.info("🔍 Scanning modules directory...")

        for module_dir in sorted(self.modules_dir.iterdir()):
            # 跳过非目录和以 _ 开头的目录
            if not module_dir.is_dir() or module_dir.name.startswith("_"):
                continue

            module_name = module_dir.name

            # 跳过排除的模块
            if module_name in exclude:
                logger.info(f"⏭️  Skipping excluded module: {module_name}")
                skipped_count += 1
                continue

            # 尝试注册路由
            if self._register_module(module_name, prefix):
                registered_count += 1

        logger.info(f"✅ Router registration complete: {registered_count} registered, {skipped_count} skipped")

    def _register_module(self, module_name: str, prefix: str) -> bool:
        """
        注册单个模块的路由

        支持两种模式:
        1. 标准 API 模块: app.modules.{module_name}.api -> router
        2. Creative 模块: app.modules.{module_name} -> router

        Args:
            module_name: 模块名
            prefix: 路由前缀

        Returns:
            bool: 是否成功注册
        """
        # 尝试标准 API 模块 (api.py)
        try:
            api_module = importlib.import_module(f"app.modules.{module_name}.api")
            router = getattr(api_module, "router", None)
            extra_routers = getattr(api_module, "extra_routers", None)

            registered_any = False
            if router and isinstance(router, APIRouter):
                self.app.include_router(router, prefix=prefix)
                logger.info(f"   ✅ [{module_name}] Registered standard API router")
                registered_any = True

            if extra_routers and isinstance(extra_routers, list):
                for extra_router in extra_routers:
                    if isinstance(extra_router, APIRouter):
                        self.app.include_router(extra_router, prefix=prefix)
                        logger.info(f"   ✅ [{module_name}] Registered extra router {extra_router.prefix}")
                        registered_any = True

            if registered_any:
                return True
        except ImportError:
            pass

        # 尝试 Creative 模块 (直接在 __init__.py 中定义 router)
        try:
            module = importlib.import_module(f"app.modules.{module_name}")
            router = getattr(module, "router", None)

            if router and isinstance(router, APIRouter):
                self.app.include_router(router, prefix=prefix)
                logger.info(f"   ✅ [{module_name}] Registered creative module router")
                return True
        except (ImportError, AttributeError):
            pass

        # 模块没有路由
        logger.debug(f"   ⏭️  [{module_name}] No router found, skipping")
        return False

    def register_router(
        self,
        router: APIRouter,
        prefix: str = "/api",
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        手动注册单个路由

        Args:
            router: APIRouter 实例
            prefix: 路由前缀
            tags: 路由标签
        """
        self.app.include_router(router, prefix=prefix, tags=tags)
        logger.info(f"   ✅ Manually registered router: {router.prefix or tags}")
