#!/usr/bin/env python3
"""
模块脚手架生成器 - 快速创建新的业务模块

使用方式:
    python scripts/create_module.py <module_name>

示例:
    python scripts/create_module.py chatbot
    python scripts/create_module.py notification
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def to_pascal_case(name: str) -> str:
    """将 snake_case 转换为 PascalCase"""
    return "".join(word.capitalize() for word in name.split("_"))


def generate_init_py(module_name: str, model_name: str) -> str:
    """生成 __init__.py 内容"""
    return f'''"""
{module_name} module - {model_name} management.
Handles CRUD operations for {model_name}.
"""

from .models import {model_name}
from .dao import {model_name}DAO
from .service import {model_name}Service
from .schemas import {model_name}Base, {model_name}Create, {model_name}Response

__all__ = [
    "{model_name}",
    "{model_name}DAO",
    "{model_name}Service",
    "{model_name}Base",
    "{model_name}Create",
    "{model_name}Response",
]
'''


def generate_models_py(module_name: str, model_name: str) -> str:
    """生成 models.py 内容"""
    return f'''"""
{module_name} SQLAlchemy models.
"""

from sqlalchemy import Column, String, DateTime, Float, Text
from sqlalchemy.sql import func
from app.models import Base


class {model_name}(Base):
    """{model_name} model."""
    __tablename__ = "{module_name}s"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<{model_name}(id={{self.id}}, name={{self.name}})>"
'''


def generate_schemas_py(module_name: str, model_name: str) -> str:
    """生成 schemas.py 内容"""
    return f'''"""
{module_name} Pydantic schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class {model_name}Base(BaseModel):
    """Base schema for {model_name}."""
    name: str = Field(..., description="Name of the {module_name}")
    description: Optional[str] = Field(None, description="Description")


class {model_name}Create({model_name}Base):
    """Schema for creating a new {model_name}."""
    pass


class {model_name}Response({model_name}Base):
    """Schema for {model_name} response."""
    id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
'''


def generate_dao_py(module_name: str, model_name: str) -> str:
    """生成 dao.py 内容"""
    return f'''"""
{module_name} Data Access Object.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.base_dao import BaseDAO
from app.modules.{module_name}.models import {model_name}


class {model_name}DAO(BaseDAO[{model_name}]):
    """DAO for {model_name} model."""

    async def get_by_status(self, status: str) -> List[{model_name}]:
        """Get {module_name}s by status."""
        result = await self.session.execute(
            select({model_name}).where({model_name}.status == status)
        )
        return list(result.scalars().all())

    async def search_by_name(self, keyword: str, limit: int = 50) -> List[{model_name}]:
        """Search {module_name}s by name keyword."""
        result = await self.session.execute(
            select({model_name})
            .where({model_name}.name.contains(keyword))
            .limit(limit)
        )
        return list(result.scalars().all())
'''


def generate_service_py(module_name: str, model_name: str) -> str:
    """生成 service.py 内容"""
    return f'''"""
{module_name} business service.
"""

import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_service import BaseService
from app.modules.{module_name}.dao import {model_name}DAO
from app.modules.{module_name}.models import {model_name}
from app.modules.{module_name}.schemas import {model_name}Create, {model_name}Response

logger = logging.getLogger(__name__)


class {model_name}Service(BaseService[{model_name}DAO]):
    """Service for {module_name} management."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, {model_name}DAO, {model_name})

    async def create_{module_name}(self, data: {model_name}Create) -> {model_name}:
        """Create a new {module_name}."""
        {module_name_lower} = await self.dao.create(
            name=data.name,
            description=data.description,
            status="active",
        )
        self.log_info("{model_name} created", id={module_name_lower}.id, name={module_name_lower}.name)
        return {module_name_lower}

    async def get_{module_name}(self, id: str) -> Optional[{model_name}]:
        """Get {module_name} by ID."""
        return await self.dao.get(id)

    async def list_{module_name}s(self, limit: int = 100, offset: int = 0) -> List[{model_name}]:
        """List all {module_name}s."""
        return await self.dao.get_all(limit=limit, offset=offset)

    async def update_{module_name}(self, id: str, **kwargs) -> Optional[{model_name}]:
        """Update {module_name}."""
        result = await self.dao.update(id, **kwargs)
        if result:
            self.log_info("{model_name} updated", id=id)
        return result

    async def delete_{module_name}(self, id: str) -> bool:
        """Delete {module_name} by ID."""
        result = await self.dao.delete(id)
        if result:
            self.log_info("{model_name} deleted", id=id)
        return result

    async def get_by_status(self, status: str) -> List[{model_name}]:
        """Get {module_name}s by status."""
        return await self.dao.get_by_status(status)

    async def search_by_name(self, keyword: str) -> List[{model_name}]:
        """Search {module_name}s by name."""
        return await self.dao.search_by_name(keyword)
'''


def generate_api_py(module_name: str, model_name: str) -> str:
    """生成 api.py 内容"""
    return f'''"""
{module_name} API routes.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.modules.{module_name} import {model_name}Service, {model_name}Create, {model_name}Response

router = APIRouter(prefix="/{module_name}s", tags=["{module_name}s"])


def get_{module_name}_service(db: AsyncSession = Depends(get_db)) -> {model_name}Service:
    """Dependency for {model_name}Service."""
    return {model_name}Service(db)


@router.post("/", response_model={model_name}Response)
async def create_{module_name}(
    data: {model_name}Create,
    service: {model_name}Service = Depends(get_{module_name}_service),
):
    """Create a new {module_name}."""
    return await service.create_{module_name}(data)


@router.get("/", response_model=List[{model_name}Response])
async def list_{module_name}s(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: {model_name}Service = Depends(get_{module_name}_service),
):
    """List all {module_name}s."""
    items = await service.list_{module_name}s(limit=limit, offset=offset)
    return [{model_name}Response.model_validate(item) for item in items]


@router.get("/{{item_id}}", response_model={model_name}Response)
async def get_{module_name}(
    item_id: str,
    service: {model_name}Service = Depends(get_{module_name}_service),
):
    """Get {module_name} by ID."""
    item = await service.get_{module_name}(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{model_name} not found: {{item_id}}")
    return item


@router.delete("/{{item_id}}")
async def delete_{module_name}(
    item_id: str,
    service: {model_name}Service = Depends(get_{module_name}_service),
):
    """Delete {module_name} by ID."""
    result = await service.delete_{module_name}(item_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"{model_name} not found: {{item_id}}")
    return {{"status": "deleted", "id": item_id}}
'''


def create_module(module_name: str) -> None:
    """创建新模块"""
    # 验证模块名
    if not module_name.islower() or not module_name.isidentifier():
        print(f"❌ 错误: 模块名必须是有效的 snake_case 标识符")
        print(f"   示例: chatbot, user_profile, notification_service")
        sys.exit(1)

    # 计算路径
    model_name = to_pascal_case(module_name)
    modules_dir = Path(__file__).parent.parent / "packages" / "backend" / "app" / "modules"
    module_dir = modules_dir / module_name

    # 检查模块是否已存在
    if module_dir.exists():
        print(f"❌ 错误: 模块 '{module_name}' 已存在")
        sys.exit(1)

    # 创建目录
    module_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 创建目录: {module_dir.relative_to(project_root)}")

    # 生成文件
    files = {
        "__init__.py": generate_init_py(module_name, model_name),
        "models.py": generate_models_py(module_name, model_name),
        "schemas.py": generate_schemas_py(module_name, model_name),
        "dao.py": generate_dao_py(module_name, model_name),
        "service.py": generate_service_py(module_name, model_name),
        "api.py": generate_api_py(module_name, model_name),
    }

    for filename, content in files.items():
        file_path = module_dir / filename
        file_path.write_text(content, encoding="utf-8")
        print(f"   ✅ {filename}")

    # 提示后续步骤
    print(f"\n🎉 模块 '{module_name}' 创建成功!")
    print(f"\n📋 后续步骤:")
    print(f"   1. 根据需求调整模型: {module_dir / 'models.py'}")
    print(f"   2. 调整 Schema: {module_dir / 'schemas.py'}")
    print(f"   3. 实现业务逻辑: {module_dir / 'service.py'}")
    print(f"   4. 自定义 API 端点: {module_dir / 'api.py'}")
    print(f"\n💡 路由会自动注册，无需修改 main.py")


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python scripts/create_module.py <module_name>")
        print("\n示例:")
        print("  python scripts/create_module.py chatbot")
        print("  python scripts/create_module.py user_profile")
        sys.exit(1)

    module_name = sys.argv[1]
    create_module(module_name)


if __name__ == "__main__":
    main()
