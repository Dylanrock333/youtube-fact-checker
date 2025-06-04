import anthropic
import json
from typing import List, Dict, Any
import requests
from app.config import get_settings
from google import genai
import nltk
from app.schemas import ClaimResponse
from datetime import datetime
from app.api.video_handlers.translate import translate_full_prompt, get_language_instruction
# Add Perplexity API URL
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

import logging

#GEMINI_MODEL = "gemini-2.5-flash-preview-05-20" # INPUT: $0.15 per 1M tokens, OUTPUT: $0.60 per 1M tokens (Great results, cost effective, slower) 35sec for 3hr 80 claims
GEMINI_MODEL = "gemini-2.0-flash-lite" # INPUT: $0.075 per 1M tokens, OUTPUT: $0.30 per 1M tokens (good results, cost efficient, low latency) (Need it to elaborate more for context and search query) 16 sec for 3hr 61 claims

#GEMINI_MODEL = "gemini-2.5-pro-preview-05-06" # INPUT: $1.25 per 1M tokens, OUTPUT: $10.00 per 1M tokens (Best results, super slow, expensive) 2min 6sec for 3hr 135 claims
#GEMINI_MODEL = "gemini-2.0-flash" # INPUT: $0.10 per 1M tokens, OUTPUT: $0.40 per 1M tokens (multi-modal, good for images ect) 16 sec for 3hr 54 claims

async def extract_claims(transcript_text: str, video_data: Dict[str, Any], language: str) -> List[Dict[str, Any]]:
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
        #TODO: Fix time stamp
    prompt = f"""
    You are an expert fact-checker analyzing a video transcript.
    Identify selective statements presented as facts that warrant verification, potentially misleading, factually questionable or contreversial and provide a detailed analysis of the claim.
    
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
    
    IGNORE obviously true statements of common knowledge
    IGNORE opinions clearly framed as such ("I believe," "I think," etc.)
    IGNORE opinions, hypotheticals, or personal preferences. 
    IGNORE statements that are not presented as facts.
    
    For each claim:
        1. Generate a very short and simple title that summarizes the claim
        2. Extract the exact quote containing the factual claim, including any qualifying phrases, supporting details, or
        contextual elements that are part of the same thought or argument. This should be comprehensive enough to stand on its 
        own for verification purposes.
        3. Provide comprehensive context for the claim (4-6 sentences) that:
            - Captures what led up to this statement in the video
            - Provides necessary context from the surrounding discussion
            - Explains the speaker's apparent purpose or intent when making the claim
            - Notes any qualifiers the speaker used before or after the claim
            - Includes relevant background information that helps understand why this claim was made
        4. Note the timestamp where it appears
        5. Categorize the claim in a single word (statistical, historical, scientific, legal, causal, political, etc.)
        6. Rate the "controversy score" on a scale of 1-5:
            - 5: Highly controversial, directly contradicts established consensus
            - 4: Significantly surprising or questionable given available evidence
            - 3: Somewhat misleading or lacking important context
            - 2: Slightly oversimplified but not entirely wrong
            - 1: Potentially misleading framing of otherwise accurate information
        7. Create an objective research query that will help substantiate the factual accuracy of this claim. Format it as a detailed research prompt that (3-4 sentences):
            - Includes key elements of the claim that need verification
            - Provides necessary context from the surrounding discussion
            - Identifies potential sources or types of evidence that would confirm or refute the claim
            - Asks for an evaluation of supporting and contradicting evidence
            - Requests identification of any nuance, complexity, or qualifications missing from the original claim
        
    Format your response as a JSON array of objects with these fields:
    - title: A short and simple title that summarizes the claim stated as a question (less than 1 s)
    - claim: The factual statement quoted from the transcript only 
    - context: a summary of the context for the claim that explains the claim and the context leading up to it (3-5 sentences)
    - timestamp: The timestamp from the transcript (HH:MM:SS)
    - category: Type of claim
    - controversy_score: Numeric rating (1-5)
    - search_query: A detailed search query for verification of the claim (3-4 sentences)
     
    ...
    
    VIDEO INFO:
    - title: {video_data["title"]}
    - tags: {video_data["tags"]}
    - account_name: {video_data["channel_title"]}
    - published_at: {video_data["published_at"]}
    
    TRANSCRIPT:
    {transcript_text}
    """
    
    #logging.info(f"language: {language}")
    
    if language != 'en':
        final_prompt = await translate_full_prompt(prompt, language)
        language_instruction = get_language_instruction(language)
        final_prompt = f"{language_instruction}\n\n{final_prompt}"
    else:
        final_prompt = prompt
        
    #logging.info(f"final_prompt: {final_prompt}")

    try:    
        # TODO: if there is an error retry the chunk
        
        input_tokens = len(nltk.word_tokenize(prompt))
        
        response = client.models.generate_content(
            model=GEMINI_MODEL, 
            contents=final_prompt,
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
    
#TODO: Deep search find a better model that has citations, good summary, and cheaper
'''
- Play around with perplexity api
- you.com
- paperpal
-Scite
-Originality.AI
-LongShot
'''
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
    category = '' #TODO: Add category
    
    prompt = f"""
        CLAIM:
        {claim_text}
        
        CONTEXT:
        {context}
        
        VIDEO INFO:
        Video Title: {video_title}
        Publication Date: {video_published_at}
        Video Tags: {video_tags}  
        Current Date: {datetime.now().strftime('%Y-%m-%d')} 
        
        Use the question from the search query as a starting point: 
        {query}
        

    """
                
                
    system_prompt = '''Provide a in depth and informative claim analysis on the following claim and return the results in markdown format:
        1. Analyze this claim objectively without bias
        2. Find reliable sources that confirm or contradict this claim
        3. Present evidence from multiple perspectives when relevant
        4. Note any important nuance, context, or qualifications missing from the original claim
        5. Assess the overall accuracy on a scale from "Completely False" to "Completely True"    
        
        No line divider between the sections please
    '''

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1500,
        "temperature": 0.2,
        "top_p": 0.9,
        "frequency_penalty": 1,   
    }
    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url=PERPLEXITY_API_URL, json=payload, headers=headers)
     
    #print(response.json())
    
    return response.json()

#TODO:SPEECH TO TEXT
'''
- Whisper
- AssemblyAI
- Deepgram
- Speechmatics 
- Groq-distil-whisper
'''
