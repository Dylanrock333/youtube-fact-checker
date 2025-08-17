import requests
from datetime import datetime, timedelta
from app.config import get_settings
import logging
import json
import re
import random
from pathlib import Path
import asyncio
from app.api.video_handlers.yt_handler import get_yt_video_info
import googleapiclient.discovery

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"

settings = get_settings()
google_yt_api_key = settings.google_yt_api_key

def remove_duplicate_videos_by_id(videos):
    """
    Remove duplicate videos based on videoId, keeping the first occurrence.
    
    Args:
        videos (list): List of video dictionaries
        
    Returns:
        list: List of videos with duplicates removed
    """
    seen_video_ids = set()
    unique_videos = []
    
    for video in videos:
        video_id = video.get("videoId")
        if video_id and video_id not in seen_video_ids:
            seen_video_ids.add(video_id)
            unique_videos.append(video)
    
    return unique_videos

async def get_all_youtube_videos(config_path: str):
    """
    Calls the full video collection process and returns cleaned video data.

    Args:
        config_path (str): Path to the JSON config.
        n_random_queries (int): Number of random queries to select from each category (default: 2).

    Returns:
        list: List of cleaned video dictionaries with core metadata.
    """
    n_random_queries = 2 #number of random queries to select from each category from video_queries.json
    raw_results = await collect_all_videos_from_config(config_path, n_random_queries)

    # Filter videos for quality
    quality_videos = [video for video in raw_results if is_quality_video(video)]
    removed_count = len(raw_results) - len(quality_videos)
    logging.info(f"Removed {removed_count} videos due to quality filters")

    # Remove videos duplicates by videoID
    unique_videos = remove_duplicate_videos_by_id(quality_videos)
    duplicate_count = len(quality_videos) - len(unique_videos)
    logging.info(f"Removed {duplicate_count} duplicate videos by videoId")
    
    # Extract only important fields
    cleaned_videos = []
    for video in unique_videos:
        cleaned = {
            "videoId": video.get("videoId"),
            "title": video.get("title"),
            "description": video.get("description"),
            "channelTitle": video.get("channelTitle"),
            "publishedAt": video.get("publishedAt"),
            "category": video.get("category"),
            "original_query": video.get("original_query"),
            "view_count": video.get("view_count"),
            "duration": video.get("duration"),
            "tags": video.get("tags", []),
            "thumbnail": video.get("thumbnail"),
            "channel_subscriber_count": video.get("channel_subscriber_count")
        }
        cleaned_videos.append(cleaned)

    return cleaned_videos


def fetch_videos(query: str):
    """
    Fetch YouTube videos based on the query using recommended settings.
    
    Args:
        query (str): The search term.
    
    Returns:
        list: List of video metadata dictionaries.
    """
    max_results = 50
    
    logging.info(f"Fetching videos for query: '{query}', max_results: {max_results}")
    
    # Check if API key is available
    if not settings.google_yt_api_key:
        logging.error("YouTube API key is not configured")
        raise Exception("YouTube API key is not configured")

    # Recommended single configuration for quality results
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": "relevance",
        "relevanceLanguage": "en",
        "videoDefinition": "high",   # HD videos only
        "regionCode": "US",          # Consistent region for relevance
        "key": settings.google_yt_api_key
    }

    logging.info("Fetching videos (order by relevance, published within last 90 days)")
    logging.info(f"Making request to YouTube API: {YOUTUBE_API_URL}")
    logging.info(f"Request parameters: {dict(params, key='[HIDDEN]')}")  # Hide the API key in logs

    try:
        response = requests.get(YOUTUBE_API_URL, params=params, timeout=30)
        logging.info(f"YouTube API response status: {response.status_code}")
        
    except requests.exceptions.Timeout:
        logging.error("YouTube API request timed out")
        raise Exception("YouTube API request timed out")
    except requests.exceptions.RequestException as e:
        logging.error(f"YouTube API request failed: {e}")
        raise Exception(f"YouTube API request failed: {e}")

    if response.status_code != 200:
        logging.error(f"YouTube API error: {response.status_code} - {response.text}")
        raise Exception(f"Error fetching YouTube videos: {response.status_code} - {response.text}")

    try:
        response_data = response.json()
        items = response_data.get("items", [])
        logging.info(f"Successfully retrieved {len(items)} videos from YouTube API")
        
        if not items:
            logging.warning("No videos found for the given query")
            return []
        
    except ValueError as e:
        logging.error(f"Failed to parse YouTube API response as JSON: {e}")
        raise Exception(f"Failed to parse YouTube API response: {e}")
    
    videos = [
        {
            "videoId": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channelTitle": item["snippet"]["channelTitle"],
            "publishedAt": item["snippet"]["publishedAt"],
            "description": item["snippet"]["description"]
        }
        for item in items
    ]
    
    logging.info(f"Formatted {len(videos)} video objects")
    return videos


async def collect_all_videos_from_config(config_path: str, n_random_queries: int = 2):
    """
    Loads a JSON config and fetches YouTube videos for randomly selected queries from each category.
    
    Args:
        config_path (str): Path to the JSON config file.
        n_random_queries (int): Number of random queries to select from each category (default: 2).
    
    Returns:
        list: All video results with added category and original_query.
    """
    all_results = []

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        raise Exception(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in config file: {e}")
        raise Exception(f"Invalid JSON in config file: {e}")

    logging.info(f"Loading video queries from config: {config_path}")

    for category, queries in config.items():
        # Randomly select n_random_queries from this category
        if len(queries) <= n_random_queries:
            selected_queries = queries  # Use all queries if we have fewer than requested
            logging.info(f"Using all {len(queries)} queries for category '{category}' (requested {n_random_queries})")
        else:
            selected_queries = random.sample(queries, n_random_queries)
            logging.info(f"Randomly selected {n_random_queries} queries from {len(queries)} available for category '{category}'")
        
        # Process selected queries for this category
        for query in selected_queries:
            try:
                logging.info(f"Fetching videos for: [{category}] → '{query}'")
                videos = fetch_videos(query=query)
                
                # Enrich each video with detailed info before quality filtering
                enriched_videos = []
                for video in videos:
                    try:
                        # Get detailed video info (this is async, so we need to handle it)
                        video_info = await get_yt_video_info(video["videoId"])
                        if video_info and "error" not in video_info:
                            # Merge the additional video info into the base video data
                            video.update(video_info)
                        channel_info = get_yt_channel_info(video["channelId"])
                        video.update({"channel_subscriber_count": channel_info})
                        enriched_videos.append(video)
                        
                    except Exception as e:
                        logging.warning(f"Failed to get video info for {video.get('videoId', 'unknown')}: {e}")
                        enriched_videos.append(video)  # Keep the video even if we can't get extra info
                
                for video in enriched_videos:
                    video.update({
                        "category": category,
                        "original_query": query
                    })
                all_results.extend(enriched_videos)
            except Exception as e:
                logging.error(f"Failed query '{query}': {e}")

    logging.info(f"Collected total of {len(all_results)} videos from all queries")
    return all_results

def get_yt_channel_info(channel_id: str):
    """Get channel info for a given channel ID."""
    try:
        youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=google_yt_api_key)
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            id=channel_id
        )
        response = request.execute()
        subscriber_count = response['items'][0]['statistics']['subscriberCount']
        logging.info(f"Channel info response: {subscriber_count}")
        
        if not response['items']:
            logging.warning(f"No channel found for ID: {channel_id}")
            return None
        
        return subscriber_count
    
    except Exception as e:
        logging.error(f"Error fetching channel info for ID {channel_id}: {e}")
        return None

def parse_duration_to_minutes(duration_str):
    # Converts '4:05:16' → 245, '18:30' → 18
    parts = list(map(int, duration_str.split(":")))
    if len(parts) == 3:
        hours, minutes, _ = parts
        return hours * 60 + minutes
    elif len(parts) == 2:
        minutes, _ = parts
        return minutes
    return 0

def parse_int(value):
    # Safely parses int from string like "475,000"
    if not value or str(value).strip() == "":
        return 0
    cleaned = re.sub(r"[^\d]", "", str(value))
    return int(cleaned) if cleaned else 0

def is_recent(published_at_str, days=3):
    # Checks if the video was published within the last `days`
    published = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
    return datetime.utcnow() - published <= timedelta(days=days)

def is_quality_video(video):
    # --- Parse fields safely ---
    duration_minutes = parse_duration_to_minutes(video.get("duration", "0:00"))
    subscriber_count = parse_int(video.get("channel_subscriber_count", "0"))
    view_count = parse_int(video.get("view_count", "0"))
    like_count = parse_int(video.get("like_count", "0"))
    comment_count = parse_int(video.get("comment_count", "0"))
    title = video.get("title", "").lower()
    tags = [tag.lower() for tag in video.get("tags", [])]
    description = video.get("description", "")
    published_at = video.get("publishedAt", video.get("published_at", ""))
    channel_title = video.get("channelTitle", "")

    # --- Hard Filters ---
    if duration_minutes < 15:
        logging.info(f"Video {video.get('videoId')} rejected: duration {duration_minutes} minutes is less than 15 minutes")
        return False

    if subscriber_count < 20000:
        logging.info(f"Video {video.get('videoId')} rejected: subscriber count {subscriber_count} is less than 40,000")
        return False

    if view_count < 10000 and not is_recent(published_at):
        logging.info(f"Video {video.get('videoId')} rejected: view count {view_count} is less than 10,000 and not recent")
        return False

    if not description or len(description.strip()) < 15:
        logging.info(f"Video {video.get('videoId')} rejected: description is missing or too short")
        return False

    # # --- Enhanced Quality Indicators ---
    # # Check engagement ratio (likes per view)
    # if view_count > 0:
    #     like_ratio = like_count / view_count
    #     if like_ratio < 0.005:  # Less than 0.5% like ratio
    #         logging.info(f"Video {video.get('videoId')} rejected: low engagement ratio {like_ratio:.4f}")
    #         return False

    # # Check comment engagement
    # if view_count > 0:
    #     comment_ratio = comment_count / view_count
    #     if comment_ratio < 0.001:  # Less than 0.1% comment ratio
    #         logging.info(f"Video {video.get('videoId')} rejected: low comment engagement {comment_ratio:.4f}")
    #         return False

    return True
