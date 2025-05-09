from typing import List, Dict, Any

#chunk size is 
# 5000 for 3hr  83 claims, 31 chunks
# 6000 for 3hr 74 claims, 26 chunks
# 7000 for 3hr 61 claims, 20 chunks
# 8000 for 3hr 84 claims, 19 chunks
# 9000 for 3hr 67 claims, 17 chunks
# 10000 for 3hr 65 claims, 16 chunks
# 11000 for 3hr 72 claims, 14 chunks
# 12000 for 3hr 61 claims, 13 chunks

def chunk_transcript(transcript: List[Dict[str, Any]], chunk_size: int = 8000) -> List[List[Dict[str, Any]]]:
    """
    Split transcript into chunks to handle API context limits.
    Returns a list of lists, where each inner list contains transcript entries
    with a total text size under the chunk_size limit.
    """
    
    #TODO: Implement a time based chunking method with some overlap
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for entry in transcript:
        # Calculate the size of this entry's text
        entry_size = len(entry['text'])
        
        # If adding this entry would exceed the chunk size and we already have entries,
        # save the current chunk and start a new one
        if current_size + entry_size > chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [entry]
            current_size = entry_size
        else:
            # Add the entry to the current chunk
            current_chunk.append(entry)
            current_size += entry_size
            
    # Add the last chunk if it has any entries
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks