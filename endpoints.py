from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
import re
from youtube_data import extract_youtube_video_id
from claim_extraction import process_video_claims
import os

router = APIRouter()

anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

# Health check endpoint
@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy"}

# Define request model for execute endpoint
class VideoRequest(BaseModel):
    url: str

# Execute endpoint
@router.post("/execute", tags=["Processing"])
async def execute(request: VideoRequest):
    """
    Process a YouTube video and extract controversial claims.
    This endpoint is a placeholder and doesn't contain implementation yet.
    """
    # Extract video ID if a full URL was provided
    video_id = extract_youtube_video_id(request.url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube video ID or URL")
    
    claims, video_title = process_video_claims(video_id, anthropic_api_key)
    
    # Implementation will be added later
    return {"claims": claims, "video_title": video_title, "video_id": video_id, "claim_count": len(claims)}
