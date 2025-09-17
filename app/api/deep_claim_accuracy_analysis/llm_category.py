import logging
import json
from ..agent import call_gemini_agent

async def category_label_generation_1(data):
    """
    Generate category labels using LLM.
    """
    categories = {}
    
    #logging.info(f"Generating category:{data}")

    for cluster_id, claims in data.items():
        # Skip noise cluster
        logging.info(f"Generating category:{cluster_id}")
        if str(cluster_id) == "-1" or cluster_id == -1:
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

    for cluster_id, claims in data.items():
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

def category_noise_assignment_1(data):
    """
    Assign categories to noise clusters using LLM.
    """
    pass