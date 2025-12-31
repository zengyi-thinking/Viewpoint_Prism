"""Analysis routes: conflicts, graph, timeline."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import Source, Evidence
from app.services.analysis_service import get_analysis_service

router = APIRouter()


class AnalysisRequest(BaseModel):
    source_ids: List[str]


@router.post("/generate")
async def generate_analysis(request: AnalysisRequest):
    """Generate conflicts, graph, timeline."""
    try:
        # In real app, query sources and evidences from DB
        analysis_service = get_analysis_service()

        # Mock sources - in real app, query from DB
        sources = []
        evidences = []

        # Generate conflicts
        conflicts = await analysis_service.generate_conflicts(sources, evidences)

        # Generate graph
        graph = await analysis_service.generate_graph(evidences)

        # Generate timeline
        timeline = await analysis_service.generate_timeline(evidences)

        return {
            "conflicts": conflicts,
            "graph": graph,
            "timeline": timeline
        }

    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.get("/conflicts")
async def get_conflicts(source_ids: str):
    """Get conflicts for sources."""
    # Parse comma-separated IDs
    ids = source_ids.split(",") if source_ids else []
    return {"conflicts": []}


@router.get("/graph")
async def get_graph(source_ids: str):
    """Get knowledge graph."""
    return {"nodes": [], "links": []}


@router.get("/timeline")
async def get_timeline(source_id: str):
    """Get timeline for source."""
    return {"timeline": []}
