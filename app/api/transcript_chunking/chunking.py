from typing import List, Dict, Any


def chunk_transcript(transcript: List[Dict[str, Any]], chunk_size: int = 10000) -> List[List[Dict[str, Any]]]:
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