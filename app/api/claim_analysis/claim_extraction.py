from ..video_handlers.yt_handler import get_yt_transcript
from .formatting import format_transcript_for_analysis
from ..agent import extract_claims
from ..transcript_chunking.chunking import chunk_transcript
from typing import List, Dict, Any
import concurrent.futures
import itertools
import logging # Import the logging module

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function to process a single chunk
def _process_chunk(chunk_data: tuple) -> List[Dict[str, Any]]:
    """Formats a chunk and extracts claims. Expects a tuple: (index, chunk, api_key, video_data)."""
    index, chunk, video_data = chunk_data 
    logging.info(f"Starting processing for chunk {index + 1}...") # Log start
    
    formatted_chunk = format_transcript_for_analysis(chunk)
    claims = extract_claims(formatted_chunk, video_data)
    
    logging.info(f"Finished processing for chunk {index + 1}. Found {len(claims)} claims.") # Log finish
    return claims

def process_video_claims(video_id: str, origin: str) -> tuple[List[Dict[str, Any]], str]:
    """Process a YouTube video and extract controversial or questionable factual claims."""
    
    if origin == "youtube":
        video_data, transcript = get_yt_transcript(video_id)
    else:
        raise ValueError(f"Unsupported origin: {origin}")
    
    if not video_data or not transcript: 
        logging.warning(f"No video data or transcript found for video_id: {video_id}") # Log warning
        return [], None 
    
    transcript_chunks = chunk_transcript(transcript)
    logging.info(f"Split transcript into {len(transcript_chunks)} chunks for video_id: {video_id}")
    
    all_claims_from_chunks = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        chunk_indices = range(len(transcript_chunks))
        video_data_list = itertools.repeat(video_data, len(transcript_chunks))
        
        # Combine arguments into tuples for each chunk: (index, chunk, api_key, video_data)
        map_args = zip(chunk_indices, transcript_chunks, video_data_list)
        
        print(map_args)
        
        # map executes _process_chunk for each item in map_args concurrently
        results = executor.map(_process_chunk, map_args)
        
        for chunk_claims in results:
            all_claims_from_chunks.append(chunk_claims)

    all_claims = [claim for sublist in all_claims_from_chunks for claim in sublist]

    for i, claim in enumerate(all_claims):
        claim['id'] = i
     
    logging.info(f"Extracted {len(all_claims)} claims in total for video_id: {video_id}.") # Log total
    return all_claims, video_data
