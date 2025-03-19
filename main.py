import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from formatting import chunk_transcript, format_transcript_for_analysis, reorder_claims_by_timestamp, save_claims_to_file
from youtube_data import get_transcript
from agent import extract_claims, execute_web_search

# Load environment variables from .env file
load_dotenv()



def process_video_claims(video_id: str, api_key: str) -> tuple[List[Dict[str, Any]], str]:
    """Process a YouTube video and extract controversial or questionable factual claims."""
    # Get the transcript and title
    transcript, video_title = get_transcript(video_id)
    if not transcript:
        return [], None
    
    # Split transcript into manageable chunks (now returns list of lists)
    transcript_chunks = chunk_transcript(transcript)
    print(f"Split transcript into {len(transcript_chunks)} chunks")
    
    # Process each chunk and collect claims
    all_claims = []
    claim_id = 0  # Initialize a counter for unique claim IDs
    
    for i, chunk in enumerate(transcript_chunks):
        print(f"Processing chunk {i+1}/{len(transcript_chunks)}...")
        
        # Format this chunk for the LLM
        formatted_chunk = format_transcript_for_analysis(chunk)
        
        # Extract claims from the formatted chunk
        chunk_claims = extract_claims(formatted_chunk, api_key)
        
        # Add unique ID to each claim
        for claim in chunk_claims:
            claim['id'] = claim_id
            claim_id += 1
        
        all_claims.extend(chunk_claims)
     
    return all_claims, video_title


# Main execution
if __name__ == "__main__":
    video_id = "cp7go61oDeY"
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if not anthropic_api_key or not perplexity_api_key:
        print("Please set the ANTHROPIC_API_KEY and PERPLEXITY_API_KEY environment variables")
        exit(1)
    
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