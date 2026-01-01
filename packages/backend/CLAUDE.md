[根目录](../CLAUDE.md) > [packages](../) > **backend**

---

# Backend - 后端服务模块

> FastAPI + Python 构建的 AI 后端服务

---

## 变更记录 (Changelog)

### 2025-12-30 14:03:28 - 初始化模块文档
- 创建后端模块文档
- 记录 API 路由、服务层和数据模型

---

## 模块职责

后端模块是 Viewpoint Prism 的核心服务层，负责：
- 视频文件接收与存储
- AI 智能分析（ASR 转写、视觉理解、LLM 推理）
- 向量存储与检索（ChromaDB）
- RESTful API 提供
- 异步任务处理（创意内容生成）
- 网络视频抓取

---

## 入口与启动

### 入口文件
- **主应用**: `app/main.py` - FastAPI 应用入口
- **配置**: `app/core/config.py` - 环境配置管理
- **数据库**: `app/core/database.py` - 数据库连接

### 启动命令
```bash
# 开发模式
pnpm dev:backend
# 或
cd packages/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 服务地址
- API: http://localhost:8000
- 文档: http://localhost:8000/docs (Swagger UI)
- 健康检查: http://localhost:8000/health

---

## 对外接口（API 路由）

### API 路由结构
```
/api
├── /sources/           # 视频源管理
├── /analysis/          # 分析功能
├── /chat/              # AI 聊天
├── /create/            # 创意生成
└── /ingest/            # 网络摄入
```

### 路由文件详情

| 文件 | 端点 | 功能 |
|------|------|------|
| `upload.py` | `POST /api/sources/upload` | 上传视频文件 |
| `chat.py` | `POST /api/chat/` | AI 聊天对话 |
| `analysis.py` | `POST /api/analysis/generate` | 生成分析结果 |
| `creative.py` | `POST /api/create/debate` | 生成辩论视频 |
| `creative.py` | `POST /api/create/supercut` | 生成实体蒙太奇 |
| `creative.py` | `POST /api/create/digest` | 生成智能浓缩 |
| `creative.py` | `POST /api/create/director_cut` | 生成 AI 导演剪辑 |
| `ingest.py` | `POST /api/ingest/search` | 网络搜索视频 |

---

## 关键依赖与配置

### 核心依赖
```
# Web 框架
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# 数据库
sqlalchemy>=2.0.25
aiosqlite>=0.19.0

# AI/LLM
dashscope>=1.14.0        # 阿里云 DashScope
langchain>=0.1.5
openai>=1.12.0           # ModelScope 兼容

# 向量存储
chromadb>=0.4.22

# 媒体处理
ffmpeg-python>=0.2.0
yt-dlp>=2023.0.0

# 内容生成
edge-tts>=6.1.9          # 微软 TTS
moviepy>=1.0.3           # 视频编辑
```

### 环境变量
在项目根 `.env` 文件中配置：

```env
# DashScope API (阿里云)
DASHSCOPE_API_KEY=your_key_here

# ModelScope API
MODELSCOPE_API_KEY=your_key_here
MODELSCOPE_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/viewpoint_prism.db

# ChromaDB
CHROMA_DB_DIR=data/chromadb

# 目录
UPLOAD_DIR=data/uploads
TEMP_DIR=data/temp
MAX_UPLOAD_SIZE=1073741824
```

---

## 目录结构

```
packages/backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   ├── upload.py        # 上传接口
│   │   ├── chat.py          # 聊天接口
│   │   ├── analysis.py      # 分析接口
│   │   ├── creative.py      # 创意生成接口
│   │   ├── ingest.py        # 网络摄入接口
│   │   └── schemas.py       # Pydantic 模型
│   ├── services/            # 业务服务层
│   │   ├── __init__.py
│   │   ├── intelligence.py  # AI 智能服务
│   │   ├── analysis_service.py  # 分析服务
│   │   ├── rag_service.py   # RAG 检索服务
│   │   ├── media_processor.py   # 媒体处理
│   │   ├── vector_store.py  # 向量存储
│   │   ├── director.py      # AI 导演服务
│   │   ├── creator.py       # 创意生成服务
│   │   └── crawler.py       # 网络爬虫
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   └── models.py        # SQLAlchemy 模型
│   ├── core/                # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py        # 配置管理
│   │   └── database.py      # 数据库连接
│   └── __init__.py
├── tests/                   # 测试文件
│   ├── e2e_test.py
│   └── test_phase8.py
├── data/                    # 数据目录（运行时生成）
│   ├── uploads/             # 上传文件
│   ├── temp/                # 临时文件
│   ├── chromadb/            # 向量数据库
│   └── generated/           # 生成内容
├── requirements.txt
└── package.json
```

---

## 数据模型

### SQLAlchemy 模型 (`app/models/models.py`)

| 模型 | 表名 | 描述 |
|------|------|------|
| `Source` | `sources` | 视频源存储 |
| `Evidence` | `evidences` | 转写片段和关键帧 |
| `AnalysisResult` | `analysis_results` | 分析结果缓存 |
| `ChatMessage` | `chat_messages` | 聊天历史 |

### Source 状态枚举
- `UPLOADED` - 已上传
- `PROCESSING` - 处理中
- `ANALYZING` - 分析中
- `DONE` - 完成
- `ERROR` - 错误

---

## 服务层说明

### IntelligenceService (`services/intelligence.py`)
DashScope AI 服务封装：
- `transcribe_audio()` - Paraformer ASR 音频转写
- `analyze_frame()` - Qwen-VL 单帧分析
- `analyze_frames()` - 批量帧分析

### AnalysisService (`services/analysis_service.py`)
分析服务核心：
- 生成冲突检测结果
- 构建知识图谱
- 生成时间轴

### RAGService (`services/rag_service.py`)
检索增强生成：
- ChromaDB 向量存储
- 语义搜索
- 上下文检索

### CreatorService (`services/creator.py`)
创意内容生成：
- 辩论视频生成
- 实体蒙太奇
- 智能浓缩

### DirectorService (`services/director.py`)
AI 导演服务：
- 多角色配音
- 剧本生成
- 视频合成

### CrawlerService (`services/crawler.py`)
网络视频抓取：
- yt-dlp 集成
- 多平台支持

---

## 测试

### 测试文件
- `tests/e2e_test.py` - 端到端测试
- `tests/test_phase8.py` - Phase 8 功能测试

### 运行测试
```bash
cd packages/backend
pytest tests/
```

---

## 常见问题 (FAQ)

### Q: 如何更换 AI 模型？
编辑 `app/core/config.py` 中的模型配置，或修改 `intelligence.py` 中的模型调用。

### Q: 如何添加新的 API 端点？
1. 在 `app/api/` 下创建新路由文件
2. 在 `app/api/__init__.py` 中注册路由
3. 定义 Pydantic schemas（如需要）

### Q: 数据存储在哪里？
- SQLite 数据库: `data/viewpoint_prism.db`
- 向量数据库: `data/chromadb/`
- 上传文件: `data/uploads/`
- 生成内容: `data/generated/`

### Q: 如何清理所有数据？
运行项目根目录的 `scripts/hard_reset.py` 脚本。

---

## 相关文件清单

### 核心文件
- `app/main.py`
- `app/core/config.py`
- `app/core/database.py`
- `app/models/models.py`

### API 路由
- `app/api/__init__.py`
- `app/api/upload.py`
- `app/api/chat.py`
- `app/api/analysis.py`
- `app/api/creative.py`
- `app/api/ingest.py`
- `app/api/schemas.py`

### 服务层
- `app/services/intelligence.py`
- `app/services/analysis_service.py`
- `app/services/rag_service.py`
- `app/services/creator.py`
- `app/services/director.py`
- `app/services/crawler.py`

### 配置
- `requirements.txt`
- `package.json`
