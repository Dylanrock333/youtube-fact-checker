import anthropic
import json
from typing import List, Dict, Any
import httpx
from app.config import get_settings
#import google.generativeai as genai
from google import genai
import nltk
from app.schemas import ClaimResponse
from datetime import datetime
from app.api.video_handlers.translate import translate_full_prompt, get_language_instruction
# Add Perplexity API URL
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

import logging
import asyncio

settings = get_settings()

# Create a single, reusable client instance. This is more efficient and thread-safe.
gemini_client = genai.Client(api_key=settings.google_gemini_api_key)

#GEMINI_MODEL = "gemini-2.5-flash" # INPUT: $0.30 per 1M tokens, OUTPUT: $2.50 per 1M tokens (Great results, output is extensive) 1:06 min for 3hr 167 claims
GEMINI_MODEL = "gemini-2.5-flash-lite-preview-06-17" # INPUT: $0.10 per 1M tokens, OUTPUT: $0.40 per 1M tokens (Good results, cheaper, faster) 27 sec for 3hr 117 claims

#GEMINI_MODEL = "gemini-2.5-pro" # INPUT: $1.25 per 1M tokens, OUTPUT: $10.00 per 1M tokens (Best results, super slow, expensive) 1:40 min for 3hr 113 claims
#GEMINI_MODEL = "gemini-2.0-flash" # INPUT: $0.10 per 1M tokens, OUTPUT: $0.70 per 1M tokens (okay results, cheaper, faster, fewer claims) 26 sec for 3hr 78 claims

async def extract_claims(transcript_text: str, video_data: Dict[str, Any], language: str) -> tuple[List[Dict[str, Any]], int, int]:
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
    # genai.configure(api_key=get_settings().google_gemini_api_key)
    # model = genai.GenerativeModel(GEMINI_MODEL)

    def _sync_generate_content(final_prompt):
        """Synchronous wrapper for Gemini API call that reuses the global client."""
        return gemini_client.models.generate_content(
            model=GEMINI_MODEL, 
            contents=final_prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': list[ClaimResponse],
            },
        )
        
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
    - title: A short and simple title that summarizes the claim stated as a question (less than 10 words)
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
    
    if language != 'en':
        final_prompt = await translate_full_prompt(prompt, language)
        language_instruction = get_language_instruction(language)
        final_prompt = f"{language_instruction}\n\n{final_prompt}"
    else:
        final_prompt = prompt
        
    try:    
        input_tokens = len(nltk.word_tokenize(prompt))
        
        # Use asyncio.to_thread to run the synchronous API call concurrently
        response = await asyncio.to_thread(_sync_generate_content, final_prompt)

    
        response_text = response.text
        output_tokens = len(nltk.word_tokenize(response_text))        

        claims = json.loads(response_text)
        
        return claims, input_tokens, output_tokens
    except (AttributeError, IndexError, json.JSONDecodeError, Exception) as e:
        print(f"Error processing response: {e}")
        try:
            problematic_text = response.candidates[0].content.parts[0].text
            print(f"Problematic text snippet: {problematic_text[:100]}...")
        except Exception as log_e:
            print(f"Could not extract problematic text: {log_e}")
            if 'response' in locals():
                 print(f"Full response object: {response}")
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
async def execute_web_search(perplexity_api_key: str, claim_text: str = None, context: str = None, 
                      video_data: dict = None, query: str = None, language: str = None):
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
    
    user_prompt = f"""
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
    
    if language != 'en':
        logging.info(f"Translating user prompt to {language}")
        final_user_prompt = await translate_full_prompt(user_prompt, language)
        final_system_prompt = await translate_full_prompt(system_prompt, language)
        language_instruction = get_language_instruction(language)
        final_system_prompt = f"{language_instruction}\n\n{final_system_prompt}"
    else:
        final_user_prompt = user_prompt
        final_system_prompt = system_prompt
        
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": final_system_prompt
            },
            {
                "role": "user",
                "content": final_user_prompt
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
    
    # Use an async HTTP client
    async with httpx.AsyncClient() as client:
        response = await client.post(url=PERPLEXITY_API_URL, json=payload, headers=headers, timeout=30.0)
    
    response.raise_for_status()  # Raise an exception for bad status codes
    return response.json()

#TODO:SPEECH TO TEXT
'''
- Whisper
- AssemblyAI
- Deepgram
- Speechmatics 
- Groq-distil-whisper
'''

async def tweet_generation_agent(prompt: str):
    """
    Calls the Gemini API with a generic prompt and returns the response.
    """
    
    def _sync_generate_content(prompt):
        """Synchronous wrapper for Gemini API call that reuses the global client."""
        return gemini_client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt
        )

    try:
        response = await asyncio.to_thread(_sync_generate_content, prompt)
        return response.text
    except Exception as e:
        logging.error(f"Error calling Gemini API: {e}")
        raise
    
    
def call_gemini_agent(prompt: str, inputs: Dict[str, Any] = None, schema: Dict[str, Any] = None):
    """
    Synchronous Gemini API call with support for structured output.
    
    Args:
        prompt: The prompt to send to the model
        inputs: Additional data to include in the prompt (optional)
        schema: JSON schema for structured output (optional)
    """
    try:
        # Build the full prompt with inputs if provided
        if inputs:
            full_prompt = f"{prompt}\n\nData:\n{json.dumps(inputs, indent=2)}"
        else:
            full_prompt = prompt
            
        # Configure the generation config based on whether schema is provided
        if schema:
            config = {
                'response_mime_type': 'application/json',
                'response_schema': schema,
            }
        else:
            config = {}
            
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=config
        )
        
        # If schema is provided, parse the JSON response
        if schema:
            try:
                return json.loads(response.text)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                logging.error(f"Raw response: {response.text}")
                raise
        
        return response.text
    except Exception as e:
        logging.error(f"Error calling Gemini API: {e}")
        raise   
    
def filter_and_clean_claims_agent(claim_list, video_data, video_id):
    

    full_prompt = f"""
    You are helping design a front page for the app **Video Claim Catcher**, which extracts and analyzes statements made in YouTube videos. 

    You are given a list of claims extracted from a video, along with context and metadata.

    Your job is to:
    1. **Select 3–6 claims** that are the most useful, interesting, or surprising — things that invite users to learn more or verify.
    2. **Rewrite each claim to be short, clear, and punchy** — it must be easy to read and fit nicely on a UI card. Prioritize simple sentence structure and clarity. Limit each claim to around **1 sentence** or about **40 words**.
    3. **Do not change the meaning of the claim**, just make it **more readable and catchy**. Avoid long or complex phrasing.
    4. **Preserve attribution** only if it's important to the credibility (e.g. "according to a professor" or "Maya Angelou said..."). Otherwise, focus on the core message.

    Video Title:
    {video_data["title"]}

    Channel:
    {video_data["channel_title"]}

    Published:
    {video_data["published_at"]}

    List of claims:
    {claim_list}
    """

    
    
        
    max_retries = 3
    claims = []
    
    for attempt in range(max_retries):
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=full_prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': list[ClaimResponse],
                }
            )
            
            response_text = response.text
            claims = json.loads(response_text)
            # If we get here, the JSON parsing was successful
            break
            
        except json.JSONDecodeError as e:
            logging.warning(f"JSON parsing failed on attempt {attempt + 1}/{max_retries} in filter_and_clean_claims_agent: {e}")
            if attempt == max_retries - 1:  # Last attempt
                logging.error(f"Failed to parse JSON response after {max_retries} attempts")
                logging.error(f"Raw response: {response_text}")
                claims = []
            else:
                logging.info(f"Retrying API call (attempt {attempt + 2}/{max_retries})")
                
        except Exception as e:
            logging.warning(f"API call failed on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt == max_retries - 1:  # Last attempt
                logging.error(f"Failed to call Gemini API after {max_retries} attempts: {e}")
                claims = []
            else:
                logging.info(f"Retrying API call (attempt {attempt + 2}/{max_retries})")
    
    return_dict = {
        "video_id": video_id,
        "title": video_data["title"],
        "channel_title": video_data["channel_title"],
        "published_at": video_data["published_at"],
        "view_count": video_data["view_count"],
        "duration": video_data["duration"],
        "claims": claims
    }
    
    return return_dict
        