import logging
import asyncio
import numpy as np
import hdbscan
from collections import defaultdict
from ..embedding_service import EmbeddingService
from .llm_category import category_label_generation_1, category_noise_assignment_1, sort_claims_by_timestamp

#Embedding based clustering
async def claim_clustering_1(data):
    """
    First claim clustering function.
    """
    logging.info("Executing claim_clustering_1")
    
    claim_length = len(data.get("claims", []))
    claim_list = data.get("claims", [])

    embedding_service = EmbeddingService()

    flattened_claims = []
    claim_texts = []

    #Flatten the claims to a list of strings
    for claim in claim_list:
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

    # for i, claim in enumerate(flattened_claims):
    #     logging.info(f"Claim {claim['id']}: embedding value (first 50 chars) = {str(claim['claim_embedding'])[:50]}")
    #     logging.info("--------------------------------")

    # HDBSCAN Clustering
    if len(flattened_claims) < 2:
        # If we have less than 2 claims, put them all in cluster 0
        cluster_groups = {0: [claim["id"] for claim in flattened_claims]}
        logging.info("Less than 2 claims, no clustering performed")
    else:
        # Convert embeddings to numpy array
        embedding_matrix = np.array([claim["claim_embedding"] for claim in flattened_claims])

        # Normalize embeddings for cosine similarity (use L2 norm then euclidean = cosine)
        from sklearn.preprocessing import normalize
        embedding_matrix = normalize(embedding_matrix, norm='l2')

        if claim_length <= 10:
            min_cluster_size = 2
        elif claim_length <= 50:
            min_cluster_size = max(3, int(claim_length * 0.05))   # 5% of claims
        elif claim_length <= 200:
            min_cluster_size = max(5, int(claim_length * 0.03))   # 3% of claims
        else:
            min_cluster_size = max(10, int(claim_length * 0.02))  # 2% of claims
    
        # Perform HDBSCAN clustering
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=1,
            # random_state=42,
            metric='euclidean'
        )
        cluster_labels = clusterer.fit_predict(embedding_matrix)

        # Group claims by cluster ID
        cluster_groups = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            claim_id = flattened_claims[i]["id"]
            cluster_groups[int(label)].append(claim_id)

        # Convert defaultdict to regular dict and ensure it's in the requested format
        cluster_groups = dict(cluster_groups)

        logging.info(f"HDBSCAN clustering completed. Found {len(cluster_groups)} clusters")
        for cluster_id, claim_ids in cluster_groups.items():
            if cluster_id == -1:
                logging.info(f"Noise cluster: {claim_ids}")
            else:
                logging.info(f"Cluster {cluster_id}: {claim_ids}")

    # Create clustered claims structure with full claim objects
    clustered_claims = {}

    # Create a mapping from claim ID to full claim object for quick lookup
    claim_id_to_claim = {claim["id"]: claim for claim in claim_list}

    # For each cluster, get the full claim objects
    for cluster_id, claim_ids in cluster_groups.items():
        clustered_claims[cluster_id] = []
        for claim_id in claim_ids:
            if claim_id in claim_id_to_claim:
                clustered_claims[cluster_id].append(claim_id_to_claim[claim_id])

    # Preserve the original data structure and add clustered claims
    result = {
        "video_data": data.get("video_data"),
        "videoID": data.get("videoID"),
        "claim_count": data.get("claim_count"),
        **clustered_claims  # Merge clustered claims as top-level keys
    }

    return result

async def claim_grouping_1(data):
        #Clustering claims
    clustering_result_1 = await claim_clustering_1(data)

    #Category label generation
    labeled_result = await category_label_generation_1(clustering_result_1)

    #Category noise assignment
    if "-1" in labeled_result or -1 in labeled_result:
        logging.info("Found -1 category, running category noise assignment")
        assigned_result = await category_noise_assignment_1(labeled_result)
    else:
        logging.info("No -1 category found, skipping category noise assignment")
        assigned_result = labeled_result

    # Sort claims by timestamp within each category
    video_clustered_result = sort_claims_by_timestamp(assigned_result)
    
    return video_clustered_result

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