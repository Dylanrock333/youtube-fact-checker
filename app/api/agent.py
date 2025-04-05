import anthropic
import json
from typing import List, Dict, Any
import requests
from app.config import get_settings
from google import genai
import nltk
from app.schemas import ClaimResponse

# Add Perplexity API URL
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

def extract_claims(transcript_text: str, video_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract controversial or potentially incorrect factual claims from transcript text.
    
    Returns a list of dictionaries containing:
    - claim: The factual claim text
    - timestamp: When the claim appears in the video
    - category: Type of claim (statistical, historical, scientific, etc.)
    - controversy_score: How controversial or surprising the claim is (1-5)
    - internet_searchability: How easily the claim can be verified online (1-5)
    - context: Surrounding text for context
    """
    client = genai.Client(api_key=get_settings().google_gemini_api_key)
    
    prompt = f"""
    You are an expert fact-checker analyzing a YouTube video transcript.
    Identify statements presented as facts that warrant verification, potentially misleading, factually questionable or contreversial.
    
    Extract claims that:
    - Contradict common knowledge or scientific consensus
    - Contain specific statistics, numbers, or quantifiable assertions
    - Make historical statements about events, people, or developments
    - Present scientific or technical information
    - Reference studies, research, or data
    - State legal, regulatory, or policy information
    - Make definitive causal relationships
    - Present absolute statements using words like "always," "never," "all," etc.
    - Present correlation as causation
    
    For each claim:
    1. Extract the exact quote containing the factual claim, including any qualifying phrases, supporting details, or
    contextual elements that are part of the same thought or argument. This should be comprehensive enough to stand on its 
    own for verification purposes.
    2. Note the timestamp where it appears
    3. Categorize the claim (statistical, historical, scientific, legal, causal, political, etc.)
    4. Rate "verification importance" on a scale of 1-5:
        - 5: Central to the speaker's argument and likely to influence viewers
        - 4: Significant claim that shapes understanding of the topic
        - 3: Moderately important claim that adds context to the discussion
        - 2: Minor claim that has limited impact on the overall message
        - 1: Peripheral claim with minimal significance to the discussion
    5. Rate "factual precision" on a scale of 1-5:
        - 5: Highly specific claim with clear, verifiable components
        - 4: Specific claim with mostly verifiable elements
        - 3: Moderately specific claim with some verifiable elements
        - 2: Somewhat vague claim that's difficult but possible to verify
        - 1: Very general claim that's challenging to definitively verify
    6. Rate the "controversy score" on a scale of 1-5:
        - 5: Highly controversial, directly contradicts established consensus
        - 4: Significantly surprising or questionable given available evidence
        - 3: Somewhat misleading or lacking important context
        - 2: Slightly oversimplified but not entirely wrong
        - 1: Potentially misleading framing of otherwise accurate information
    7. Provide comprehensive context for the claim (4-6 sentences) that:
        - Captures what led up to this statement in the video
        - Provides necessary context from the surrounding discussion
        - Explains the speaker's apparent purpose or intent when making the claim
        - Notes any qualifiers the speaker used before or after the claim
        - Includes relevant background information that helps understand why this claim was made
    8. Create an objective research query that will help substantiate the factual accuracy of this claim. Format it as a detailed research prompt that:
        - Includes key elements of the claim that need verification
        - Provides necessary context from the surrounding discussion
        - Identifies potential sources or types of evidence that would confirm or refute the claim
        - Asks for an evaluation of supporting and contradicting evidence
        - Requests identification of any nuance, complexity, or qualifications missing from the original claim
    
    IGNORE obviously true statements of common knowledge
    IGNORE opinions clearly framed as such ("I believe," "I think," etc.)
    IGNORE opinions, hypotheticals, or personal preferences.  
    
    Format your response as a JSON array of objects with these fields:
    - claim: The factual statement text
    - timestamp: The timestamp from the transcript (HH:MM:SS)
    - category: Type of claim
    - verification_importance: Numeric rating (1-5)
    - controversy_score: Numeric rating (1-5)
    - factual_precision: Numeric rating (1-5)
    - context: Surrounding text
    - search_query: Search query for verification
    
    VIDEO INFO:
    - title: {video_data["title"]}
    - tags: {video_data["tags"]}
    - account_name: {video_data["channel_title"]}
    - published_at: {video_data["published_at"]}
    
    TRANSCRIPT:
    {transcript_text}
    """
    


    try:    
        # TODO: if there is an error retry the chunk
        
        input_tokens = len(nltk.word_tokenize(prompt))
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': list[ClaimResponse],
            },
        )
        
        
        response_text = response.text
        #print(response_text)
        output_tokens = len(nltk.word_tokenize(response_text))        

        claims = json.loads(response_text)
        
        return claims, input_tokens, output_tokens
    except (AttributeError, IndexError, json.JSONDecodeError, Exception) as e:
        # Handle potential errors if the response structure is unexpected or JSON is invalid
        print(f"Error processing response: {e}")
        # Attempt to log the problematic text if possible
        try:
            problematic_text = response.candidates[0].content.parts[0].text
            print(f"Problematic text: {problematic_text}")
        except Exception as log_e:
            print(f"Could not extract problematic text: {log_e}")
            print(f"Full response object: {response}")
        # Return default values matching the expected tuple structure
        return [], 0, 0
    
    
def execute_web_search(perplexity_api_key: str, claim_text: str = None, context: str = None, 
                      video_data: dict = None, query: str = None):
    """
    Execute a web search using the Perplexity API with enhanced context.
    
    Args:
        perplexity_api_key: API key for Perplexity
        claim_text: The specific claim being verified (optional)
        context: Additional context from the video (optional)
        video_data: Metadata about the video (optional)
        query: A specific search query to use (optional)
    """
    # Build a comprehensive prompt with all available information
    video_title = video_data.get('title', '') if video_data else ''
    video_published_at = video_data.get('published_at', '') if video_data else ''
    video_tags = video_data.get('tags', []) if video_data else []
    
    prompt = f"""
        CLAIM:
        {claim_text}
        
        CONTEXT:
        {context}
        
        VIDEO INFO:
        Caption: {video_title}
        Published at: {video_published_at}
        Tags: {video_tags}
        
        Please:
        1. Analyze this claim objectively without political bias
        2. Find reliable sources that confirm or contradict this claim
        3. Present evidence from multiple perspectives when relevant
        4. Note any important nuance, context, or qualifications missing from the original claim
        5. Assess the overall accuracy on a scale from "Completely False" to "Completely True"
        6. Explain specifically what parts are accurate or inaccurate if the claim is partially true
        7. Cite specific sources, studies, statistics or expert consensus that support your assessment
        
        Use this search query as a starting point: 
        {query}
                """
    
    # Rest of the function remains the same
    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 600,
        "temperature": 0.3,
        "top_p": 0.9,
        "search_domain_filter": None,
        "return_images": False,
        "return_related_questions": False,
        "search_recency_filter": "month",
        "top_k": 0,
        "stream": False,
        "presence_penalty": 0,
        "frequency_penalty": 1,
        "response_format": None
    }
    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url=PERPLEXITY_API_URL, json=payload, headers=headers)
    
    
    return response.json()

