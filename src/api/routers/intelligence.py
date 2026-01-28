"""
Intelligence API endpoints.

Expose the AI agent capabilities via REST API.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.intelligence_agent import get_intelligence_briefing
from src.api.core.deps import CurrentUser


router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


class BriefingRequest(BaseModel):
    """Request for an intelligence briefing."""

    query: str


class BriefingResponse(BaseModel):
    """Intelligence briefing response."""

    query: str
    briefing: str


@router.post("/briefing", response_model=BriefingResponse)
async def create_briefing(
    request: BriefingRequest,
    current_user: CurrentUser,
) -> BriefingResponse:
    """
    Generate an AI-powered intelligence briefing.

    The agent will:
    1. Decide whether to search internal/external sources
    2. Retrieve relevant documents
    3. Extract and analyze facts
    4. Generate an executive briefing
    """
    try:
        briefing = await get_intelligence_briefing(request.query)
        return BriefingResponse(
            query=request.query,
            briefing=briefing,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
