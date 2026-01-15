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
