from fastapi import APIRouter, HTTPException
from .claim_analysis.claim_extraction import process_video_claims
from .agent import execute_web_search
from app.config import get_settings
from app.schemas import VideoExecutionRequest, DeepSearchRequest

router = APIRouter()

# Health check endpoint
@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy"}

# Execute endpoint
@router.post("/execute", tags=["Processing"])
async def execute(request: VideoExecutionRequest):
    """
    Process a video and extract controversial claims.
    """
    try:
        settings = get_settings()
        claims, video_data = process_video_claims(request.videoID, settings.anthropic_api_key, request.origin)
        
        #return ExecuteResponse(claims=claims, video_data=video_data, videoID=request.videoID, claim_count=len(claims))   //TODO: Uncomment this when the schema is implemented(claims, videoData)
        return {"claims": claims, "video_data": video_data, "videoID": request.videoID, "claim_count": len(claims)}
    except Exception as e:
        print(f"Error processing video {request.videoID}: {e}")
        raise HTTPException(status_code=500, detail="Error processing video")


# Deepsearch endpoint   
@router.post("/deepsearch", tags=["Search"])
async def deepsearch(request: DeepSearchRequest):
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
    
    settings = get_settings()
    try:
        response = execute_web_search(
            perplexity_api_key=settings.perplexity_api_key,
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


