from ..video_handlers.yt_handler import get_yt_transcript, get_yt_video_info, timestamp_format
from .formatting import format_transcript_for_analysis
from ..agent import extract_claims
from ..transcript_chunking.chunking import chunk_transcript
from typing import List, Dict, Any, AsyncGenerator
import asyncio
import logging
from fastapi import HTTPException
import time

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def process_video_claims_stream(video_id: str, origin: str, language: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process a YouTube video, streaming progress and extracting claims.
    Yields status updates throughout the process.
    """
    if origin == "youtube":
        
        yield {
            "status": "progress", 
            "percentage": 5
        }
        
        
        transcript = get_yt_transcript(video_id)
        video_data = await get_yt_video_info(video_id, language)
        
        yield {
            "status": "progress", 
            "percentage": 10
        }
        
    else:
        raise ValueError(f"Unsupported origin: {origin}")

    if isinstance(transcript, dict) and transcript.get("code") == 403:
        logging.error(f"Video is private: {video_id}")
        yield {
            "status": "error",
            "message": "The video is private and cannot be processed."
        }
        return
    
    if not video_data or not transcript:
        logging.warning(f"No video data or transcript found for video_id: {video_id}")
        raise HTTPException(status_code=404, detail=f"Failed to retrieve video data or transcript for video ID: {video_id}")

    yield {
        "status": "progress", 
        "percentage": 15
    }
    
    transcript_chunks = chunk_transcript(transcript)
    num_chunks = len(transcript_chunks)
    logging.info(f"Split transcript into {num_chunks} chunks for video_id: {video_id}")

    yield {
        "status": "progress", 
        "percentage": 20
    }

    all_claims_from_chunks = []
    total_input_tokens = 0
    total_output_tokens = 0
    
    async def _process_chunk(index: int, chunk: List[Dict[str, Any]]):
        """Processes a single chunk asynchronously."""
        logging.info(f"Starting processing for chunk {index + 1}...")
        start_time = time.time()

        formatted_chunk = format_transcript_for_analysis(chunk)
        # Directly await the async extract_claims function
        claims, input_tokens, output_tokens = await extract_claims(formatted_chunk, video_data, language)

        #TODO: Fix timestamp formatting
        # Format timestamps for consistency
        for claim in claims:
            if 'timestamp' in claim and claim['timestamp']:
                claim['timestamp'] = timestamp_format(claim['timestamp'])
            else:
                logging.warning(f"Claim missing timestamp: {claim.get('claim', 'Unknown claim')[:50]}...")
                #logging.info(f"claim: {claim}")
                claim['timestamp'] = "00:00"  # Default timestamp
            #logging.info(f"claim: {claim}")

        processing_time_seconds = round(time.time() - start_time, 2)
        logging.info(f"Finished processing for chunk {index + 1} in {processing_time_seconds}s. Found {len(claims)} claims.")
        return claims, input_tokens, output_tokens, (index + 1)

    # Create and run tasks concurrently using asyncio
    tasks = [_process_chunk(i, chunk) for i, chunk in enumerate(transcript_chunks)]
    
    chunks_processed = 0
    for future in asyncio.as_completed(tasks):
        chunk_claims, input_tokens, output_tokens, chunk_index = await future
        all_claims_from_chunks.append((chunk_index, chunk_claims))
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        chunks_processed += 1
        
        # Calculate percentage from 20% to 100% based on chunk progress
        chunk_progress = (chunks_processed / num_chunks) * 75
        percentage = round(25 + chunk_progress)
        
        yield {
            "status": "progress",
            "percentage": percentage
        }

    all_claims_from_chunks.sort(key=lambda x: x[0])
    final_claims = [claim for _, sublist in all_claims_from_chunks for claim in sublist]

    for i, claim in enumerate(final_claims):
        claim['id'] = i

    logging.info(f"Extracted {len(final_claims)} claims in total for video_id: {video_id}.")
    logging.info(f"Total input tokens used for video_id {video_id}: {total_input_tokens}")
    logging.info(f"Total output tokens generated for video_id {video_id}: {total_output_tokens}")
    
    yield {
        "status": "complete",
        "data": {
            "claims": final_claims,
            "video_data": video_data,
            "videoID": video_id,
            "claim_count": len(final_claims)
        },
        "token_summary": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        },
        "language": language
    }


async def process_video_claims(video_id: str, origin: str, language: str) -> tuple[List[Dict[str, Any]], Dict[str, Any], int, int, str]:
    """
    Processes a video to extract claims, waits for the full result.
    This function now wraps the streaming version to maintain the original blocking behavior for the existing endpoint.
    """
    final_result = None
    async for update in process_video_claims_stream(video_id, origin, language):
        if update["status"] == "complete":
            final_result = update
            break
    
    if not final_result:
        raise HTTPException(status_code=500, detail="Failed to process video claims.")

    data = final_result["data"]
    tokens = final_result["token_summary"]
    
    return data["claims"], data["video_data"], tokens["input_tokens"], tokens["output_tokens"], final_result["language"]
