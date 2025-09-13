from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Define request model for execute endpoint
class VideoExecutionRequest(BaseModel):
    url: str
    origin: str
    videoID: str
    selectedLanguage: str = "en"

# Define request model for deepsearch endpoint
class DeepSearchRequest(BaseModel):
    claimText: Optional[str] = None # Using Optional for clarity
    context: Optional[str] = None
    videoTitle: Optional[str] = None
    videoPublishedAt: Optional[str] = None
    videoTags: Optional[List[str]] = None # Optional list of strings
    query: Optional[str] = None
    selectedLanguage: str = "en"
    
class PostGenerationRequest(BaseModel):
    prompt: str 
    
class ClaimResponse(BaseModel):
    title: str
    claim: str
    context: str
    timestamp: str
    category: str
    controversy_score: int
    search_query: str
    

