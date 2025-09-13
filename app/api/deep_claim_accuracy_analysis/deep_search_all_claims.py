import logging
from typing import Dict, Any
from ..agent import execute_web_search
from app.config import get_settings

async def deep_search_all_claims(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform deep web search for each claim and add results to claim data.
    Returns the modified data with search results added to each claim.
    """
    logging.info(f"Starting deep search for {data.get('claim_count', 0)} claims")

    settings = get_settings()
    video_data = data.get('video_data', {})
    claims = data.get('claims', [])
    total_deep_search_cost = 0.0

    async def _search_single_claim(i: int, claim: dict):
        """Search a single claim asynchronously."""
        try:
            logging.info(f"Searching claim {i+1}/{len(claims)}: {claim.get('claim', '')[:50]}...")

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
            logging.info(f"Search result cost for claim {i+1}: ${claim_cost}")

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
            logging.info(f"Successfully added filtered search results to claim {i+1}")
            return claim_cost

        except Exception as e:
            logging.error(f"Error searching claim {i+1}: {str(e)}")
            claim['deep_search_result'] = {
                'error': str(e),
                'status': 'failed'
            }
            return 0

    # Create tasks for all claims and run them concurrently
    import asyncio
    tasks = [_search_single_claim(i, claim) for i, claim in enumerate(claims)]
    costs = await asyncio.gather(*tasks)
    total_deep_search_cost = sum(costs)

    logging.info(f"Completed deep search for all claims. Total cost: ${total_deep_search_cost:.4f}")
    return data

async def get_accuracy_score(data: Dict[str, Any]):
    """
    Analyze all claims and their deep search results to calculate accuracy scores.
    """
    from ..agent import call_gemini_agent

    logging.info(f"Calculating accuracy scores for {len(data.get('claims', []))} claims")

    claims = data.get('claims', [])

    for i, claim in enumerate(claims):
        deep_search = claim.get('deep_search_result', {})

        if 'error' not in deep_search:
            # Create generic prompt for accuracy scoring
            prompt = f"""
            Create accuracy score for the following claim and analysis based on the search result from verifiable sources.

            TITLE: {claim.get('title', '')}
            CLAIM: {claim.get('claim', '')}
            CONTEXT: {claim.get('context', '')}
            
            SEARCH RESULT: {deep_search.get('message', '')}

            Provide an accuracy score 0-100. 0 being the lowest accuracy and 100 being the highest accuracy.
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
                claim['accuracy_score_result'] = response
                logging.info(f"Generated accuracy score for claim {i+1}")
            except Exception as e:
                logging.error(f"Error generating accuracy score for claim {i+1}: {str(e)}")
                claim['accuracy_score_result'] = f"Error: {str(e)}"

    logging.info("Completed accuracy scoring for all claims")