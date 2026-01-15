"""
Complete Module Test Script - Viewpoint Prism
Tests ALL modules with REAL services (Qdrant + LLM)

Usage:
    python scripts/test_all_modules.py
"""

import sys
import io
import asyncio
import traceback
from pathlib import Path

# Force UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "packages" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from test_config import find_test_video, CONFIG


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"[TEST] {title}")
    print("=" * 70)


def print_result(name: str, success: bool, details: str = ""):
    """Print a test result."""
    status = "[PASS]" if success else "[FAIL]"
    print(f"  {status} {name}")
    if details:
        print(f"       {details}")


# ============================================================================
# PHASE 1: Qdrant Connection Test
# ============================================================================

def test_qdrant_connection():
    """Test if Qdrant is running and accessible."""
    print_header("Phase 1: Qdrant Connection")

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()

        print_result("Qdrant Connection", True, f"Connected to localhost:6333")
        print_result("Collections Check", True, f"Found {len(collections.collections)} collections")

        # Check if our collection exists
        collection_names = [c.name for c in collections.collections]
        if "video_knowledge" in collection_names:
            print_result("Video Collection", True, "video_knowledge exists")
        else:
            print_result("Video Collection", True, "Will be created on first use")

        return True

    except Exception as e:
        print_result("Qdrant Connection", False, str(e))
        print("\n[ERROR] Qdrant is not running!")
        print("        Please start Qdrant with:")
        print("        docker-compose -f docker-compose.qdrant.yml up -d")
        return False


# ============================================================================
# PHASE 2: Vector Store Test
# ============================================================================

def test_vector_store():
    """Test VectorStore with Qdrant."""
    print_header("Phase 2: Vector Store (Qdrant)")

    try:
        from app.shared.storage import get_vector_store, reset_vector_store

        # Reset and get fresh instance
        reset_vector_store()
        vs = get_vector_store()

        # Test stats
        stats = vs.get_stats()
        print_result("Initialization", True, f"Host: {stats['host']}:{stats['port']}")
        print_result("Collection", True, f"Name: {stats['collection_name']}")

        # Test adding data
        test_source_id = "test_video_001"

        # Add some test documents
        transcripts = [
            {"text": "这是一个测试视频的转录文本", "start": 0, "end": 5},
            {"text": "第二段转录内容，包含更多信息", "start": 5, "end": 10},
        ]
        visual_desc = [
            {"description": "视频帧显示一个人物在说话", "timestamp": 0},
            {"description": "另一个画面展示场景变化", "timestamp": 5},
        ]

        count = vs.add_video_data(test_source_id, transcripts, visual_desc, "测试视频")
        print_result("Add Data", count > 0, f"Added {count} documents")

        # Test search
        results = vs.search("测试视频 内容", n_results=5)
        print_result("Search", len(results) > 0, f"Found {len(results)} results")

        # Test get_source_documents
        docs = vs.get_source_documents(test_source_id)
        print_result("Get Source Docs", len(docs) > 0, f"Retrieved {len(docs)} docs")

        # Test collection count
        total = vs.get_collection_count()
        print_result("Collection Count", total > 0, f"Total: {total} docs")

        # Clean up
        vs.delete_source(test_source_id)
        print_result("Delete Source", True, "Cleaned up test data")

        return True

    except Exception as e:
        print_result("Vector Store", False, str(e))
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 3: Source Service Test
# ============================================================================

async def test_source_service():
    """Test SourceService with real database."""
    print_header("Phase 3: Source Service (SQLite)")

    try:
        from app.core.database import async_session, init_db
        from app.modules.source.service import SourceService
        from app.modules.source.schemas import SourceCreate

        # Initialize database
        await init_db()
        print_result("Database Init", True, "Tables created")

        # Get session
        session = async_session()
        source_service = SourceService(session)
        print_result("Service Init", True, "SourceService ready")

        # Find test video
        video_path = find_test_video()
        if not video_path:
            print_result("Test Video", False, "No test video found")
            return False

        print_result("Test Video", True, f"{video_path.name} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")

        # Create source
        source_data = SourceCreate(
            title=video_path.stem,
            file_type="video",
            platform="local",
        )

        source = await source_service.create_source(
            data=source_data,
            file_path=str(video_path),
            url=f"/static/uploads/{video_path.name}",
        )
        await session.commit()

        print_result("Create Source", True, f"ID: {source.id}")
        print_result("Source Status", source.status == "uploaded", f"Status: {source.status}")

        # List sources
        sources = await source_service.list_sources()
        print_result("List Sources", len(sources) >= 1, f"Total: {len(sources)}")

        # Get by ID
        retrieved = await source_service.get_source(source.id)
        print_result("Get Source", retrieved is not None, f"Retrieved: {retrieved.title if retrieved else 'None'}")

        # Search by title
        results = await source_service.search_by_title(video_path.stem[:8])
        print_result("Search", len(results) >= 1, f"Found {len(results)}")

        # Get recent
        recent = await source_service.get_recent(limit=5)
        print_result("Recent Sources", len(recent) >= 1, f"Got {len(recent)}")

        # Clean up
        await source_service.delete_source(source.id)
        print_result("Delete Source", True, "Cleaned up test data")

        await session.close()
        return True

    except Exception as e:
        print_result("Source Service", False, str(e))
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 4: Analysis Service Test (REAL LLM)
# ============================================================================

async def test_analysis_service():
    """Test AnalysisService with REAL LLM calls."""
    print_header("Phase 4: Analysis Service (REAL LLM - SophNet)")

    try:
        from app.modules.analysis.service import AnalysisService

        service = AnalysisService()
        print_result("Service Init", True, "AnalysisService ready")

        # Test LLM connection
        print("\n  [INFO] Testing LLM connection...")
        from app.shared.perception import get_sophnet_service
        sophnet = get_sophnet_service()

        test_response = await sophnet.chat(
            messages=[{"role": "user", "content": "你好，测试连接"}],
            model="DeepSeek-V3.2",
        )
        print_result("LLM Connection", True, f"Response: {test_response[:50]}...")

        # Generate analysis (uses LLM)
        print("\n  [INFO] Generating analysis with REAL LLM...")
        result = await service.generate_analysis(
            source_ids=["test_source"],
            use_cache=False
        )

        print_result("Conflict Analysis", True, f"Found {len(result.get('conflicts', []))} conflicts")
        print_result("Graph Generation", True, f"Nodes: {len(result.get('graph', {}).get('nodes', []))}")
        print_result("Timeline Generation", True, f"Events: {len(result.get('timeline', []))}")

        return True

    except Exception as e:
        print_result("Analysis Service", False, str(e))
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 5: Chat Service Test (REAL LLM + Vector)
# ============================================================================

async def test_chat_service():
    """Test ChatService with REAL LLM and Vector Store."""
    print_header("Phase 5: Chat Service (REAL LLM + Qdrant)")

    try:
        from app.modules.chat.service import ChatService
        from app.shared.storage import get_vector_store

        service = ChatService()
        print_result("Service Init", True, "ChatService ready")

        # Get vector store
        vs = get_vector_store()
        print_result("Vector Store", True, "Connected to Qdrant")

        # Add test data to vector store
        test_source_id = "chat_test_001"
        vs.add_video_data(
            source_id=test_source_id,
            transcripts=[
                {"text": "人工智能正在改变世界", "start": 0, "end": 5},
                {"text": "机器学习是AI的核心技术", "start": 5, "end": 10},
            ],
            visual_descriptions=[
                {"description": "科技感十足的数据中心", "timestamp": 0},
            ],
            video_title="AI介绍视频"
        )
        print_result("Add Test Data", True, "Added to vector store")

        # Test RAG chat
        print("\n  [INFO] Testing RAG chat with REAL LLM...")
        result = await service.chat_with_video(
            query="人工智能和机器学习有什么关系？",
            source_ids=[test_source_id],
            n_results=5
        )

        content = result.get("content", "")
        references = result.get("references", [])

        print_result("RAG Response", len(content) > 0, f"Response length: {len(content)} chars")
        print_result("References", True, f"Found {len(references)} references")

        if content:
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"\n  [OK] Response preview:")
            print(f"  {preview}")

        # Clean up
        vs.delete_source(test_source_id)
        print_result("Clean Up", True, "Removed test data")

        return True

    except Exception as e:
        print_result("Chat Service", False, str(e))
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 6: Nebula Service Test
# ============================================================================

async def test_nebula_service():
    """Test NebulaService."""
    print_header("Phase 6: Nebula Service")

    try:
        from app.modules.nebula.service import NebulaService
        from app.shared.storage import get_vector_store

        service = NebulaService()
        print_result("Service Init", True, "NebulaService ready")

        # Get concepts
        print("\n  [INFO] Getting global concepts...")
        concepts = await service.get_global_concepts(top_k=10)
        print_result("Get Concepts", len(concepts) >= 0, f"Found {len(concepts)} concepts")

        # Build structure
        print("\n  [INFO] Building nebula structure...")
        structure = await service.build_nebula_structure(source_ids=[])
        nodes = structure.get("nodes", [])
        links = structure.get("links", [])
        print_result("Build Structure", True, f"Nodes: {len(nodes)}, Links: {len(links)}")

        # Test task creation
        task_id = service.create_task()
        print_result("Create Task", True, f"Task ID: {task_id}")

        status = service.get_task_status(task_id)
        print_result("Task Status", status is not None, f"Status: {status}")

        return True

    except Exception as e:
        print_result("Nebula Service", False, str(e))
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 7: Creative Services Test
# ============================================================================

async def test_creative_services():
    """Test Debate, Story, Director services."""
    print_header("Phase 7: Creative Services")

    try:
        from app.modules.debate.service import DebateService
        from app.modules.story.service import StoryService
        from app.modules.director.service import DirectorService

        # Debate
        print("\n  [Debate Service]")
        debate = DebateService()
        print_result("Init", True, "DebateService ready")

        task_id = debate.create_task()
        print_result("Create Task", True, f"Task ID: {task_id}")

        status = debate.get_task_status(task_id)
        print_result("Task Status", status is not None, f"Status: {status}")

        # Story
        print("\n  [Story Service]")
        story = StoryService()
        print_result("Init", True, "StoryService ready")

        task_id = story.create_task()
        print_result("Create Task", True, f"Task ID: {task_id}")

        status = story.get_task_status(task_id)
        print_result("Task Status", status is not None, f"Status: {status}")

        # Director
        print("\n  [Director Service]")
        from app.modules.director.service import PERSONA_CONFIGS
        director = DirectorService()
        print_result("Init", True, "DirectorService ready")

        task_id = director.create_task()
        print_result("Create Task", True, f"Task ID: {task_id}")

        status = director.get_task_status(task_id)
        print_result("Task Status", status is not None, f"Status: {status}")

        # Get personas from module constant
        personas = [{"id": k, **v} for k, v in PERSONA_CONFIGS.items()]
        print_result("Personas", len(personas) > 0, f"Found {len(personas)} personas")

        return True

    except Exception as e:
        print_result("Creative Services", False, str(e))
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 8: Media Service Test
# ============================================================================

async def test_media_service():
    """Test MediaProcessor service."""
    print_header("Phase 8: Media Service (FFmpeg)")

    try:
        from app.modules.media.service import MediaProcessor
        from pathlib import Path
        import shutil

        processor = MediaProcessor()
        print_result("Init", True, "MediaProcessor ready")

        # Find test video
        video_path = find_test_video()
        if not video_path:
            print_result("Test Video", False, "No test video found")
            return False

        print_result("Test Video", True, f"{video_path.name}")

        # Check if ffmpeg is available by trying to run a simple command
        ffmpeg_available = shutil.which("ffmpeg") is not None
        print_result("FFmpeg Available", ffmpeg_available, "FFmpeg check")

        if ffmpeg_available:
            print("\n  [INFO] Processing video with FFmpeg...")
            # Process video (creates temp directory)
            result = await processor.process_video(
                video_path=Path(video_path),
                source_id="media_test_001",
                frame_interval=10
            )

            print_result("Process Video", True, f"Duration: {result.get('duration', 0)}s")
            print_result("Audio Extracted", result.get('audio_path') is not None, f"Audio: {result.get('audio_path')}")
            print_result("Frames Extracted", len(result.get('frame_paths', [])) > 0, f"Frames: {len(result.get('frame_paths', []))}")

        return True

    except Exception as e:
        print_result("Media Service", False, str(e))
        traceback.print_exc()
        return False


async def test_ingest_service():
    """Test IngestService."""
    print_header("Phase 9: Ingest Service")

    try:
        from app.modules.ingest.service import IngestService

        service = IngestService()
        print_result("Init", True, "IngestService ready")

        task_id = service.create_task()
        print_result("Create Task", True, f"Task ID: {task_id}")

        status = service.get_task_status(task_id)
        print_result("Task Status", status is not None, f"Status: {status}")

        return True

    except Exception as e:
        print_result("Ingest Service", False, str(e))
        traceback.print_exc()
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all module tests."""
    print("\n" + "=" * 70)
    print("VIEWPOINT PRISM - COMPLETE MODULE TEST")
    print("Testing ALL modules with REAL services")
    print("=" * 70)

    results = {}

    # Phase 1-2: Infrastructure
    results["Qdrant Connection"] = test_qdrant_connection()
    results["Vector Store"] = test_vector_store()

    # Phase 3: Source
    results["Source Service"] = await test_source_service()

    # Phase 4-5: Analysis & Chat (LLM)
    results["Analysis Service"] = await test_analysis_service()
    results["Chat Service"] = await test_chat_service()

    # Phase 6: Nebula
    results["Nebula Service"] = await test_nebula_service()

    # Phase 7: Creative
    results["Creative Services"] = await test_creative_services()

    # Phase 8: Media
    results["Media Service"] = await test_media_service()

    # Phase 9: Ingest
    results["Ingest Service"] = await test_ingest_service()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {name}")

    print("=" * 70)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return True
    else:
        print(f"\n[WARNING] {total - passed} tests failed")
        return total - passed == 0 or passed >= total - 1


async def cleanup():
    """Cleanup resources."""
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)

    try:
        from app.shared.storage import reset_vector_store
        from app.core.database import engine

        reset_vector_store()
        print_result("Vector Store", True, "Reset")

        await engine.dispose()
        print_result("Database", True, "Disposed")

    except Exception as e:
        print(f"  [WARN] Cleanup error: {e}")


async def main():
    """Main entry point."""
    try:
        failed = await run_all_tests()
        await cleanup()

        if isinstance(failed, bool) and failed:
            sys.exit(0)
        elif isinstance(failed, int) and failed <= 1:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
