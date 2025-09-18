import logging
import json
from ..agent import call_gemini_agent

async def category_label_generation_1(data):
    """
    Generate category labels using LLM.
    """
    categories = {}
    
    #logging.info(f"Generating category:{data}")

    # Define metadata fields to skip
    metadata_fields = ["video_data", "videoID", "claim_count"]

    for cluster_id, claims in data.items():
        # Skip metadata fields and noise cluster
        logging.info(f"Generating category:{cluster_id}")
        if cluster_id in metadata_fields or str(cluster_id) == "-1" or cluster_id == -1:
            continue

        # Extract titles and contexts
        formatted_content = ""
        for claim in claims:
            formatted_content += f"{claim['title']}\n{claim['context']}\n\n"

        # Create prompt for Gemini
        prompt = f"""Create a single descriptive title (less than 10 words) and summary (less than 70 words) for these related claims from a YouTube video analysis.

            Claims content:
            {formatted_content.strip()}

            Analyze the common themes, topics, and contexts across these claims to generate:
            1. A concise, descriptive title that captures the main subject matter
            2. A detailed summary explaining what these claims collectively discuss and their shared context

            Respond in this exact JSON format:
            {{"category_title": "...", "category_summary": "..."}}
        """

        # Call Gemini agent
        response = await call_gemini_agent(
            prompt,
            model="gemini-2.5-flash-lite",
            schema={
                "type": "object",
                "properties": {
                    "category_title": {"type": "string"},
                    "category_summary": {"type": "string"}
                },
                "required": ["category_title", "category_summary"]
            }
        )

        # Parse response and store
        if isinstance(response, str):
            try:
                categories[cluster_id] = json.loads(response)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON response for cluster {cluster_id}: {response}")
                categories[cluster_id] = {"category_title": "Unknown Category", "category_summary": "Failed to generate summary"}
        else:
            categories[cluster_id] = response

    # Now restructure the data to include category info
    enhanced_data = {}

    # Preserve metadata fields (non-cluster data)
    metadata_fields = ["video_data", "videoID", "claim_count"]
    for field in metadata_fields:
        if field in data:
            enhanced_data[field] = data[field]

    for cluster_id, claims in data.items():
        # Skip metadata fields when processing clusters
        if cluster_id in metadata_fields:
            continue

        cluster_data = {
            "claims": claims
        }

        # Add category info if available (skip -1 noise cluster)
        if cluster_id in categories:
            cluster_data["category_title"] = categories[cluster_id]["category_title"]
            cluster_data["category_summary"] = categories[cluster_id]["category_summary"]

        enhanced_data[cluster_id] = cluster_data

    logging.info(f"Generated category labels for {len(categories)} clusters")
    return enhanced_data

async def category_noise_assignment_1(data):
    """
    Assign categories to noise clusters using LLM.
    """
    #logging.info(f"Starting category noise assignment with data keys: {list(data.keys())}")

    # Create video_categories string with all category data
    video_categories = ""
    metadata_fields = ["video_data", "videoID", "claim_count"]

    for category_id, category_data in data.items():
        # Skip metadata fields, noise cluster, and ensure category_data is a dict with category_title
        if (category_id in metadata_fields or
            str(category_id) == "-1" or
            not isinstance(category_data, dict) or
            "category_title" not in category_data):
            continue

        video_categories += f'Category ID: "{category_id}":\n'
        video_categories += f'Title: {category_data["category_title"]}\n'
        video_categories += f'Summary: {category_data["category_summary"]}\n\n'

    logging.info(f"Generated video_categories string length: {len(video_categories)}")

    # Get unmatched claims from "-1" category (check both string and integer keys)
    unmatched_claims_list = data.get("-1", {}).get("claims", []) or data.get(-1, {}).get("claims", [])
    logging.info(f"Found {len(unmatched_claims_list)} unmatched claims in '-1' category")

    results = {}

    # Check if there are any unmatched claims to process
    if not unmatched_claims_list:
        logging.info("No unmatched claims found, returning empty results")
        return results

    # Process unmatched claims in groups of max 5
    for i in range(0, len(unmatched_claims_list), 5):
        batch_claims = unmatched_claims_list[i:i+5]
        logging.info(f"Processing batch {i//5 + 1} with {len(batch_claims)} claims")

        # Format unmatched_claims string for current batch
        unmatched_claims = ""
        for claim in batch_claims:
            unmatched_claims += f'Claim ID: {claim["id"]}\n'
            unmatched_claims += f'Claim Title: "{claim["title"]}"\n'
            unmatched_claims += f'Claim Context: "{claim["context"]}"\n'
            unmatched_claims += f'Claim Search Query: "{claim["search_query"]}"\n\n'

        # Create prompt for Gemini
        prompt = f"""I have a list of unmatched claims that need to be matched to a specific category.
I need you to evaluate the claim and find the best matching category by category ID using the claim data and finding its closest matching category using the category title and summary

These are the claims that need to be matched:
{unmatched_claims}

and these are the categories that you need to match to:
{video_categories}

your output should look like this
{{
    "[Category ID]": [
      [Claim_ID], [Claim_ID],...[Claim_ID]
    ],
    "[Category_ID]": [
      [Claim_ID], [Claim_ID],...[Claim_ID]
    ],
  ...
}}

there should only be numbers only. make sure its formatted in this JSON format"""

        # Call Gemini agent without schema validation (Gemini will return free-form JSON)
        response = await call_gemini_agent(
            prompt,
            model="gemini-2.5-flash-lite"
        )
        
        #logging.info(f"Batch {i//5 + 1} response: {response}")

        # Parse response and merge with results
        if isinstance(response, str):
            try:
                # Extract JSON from markdown code blocks if present
                response_text = response.strip()
                if "```json" in response_text:
                    # Find the JSON content between ```json and ```
                    start_idx = response_text.find("```json") + 7
                    end_idx = response_text.find("```", start_idx)
                    if end_idx != -1:
                        response_text = response_text[start_idx:end_idx].strip()
                    else:
                        # If no closing ```, try to extract everything after ```json
                        response_text = response_text[start_idx:].strip()

                # Additional cleanup: remove any trailing incomplete content
                # Look for the last complete JSON object
                if response_text.count('{') > response_text.count('}'):
                    # Find the last complete closing brace
                    last_brace = response_text.rfind('}')
                    if last_brace != -1:
                        response_text = response_text[:last_brace + 1]

                batch_results = json.loads(response_text)
                logging.info(f"Batch {i//5 + 1} results: {batch_results}")
                # Validate and process results
                for category_id, claim_ids in batch_results.items():
                    # Ensure category_id is a string representing a number
                    if not str(category_id).isdigit():
                        logging.warning(f"Invalid category ID '{category_id}' in batch {i//5 + 1}, skipping")
                        continue
                    # Ensure claim_ids is a list of integers
                    if not isinstance(claim_ids, list) or not all(isinstance(id, int) for id in claim_ids):
                        logging.warning(f"Invalid claim IDs format for category '{category_id}' in batch {i//5 + 1}, skipping")
                        continue

                    if category_id not in results:
                        results[category_id] = []
                    results[category_id].extend(claim_ids)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON response for batch {i//5 + 1}: {response}")
        else:
            logging.info(f"Batch {i//5 + 1} results: {response}")
            # Validate and process results
            for category_id, claim_ids in response.items():
                # Ensure category_id is a string representing a number
                if not str(category_id).isdigit():
                    logging.warning(f"Invalid category ID '{category_id}' in batch {i//5 + 1}, skipping")
                    continue
                # Ensure claim_ids is a list of integers
                if not isinstance(claim_ids, list) or not all(isinstance(id, int) for id in claim_ids):
                    logging.warning(f"Invalid claim IDs format for category '{category_id}' in batch {i//5 + 1}, skipping")
                    continue

                if category_id not in results:
                    results[category_id] = []
                results[category_id].extend(claim_ids)

    logging.info(f"Final category assignment results: {results}")

    # Now move claims from "-1" category to their assigned categories based on results
    if results:
        # Get the noise claims (check both string and integer keys)
        noise_claims = data.get("-1", {}).get("claims", []) or data.get(-1, {}).get("claims", [])

        # Create a mapping of claim_id to claim object for faster lookup
        claim_lookup = {claim["id"]: claim for claim in noise_claims}

        # Move claims to their assigned categories
        for category_id, claim_ids in results.items():
            category_key = str(category_id)

            # Ensure the target category exists in data
            if category_key in data:
                # Add the reassigned claims to the target category
                for claim_id in claim_ids:
                    if claim_id in claim_lookup:
                        data[category_key]["claims"].append(claim_lookup[claim_id])
                        logging.info(f"Moved claim {claim_id} to category {category_key}")

        # Remove the "-1" noise category after moving claims
        if "-1" in data:
            del data["-1"]
            logging.info("Removed '-1' noise category after claim reassignment")
        if -1 in data:
            del data[-1]
            logging.info("Removed -1 noise category after claim reassignment")

    return data

def sort_claims_by_timestamp(data):
    """
    Sort claims by timestamp within each category.
    """
    def parse_timestamp(timestamp_str):
        """Convert timestamp string like '4:51.4' to total seconds for sorting."""
        try:
            parts = timestamp_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            return 0
        except (ValueError, IndexError):
            logging.warning(f"Could not parse timestamp: {timestamp_str}")
            return 0

    metadata_fields = ["video_data", "videoID", "claim_count"]

    for category_id, category_data in data.items():
        # Skip metadata fields and ensure category_data is a dict with claims
        if (category_id in metadata_fields or
            not isinstance(category_data, dict) or
            "claims" not in category_data or
            not isinstance(category_data["claims"], list)):
            continue

        # Sort claims by timestamp
        category_data["claims"].sort(key=lambda claim: parse_timestamp(claim.get("timestamp", "0:0.0")))
        logging.info(f"Sorted {len(category_data['claims'])} claims by timestamp in category {category_id}")

    return data