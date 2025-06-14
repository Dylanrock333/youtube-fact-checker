from ..video_handlers.yt_handler import get_yt_transcript, get_yt_video_info, timestamp_format
from .formatting import format_transcript_for_analysis
from ..agent import extract_claims
from ..transcript_chunking.chunking import chunk_transcript
from typing import List, Dict, Any
import concurrent.futures
import itertools
import logging # Import the logging module
from fastapi import HTTPException
import asyncio # Add asyncio import
import time

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function to process a single chunk
def _process_chunk(chunk_data: tuple) -> List[Dict[str, Any]]: # Make sync function
    """Formats a chunk and extracts claims. Expects a tuple: (index, chunk, api_key, video_data)."""
    index, chunk, video_data, language = chunk_data 
    logging.info(f"Starting processing for chunk {index + 1}...") # Log start
    start_time = time.time()
    
    formatted_chunk = format_transcript_for_analysis(chunk)
    # Handle async extract_claims within sync function
    claims, input_tokens, output_tokens = asyncio.run(extract_claims(formatted_chunk, video_data, language))
    
    #format timestamps for consistency
    for claim in claims:
        claim['timestamp'] = timestamp_format(claim['timestamp'])
    
    processing_time_seconds = round(time.time() - start_time, 2)
    logging.info(f"Finished processing for chunk {index + 1} in {processing_time_seconds}s. Found {len(claims)} claims.") 
    return claims, input_tokens, output_tokens, (index+1)

async def process_video_claims(video_id: str, origin: str, language: str) -> tuple[List[Dict[str, Any]], str]: # Keep async
    """Process a YouTube video and extract controversial or questionable factual claims."""
    
    #TODO: Have standard way of getting transcript
    if origin == "youtube":
        transcript = get_yt_transcript(video_id)
        video_data = await get_yt_video_info(video_id, language)
        #logging.info(f"video_data: {video_data}")
    else:
        raise ValueError(f"Unsupported origin: {origin}")
    
    if not video_data or not transcript: 
        logging.warning(f"No video data or transcript found for video_id: {video_id}") # Log warning
        raise HTTPException(status_code=500, detail=f"Failed to retrieve video data or transcript for video ID: {video_id}")
    
    transcript_chunks = chunk_transcript(transcript)
    logging.info(f"Split transcript into {len(transcript_chunks)} chunks for video_id: {video_id}")
    
    all_claims_from_chunks = []
    total_input_tokens = 0 # Initialize input token counter
    total_output_tokens = 0 # Initialize output token counter
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Prepare chunk data for processing
        chunk_data_list = [(i, chunk, video_data, language) for i, chunk in enumerate(transcript_chunks)]
        
        # Use executor.map to process chunks in parallel and preserve order
        results = executor.map(_process_chunk, chunk_data_list)
        
        # Unpack results and aggregate
        for chunk_claims, input_tokens, output_tokens, chunk_index in results:
            all_claims_from_chunks.extend(chunk_claims)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

    # Flatten the list of claims (already done by extend)
    # all_claims = [claim for sublist in all_claims_from_chunks for claim in sublist] # No longer needed if using extend

    for i, claim in enumerate(all_claims_from_chunks): # Iterate directly over the extended list
        claim['id'] = i

    logging.info(f"Extracted {len(all_claims_from_chunks)} claims in total for video_id: {video_id}.") # Log total claims
    # Log total token counts
    logging.info(f"Total input tokens used for video_id {video_id}: {total_input_tokens}")
    logging.info(f"Total output tokens generated for video_id {video_id}: {total_output_tokens}")
    return all_claims_from_chunks, video_data, total_input_tokens, total_output_tokens, language
