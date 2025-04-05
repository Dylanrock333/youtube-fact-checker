

from ..video_handlers.yt_handler import get_yt_transcript
from .formatting import format_transcript_for_analysis
from ..agent import extract_claims
from ..transcript_chunking.chunking import chunk_transcript
from typing import List, Dict, Any

def process_video_claims(video_id: str, api_key: str, origin: str) -> tuple[List[Dict[str, Any]], str]:
    """Process a YouTube video and extract controversial or questionable factual claims."""
    
    if origin == "youtube":
        video_data, transcript = get_yt_transcript(video_id)
    else:
        raise ValueError(f"Unsupported origin: {origin}")
    
    if not video_data:
        return [], None
    
    # TODO: Keep in mind what format the the transcript is in depending on the origin
    transcript_chunks = chunk_transcript(transcript)
    print(f"Split transcript into {len(transcript_chunks)} chunks")
    
    # Process each chunk and collect claims
    all_claims = []
    claim_id = 0  # Initialize a counter for unique claim IDs
    
    
    #TODO: Will create for this
    #TODO: will make parallel function calls to the LLM one for each chunk to speed up the process
    for i, chunk in enumerate(transcript_chunks):
        print(f"Processing chunk {i+1}/{len(transcript_chunks)}...")
        
        # Format this chunk for the LLM
        formatted_chunk = format_transcript_for_analysis(chunk)
        
        # Extract claims from the formatted chunk
        chunk_claims = extract_claims(formatted_chunk, api_key, video_data)
        
        # Add unique ID to each claim
        for claim in chunk_claims:
            claim['id'] = claim_id
            claim_id += 1
        
        all_claims.extend(chunk_claims)
     
    return all_claims, video_data
