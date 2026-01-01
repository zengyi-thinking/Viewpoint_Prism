# 视界棱镜 Viewpoint Prism

> 🔮 多源视频情报分析系统 | Multi-source Video Intelligence Analysis System

---

## 📖 详细使用教程 / User Manual

**👉 [点击查看操作手册 / Click to view User Manual](docs/USER_MANUAL.md)**

---

## 项目简介 / Overview

"视界棱镜"是一个视频结构化分析平台，旨在解决长视频内容"理解成本高、信息分散"的问题。

核心理念是 **"多源情报重构"**：用户上传多个关于同一主题的视频（如游戏攻略、科技评测），AI 会自动提取关键信息，生成：

- 🔥 **观点碰撞** - 自动检测不同视频间的观点冲突
- 🕸️ **知识图谱** - 可视化实体关系网络
- 📅 **智能时间轴** - 关键事件时间线
- 💬 **RAG 对话** - 基于视频内容的智能问答（带时间戳引用）

---

## 快速开始 / Quick Start

### 环境要求

- Node.js >= 18.0.0
- pnpm >= 8.0.0
- Python >= 3.10
- FFmpeg

### 安装依赖

```bash
# 前端
pnpm install

# 后端
cd packages/backend
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp packages/backend/.env.example packages/backend/.env
# 编辑 .env 填入 API Keys (DashScope/ModelScope)
```

### 启动服务

```bash
# 方式一：分别启动
pnpm dev:frontend    # 前端 http://localhost:5173
pnpm dev:backend     # 后端 http://localhost:8000

# 方式二：同时启动
pnpm dev
```

---

## Docker 部署 / Docker Deployment

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 访问
# 前端: http://localhost:5173
# 后端: http://localhost:8000
```

---

## 技术栈 / Tech Stack

### Frontend
- React 18 + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- Zustand (状态管理)
- XGPlayer (视频播放)
- ECharts (图表可视化)

### Backend
- FastAPI (Python)
- SQLite + SQLAlchemy
- ChromaDB (向量存储)
- DashScope ASR/VLM
- ModelScope LLM

---

## 项目结构 / Structure

```
Viewpoint Prism/
├── packages/
│   ├── frontend/          # React 前端
│   └── backend/           # FastAPI 后端
├── docs/
│   └── USER_MANUAL.md     # 操作手册
├── scripts/
│   └── hard_reset.py      # 硬重置脚本
└── README.md
```

---

## 开发工具 / Scripts

```bash
# 系统硬重置（清除所有数据）
python scripts/hard_reset.py

# E2E 测试
cd packages/backend
python tests/e2e_test.py
```

---

## License

MIT

---

*视界棱镜 MVP v1.0 - 2025.12*
