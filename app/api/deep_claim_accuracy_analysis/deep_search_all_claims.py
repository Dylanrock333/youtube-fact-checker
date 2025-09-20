import logging
import json
from typing import Dict, Any
from ..agent import execute_web_search, call_gemini_agent
from app.config import get_settings
import asyncio

async def deep_search_all_claims(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform deep web search for each claim and add results to claim data.
    Returns the modified data with search results added to each claim.
    """
    # Deep search all claims (after clustering)
    deep_search_result = await deep_search_each_claim(data)

    return deep_search_result


    # Calculate accuracy scores for all claims
    accuracy_score_result = await get_accuracy_score(deep_search_result)
    
    return accuracy_score_result

async def deep_search_each_claim(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform deep web search for each claim and add results to claim data.
    Returns the modified data with search results added to each claim.
    """
    logging.info(f"Starting deep search for {data.get('claim_count', 0)} claims")


    


    settings = get_settings()
    video_data = data.get('video_data', {})
    total_deep_search_cost = 0.0

    async def _search_single_claim(category_key: str, claim_index: int, claim: dict, total_claims: int, current_claim_num: int):
        """Search a single claim asynchronously."""
        try:
            logging.info(f"Searching claim {current_claim_num}/{total_claims}: {claim.get('claim', '')[:50]}...")

            # Perform web search for this claim
            search_result = await execute_web_search(
                perplexity_api_key=settings.perplexity_api_key,
                claim_text=claim.get('claim', ''),
                context=claim.get('context', ''),
                video_data=video_data,
                query=claim.get('search_query', ''),
            )

            #logging.info(f"Search result: {search_result}")
            claim_cost = search_result.get('usage', {}).get('cost', {}).get('total_cost', 0)
            logging.info(f"Search result cost for claim {current_claim_num}: ${claim_cost}")

            # Extract only the required fields from search result
            # Get the message content from choices
            message_content = ""
            choices = search_result.get("choices", [])
            if choices and len(choices) > 0:
                message_content = choices[0].get("message", {}).get("content", "")

            filtered_result = {
                "citations": search_result.get("citations", []),
                "search_results": search_result.get("search_results", []),
                "message": message_content
            }
            
            claim['deep_search_result'] = filtered_result
            
            claim['accuracy_score_result'] = await get_accuracy_score(claim)
            
            logging.info(f"Successfully added filtered search results to claim {current_claim_num}")
            return claim_cost

        except Exception as e:
            logging.error(f"Error searching claim {current_claim_num}: {str(e)}")
            claim['deep_search_result'] = {
                'error': str(e),
                'status': 'failed'
            }
            return 0

    # Create tasks for all claims across all categories
    tasks = []
    current_claim_num = 0

    # Iterate through numbered keys only (ignore video_data, videoID, claim_count)
    numeric_keys = [key for key in data.keys() if str(key).isdigit()]
    for key in sorted(numeric_keys, key=int):
        category = data[key]
        claims = category.get('claims', [])

        for claim_index, claim in enumerate(claims):
            current_claim_num += 1
            task = _search_single_claim(key, claim_index, claim, data.get('claim_count', 0), current_claim_num)
            tasks.append(task)

    costs = await asyncio.gather(*tasks)
    total_deep_search_cost = sum(costs)

    logging.info(f"Completed deep search for all claims. Total cost: ${total_deep_search_cost:.4f}")
    return data

async def get_accuracy_score(claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze all claims and their deep search results to calculate accuracy scores.
    Returns simplified data with only id, deep_search_result, and accuracy_score_result.
    """

    deep_search = claim.get("deep_search_result", {})

    # Create generic prompt for accuracy scoring
    prompt = f"""
    You are given a claim form a video. This claim is combined with the context and a short title.
    You are given a search result which is a summary of an investigation into the claim using verifiable sources.

    Your task is to evaluate how accurate the claim is based on the provided evidence.
        - Compare the claim directly to the evidence.
        - If the evidence fully supports the claim, score it as highly accurate.
        - If the evidence partially supports it, give a moderate score.
        - If the evidence contradicts or provides no support, give a low score.

    TITLE: {claim.get('title', '')}
    CLAIM: {claim.get('claim', '')}
    CONTEXT: {claim.get('context', '')}

    SEARCH RESULT: {deep_search.get('message', '')}

    Provide an accuracy score, an integer from 0 to 100, no rounding to multiples of 5 or 10.
    """

    try:
        # Define schema for accuracy score response
        accuracy_schema = {
            "type": "object",
            "properties": {
                "accuracy_score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100
                }
            },
            "required": ["accuracy_score"]
        }

        response = await call_gemini_agent(prompt, "gemini-2.5-flash-lite", accuracy_schema)

        # Parse the JSON response if it's a string
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON response for claim {claim.get('id')}: {response}")
                response = {"accuracy_score": 0}

        return response
    except Exception as e:
        logging.error(f"Error generating accuracy score for claim {claim.get('id')}: {str(e)}")
        return f"Error: {str(e)}"
