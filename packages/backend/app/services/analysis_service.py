"""Analysis service: conflicts, graph, timeline generation."""
import logging
import json
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.intelligence import get_intelligence_service
from app.models.models import Source, Evidence

logger = logging.getLogger(__name__)


class AnalysisService:
    """Generate conflicts, graph, timeline from analyzed sources."""

    def __init__(self):
        self.intel = get_intelligence_service()

    async def generate_conflicts(
        self,
        sources: List[Source],
        evidences: List[Evidence]
    ) -> List[Dict[str, Any]]:
        """Detect viewpoint conflicts between sources."""

        # Build context from ASR
        asr_texts = []
        for s in sources:
            s_evidences = [e for e in evidences if e.source_id == s.id and e.chunk_type == "asr"]
            texts = [e.content for e in s_evidences[:20]]  # Limit
            asr_texts.append(f"{s.title}:\n" + "\n".join(texts))

        context = "\n\n".join(asr_texts)

        prompt = """分析以下多个视频源的字幕内容，找出观点分歧、事实矛盾或打法差异。

返回 JSON 格式（必须严格遵循）:
```json
{
  "conflicts": [
    {
      "id": "conflict_001",
      "topic": "分歧主题",
      "viewpoint_a": {
        "source_id": "xxx",
        "title": "视频标题",
        "view": "观点内容",
        "timestamp": 120.5
      },
      "viewpoint_b": {
        "source_id": "yyy",
        "title": "视频标题",
        "view": "观点内容",
        "timestamp": 45.0
      },
      "verdict": "AI 裁判的客观结论"
    }
  ]
}
```

内容:
""" + context[:4000]  # Limit context

        messages = [{"role": "user", "content": prompt}]

        result = await self.intel.chat_completion(messages)
        if not result:
            return []

        try:
            content = result.output["choices"][0]["message"]["content"]
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            return data.get("conflicts", [])

        except Exception as e:
            logger.error(f"Conflict parsing error: {e}")
            return []

    async def generate_graph(
        self,
        evidences: List[Evidence]
    ) -> Dict[str, Any]:
        """Generate knowledge graph from entities."""

        # Collect ASR texts
        texts = [e.content for e in evidences if e.chunk_type == "asr"][:50]
        context = "\n".join(texts)

        prompt = """从以下文本中提取实体（人物、物品、地点）及其关系。

返回 JSON 格式:
```json
{
  "nodes": [
    {"id": "实体名", "category": "boss|item|location|character", "value": 10}
  ],
  "links": [
    {"source": "实体A", "target": "实体B", "value": 1}
  ]
}
```

文本:
""" + context[:3000]

        messages = [{"role": "user", "content": prompt}]

        result = await self.intel.chat_completion(messages)
        if not result:
            return {"nodes": [], "links": []}

        try:
            content = result.output["choices"][0]["message"]["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            return data

        except Exception as e:
            logger.error(f"Graph parsing error: {e}")
            return {"nodes": [], "links": []}

    async def generate_timeline(
        self,
        evidences: List[Evidence]
    ) -> List[Dict[str, Any]]:
        """Generate timeline from events."""

        # Collect all evidences sorted by timestamp
        sorted_evidences = sorted(evidences, key=lambda e: e.timestamp)

        # Build context
        lines = []
        for e in sorted_evidences[:50]:
            time_str = f"{int(e.timestamp//60):02d}:{int(e.timestamp%60):02d}"
            content = e.content[:100]
            lines.append(f"{time_str} {content}")

        context = "\n".join(lines)

        prompt = """从以下内容中提取关键事件，判断事件类型：
- STORY: 剧情/对话/过场动画
- COMBAT: BOSS战/打怪
- EXPLORE: 跑图/收集/闲聊

返回 JSON 格式:
```json
{
  "timeline": [
    {
      "time": "MM:SS",
      "timestamp": 123.4,
      "title": "事件标题",
      "type": "STORY|COMBAT|EXPLORE",
      "description": "详细描述"
    }
  ]
}
```

内容:
""" + context[:3000]

        messages = [{"role": "user", "content": prompt}]

        result = await self.intel.chat_completion(messages)
        if not result:
            return []

        try:
            content = result.output["choices"][0]["message"]["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            return data.get("timeline", [])

        except Exception as e:
            logger.error(f"Timeline parsing error: {e}")
            return []


# Singleton
_analysis_service = None


def get_analysis_service() -> AnalysisService:
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service
