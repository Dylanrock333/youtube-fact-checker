

from youtube_data import get_transcript
from formatting import chunk_transcript, format_transcript_for_analysis
from agent import extract_claims
from typing import List, Dict, Any

def process_video_claims(video_id: str, api_key: str) -> tuple[List[Dict[str, Any]], str]:
    """Process a YouTube video and extract controversial or questionable factual claims."""
    # Get the transcript and title
    video_data, transcript = get_transcript(video_id)
    if not video_data:
        return [], None
    
    # Split transcript into manageable chunks (now returns list of lists)
    transcript_chunks = chunk_transcript(transcript)
    print(f"Split transcript into {len(transcript_chunks)} chunks")
    
    # Process each chunk and collect claims
    all_claims = []
    claim_id = 0  # Initialize a counter for unique claim IDs
    
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
