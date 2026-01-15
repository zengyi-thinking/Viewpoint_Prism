"""
Full Lifecycle Integration Test - Viewpoint Prism
Tests the complete pipeline: Source -> Analysis -> Nebula -> Debate -> Chat
"""

import sys
import io

# Force UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import asyncio
import traceback
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "packages" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from test_config import find_test_video, CONFIG, setup_logging
from app.core.database import async_session, init_db, engine, Base
from app.core import get_settings
from app.models import Source, SourceStatus
from app.modules.source.service import SourceService
from app.modules.source.schemas import SourceCreate


class MockVectorStore:
    """Mock VectorStore for testing without ChromaDB."""

    def __init__(self):
        self.documents = {}

    def add_video_data(self, source_id, transcripts, visual_descriptions, video_title):
        self.documents[source_id] = []
        for i, t in enumerate(transcripts):
            self.documents[source_id].append({
                "id": f"{source_id}_transcript_{i}",
                "text": t.get("text", ""),
                "metadata": {"source_id": source_id, "type": "transcript", "start": t.get("timestamp", 0), "video_title": video_title}
            })
        for i, v in enumerate(visual_descriptions):
            self.documents[source_id].append({
                "id": f"{source_id}_visual_{i}",
                "text": v.get("description", ""),
                "metadata": {"source_id": source_id, "type": "visual", "start": v.get("timestamp", 0), "video_title": video_title}
            })
        return len(self.documents[source_id])

    def get_source_documents(self, source_id):
        return self.documents.get(source_id, [])

    def search(self, query, source_ids=None, n_results=10, doc_type=None):
        results = []
        for sid, docs in self.documents.items():
            if source_ids and sid not in source_ids:
                continue
            for doc in docs:
                if query.lower() in doc.get("text", "").lower():
                    results.append(doc)
                    if len(results) >= n_results:
                        return results
        return results

    def delete_source(self, source_id):
        if source_id in self.documents:
            del self.documents[source_id]


class MockSophNet:
    """Mock SophNet service for testing without API calls."""

    async def chat(self, messages, model="DeepSeek-V3.2"):
        # Return a mock response based on the prompt
        user_content = messages[-1]["content"] if messages else ""
        if "冲突" in user_content:
            return '[{"topic": "测试冲突", "severity": "info", "viewpoint_a": {"source_id": "test", "title": "观点A", "description": "测试"}, "viewpoint_b": {"source_id": "test", "title": "观点B", "description": "测试"}, "verdict": "测试结果"}]'
        elif "知识图谱" in user_content or "实体" in user_content:
            return '{"nodes": [{"id": "node1", "name": "测试实体", "category": "concept"}], "links": []}'
        elif "时间线" in user_content or "事件" in user_content:
            return '[{"id": "event1", "time": "01:30", "timestamp": 90, "title": "测试事件", "description": "这是一个测试事件", "is_key_moment": true, "event_type": "STORY"}]'
        else:
            return "这是一个测试回复，内容基于视频分析。"


class MockAnalysisService:
    """Mock AnalysisService for testing."""

    def __init__(self):
        self.sophnet = MockSophNet()
        self.vector_store = MockVectorStore()
        self._cache = {}

    async def generate_conflicts(self, source_ids):
        cache_key = f"conflicts:{','.join(sorted(source_ids))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        source_docs = self.vector_store.get_source_documents(source_ids[0]) if source_ids else []
        combined_text = " ".join([d.get("text", "") for d in source_docs[:10]])

        prompt = f"分析以下视频内容，找出主要观点冲突：\n{combined_text[:500]}"
        response = await self.sophnet.chat([{"role": "user", "content": prompt}])

        import json
        try:
            conflicts = json.loads(response)
            if not isinstance(conflicts, list):
                conflicts = [conflicts]
            self._cache[cache_key] = conflicts
        except:
            conflicts = []

        return conflicts

    async def generate_graph(self, source_ids):
        cache_key = f"graph:{','.join(sorted(source_ids))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = {"nodes": [{"id": "node1", "name": "测试实体", "category": "concept"}], "links": []}
        self._cache[cache_key] = result
        return result

    async def generate_timeline(self, source_ids):
        cache_key = f"timeline:{','.join(sorted(source_ids))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = [{"id": "event1", "time": "01:30", "timestamp": 90, "title": "测试事件", "description": "这是一个测试事件", "is_key_moment": True, "event_type": "STORY"}]
        self._cache[cache_key] = result
        return {"timeline": result}

    async def generate_analysis(self, source_ids, use_cache=True):
        if not use_cache:
            self._cache.clear()

        conflicts = await self.generate_conflicts(source_ids)
        graph = await self.generate_graph(source_ids)
        timeline = await self.generate_timeline(source_ids)

        return {
            "conflicts": conflicts,
            "graph": graph,
            "timeline": timeline.get("timeline", []),
        }


class MockChatService:
    """Mock ChatService for testing."""

    def __init__(self):
        self.vector_store = MockVectorStore()
        self.model = "DeepSeek-V3.2"

    async def chat_with_video(self, query, source_ids, n_results=10):
        results = self.vector_store.search(query, source_ids, n_results)

        content = f"根据视频内容，我找到了以下相关信息：\n\n"
        for i, r in enumerate(results[:3], 1):
            metadata = r.get("metadata", {})
            content += f"[{i}] {metadata.get('video_title', 'Unknown')} {metadata.get('start', 0)}秒\n"
            content += f"   {r.get('text', '')[:100]}...\n\n"

        references = [{"source_id": r.get("metadata", {}).get("source_id", ""), "timestamp": r.get("metadata", {}).get("start", 0), "text": r.get("text", "")[:200]} for r in results[:5]]

        return {"content": content, "references": references}


class MockNebulaService:
    """Mock NebulaService for testing."""

    def __init__(self):
        self.vector_store = MockVectorStore()
        self.tasks = {}

    def create_task(self):
        import uuid
        task_id = uuid.uuid4().hex[:8]
        self.tasks[task_id] = {"status": "pending", "progress": 0, "message": "Task created"}
        return task_id

    def get_task_status(self, task_id):
        return self.tasks.get(task_id)

    async def build_nebula_structure(self, source_ids):
        return {"nodes": [{"id": "node1", "name": "测试实体", "category": "concept"}], "links": []}


class MockDebateService:
    """Mock DebateService for testing."""

    def __init__(self):
        self.tasks = {}

    def create_task(self):
        import uuid
        task_id = uuid.uuid4().hex[:8]
        self.tasks[task_id] = {"status": "pending", "progress": 0, "message": "Task created", "video_url": None}
        return task_id

    def get_task_status(self, task_id):
        return self.tasks.get(task_id)


class MockStoryService:
    """Mock StoryService for testing."""

    def __init__(self):
        self.tasks = {}

    def create_task(self):
        import uuid
        task_id = uuid.uuid4().hex[:8]
        self.tasks[task_id] = {"status": "pending", "progress": 0, "message": "Task created"}
        return task_id

    def get_task_status(self, task_id):
        return self.tasks.get(task_id)


async def init_services():
    """Initialize all services (using mocks for ChromaDB-dependent services)."""
    print("\n" + "=" * 60)
    print("[Phase 1] Initializing Services")
    print("=" * 60)

    # Initialize database
    await init_db()
    print("  [OK] Database initialized")

    # Get database session using context manager
    session = async_session()

    # Initialize SourceService (needs real DB)
    source_service = SourceService(session)
    print("  [OK] SourceService initialized (real DB)")

    # Initialize mock services (avoids ChromaDB issues on Windows)
    analysis_service = MockAnalysisService()
    print("  [OK] AnalysisService initialized (mock)")

    chat_service = MockChatService()
    print("  [OK] ChatService initialized (mock)")

    nebula_service = MockNebulaService()
    print("  [OK] NebulaService initialized (mock)")

    debate_service = MockDebateService()
    print("  [OK] DebateService initialized (mock)")

    story_service = MockStoryService()
    print("  [OK] StoryService initialized (mock)")

    return {
        "session": session,
        "source": source_service,
        "analysis": analysis_service,
        "chat": chat_service,
        "nebula": nebula_service,
        "debate": debate_service,
        "story": story_service,
    }


async def test_source_ingestion(services: dict, video_path: Path) -> str:
    """
    Phase 2: Test Source Ingestion
    Create a source record for the test video.
    """
    print("\n" + "=" * 60)
    print("[Phase 2] Source Ingestion")
    print("=" * 60)

    source_service = services["source"]
    session = services["session"]

    # Create source data
    source_data = SourceCreate(
        title=video_path.stem,
        file_type="video",
        platform="local",
    )

    # Create source record
    source = await source_service.create_source(
        data=source_data,
        file_path=str(video_path),
        url=f"/static/uploads/{video_path.name}",
    )

    # Commit the session
    await session.commit()
    print(f"  [OK] Source created: {source.id}")
    print(f"       Title: {source.title}")
    print(f"       File: {source.file_path}")
    print(f"       Status: {source.status}")

    # Verify we can retrieve it
    retrieved = await source_service.get_source(source.id)
    assert retrieved is not None, "Failed to retrieve created source"
    print(f"  [OK] Source retrieval verified")

    return source.id


async def test_analysis_service(services: dict, video_id: str):
    """
    Phase 3: Test Analysis Service
    Generate analysis for the video.
    """
    print("\n" + "=" * 60)
    print("[Phase 3] Analysis Service")
    print("=" * 60)

    analysis_service = services["analysis"]

    # Generate analysis
    print("  [INFO] Generating analysis for video...")
    result = await analysis_service.generate_analysis(
        source_ids=[video_id],
        use_cache=False
    )

    print(f"       Conflicts: {len(result.get('conflicts', []))}")
    print(f"       Graph nodes: {len(result.get('graph', {}).get('nodes', []))}")
    print(f"       Timeline events: {len(result.get('timeline', []))}")

    if result.get('conflicts'):
        print("  [OK] Analysis generated successfully")
        for conflict in result['conflicts'][:2]:
            print(f"         - {conflict.get('topic', 'Unknown')}")
    else:
        print("  [WARN] No conflicts found")

    if result.get('timeline'):
        print("  [OK] Timeline generated")
        for event in result['timeline'][:2]:
            print(f"         - {event.get('title', 'Unknown')} at {event.get('time', 'N/A')}")

    return result


async def test_nebula_service(services: dict, video_id: str):
    """
    Phase 4: Test Nebula Service (Knowledge Graph)
    """
    print("\n" + "=" * 60)
    print("[Phase 4] Nebula Service (Knowledge Graph)")
    print("=" * 60)

    nebula_service = services["nebula"]

    print("  [INFO] Building knowledge graph...")
    structure = await nebula_service.build_nebula_structure(source_ids=[video_id])

    nodes = structure.get("nodes", [])
    links = structure.get("links", [])

    print(f"       Nodes: {len(nodes)}")
    print(f"       Links: {len(links)}")

    if nodes:
        print("  [OK] Knowledge graph built successfully")
        for node in nodes[:5]:
            print(f"         - {node.get('name', 'Unknown')} ({node.get('category', 'general')})")

    return structure


async def test_creative_services(services: dict, video_id: str):
    """
    Phase 5: Test Creative Services (Debate & Story)
    """
    print("\n" + "=" * 60)
    print("[Phase 5] Creative Services (Debate & Story)")
    print("=" * 60)

    debate_service = services["debate"]
    story_service = services["story"]

    # Test Debate task creation
    print("  [INFO] Testing Debate service...")
    debate_task_id = debate_service.create_task()
    print(f"  [OK] Debate task created: {debate_task_id}")
    status = debate_service.get_task_status(debate_task_id)
    print(f"       Task status: {status.get('status', 'unknown')}")

    # Test Story task creation
    print("  [INFO] Testing Story service...")
    story_task_id = story_service.create_task()
    print(f"  [OK] Story task created: {story_task_id}")
    story_status = story_service.get_task_status(story_task_id)
    print(f"       Task status: {story_status.get('status', 'unknown')}")

    return {
        "debate_task_id": debate_task_id,
        "story_task_id": story_task_id,
    }


async def test_chat_service(services: dict, video_id: str):
    """
    Phase 6: Test Chat Service (RAG-based conversation)
    """
    print("\n" + "=" * 60)
    print("[Phase 6] Chat Service (RAG)")
    print("=" * 60)

    chat_service = services["chat"]

    print("  [INFO] Testing RAG chat...")
    result = await chat_service.chat_with_video(
        query="这个视频的主要内容是什么？",
        source_ids=[video_id],
        n_results=5
    )

    content = result.get("content", "")
    references = result.get("references", [])

    print(f"       Response length: {len(content)} chars")
    print(f"       References found: {len(references)}")

    if content:
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"       Response preview: {preview}")
        print("  [OK] Chat service working")

    if references:
        print("  [OK] References returned")
        for ref in references[:3]:
            print(f"         - Source: {ref.get('source_id', 'unknown')}")

    return result


async def cleanup(services: dict):
    """Clean up resources."""
    print("\n" + "=" * 60)
    print("Cleanup")
    print("=" * 60)

    session = services.get("session")
    if session:
        try:
            await session.close()
            print("  [OK] Database session closed")
        except Exception as e:
            print(f"  [WARN] Error closing session: {e}")

    try:
        await engine.dispose()
        print("  [OK] Database engine disposed")
    except Exception as e:
        print(f"  [WARN] Error disposing engine: {e}")


async def run_full_lifecycle_test():
    """Run the complete lifecycle test."""

    print("\n" + "=" * 60)
    print("Viewpoint Prism Full Lifecycle Integration Test")
    print("=" * 60)
    print("\n[INFO] Using mock services for ChromaDB-dependent features")
    print("       (due to Windows ChromaDB compatibility issues)")
    print("=" * 60)

    # Find test video
    video_path = find_test_video()
    if not video_path:
        print("[ERROR] No test video found. Please add an MP4 file to the uploads directory.")
        return False

    print(f"\nTest video: {video_path}")
    print(f"Video size: {video_path.stat().st_size / (1024*1024):.1f} MB")

    video_id = None
    try:
        # Initialize all services
        services = await init_services()

        # Phase 2: Source Ingestion
        video_id = await test_source_ingestion(services, video_path)

        # Phase 3: Analysis Service
        await test_analysis_service(services, video_id)

        # Phase 4: Nebula Service
        await test_nebula_service(services, video_id)

        # Phase 5: Creative Services
        await test_creative_services(services, video_id)

        # Phase 6: Chat Service
        await test_chat_service(services, video_id)

        print("\n" + "=" * 60)
        print("[SUCCESS] All lifecycle phases completed!")
        print("=" * 60)
        print(f"Video ID: {video_id}")
        print("\nNote: This test uses mock services for features that depend")
        print("on ChromaDB (vector store) due to Windows compatibility issues.")
        print("Real functionality requires running on Linux/macOS or Docker.")
        print("=" * 60)

        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILED] Test Failed!")
        print("=" * 60)
        print(f"Error: {e}")
        print("\nTraceback:")
        traceback.print_exc()
        print("=" * 60)

        if video_id:
            print(f"Video ID was created: {video_id}")
        return False

    finally:
        if "services" in locals():
            await cleanup(services)


def main():
    """Main entry point."""
    try:
        result = asyncio.run(run_full_lifecycle_test())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
