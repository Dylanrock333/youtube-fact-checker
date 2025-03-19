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
    
    prompt = f"""
    You are an expert fact-checker analyzing a YouTube video transcript. 
    Identify ONLY statements that are potentially controversial, surprising, misleading, or factually questionable.
    
    Focus on claims that:
    - Contradict common knowledge or scientific consensus
    - Make bold or surprising statistical assertions
    - Oversimplify complex topics in potentially misleading ways
    - Present contested historical interpretations as settled fact
    - Make sweeping generalizations about groups of people
    - Cite statistics or studies without proper context
    - Present correlation as causation
    - Make specific predictions about the future presented as certainty
    
    For each claim:
    1. Extract the exact quote containing the controversial/questionable claim
    2. Note the timestamp where it appears
    3. Categorize the type of claim (statistical, historical, scientific, political, etc.)
    4. Rate the "controversy score" on a scale of 1-5:
       - 5: Highly controversial, directly contradicts established consensus
       - 4: Significantly surprising or questionable given available evidence
       - 3: Somewhat misleading or lacking important context
       - 2: Slightly oversimplified but not entirely wrong
       - 1: Potentially misleading framing of otherwise accurate information
    5. Rate the "internet searchability" on a scale of 1-5:
       - 5: Abundant information available online to verify/reject the claim
       - 4: Significant information available from multiple reliable sources
       - 3: Moderate amount of information available with some research
       - 2: Limited information available, requiring deep research
       - 1: Very little information available online about this specific claim
    6. Provide 2-4 sentences of surrounding context elaborating on the claim and the context in which it is made.
    7. provide an internet search query that can be used to verify the claim.
    
    IGNORE general factual statements that are likely true and non-controversial.
    IGNORE opinions, hypotheticals, or personal preferences.
    
    Format your response as a JSON array of objects with these fields:
    - claim: The controversial/questionable claim text
    - timestamp: The timestamp from the transcript
    - category: Type of claim
    - controversy_score: Numeric rating (1-5)
    - internet_searchability: Numeric rating (1-5)
    - context: Surrounding text
    - internet_search_query: internet search query that can be used to verify the claim.    
    
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
        Claim: {claimContent["claim"]}
        Context: {claimContent["context"]}
        Search query: {claimContent["internet_search_query"]}

    """
    

    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "model": "sonar",
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
        "max_tokens": 250,
        "temperature": 0.2,
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
