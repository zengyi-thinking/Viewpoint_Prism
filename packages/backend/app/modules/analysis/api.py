"""
Analysis API routes.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.modules.analysis import (
    AnalysisService,
    get_analysis_service,
    AnalysisResponse,
    SearchResult,
    SearchResponse,
    GenerateRequest,
    OnePagerRequest,
    OnePagerResponse,
)
from app.modules.analysis.schemas import (
    EntityListResponse,
    EntityDetailResponse,
    EntityMentionListResponse,
    ExtractEntitiesResponse,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_analysis_svc() -> AnalysisService:
    """Dependency to get AnalysisService."""
    return get_analysis_service()


@router.post("/generate", response_model=AnalysisResponse)
async def generate_analysis(
    request: GenerateRequest,
    service: AnalysisService = Depends(get_analysis_svc),
):
    """Generate AI analysis for video sources."""
    if not request.source_ids:
        raise HTTPException(status_code=400, detail="No source IDs provided")

    available_source_ids = []
    for sid in request.source_ids:
        result = service.vector_store.get_source_documents(sid)
        if result:
            available_source_ids.append(sid)

    if not available_source_ids:
        return AnalysisResponse(conflicts=[], graph={"nodes": [], "links": []}, timeline=[])

    try:
        analysis = await service.generate_analysis(
            source_ids=available_source_ids,
            use_cache=request.use_cache,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    return AnalysisResponse(
        conflicts=analysis["conflicts"],
        graph=analysis["graph"],
        timeline=analysis["timeline"],
    )


@router.post("/one-pager", response_model=OnePagerResponse)
async def generate_one_pager(
    request: OnePagerRequest,
    service: AnalysisService = Depends(get_analysis_svc),
):
    """Generate one-pager summary for selected sources."""
    if not request.source_ids:
        raise HTTPException(status_code=400, detail="No source IDs provided")

    result = await service.generate_one_pager(
        source_ids=request.source_ids,
        use_cache=request.use_cache,
    )

    return OnePagerResponse(**result)


@router.get("/search", response_model=SearchResponse)
async def search_knowledge(
    q: str = Query(..., description="Search query"),
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs"),
    limit: int = Query(10, ge=1, le=50),
    service: AnalysisService = Depends(get_analysis_svc),
):
    """Search the video knowledge base."""
    source_id_list = None
    if source_ids:
        source_id_list = [s.strip() for s in source_ids.split(",") if s.strip()]

    results = service.vector_store.search(
        query=q,
        source_ids=source_id_list,
        n_results=limit,
    )

    return SearchResponse(
        query=q,
        results=[
            SearchResult(
                text=r.get("text", ""),
                source_id=r.get("metadata", {}).get("source_id", ""),
                type=r.get("metadata", {}).get("type", "text"),
                start=r.get("metadata", {}).get("start", 0),
                end=r.get("metadata", {}).get("end", 0),
                video_title=r.get("metadata", {}).get("video_title", ""),
                distance=r.get("distance", 0.0),
            )
            for r in results
        ],
        total=len(results),
    )


# ===== 实体管理 API =====

@router.get("/entities", response_model=EntityListResponse)
async def search_entities(
    query: str = Query(..., description="搜索关键词"),
    type: Optional[str] = Query(None, description="实体类型"),
    limit: int = Query(20, ge=1, le=100),
):
    """搜索实体"""
    from app.core.database import async_session
    from app.modules.analysis.dao import EntityDAO

    async with async_session() as session:
        entity_dao = EntityDAO(session)
        entities = await entity_dao.find_similar(query, limit=limit)

        return EntityListResponse(entities=[
            {
                "id": e.id,
                "name": e.name,
                "type": e.type,
                "description": e.description,
                "mention_count": e.mention_count,
                "first_seen_at": e.first_seen_at.isoformat(),
                "last_seen_at": e.last_seen_at.isoformat()
            }
            for e in entities
        ])


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_details(entity_id: str):
    """获取实体详情"""
    from app.core.database import async_session
    from app.modules.analysis.dao import EntityDAO, EntityMentionDAO

    async with async_session() as session:
        entity_dao = EntityDAO(session)
        mention_dao = EntityMentionDAO(session)

        entity = await entity_dao.get(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        mentions = await mention_dao.get_entity_mentions(entity_id)

        return EntityDetailResponse(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            description=entity.description,
            mention_count=entity.mention_count,
            mentions=[
                {
                    "id": m.id,
                    "source_id": m.source_id,
                    "timestamp": m.timestamp,
                    "context": m.context
                }
                for m in mentions[:50]
            ]
        )


@router.get("/entities/{entity_id}/mentions", response_model=EntityMentionListResponse)
async def get_entity_mentions(
    entity_id: str,
    source_id: Optional[str] = None
):
    """获取实体提及列表"""
    from app.core.database import async_session
    from app.modules.analysis.dao import EntityMentionDAO

    async with async_session() as session:
        mention_dao = EntityMentionDAO(session)
        mentions = await mention_dao.get_entity_mentions(entity_id, source_id)

        return EntityMentionListResponse(
            entity_id=entity_id,
            mentions=[
                {
                    "id": m.id,
                    "source_id": m.source_id,
                    "timestamp": m.timestamp,
                    "context": m.context,
                    "confidence": m.confidence
                }
                for m in mentions
            ]
        )


@router.post("/sources/{source_id}/extract-entities", response_model=ExtractEntitiesResponse)
async def extract_entities_from_source(source_id: str):
    """从视频源中抽取实体"""
    from app.modules.analysis.service import get_analysis_service

    analysis_service = get_analysis_service()
    entities = await analysis_service.extract_entities_from_source(source_id)

    return ExtractEntitiesResponse(
        source_id=source_id,
        entity_count=len(entities),
        entities=[
            {
                "id": e.id,
                "name": e.name,
                "type": e.type,
                "description": e.description,
                "mention_count": e.mention_count,
                "first_seen_at": e.first_seen_at.isoformat(),
                "last_seen_at": e.last_seen_at.isoformat()
            }
            for e in entities
        ]
    )
