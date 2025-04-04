import os
from typing import List, Dict, Any
from dotenv import load_dotenv
# from app.api.formatting import save_claims_to_file
# from app.api.agent import execute_web_search
from fastapi import FastAPI
import uvicorn
from api.endpoints import router
from api.claim_extraction import process_video_claims
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="YouTube Claims API",
    description="API for processing YouTube videos and extracting controversial claims",
    version="1.0.0"
)

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include the router from endpoints
app.include_router(router)

# Main execution
if __name__ == "__main__":
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if not anthropic_api_key or not perplexity_api_key:
        print("Please set the ANTHROPIC_API_KEY and PERPLEXITY_API_KEY environment variables")
        exit(1)
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    