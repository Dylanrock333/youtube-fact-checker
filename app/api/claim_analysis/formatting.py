import json
import os
from typing import List, Dict, Any


def format_transcript_for_analysis(transcript_chunk: List[Dict[str, Any]]) -> str:
    """Format a chunk of transcript entries with timestamps for LLM analysis."""
    formatted_text = ""
    current_time_bucket = -1
    current_text_bucket = ""
    bucket_start_time = 0.0  # Track the actual start time of the bucket
    
    for entry in transcript_chunk:
        time = entry['start']  # Keep original precision
        time_bucket = int(time // 10)  # Only bucket for grouping
        
        if time_bucket != current_time_bucket:
            # If we have accumulated text, add it to the formatted output
            if current_text_bucket:
                # Use the actual start time, preserving precision
                actual_minutes = int(bucket_start_time // 60)
                actual_seconds = int(bucket_start_time % 60)
                subseconds = int((bucket_start_time % 1) * 10)  # Keep 1 decimal place
                formatted_text += f"[{actual_minutes}:{actual_seconds:02d}.{subseconds}] {current_text_bucket.strip()}\n"
            
            # Start a new time bucket
            current_time_bucket = time_bucket
            bucket_start_time = time  # Store the actual start time
            current_text_bucket = entry['text'] + " "
        else:
            # Add to current bucket
            current_text_bucket += entry['text'] + " "
    
    # Add the last bucket if it exists
    if current_text_bucket:
        # Use the actual start time for the final bucket
        actual_minutes = int(bucket_start_time // 60)
        actual_seconds = int(bucket_start_time % 60)
        subseconds = int((bucket_start_time % 1) * 10)
        formatted_text += f"[{actual_minutes}:{actual_seconds:02d}.{subseconds}] {current_text_bucket.strip()}\n"
        
    return formatted_text
    