from pydantic import BaseModel
from typing import Optional, List

# Define request model for execute endpoint
class VideoExecutionRequest(BaseModel):
    url: str
    origin: str
    videoID: str

# Define request model for deepsearch endpoint
class DeepSearchRequest(BaseModel):
    claimText: Optional[str] = None # Using Optional for clarity
    context: Optional[str] = None
    videoTitle: Optional[str] = None
    videoPublishedAt: Optional[str] = None
    videoTags: Optional[List[str]] = None # Optional list of strings
    query: Optional[str] = None
    
class ClaimResponse(BaseModel):
    title: str
    claim: str
    context: str
    timestamp: str
    category: str
    controversy_score: int
    search_query: str
    

# Define response model for execute endpoint
# class ExecuteResponse(BaseModel):
#     claims: List[Claim] # Use the Claim schema here
#     video_data: Optional[VideoData] # Use the VideoData schema, make it optional if it can be None
#     videoID: str
#     claim_count: int
