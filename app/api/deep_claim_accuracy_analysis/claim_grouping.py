import logging
import asyncio
from ..embedding_service import EmbeddingService

#Embedding based clustering
async def claim_clustering_1(data):
    """
    First claim clustering function.
    """
    logging.info("Executing claim_clustering_1")

    embedding_service = EmbeddingService()

    flattened_claims = []
    claim_texts = []

    for claim in data.get("claims", []):
        claim_embedding_text = f'''
            Title: {claim["title"]}
            Claim: {claim["claim"]}
            Context: {claim["context"]}
            Search Query: {claim["search_query"]}
            '''

        flattened_claims.append({
            "id": claim["id"],
            "claim_embedding_text": claim_embedding_text
        })
        claim_texts.append(claim_embedding_text)

    # Get embeddings for all claim texts
    embeddings = await embedding_service.embed_texts(claim_texts)

    # Replace claim_embedding_text with actual embedding values
    for i, claim in enumerate(flattened_claims):
        claim["claim_embedding"] = embeddings[i]
        del claim["claim_embedding_text"]  # Remove the text version

    for i, claim in enumerate(flattened_claims):
        logging.info(f"Claim {claim['id']}: embedding value (first 50 chars) = {str(claim['claim_embedding'])[:50]}")
        logging.info("--------------------------------")
    
    # Placeholder clustering logic
    # result = {
    #     "method": "clustering_1",
    #     "processed_claims": len(data.get("claims", [])) if isinstance(data, dict) else 0,
    #     "status": "completed"
    # }

    #logging.info(f"claim_clustering_1 results: {result}")
    return flattened_claims

#LLM based clustering
def claim_clustering_2(data):
    """
    Second claim clustering function.
    """
    logging.info("Executing claim_clustering_2")

    # Placeholder clustering logic
    result = {
        "method": "clustering_2",
        "processed_claims": len(data.get("claims", [])) if isinstance(data, dict) else 0,
        "status": "completed"
    }

    logging.info(f"claim_clustering_2 results: {result}")
    return result