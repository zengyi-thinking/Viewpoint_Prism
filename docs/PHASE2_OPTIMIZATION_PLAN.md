# Phase 2 优化方案

## 当前架构评估

### 优势
- ✅ 清晰的 Modular Monolith 架构
- ✅ 前后端模块化组织
- ✅ 类型安全的 API 层
- ✅ 泛型基类减少重复代码

### 待优化点
- ⚠️ 新增模块需手动配置路由
- ⚠️ 模块间通信缺少统一机制
- ⚠️ 依赖注入不够完善
- ⚠️ 缓存策略简单（仅内存）
- ⚠️ 缺少代码生成工具

---

## 优化路线图

```
Phase 2 优化
├── 后端优化
│   ├── A. 自动化与工具
│   │   ├── A1. 自动路由注册
│   │   ├── A2. 模块脚手架生成器
│   │   └── A3. API 文档自动生成
│   │
│   ├── B. 架构增强
│   │   ├── B1. 依赖注入容器
│   │   ├── B2. 事件总线（模块间通信）
│   │   └── B3. 服务接口抽象
│   │
│   └── C. 性能与可靠性
│       ├── C1. Redis 缓存层
│       ├── C2. 任务队列集成
│       └── C3. 请求限流与熔断
│
└── 前端优化
    ├── D. 状态管理升级
    │   ├── D1. 模块化 Store 拆分
    │   └── D2. React Query 集成
    │
    └── E. 性能优化
        ├── E1. 路由懒加载
        └── E2. 虚拟滚动
```

---

## A. 后端自动化优化

### A1. 自动路由注册

**问题**：当前每个新模块都需要在 `main.py` 手动注册路由

**解决方案**：实现模块自动发现和注册

```python
# app/core/router_registry.py
from fastapi import FastAPI
from pathlib import Path
import importlib

class RouterRegistry:
    def __init__(self, app: FastAPI):
        self.app = app

    def register_modules(self, modules_dir: Path = Path(__file__).parent.parent / "modules"):
        """自动发现并注册所有模块路由"""
        for module_dir in modules_dir.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith("_"):
                try:
                    # 动态导入模块的 api.py
                    api_module = importlib.import_module(f"app.modules.{module_dir.name}.api")
                    router = getattr(api_module, "router", None)
                    if router:
                        self.app.include_router(router, prefix="/api", tags=[module_dir.name])
                        print(f"✅ Registered router: {module_dir.name}")
                except ImportError:
                    # 模块没有 api.py，跳过
                    pass

# main.py 中使用
from app.core.router_registry import RouterRegistry

app = FastAPI(title="Viewpoint Prism API")
registry = RouterRegistry(app)
registry.register_modules()  # 自动注册所有模块
```

**收益**：
- 新增模块无需修改 `main.py`
- 即插即用，真正的模块化

---

### A2. 模块脚手架生成器

**问题**：新增模块需要创建多个文件（api.py, service.py, dao.py, schemas.py）

**解决方案**：CLI 工具自动生成模块模板

```bash
# 使用方式
python scripts/create_module.py chatbot

# 自动生成：
# app/modules/chatbot/
# ├── __init__.py
# ├── api.py
# ├── service.py
# ├── dao.py
# ├── schemas.py
# └── models.py
```

**实现**：
```python
# scripts/create_module.py
import os
from pathlib import Path

MODULE_TEMPLATE = """
\"\"\"{module_name} 模块\"\"\"
from .models import {ModelName}
from .dao import {ModelName}DAO
from .service import {ModelName}Service
from .schemas import {ModelName}Base, {ModelName}Create, {ModelName}Response

__all__ = [
    "{ModelName}",
    "{ModelName}DAO",
    "{ModelName}Service",
    "{ModelName}Base",
    "{ModelName}Create",
    "{ModelName}Response",
]
"""

DAO_TEMPLATE = """
from app.core.base_dao import BaseDAO
from app.modules.{module_name}.models import {ModelName}
from sqlalchemy.ext.asyncio import AsyncSession

class {ModelName}DAO(BaseDAO[{ModelName}]):
    def __init__(self, session: AsyncSession):
        super().__init__({ModelName}, session)
"""

# ... 更多模板

def create_module(module_name: str):
    """创建新模块"""
    module_path = Path("app/modules") / module_name
    module_path.mkdir(exist_ok=True)

    # 生成标准文件
    templates = {
        "__init__.py": MODULE_TEMPLATE,
        "dao.py": DAO_TEMPLATE,
        "service.py": SERVICE_TEMPLATE,
        "api.py": API_TEMPLATE,
        "schemas.py": SCHEMAS_TEMPLATE,
        "models.py": MODELS_TEMPLATE,
    }

    for filename, template in templates.items():
        content = template.format(
            module_name=module_name,
            ModelName=module_name.title().replace("_", "")
        )
        (module_path / filename).write_text(content)

    print(f"✅ Module '{module_name}' created successfully!")
```

**收益**：
- 30秒创建完整模块
- 标准化代码结构
- 减少人为错误

---

## B. 后端架构增强

### B1. 依赖注入容器

**问题**：当前 Service 的 DAO 是硬编码初始化

**解决方案**：使用 `dependency-injector` 实现真正的 DI

```python
# app/core/container.py
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide

class Container(containers.DeclarativeContainer):
    """依赖注入容器"""

    # 配置
    config = providers.Configuration()

    # 核心依赖
    database = providers.Singleton(async_session)

    # 共享服务
    sophnet_service = providers.Singleton(
        SophNetService,
        api_key=config.sophnet.api_key
    )

    vector_store = providers.Singleton(
        VectorStore,
        url=config.qdrant.url
    )

    # 业务模块（按需注册）
    source_service = providers.Factory(
        SourceService,
        session=database,
    )

    chat_service = providers.Factory(
        ChatService,
        session=database,
        sophnet=sophnet_service,
        vector_store=vector_store
    )

# 使用 FastAPI 依赖注入
from fastapi import Depends
from app.core.container import Container

def get_source_service(
    service: SourceService = Depends(Provide[Container.source_service])
) -> SourceService:
    return service

# API 中使用
@router.get("/sources")
async def list_sources(
    service: SourceService = Depends(get_source_service)
):
    return await service.list_all()
```

**收益**：
- 松耦合，便于测试
- 统一管理依赖
- 支持多种配置（开发/生产）

---

### B2. 事件总线（模块间通信）

**问题**：模块间如果要交互，需要直接导入，产生耦合

**解决方案**：实现事件驱动的模块通信

```python
# app/core/event_bus.py
from typing import Callable, Dict, List
from dataclasses import dataclass

@dataclass
class Event:
    """事件基类"""
    name: str
    data: dict

class EventBus:
    """简单事件总线"""
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable):
        """订阅事件"""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def publish(self, event: Event):
        """发布事件"""
        if event.name in self._listeners:
            for callback in self._listeners[event.name]:
                callback(event.data)

# 全局事件总线
event_bus = EventBus()

# 使用示例
# source/service.py - 视频分析完成后发布事件
async def complete_analysis(self, source_id: str):
    await self._dao.update(source_id, status="done")
    event_bus.publish(Event(
        name="source.analyzed",
        data={"source_id": source_id}
    ))

# chat/service.py - 订阅分析完成事件，更新向量库
def __init__(self, ...):
    event_bus.subscribe("source.analyzed", self._on_source_analyzed)

def _on_source_analyzed(self, data: dict):
    """视频分析完成，更新向量库"""
    asyncio.create_task(self._update_vector_store(data["source_id"]))
```

**收益**：
- 模块间零耦合
- 易于扩展新功能
- 支持异步处理

---

## C. 后端性能与可靠性

### C1. Redis 缓存层

**问题**：当前仅用简单内存缓存（无过期策略）

**解决方案**：集成 Redis 缓存

```python
# app/core/cache.py
import redis.asyncio as redis
from typing import Optional
import json

class CacheService:
    """Redis 缓存服务"""
    def __init__(self, url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(url, encoding="utf-8", decode=True)

    async def get(self, key: str) -> Optional[dict]:
        """获取缓存"""
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: dict, ttl: int = 300):
        """设置缓存（默认5分钟过期）"""
        await self.redis.setex(key, ttl, json.dumps(value))

    async def delete(self, key: str):
        """删除缓存"""
        await self.redis.delete(key)

    async def invalidate_pattern(self, pattern: str):
        """批量删除（支持通配符）"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

# BaseService 中集成
from app.core.cache import cache_service

class BaseService:
    async def get_with_cache(self, id: str, cache_key: str) -> Optional[ModelType]:
        """先查缓存，再查数据库"""
        cached = await cache_service.get(cache_key)
        if cached:
            return self._model(**cached)

        entity = await self._dao.get(id)
        if entity:
            await cache_service.set(cache_key, entity.dict())

        return entity
```

**收益**：
- 持久化缓存
- 支持分布式部署
- 灵活的过期策略

---

### C2. 任务队列集成

**问题**：长时间任务（视频分析）阻塞请求

**解决方案**：集成 Celery + Redis 任务队列

```python
# app/worker/tasks.py
from celery import Celery

celery_app = Celery(
    "viewpoint_prism",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@celery_app.task
def analyze_video_task(source_id: str):
    """异步视频分析任务"""
    # 执行耗时的分析操作
    result = perform_analysis(source_id)
    return result

# service.py 中调用
from app.worker.tasks import analyze_video_task

class SourceService:
    def analyze_source(self, source_id: str):
        """启动异步分析任务"""
        task = analyze_video_task.delay(source_id)
        return {"task_id": task.id, "status": "pending"}

    def get_task_status(self, task_id: str):
        """查询任务状态"""
        result = celery_app.AsyncResult(task_id)
        return {
            "status": result.status,
            "result": result.result
        }
```

**收益**：
- 请求不阻塞
- 支持任务重试
- 可横向扩展 Worker

---

## D. 前端状态管理升级

### D1. 模块化 Store 拆分

**问题**：`app-store.ts` 单一文件包含所有状态，随功能增加会臃肿

**解决方案**：按模块拆分 Store

```typescript
// stores/modules/source.ts
import { create } from 'zustand';
import { SourceAPI } from '@/api/modules/source';

interface SourceStore {
  sources: VideoSource[];
  selectedIds: string[];
  fetchSources: () => Promise<void>;
  uploadVideo: (file: File) => Promise<void>;
  deleteSource: (id: string) => Promise<void>;
}

export const useSourceStore = create<SourceStore>((set, get) => ({
  sources: [],
  selectedIds: [],

  fetchSources: async () => {
    const result = await SourceAPI.list(100, 0);
    set({ sources: result.sources });
  },

  uploadVideo: async (file) => {
    const source = await SourceAPI.upload(file);
    set(state => ({ sources: [...state.sources, source] }));
  },

  deleteSource: async (id) => {
    await SourceAPI.delete(id);
    set(state => ({
      sources: state.sources.filter(s => s.id !== id)
    }));
  },
}));

// stores/modules/analysis.ts
export const useAnalysisStore = create<AnalysisStore>((set, get) => ({
  // ...
}));

// stores/modules/chat.ts
export const useChatStore = create<ChatStore>((set, get) => ({
  // ...
}));

// stores/index.ts - 统一导出
export { useSourceStore } from './modules/source';
export { useAnalysisStore } from './modules/analysis';
export { useChatStore } from './modules/chat';
```

**收益**：
- 每个模块独立维护
- 减少单文件复杂度
- 更好的代码分割

---

### D2. React Query 集成

**问题**：手动管理缓存、加载状态、错误处理

**解决方案**：使用 React Query 自动管理服务器状态

```typescript
// api/hooks.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SourceAPI } from './modules/source';

export const useSources = () => {
  return useQuery({
    queryKey: ['sources'],
    queryFn: () => SourceAPI.list(100, 0),
  });
};

export const useSourceUpload = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => SourceAPI.upload(file),
    onSuccess: () => {
      // 自动刷新列表
      queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
  });
};

export const useSourceDelete = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => SourceAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
  });
};

// 组件中使用
function SourcesPanel() {
  const { data, isLoading, error } = useSources();
  const deleteSource = useSourceDelete();

  if (isLoading) return <Loading />;
  if (error) return <Error />;

  return (
    <ul>
      {data.sources.map(source => (
        <li key={source.id}>
          {source.title}
          <button onClick={() => deleteSource.mutate(source.id)}>
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}
```

**收益**：
- 自动缓存、重试、刷新
- 减少样板代码
- 更好的用户体验

---

## E. 前端性能优化

### E1. 路由懒加载

**问题**：所有组件打包到主 bundle

**解决方案**：React.lazy + Suspense

```typescript
// App.tsx
import { lazy, Suspense } from 'react';
import { Spinner } from '@/components/ui/spinner';

const MainLayout = lazy(() => import('@/components/layout/MainLayout'));
const ProductPage = lazy(() => import('@/components/ui/ProductPage'));

function App() {
  return (
    <Suspense fallback={<Spinner />}>
      {showProductPage ? <ProductPage /> : <MainLayout />}
    </Suspense>
  );
}
```

**收益**：
- 减少初始加载时间
- 按需加载组件

---

## 优化实施建议

### 优先级排序

| 优先级 | 优化项 | 预计工作量 | 收益 |
|-------|--------|-----------|------|
| **P0** | A2. 模块脚手架生成器 | 2天 | 开发效率提升50% |
| **P0** | A1. 自动路由注册 | 1天 | 减少配置工作 |
| **P1** | B2. 事件总线 | 3天 | 模块解耦 |
| **P1** | D1. 模块化 Store | 2天 | 代码可维护性 |
| **P1** | E1. 路由懒加载 | 1天 | 性能提升 |
| **P2** | B1. 依赖注入 | 3天 | 便于测试 |
| **P2** | C1. Redis 缓存 | 2天 | 性能提升 |
| **P2** | D2. React Query | 2天 | 用户体验 |
| **P3** | C2. 任务队列 | 4天 | 可靠性提升 |

### 推荐实施路径

**第一阶段（1周）- 快速见效**
1. A2. 模块脚手架生成器
2. A1. 自动路由注册
3. E1. 路由懒加载

**第二阶段（2周）- 架构增强**
4. B2. 事件总线
5. D1. 模块化 Store
6. D2. React Query

**第三阶段（2周）- 性能与可靠性**
7. B1. 依赖注入
8. C1. Redis 缓存
9. C2. 任务队列

---

## 总结

Phase 2 优化聚焦于：

1. **自动化**：减少重复工作，提高开发效率
2. **解耦**：事件总线 + 依赖注入，模块间零耦合
3. **性能**：缓存 + 任务队列 + 懒加载
4. **可维护性**：模块化 Store + 脚手架工具

建议优先实施**快速见效**的优化（第一阶段），然后根据项目需求逐步推进后续优化。
