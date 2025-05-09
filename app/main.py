import os
from fastapi import FastAPI, Request
import uvicorn
from app.api.endpoints import router
from fastapi.middleware.cors import CORSMiddleware
import nltk
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.utility import limiter
from slowapi.util import get_remote_address
import logging
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.analytics import AnalyticsDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="YouTube Claims API",
    description="API for processing YouTube videos and extracting controversial claims",
    version="1.0.0"
)

nltk.download('punkt')
nltk.download('punkt_tab') #TODO: Do I need this?

#initialize the limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add this near the top of your file, after other imports
analytics_db = AnalyticsDB()

# Add to your FastAPI app
app.state.analytics_db = analytics_db

# Custom rate limit handler
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    reset_time = datetime.now() + timedelta(hours=1)  # Adjust based on your limit window
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "message": "Rate limit exceeded. Please try again later.",
            "resetTime": reset_time.isoformat()
        }
    )

# Add CORS middleware configuration
if settings.environment.lower() == "dev":
    # Development mode - allow localhost
    logger.info("Running in DEVELOPMENT mode with permissive CORS")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Adjust ports as needed
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production mode - only allow specific frontend
    logger.info(f"Running in PRODUCTION mode with restricted CORS to {settings.frontend_url}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_url,
            "https://www.videoclaimcatcher.com",
            "https://videoclaimcatcher.com",
            "https://backdoor-1j4w.onrender.com"    
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


# Include the router from endpoints
app.include_router(router, prefix="/api")

# Main execution
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
    
    