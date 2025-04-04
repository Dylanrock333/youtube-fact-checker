import os
from fastapi import FastAPI
import uvicorn
from app.api.endpoints import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="YouTube Claims API",
    description="API for processing YouTube videos and extracting controversial claims",
    version="1.0.0"
)

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Include the router from endpoints
app.include_router(router)

# Main execution
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    
    