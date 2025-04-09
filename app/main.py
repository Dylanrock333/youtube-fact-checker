import os
from fastapi import FastAPI
import uvicorn
from app.api.endpoints import router
from fastapi.middleware.cors import CORSMiddleware
import nltk

app = FastAPI(
    title="YouTube Claims API",
    description="API for processing YouTube videos and extracting controversial claims",
    version="1.0.0"
)

nltk.download('punkt')
nltk.download('punkt_tab')

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include the router from endpoints
app.include_router(router, prefix="/api")

# Main execution
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
    
    