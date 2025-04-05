import json
import os
from typing import List, Dict, Any


def format_transcript_for_analysis(transcript_chunk: List[Dict[str, Any]]) -> str:
    """Format a chunk of transcript entries with timestamps for LLM analysis."""
    formatted_text = ""
    current_time_bucket = -1
    current_text_bucket = ""
    
    for entry in transcript_chunk:
        time = int(entry['start'])
        time_bucket = time // 10  # Group by 10-second intervals
        
        if time_bucket != current_time_bucket:
            # If we have accumulated text, add it to the formatted output
            if current_text_bucket:
                minutes = (current_time_bucket * 10) // 60
                seconds = (current_time_bucket * 10) % 60
                formatted_text += f"[{minutes}:{seconds:02d}] {current_text_bucket.strip()}\n"
            
            # Start a new time bucket
            current_time_bucket = time_bucket
            current_text_bucket = entry['text'] + " "
        else:
            # Add to current bucket
            current_text_bucket += entry['text'] + " "
    
    # Add the last bucket if it exists
    if current_text_bucket:
        minutes = (current_time_bucket * 10) // 60
        seconds = (current_time_bucket * 10) % 60
        formatted_text += f"[{minutes}:{seconds:02d}] {current_text_bucket.strip()}\n"
        
    return formatted_text
    