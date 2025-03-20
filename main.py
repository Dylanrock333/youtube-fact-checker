import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from formatting import save_claims_to_file
from agent import execute_web_search
from fastapi import FastAPI
import uvicorn
from endpoints import router
from claim_extraction import process_video_claims
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

def terminal_execution(video_id: str, anthropic_api_key: str, perplexity_api_key: str):
        
    claims, video_title = process_video_claims(video_id, anthropic_api_key)
    #claims = reorder_claims_by_timestamp(claims)
    
    if claims:
        print(f"Video Title: {video_title}")
        print(f"Found {len(claims)} controversial claims in the video")
        save_claims_to_file(claims, video_id)
        
        # Print top 5 most controversial claims
        print("\nTOP 5 MOST CONTROVERSIAL CLAIMS:")
        for i, claim in enumerate(claims[:5], 1):
            print(f"{i}. [{claim['timestamp']}] \"{claim['claim']}\" (Controversy: {claim['controversy_score']}/5)")
    else:
        print("No controversial claims were identified in this video")
        
        
    claimId = int(input("Enter Id to execute web search: "))  # Convert to integer
    # Find the claim with matching id
    claimContent = None
    for claim in claims:
        if claim["id"] == claimId:
            claimContent = claim
            break

    if claimContent:
        response = execute_web_search(claimContent, perplexity_api_key)
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            print("\nSearch Result:")
            print(content)
            
            # If you want to display citations as well
            if 'citations' in response:
                print("\nSources:")
                for citation in response['citations']:
                    print(f"- {citation}")
        else:
            print("No content found in response")
            print(response)  # Print full response for debugging
    else:
        print(f"No claim found with id {claimId}")


# Main execution
if __name__ == "__main__":
    video_id = "R9AQ6YffF78"
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if not anthropic_api_key or not perplexity_api_key:
        print("Please set the ANTHROPIC_API_KEY and PERPLEXITY_API_KEY environment variables")
        exit(1)
        
    #terminal_execution(video_id, anthropic_api_key, perplexity_api_key)
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    