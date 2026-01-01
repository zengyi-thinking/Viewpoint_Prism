[根目录](../CLAUDE.md) > [packages](../) > **frontend**

---

# Frontend - 前端应用模块

> React + TypeScript + Vite 构建的单页应用

---

## 变更记录 (Changelog)

### 2025-12-30 14:03:28 - 初始化模块文档
- 创建前端模块文档
- 记录组件结构、状态管理和路由配置

---

## 模块职责

前端模块是 Viewpoint Prism 的用户界面层，负责：
- 视频源上传与管理
- 可视化分析结果展示（冲突表格、知识图谱、时间轴）
- AI 聊天对话界面
- 创意内容生成（辩论视频、蒙太奇、浓缩视频）
- 视频播放与溯源跳转

---

## 入口与启动

### 入口文件
- **HTML**: `index.html` - 页面模板
- **TSX**: `src/main.tsx` - React 应用入口
- **组件**: `src/App.tsx` - 根组件

### 启动命令
```bash
# 开发模式
pnpm dev

# 构建生产版本
pnpm build

# 预览构建结果
pnpm preview

# 代码检查
pnpm lint
```

### 开发服务器
- 地址: http://localhost:5173
- 代理: `/api` -> `http://localhost:8000`

---

## 对外接口（API 调用）

前端通过以下端点与后端通信：

### 视频源管理
- `GET /api/sources/` - 获取视频源列表
- `POST /api/sources/upload` - 上传视频
- `DELETE /api/sources/{id}` - 删除视频源
- `POST /api/sources/{id}/reprocess` - 重新处理

### 分析功能
- `POST /api/analysis/generate` - 生成分析结果

### 聊天功能
- `POST /api/chat/` - 发送聊天消息

### 创意生成
- `POST /api/create/debate` - 生成辩论视频
- `POST /api/create/supercut` - 生成实体蒙太奇
- `POST /api/create/digest` - 生成智能浓缩
- `POST /api/create/director_cut` - 生成 AI 导演剪辑
- `GET /api/create/tasks/{task_id}` - 查询任务状态

### 网络搜索
- `POST /api/ingest/search` - 启动网络搜索
- `GET /api/ingest/tasks/{task_id}` - 查询搜索任务

---

## 关键依赖与配置

### 核心依赖
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "zustand": "^4.5.2",
  "echarts": "^5.4.3",
  "framer-motion": "^11.0.8",
  "tailwindcss": "^3.4.1",
  "typescript": "^5.3.3",
  "vite": "^5.1.6"
}
```

### 配置文件
- `vite.config.ts` - Vite 构建配置
- `tsconfig.json` - TypeScript 配置
- `tailwind.config.js` - Tailwind CSS 配置
- `postcss.config.js` - PostCSS 配置

---

## 目录结构

```
packages/frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── src/
│   ├── main.tsx              # React 入口
│   ├── App.tsx               # 根组件
│   ├── types/
│   │   └── index.ts          # TypeScript 类型定义
│   ├── stores/
│   │   └── app-store.ts      # Zustand 全局状态
│   ├── lib/
│   │   └── utils.ts          # 工具函数
│   ├── components/
│   │   ├── layout/           # 布局组件
│   │   │   ├── Header.tsx
│   │   │   └── MainLayout.tsx
│   │   ├── panels/           # 功能面板
│   │   │   ├── SourcesPanel.tsx
│   │   │   ├── AnalysisPanel.tsx
│   │   │   └── StagePanel.tsx
│   │   └── ui/               # UI 组件
│   │       └── FeatureCard.tsx
│   └── styles/
│       └── globals.css       # 全局样式
└── package.json
```

---

## 状态管理 (Zustand Store)

### 全局状态结构
```typescript
interface AppState {
  // 视频源
  sources: VideoSource[]
  selectedSourceIds: string[]
  currentSourceId: string | null

  // 播放控制
  currentTime: number
  isPlaying: boolean
  activePlayer: ActivePlayer

  // 分析结果
  conflicts: Conflict[]
  graph: KnowledgeGraph
  timeline: TimelineEvent[]

  // 聊天
  messages: ChatMessage[]
  isLoading: boolean

  // UI 状态
  activeTab: AnalysisTab
  language: Language
  panelVisibility: Record<PanelPosition, boolean>

  // 创意生成任务
  debateTasks: Record<string, DebateTask>
  supercutTasks: Record<string, SupercutTask>
  digestTask: DigestTask | null
  directorTasks: Record<string, DirectorTask>

  // 网络搜索
  networkSearchTask: NetworkSearchTask | null
}
```

### 主要 Actions
- `fetchSources()` - 获取视频源列表
- `uploadVideo(file)` - 上传视频
- `deleteSource(id)` - 删除视频源
- `fetchAnalysis(sourceIds)` - 生成分析
- `sendChatMessage(message)` - 发送聊天消息
- `seekTo(sourceId, time)` - 跳转播放
- `openEntityCard(entity, position)` - 打开实体卡片
- `startDebateGeneration(conflictId, conflict)` - 启动辩论生成

---

## 类型定义

### 核心类型 (`src/types/index.ts`)

| 类型 | 描述 |
|------|------|
| `VideoSource` | 视频源信息 |
| `Conflict` | 观点冲突 |
| `Viewpoint` | 冲突观点 |
| `KnowledgeGraph` | 知识图谱 |
| `GraphNode` | 图节点 |
| `GraphLink` | 图边 |
| `TimelineEvent` | 时间轴事件 |
| `ChatMessage` | 聊天消息 |
| `DebateTask` | 辩论视频任务 |
| `SupercutTask` | 蒙太奇任务 |
| `DigestTask` | 浓缩视频任务 |
| `DirectorTask` | 导演剪辑任务 |
| `NetworkSearchTask` | 网络搜索任务 |

---

## 组件说明

### 布局组件
- **MainLayout**: 主布局，三面板结构（左：源列表，中：播放器，右：分析）
- **Header**: 顶部导航栏

### 面板组件
- **SourcesPanel**: 视频源管理面板
  - 上传视频
  - 视频源列表
  - 网络搜索功能
- **AnalysisPanel**: 分析结果面板
  - 冲突对比表格
  - 知识图谱可视化
  - 时间轴展示
- **StagePanel**: 主舞台面板
  - 视频播放器
  - AI 聊天界面
  - 创意内容播放器

### UI 组件
- **FeatureCard**: 功能卡片组件

---

## 测试与质量

### 代码检查
```bash
pnpm lint
```

### ESLint 配置
- 使用 `@typescript-eslint/parser`
- React 插件: `eslint-plugin-react-hooks`
- 刷新插件: `eslint-plugin-react-refresh`

---

## 样式系统

### Tailwind CSS
- 使用 Tailwind 进行样式开发
- 配置文件: `tailwind.config.js`
- 自定义主题颜色和字体

### 全局样式
- `src/styles/globals.css` - 全局 CSS 变量和基础样式

---

## 常见问题 (FAQ)

### Q: 如何添加新的 API 调用？
在 `app-store.ts` 中添加新的 async action 函数。

### Q: 如何修改主题颜色？
编辑 `tailwind.config.js` 中的 `theme.colors` 配置。

### Q: 如何添加新页面？
在 `src/components/` 下创建新组件，并在路由中使用。

---

## 相关文件清单

### 配置文件
- `vite.config.ts`
- `tsconfig.json`
- `tailwind.config.js`
- `postcss.config.js`
- `package.json`

### 源代码
- `src/main.tsx`
- `src/App.tsx`
- `src/types/index.ts`
- `src/stores/app-store.ts`
- `src/lib/utils.ts`
- `src/components/**/*.tsx`
- `src/styles/globals.css`

### 静态资源
- `index.html`
