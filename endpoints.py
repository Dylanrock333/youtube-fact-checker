from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
import re
from youtube_data import extract_youtube_video_id
from claim_extraction import process_video_claims
import os
from agent import execute_web_search
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
    
    claims, video_data = process_video_claims(video_id, anthropic_api_key)
    
    # Implementation will be added later
    return {"claims": claims, "video_data": video_data, "video_id": video_id, "claim_count": len(claims)}

# Define request model for deepsearch endpoint
class SearchRequest(BaseModel):
    claimText: str = None
    context: str = None
    videoTitle: str = None
    videoPublishedAt: str = None
    videoTags: list = None
    query: str = None

# Deepsearch endpoint
@router.post("/deepsearch", tags=["Search"])
async def deepsearch(request: SearchRequest):
    """
    Perform a deep search based on the provided search prompt and additional context.
    Uses Perplexity API to verify claims from videos.
    """
    # Create a video_data dictionary from the individual fields
    video_data = {
        "title": request.videoTitle,
        "published_at": request.videoPublishedAt,
        "tags": request.videoTags
    }
    
    try:
        response = execute_web_search(
            perplexity_api_key=perplexity_api_key,
            claim_text=request.claimText,
            context=request.context,
            video_data=video_data,
            query=request.query
        )
        
        # Log the response for debugging
       # print("Response from execute_web_search:", response)
        
        return response

    except Exception as e:
        # Log the error
        print("Error in deepsearch:", str(e))
        # Return a JSON response with the error message
        return {"error": str(e)}


