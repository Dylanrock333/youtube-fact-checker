import anthropic
import json
from typing import List, Dict, Any
import requests

def extract_claims(transcript_text: str, api_key: str) -> List[Dict[str, Any]]:
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
    client = anthropic.Anthropic(api_key=api_key)
    #TODO: add more to the quote, but this might be done in the transcript processing
    #TODO: Search query should be presented more ad a question 
    #TODO: Need just a liitle more in the context 
    #TODO: look into what other metricks I can use insted of searchability and controversy score
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
    1. Extract the exact quote containing the controversial/questionable claim
    2. Note the timestamp where it appears
    3. Categorize the type of claim (statistical, historical, scientific, political, etc.)

    5. Rate the "internet searchability" on a scale of 1-5:
       - 5: Abundant information available online to verify/reject the claim
       - 4: Significant information available from multiple reliable sources
       - 3: Moderate amount of information available with some research
       - 2: Limited information available, requiring deep research
       - 1: Very little information available online about this specific claim
    6. Provide 2-4 sentences of surrounding context elaborating on the claim and the context in which it is made.
    7. provide an internet search query that can be used to verify the claim.
    
    
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
    8. Create an objective research query that will help verify the factual accuracy of this claim. Format it as a detailed research prompt that:
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
    - timestamp: The timestamp from the transcript
    - category: Type of claim
    - verification_importance: Numeric rating (1-5)
    - controversy_score: Numeric rating (1-5)
    - factual_precision: Numeric rating (1-5)
    - context: Surrounding text
    - search_query: Search query for verification
    
    TRANSCRIPT:
    {transcript_text}
    """
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4000,
        temperature=0,
        system="You are an expert fact-checker who identifies potentially controversial, misleading, or factually questionable claims in text.",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    try:
        # Extract the JSON from the response
        response_text = response.content[0].text
        # Find JSON in the response (it might be wrapped in markdown code blocks)
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            claims = json.loads(json_str)
            return claims
        else:
            print("Could not find JSON in response")
            return []
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Response was: {response.content[0].text}")
        return []
    
def execute_web_search(claimContent: int, perplexity_api_key: str):

    prompt = f"""
        {claimContent}

    """
    

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

    response = requests.request("POST", url, json=payload, headers=headers)
    
    return response.json()
