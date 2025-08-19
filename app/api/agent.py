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
GEMINI_MODEL = "gemini-2.5-flash-lite" # INPUT: $0.10 per 1M tokens, OUTPUT: $0.40 per 1M tokens (Good results, cheaper, faster) 27 sec for 3hr 117 claims

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
    IGNORE opinions, hypotheticals, sarcasm, or personal preferences. 
    IGNORE statements that are not presented as facts.
    IGNORE potential ads or sponsored content.
    
    For each claim:
        1. 'title': Generate a very short and simple title that summarizes the claim (less than 10 words)
        2. 'claim': Extract the exact quote from the transcript. Only include the text relevant to the claim. do not include any other text.
        3. `context`: 1–3 sentences explaining:
            - What led up to the claim
            - Speaker’s intent and surrounding discussion
            - Any qualifiers or background info
            - Write in a clear, concise, and neutral tone. Use plain language. Keep it simple, informative, engaging and to the point.
            - No jargon or filler. Avoid academic or overly technical language.
        4. 'timestamp': Note the timestamp of the moment the claim is made
        5. 'category': Categorize the claim in a single word (Statistical, Historical, Scientific, Legal, Causal, Political, etc.)
        6. 'controversy_score': Rate the "controversy score" on a scale of 1-5:
            - 5: Highly controversial, directly contradicts established consensus
            - 4: Significantly surprising or questionable given available evidence
            - 3: Somewhat misleading or lacking important context
            - 2: Slightly oversimplified but not entirely wrong
            - 1: Potentially misleading framing of otherwise accurate information
        7. 'search_query': Create an objective research query that will help substantiate the factual accuracy of this claim. Format it as a detailed research prompt that (3-4 sentences):
            - Includes key elements of the claim that need verification
            - Provides necessary context from the surrounding discussion
            - Identifies potential sources or types of evidence that would confirm or refute the claim
            - Asks for an evaluation of supporting and contradicting evidence
            - Requests identification of any nuance, complexity, or qualifications missing from the original claim
        
    Return your output as a JSON array with one object per claim
    
    VIDEO INFO:
    - title: {video_data["title"]}
    - tags: {video_data["tags"]}
    - account_name: {video_data["channel_title"]}
    - published_at: {video_data["published_at"]}
    
    VIDEO TRANSCRIPT:
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
                
                
    system_prompt = """
    You are an objective, helpful assistant designed to clarify factual claims from educational or informational YouTube videos. 

    Your role is to:
    - Explain the claim using verified, factual background and context.
    - Use reliable, up-to-date, and neutral sources, including major news outlets, research institutions, encyclopedias, and fact-checking organizations.
    - Avoid labeling the claim as true or false unless there is overwhelming expert consensus. If consensus exists, present it with supporting evidence and the citation.
    - If the claim is debated or uncertain, explain the perspectives clearly and cite relevant evidence for each.
    - Keep your explanation concise, neutral in tone, and easy to understand.
    - Include citations or hyperlinks in parentheses for key statements to support learning and transparency.
    - Do not speculate. Avoid biased, charged, or overly technical language unless necessary to explain the topic clearly.

    Your response will be shown to a user who may or may not be familiar with the topic, so prioritize clarity and trustworthy evidence.
    
    Match your explanation style to the type of video and claim. Use the formatting structure below, but adjust tone and examples to suit the content and audience.
    Video/Claim Types and How to Adapt Tone:
    - Political Commentary / Opinion:
        - Tone: Neutral, analytical. No bias.
        - Intro: “The speaker argues…” / “The claim centers on…”
        - Closing: Acknowledge multiple viewpoints, avoid loaded language.
        - Sources: Prioritize up-to-date, credible outlets.

    - News / Current Events:
        - Tone: Direct, factual, timely.
        - Intro: “The video reports…” / “This claim references…”
        - Closing: Clarify what’s confirmed vs. unfolding/speculative.
        - Sources: Prioritize up-to-date, credible outlets.

    - Educational / Explainer:
        - Tone: Clear, friendly, informative.
        - Intro: “The host explains…” / “The video describes…”
        - Closing: Reinforce key facts, offer helpful context.
        - Sources: Academic/institutional.
        
    - Podcast / Discussion:
        - Tone: Casual but objective.
        - Intro: “One speaker claims…” / “A point discussed was…”
        - Closing: Clarify speculation vs. fact.
        - Avoid: Overstating anecdotal claims.

    - Science / Health / Data:
        - Tone: Careful, evidence-focused.
        - Intro: “The claim suggests…” / “The video presents data on…”
        - Closing: Highlight consensus, note ongoing research.
        - Sources: Peer-reviewed studies, org sites (CDC, WHO, etc.).

    - Casual / Humorous / Miscellaneous:
        - Tone: Light, accessible, respectful.
        - Intro: “The video jokes about…” / “The claim was made playfully…”
        -  Closing: Note if it’s satire, meme, exaggeration, or harmless speculation.
        - Avoid: Overanalyzing humor unless it spreads misinformation.


    In the response, seamlessly integrate the following: 
        (1) an explanation of the claim and its video context
        (2) a clear overview of what is known based on reliable sources
        (3) any expert consensus or disagreement with citations
        (4) a neutral conclusion summarizing what is known, unknown, or debated
    
    Do not include any nm dash or em dash in your response.
    
    Avoid overusing the word “claim.” Use it only when referring to a specific assertion being fact-checked or debated. For general context, vary your phrasing to keep the response natural and user-friendly.
        Use alternatives like:
        - “The video suggests…”
        - “The speaker mentions…”
        - “One point raised is…”
        - “It’s stated that…”

    When the content is explanatory or factual, focus on clear, direct language. Prioritize tone-matching, clarity, and flow over strict labels.
    
    Use simple language, clear headings for each section, short paragraphs, and bullet points. Remove excess citations and academic tone. Make it easy to skim.
    
    Please respond in Markdown format with clear headings and bullet points.
    
    When responding, organize the explanation using concise, relevant section headings to break up information. Use 2–4 clear, short headings per response. Only add a heading if it helps users follow the flow — avoid unnecessary or repetitive headers. Use plain, intuitive language in headers, such as “Background,” “What Experts Say,” “Points to Consider,” or “Key Takeaways.
    
    Do not include any charts or graphs in your response.
    
    Keep in mind you have 600 tokens to work with so be concise and to the point and finish your response as if you had 550 tokens left.
    """

    
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
        "max_tokens": 600,
        "temperature": 0.1,
        "top_p": 0.9,
        "frequency_penalty": 0,   
        "web_search_options": {
            "search_context_size": "high"
        },
        "search_domain_filter": [
            "-pinterest.com",
            "-quora.com", 
            "-reddit.com",
            "-yahoo.answers.com",
            "-answers.com",
            "-ask.com",
            "-wikihow.com"
        ]
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

async def call_gemini_agent(prompt: str):
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
