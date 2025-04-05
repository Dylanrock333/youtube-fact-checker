import json
import os
from typing import List, Dict, Any

# def save_claims_to_file(claims: List[Dict[str, Any]], video_id: str):
#     """Save extracted claims to a JSON file within the claims folder."""
#     # Create claims directory if it doesn't exist
#     claims_dir = os.path.join(os.path.dirname(__file__), "claims")
#     os.makedirs(claims_dir, exist_ok=True)
    
#     # Save JSON file
#     json_path = os.path.join(claims_dir, f"{video_id}_claims.json")
#     with open(json_path, "w") as f:
#         json.dump(claims, f, indent=2)
    
#     # Also create a human-readable text version
#     txt_path = os.path.join(claims_dir, f"{video_id}_claims.txt")
#     with open(txt_path, "w") as f:
#         f.write(f"CONTROVERSIAL CLAIMS EXTRACTED FROM VIDEO {video_id}\n")
#         f.write("="*50 + "\n\n")
        
#         for i, claim in enumerate(claims, 1):
#             f.write(f"CLAIM #{i} - {claim['timestamp']}\n")
#             f.write(f"Statement: \"{claim['claim']}\"\n")
#             f.write(f"Category: {claim['category']}\n")
#             f.write(f"Controversy Score: {claim['controversy_score']}/5\n")
#             f.write(f"Internet Searchability: {claim['internet_searchability']}/5\n")
#             f.write(f"Context: {claim['context']}\n")
#             f.write(f"Internet Search Query: {claim['internet_search_query']}\n")
#             f.write("-"*50 + "\n\n")
            
# def chunk_transcript(transcript: List[Dict[str, Any]], chunk_size: int = 10000) -> List[List[Dict[str, Any]]]:
#     """
#     Split transcript into chunks to handle API context limits.
#     Returns a list of lists, where each inner list contains transcript entries
#     with a total text size under the chunk_size limit.
#     """
#     chunks = []
#     current_chunk = []
#     current_size = 0
    
#     for entry in transcript:
#         # Calculate the size of this entry's text
#         entry_size = len(entry['text'])
        
#         # If adding this entry would exceed the chunk size and we already have entries,
#         # save the current chunk and start a new one
#         if current_size + entry_size > chunk_size and current_chunk:
#             chunks.append(current_chunk)
#             current_chunk = [entry]
#             current_size = entry_size
#         else:
#             # Add the entry to the current chunk
#             current_chunk.append(entry)
#             current_size += entry_size
            
#     # Add the last chunk if it has any entries
#     if current_chunk:
#         chunks.append(current_chunk)
        
#     return chunks

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
    
# # Reordering claims by timestamp
# def reorder_claims_by_timestamp(claims):
#     # Convert timestamp strings to minutes and seconds for proper sorting
#     def timestamp_to_seconds(timestamp):
#         parts = timestamp.split(':')
#         if len(parts) == 2:
#             minutes, seconds = parts
#             return int(minutes) * 60 + int(seconds)
#         return 0  # Default if format is unexpected
    
#     # Sort the claims by timestamp
#     sorted_claims = sorted(claims, key=lambda x: timestamp_to_seconds(x['timestamp']))
#     return sorted_claims

