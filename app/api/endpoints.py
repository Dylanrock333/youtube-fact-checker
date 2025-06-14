from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
import json
from .claim_analysis.claim_extraction import process_video_claims, process_video_claims_stream
from .agent import execute_web_search
from app.config import get_settings
from app.schemas import VideoExecutionRequest, DeepSearchRequest
import logging
from app.utility import limiter, limitter_logger
import time


router = APIRouter()


# Health check endpoint
@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "healthy"}

# Add this function to get the analytics DB from app state
def get_analytics_db(request: Request):
    return request.app.state.analytics_db

# Execute endpoint
@router.post("/execute", tags=["Processing"])
@limiter.limit("25/hour")
async def execute(
    payload: VideoExecutionRequest, 
    request: Request,
    analytics_db = Depends(get_analytics_db)
):
    """
    Process a video and extract controversial claims.
    """
    
    limitter_logger(request, "execute")
    start_time = time.time()
    video_data_from_processing = {} # Initialize to ensure it's always defined for logging

    try:
        # Await the async process_video_claims function
        claims, video_data_from_processing, input_tokens, output_tokens, language = await process_video_claims(payload.videoID, payload.origin, payload.selectedLanguage)
        
        # Calculate processing time
        processing_time_seconds = round(time.time() - start_time, 2)
        processing_time_ms = int(processing_time_seconds * 1000)  # Keep ms for analytics DB
        
        
        # Log successful request
        analytics_db.log_video_processing(
            video_id=payload.videoID,
            origin=payload.origin,
            video_title=video_data_from_processing.get("title", "Unknown Title"), 
            status="success",
            claim_count=len(claims),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            processing_time_ms=processing_time_ms
        )
        
        # Log endpoint processing time
        logging.info(f"Execute endpoint for video {payload.videoID} completed in {processing_time_seconds}s")
        
        return {
            "claims": claims, 
            "video_data": video_data_from_processing, 
            "videoID": payload.videoID, 
            "claim_count": len(claims)
        }
    except Exception as e:
        # Calculate processing time even for errors
        processing_time_seconds = round(time.time() - start_time, 2)
        processing_time_ms = int(processing_time_seconds * 1000)  # Keep ms for analytics DB
        
        # Log failed request
        analytics_db.log_video_processing(
            video_id=payload.videoID,
            origin=payload.origin,
            video_title=video_data_from_processing.get("title", "Unknown Title (Error)"), 
            status="error",
            processing_time_ms=processing_time_ms,
            error_message=str(e)
        )
        
        logging.error(f"Execute endpoint for video {payload.videoID} failed after {processing_time_seconds}s: {e}")
        raise HTTPException(status_code=500, detail="Error processing video")


# SSE endpoint for real-time progress
@router.post("/execute/stream", tags=["Processing"])
@limiter.limit("25/hour")
async def execute_stream(
    payload: VideoExecutionRequest, 
    request: Request,
    analytics_db = Depends(get_analytics_db)
):
    """
    Process a video and stream progress and results via SSE.
    """
    limitter_logger(request, "execute_stream")
    start_time = time.time()
    
    async def event_generator():
        video_data_from_processing = {}
        try:
            async for update in process_video_claims_stream(payload.videoID, payload.origin, payload.selectedLanguage):
                yield f"data: {json.dumps(update)}\n\n"
                
                if update.get("status") == "complete":
                    # Log analytics at the end of successful processing
                    data = update["data"]
                    token_summary = update["token_summary"]
                    video_data_from_processing = data["video_data"]
                    
                    processing_time_seconds = round(time.time() - start_time, 2)
                    processing_time_ms = int(processing_time_seconds * 1000)

                    analytics_db.log_video_processing(
                        video_id=payload.videoID,
                        origin=payload.origin,
                        video_title=video_data_from_processing.get("title", "Unknown Title"),
                        status="success",
                        claim_count=data["claim_count"],
                        input_tokens=token_summary["input_tokens"],
                        output_tokens=token_summary["output_tokens"],
                        processing_time_ms=processing_time_ms
                    )
                    logging.info(f"Execute stream for video {payload.videoID} completed in {processing_time_seconds}s")

        except Exception as e:
            logging.error(f"Error during video processing stream for {payload.videoID}: {e}", exc_info=True)
            processing_time_seconds = round(time.time() - start_time, 2)
            processing_time_ms = int(processing_time_seconds * 1000)
            
            # Log the failure
            analytics_db.log_video_processing(
                video_id=payload.videoID,
                origin=payload.origin,
                video_title=video_data_from_processing.get("title", "Unknown Title (Error)"),
                status="error",
                processing_time_ms=processing_time_ms,
                error_message=str(e)
            )
            
            # Send an error event to the client
            error_payload = {"status": "error", "message": f"An error occurred: {e}"}
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Deepsearch endpoint   
@router.post("/deepsearch", tags=["Search"])
@limiter.limit("20/hour")
async def deepsearch(payload: DeepSearchRequest, request: Request):
    """
    Perform a deep search based on the provided search prompt and additional context.
    Uses Perplexity API to verify claims from videos.
    """
    
    limitter_logger(request, "deepsearch")
    start_time = time.time()
    
    # Create a video_data dictionary from the individual fields
    video_data = {
        "title": payload.videoTitle,
        "published_at": payload.videoPublishedAt,
        "tags": payload.videoTags
    }
    
    settings = get_settings()
    try:
        response = await execute_web_search(
            perplexity_api_key=settings.perplexity_api_key,
            claim_text=payload.claimText,
            context=payload.context,
            video_data=video_data,
            query=payload.query,
            language=payload.selectedLanguage
        )
        
        # Calculate processing time
        processing_time_seconds = round(time.time() - start_time, 2)
        
        # Log successful deepsearch
        logging.info(f"Deepsearch endpoint completed in {processing_time_seconds}s for claim: {payload.claimText[:50]}...")
        
        # Log the response for debugging
       # logging.info("Response from execute_web_search:", response)
        
        return response

    except Exception as e:
        # Calculate processing time even for errors
        processing_time_seconds = round(time.time() - start_time, 2)
        
        # Log the error with timing
        logging.error(f"Deepsearch endpoint failed after {processing_time_seconds}s: {str(e)}")
        # Return a JSON response with the error message
        return {"error": str(e)}

@router.get("/analytics/recent", tags=["Analytics"])
async def get_recent_analytics(
    request: Request,
    limit: int = 1000,
    analytics_db = Depends(get_analytics_db)
):
    """Get recent video processing analytics."""
    return analytics_db.get_recent_videos(limit)


