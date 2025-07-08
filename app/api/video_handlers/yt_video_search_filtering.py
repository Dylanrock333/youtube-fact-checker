import logging
from app.api.agent import call_gemini_agent, filter_and_clean_claims_agent
from app.api.claim_analysis.claim_extraction import process_video_claims_stream

async def classify_video_agent(config):
    
    logging.info(f"number of videos: {len(config['videos'])}")
    
    list_of_videos = []
    for video in config["videos"]:
         logging.info(f"Video: {video['title']}")
         # Get first 150 words of description
         description_words = video["description"].split()[:150]
         description_truncated = " ".join(description_words)
         
         list_of_videos.append(
             {
                "title": video["title"],
                "description": description_truncated,
                "videoId": video["videoId"],
                "channelTitle": video["channelTitle"],
                "publishedAt": video["publishedAt"],
                "channel_subscriber_count": video["channel_subscriber_count"],
                "tags": video["tags"],
                "duration": video["duration"],
                "view_count": video["view_count"],
            }
        )
         
   # Prompt to guide the LLM
    final_prompt = """
You are a content classifier helping curate videos for an app that extracts factual claims and assertions from YouTube videos.

Given the metadata of each video, decide if it is suitable for inclusion in a claim-extraction app. If it is, classify it into one of the following categories:

- "educational": Videos that explain scientific, technical, or academic topics (e.g., how things work, breakdowns, theories).
- "podcasts": Long-form interviews or discussions, typically from recurring podcast hosts.
- "news_and_politics": Content about elections, political analysis, government, or geopolitical current events.
- "history_and_society": Videos about past events, civilizations, historical analysis, or social structures.
- "economy_and_finance": Topics covering money, investing, economics, markets, inflation, etc.
- "none": If the video is not relevant (e.g., music, entertainment, prank, unstructured livestreams), classify it as "none".

Only use one category per video. If it does not belong anywhere, mark it as "none".

Each input includes:
- title
- description (first 150 words)
- tags (list of relevant words or phrases)
- view_count
- duration
- channel_subscriber_count
- channelTitle
- publishedAt

Respond only with a JSON array where each element has:
- "videoId": the ID from the input
- "category": the appropriate category or "none"
"""

    response_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "videoId": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": [
                        "educational",
                        "podcasts",
                        "news_and_politics",
                        "history_and_society",
                        "economy_and_finance",
                        "none"
                    ]
                }
            },
            "required": ["videoId", "category"]
        }
    }

    # Split videos into chunks of 10 or fewer
    def chunk_videos(videos, chunk_size=10):
        """Split videos into chunks of specified size."""
        for i in range(0, len(videos), chunk_size):
            yield videos[i:i + chunk_size]
    
    # Process each chunk and concatenate results
    all_results = []
    video_chunks = list(chunk_videos(list_of_videos, 10))
    
    logging.info(f"Processing {len(video_chunks)} chunks of videos")
    
    for i, chunk in enumerate(video_chunks):
        logging.info(f"Processing chunk {i+1}/{len(video_chunks)} with {len(chunk)} videos")
        
        # Send to LLM with structured schema enforcement
        chunk_result = call_gemini_agent(
            prompt=final_prompt,
            inputs={"videos": chunk},
            schema=response_schema
        )
        
        # Concatenate results
        if isinstance(chunk_result, list):
            all_results.extend(chunk_result)
        else:
            logging.warning(f"Unexpected result type from chunk {i+1}: {type(chunk_result)}")
    
    logging.info(f"Total results: {len(all_results)}")
    
    # Organize videos by category and remove those classified as 'none'
    classified_videos = classify_videos(all_results, list_of_videos)
    
    
    n_videos_per_category = 8 # Important var 
    
    for category, videos in classified_videos.items():
        videos.sort(key=lambda x: x["view_count"], reverse=True)
        classified_videos[category] = videos[:n_videos_per_category]

    video_claims_classified = {
        "educational": [],
        "podcasts": [],
        "news_and_politics": [],
        "history_and_society": [],
        "economy_and_finance": []
    }
    # Process claims for videos in each category
    for category, videos in classified_videos.items():
        logging.info(f"Processing {len(videos)} videos in category: {category}")
        for video in videos:
            try:
                # Consume the async generator to get the final result
                final_result = None
                async for update in process_video_claims_stream(video["videoId"], "youtube", "en"):
                    if update.get("status") == "complete":
                        final_result = update
                        break
                
                if final_result:
                    logging.info(f"Processed claims for video {video['videoId']} in category {category}")
                    video_claims_classified[category].append(final_result)
                else:
                    logging.warning(f"No final result received for video {video['videoId']}")
                    
            except Exception as e:
                logging.error(f"Error processing claims for video {video['videoId']}: {e}")
    
    return video_claims_classified



def classify_videos(all_results, list_of_videos):
    """
    Organize videos by their classification categories and remove videos classified as 'none'.
    
    Args:
        all_results: List of classification results with videoId and category
        list_of_videos: Original list of video objects
    
    Returns:
        Dictionary with categories as keys and lists of videos as values
    """
    # Create a mapping of videoId to video object for quick lookup
    video_lookup = {video["videoId"]: video for video in list_of_videos}
    
    # Initialize the categorized structure
    categorized_videos = {
        "educational": [],
        "podcasts": [],
        "news_and_politics": [],
        "history_and_society": [],
        "economy_and_finance": []
    }
    
    # Count statistics
    total_videos = len(all_results)
    removed_videos = 0
    
    # Process each classification result
    for result in all_results:
        video_id = result["videoId"]
        category = result["category"]
        
        # Skip videos classified as "none"
        if category == "none":
            removed_videos += 1
            logging.info(f"Removing video {video_id} (classified as 'none')")
            continue
        
        # Find the corresponding video object
        if video_id in video_lookup:
            video = video_lookup[video_id]
            # Add category to the video object
            video["classification_category"] = category
            # Add to the appropriate category
            categorized_videos[category].append(video)
        else:
            logging.warning(f"Video {video_id} not found in original video list")
    
    # Log statistics
    kept_videos = total_videos - removed_videos
    logging.info(f"Classification summary:")
    logging.info(f"  Total videos processed: {total_videos}")
    logging.info(f"  Videos removed (none): {removed_videos}")
    logging.info(f"  Videos kept: {kept_videos}")
    
    for category, videos in categorized_videos.items():
        if videos:
            logging.info(f"  {category}: {len(videos)} videos")
    
    return categorized_videos

async def get_final_front_page_videos(classified_videos):
    final_front_page_videos = {
        "educational": [],
        "podcasts": [],
        "news_and_politics": [],
        "history_and_society": [],
        "economy_and_finance": []
    }
    logging.info(f"Getting cleaning and filtering front page videos for {len(classified_videos)} categories")
    for category, videos in classified_videos.items():
        logging.info(f"Processing {len(videos)} videos in category: {category}")
        for video in videos:
            print(video['data']['video_data']['title'])
            print(len(video['data']['claims']))
            
            claim_list = video['data']['claims']
            final_claim_list = filter_and_clean_claims_agent(claim_list, video['data']['video_data'], video['data']['videoID'])
            try:
                final_front_page_videos[category].append(final_claim_list)
                    
            except Exception as e:
                logging.error(f"Error processing claims for video {video}: {e}")
    return final_front_page_videos