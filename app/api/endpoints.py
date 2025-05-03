from fastapi import APIRouter, HTTPException, Request, Depends
from .claim_analysis.claim_extraction import process_video_claims
from .agent import execute_web_search
from app.config import get_settings
from app.schemas import VideoExecutionRequest, DeepSearchRequest
import logging
from app.utility import limiter, limitter_logger
from .video_handlers.yt_handler import get_video_browse_list
from datetime import datetime, timedelta

router = APIRouter()


# Health check endpoint
@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy"}

# Execute endpoint
@router.post("/execute", tags=["Processing"])
@limiter.limit("15/hour")
async def execute(payload: VideoExecutionRequest, request: Request):
    """
    Process a video and extract controversial claims.
    """
    limitter_logger(request, "execute")
    
    try:
        claims, video_data = process_video_claims(payload.videoID, payload.origin)
        
        
        #return ExecuteResponse(claims=claims, video_data=video_data, videoID=request.videoID, claim_count=len(claims))   //TODO: Uncomment this when the schema is implemented(claims, videoData)
        return {"claims": claims, "video_data": video_data, "videoID": payload.videoID, "claim_count": len(claims)}
    except Exception as e:
        logging.error(f"Error processing video {payload.videoID}: {e}")
        raise HTTPException(status_code=500, detail="Error processing video")


# Deepsearch endpoint   
@router.post("/deepsearch", tags=["Search"])
@limiter.limit("20/hour")
async def deepsearch(payload: DeepSearchRequest, request: Request):
    """
    Perform a deep search based on the provided search prompt and additional context.
    Uses Perplexity API to verify claims from videos.
    """
    
    limitter_logger(request, "deepsearch")
    
    # Create a video_data dictionary from the individual fields
    video_data = {
        "title": payload.videoTitle,
        "published_at": payload.videoPublishedAt,
        "tags": payload.videoTags
    }
    
    settings = get_settings()
    try:
        response = execute_web_search(
            perplexity_api_key=settings.perplexity_api_key,
            claim_text=payload.claimText,
            context=payload.context,
            video_data=video_data,
            query=payload.query
        )
        
        # Log the response for debugging
       # logging.info("Response from execute_web_search:", response)
        
        return response

    except Exception as e:
        # Log the error
        logging.error("Error in deepsearch:", str(e))
        # Return a JSON response with the error message
        return {"error": str(e)}


@router.get("/home_list", tags=["Browse"])
async def get_video_home_list(request: Request, days_before: int = 14):
    """
    Get a list of videos for the home page.
    
    Args:
        days_before: Number of days before current date to search from (default: 7)
    """
    
    # Format dates in ISO 8601 format as required by YouTube API
    current_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    past_date = (datetime.now() - timedelta(days=days_before)).strftime("%Y-%m-%dT%H:%M:%SZ")
     
    query = "controversial OR long form podcast OR informative OR news OR conspiracy OR conspiracy theory OR interview"
    max_results = 50
    published_after = past_date
    published_before = current_date
    video_category_id = "22"
    relevance_language = "en"
    
    try:
        video_list = get_video_browse_list(query, max_results, published_after, published_before, video_category_id, relevance_language)
        return video_list
    except Exception as e:
        logging.error(f"Error getting video home list: {e}")
        raise HTTPException(status_code=500, detail="Error getting video home list")

