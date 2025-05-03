from youtube_transcript_api import YouTubeTranscriptApi
from typing import Dict, Any, List
import googleapiclient.discovery
import httplib2
from app.config import get_settings
from youtube_transcript_api.proxies import WebshareProxyConfig
from dotenv import load_dotenv
import os
import logging
import random
load_dotenv()

settings = get_settings()
# Initialize ytt_api inside the function using settings
ytt_api = YouTubeTranscriptApi(
    proxy_config=WebshareProxyConfig(
        proxy_username=settings.webshare_username,
        proxy_password=settings.webshare_password,
    )
)

# Function to create a YouTube API client with proxy
def get_youtube_client(api_key):
    """Create a YouTube API client with proxy configuration."""
    settings = get_settings()
    
    # Set up proxy with authentication
    proxy_info = httplib2.ProxyInfo(
        proxy_type=httplib2.socks.PROXY_TYPE_HTTP,
        proxy_host=settings.webshare_proxy_host,  # You'll need to add this to your settings
        proxy_port=settings.webshare_proxy_port,  # You'll need to add this to your settings
        proxy_user=settings.webshare_username,
        proxy_pass=settings.webshare_password
    )
    
    # Create an HTTP object with the proxy
    http = httplib2.Http(proxy_info=proxy_info)
    
    # Build the YouTube client with the proxied HTTP object
    return googleapiclient.discovery.build(
        'youtube', 'v3', 
        developerKey=api_key,
        http=http
    )

def get_yt_transcript(video_id: str) -> List[Dict[str, Any]]: # Updated return type hint
    """Retrieve transcript with timestamps and title from a YouTube video."""
    try:
        logging.info(f"getting transcript for video id: {video_id}")
        raw_transcript = ytt_api.fetch(video_id)

        
        formatted_transcript = raw_transcript.to_raw_data()

        #TODO: Have a standart transcript format schema that is used for all video origins
        return formatted_transcript
    except Exception as e:
        logging.error(f"An error occurred while fetching/formatting transcript: {e}")
        return None
    
    
def get_yt_video_info(video_id):
    settings = get_settings()
    google_yt_api_key = settings.google_yt_api_key
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=google_yt_api_key)
    
    logging.info(f"getting video info for video id: {video_id}")
    
    try:
        video_response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        ).execute()
        
    except Exception as e:
        logging.error(f"API Error: {str(e)}")
        return {"error": str(e)}
    
    # Check if video exists
    if not video_response['items']:
        return {"error": "Video not found"}
    
    # Extract the video information
    video_data = video_response['items'][0]
    
    # Format duration (in ISO 8601 format, convert if needed)
    duration = video_data['contentDetails']['duration']
    
    # Create a clean JSON response
    youtube_video_info = {
        "id": video_id,
        "title": video_data['snippet']['title'],
        "description": video_data['snippet']['description'],
        "published_at": video_data['snippet']['publishedAt'],
        "channel_title": video_data['snippet']['channelTitle'],
        "channel_id": video_data['snippet']['channelId'],
        "duration": duration,
        "view_count": video_data['statistics'].get('viewCount', 0),
        "like_count": video_data['statistics'].get('likeCount', 0),
        "comment_count": video_data['statistics'].get('commentCount', 0),
        "thumbnails": video_data['snippet']['thumbnails'],
        "tags": video_data['snippet'].get('tags', [])
    }
    
    
    youtube_video_data = {
        "title": "Unknown title",
        "tags": [],
        "channel_title": "Unknown channel title",
        "view_count": 0,
        "published_at": "Unknown published at",
        "duration": "Unknown duration"
    }
    
    youtube_video_data["title"] = youtube_video_info.get("title")
    youtube_video_data["tags"] = youtube_video_info.get("tags")
    youtube_video_data["view_count"] = youtube_video_info.get("view_count")
    youtube_video_data["channel_title"] = youtube_video_info.get("channel_title")
    youtube_video_data["published_at"] = youtube_video_info.get("published_at")
    youtube_video_data["duration"] = youtube_video_info.get("duration")
    #TODO: Fix duration format 

    return youtube_video_info

def get_video_browse_list(query: str = None, max_results: int = 10,
                          published_after: str = None, published_before: str = None,
                          video_category_id: str = None,
                          relevance_language: str = None,
                          min_views: int = 50000,
                          min_likes: int = 1000) -> Dict[str, Any]: # Changed return type hint
    """
    Search YouTube for medium/long videos, excluding live, with min views/likes.
    Returns a dictionary containing the total count and the list of videos.

    Args:
        query: Search query (default topics if None)
        max_results: Max results per duration category (medium, long).
        published_after: ISO 8601 date (YYYY-MM-DDThh:mm:ssZ)
        published_before: ISO 8601 date (YYYY-MM-DDThh:mm:ssZ)
        video_category_id: YouTube category ID
        relevance_language: ISO 639-1 language code
        min_views: Minimum view count required (default: 50000)
        min_likes: Minimum like count required (default: 1000)

    Returns:
        Dict containing 'total_videos' (int) and 'video_list' (List[Dict[str, Any]]).
    """
    settings = get_settings()
    google_yt_api_key = settings.google_yt_api_key
    
    # Use the proxied YouTube client
    youtube = get_youtube_client(google_yt_api_key)

    if not query:
        query = "politics OR documentary OR controversial OR podcast OR informative"

    logging.info(f"Searching YouTube videos with query: {query} for medium/long durations, excluding live, min_views={min_views}, min_likes={min_likes}.")

    video_details_map = {}

    # --- Search Phase (Medium & Long, filter currently live) ---
    for duration in ['medium', 'long']:
        logging.info(f"Searching for videos with duration: {duration}")
        search_params = {
            'part': 'snippet', 'q': query, 'maxResults': max_results,
            'type': 'video', 'order': 'relevance', 'videoDuration': duration
        }
        if published_after: search_params['publishedAfter'] = published_after
        if published_before: search_params['publishedBefore'] = published_before
        if relevance_language: search_params['relevanceLanguage'] = relevance_language

        try:
            search_response = youtube.search().list(**search_params).execute()
            for item in search_response.get('items', []):
                if item['snippet'].get('liveBroadcastContent') != 'live':
                    video_id = item['id']['videoId']
                    if video_id not in video_details_map:
                         video_details_map[video_id] = {
                            'video_id': video_id, 'title': item['snippet']['title'],
                            'title': item['snippet']['title'],
                            'channel_title': item['snippet']['channelTitle'],
                            'published_at': item['snippet']['publishedAt'],
                            'thumbnail': item['snippet']['thumbnails']['default']['url']
                         }
        except Exception as e:
            logging.error(f"Error searching YouTube videos for duration {duration}: {str(e)}")

    # --- Details Fetching & Filtering Phase ---
    video_ids = list(video_details_map.keys())
    final_video_list = []

    if video_ids:
        try:
            all_video_data = {}
            # Fetch details in chunks
            for i in range(0, len(video_ids), 50):
                chunk_ids = video_ids[i:i + 50]
                logging.info(f"Fetching details for {len(chunk_ids)} video IDs (chunk {i//50 + 1})...")
                videos_response = youtube.videos().list(
                    part='statistics,liveStreamingDetails', # Fetch stats & live details
                    id=','.join(chunk_ids)
                ).execute()
                for item in videos_response.get('items', []):
                    all_video_data[item['id']] = item

            # Process fetched data: filter past live, views, likes
            for video_id, details in video_details_map.items():
                if video_id in all_video_data:
                    video_data = all_video_data[video_id]

                    # Filter 1: Skip past live streams
                    if 'liveStreamingDetails' in video_data:
                        logging.debug(f"Skipping video {video_id} (was live).")
                        continue

                    # Get stats
                    stats = video_data.get('statistics', {})
                    view_count_str = stats.get('viewCount', '0')
                    like_count_str = stats.get('likeCount', 'N/A') # Likes might be hidden

                    # Convert counts to integers for comparison
                    try:
                        view_count = int(view_count_str)
                    except ValueError:
                        view_count = 0 # Treat non-integer view counts as 0

                    try:
                        # Handle case where likes are disabled ('N/A' or missing)
                        like_count = int(like_count_str) if like_count_str != 'N/A' else -1
                    except ValueError:
                        like_count = -1 # Treat other non-integer like counts as -1 (won't pass > 1000 check)


                    # Filter 2: Check minimum views
                    if view_count < min_views:
                        logging.debug(f"Skipping video {video_id} (views: {view_count} < {min_views}).")
                        continue

                    # Filter 3: Check minimum likes (only if likes are available)
                    if like_count < min_likes:
                        logging.debug(f"Skipping video {video_id} (likes: {like_count} < {min_likes}).")
                        continue

                    # If all filters passed, add stats and append to final list
                    details['view_count'] = view_count_str
                    details['like_count'] = like_count_str
                    details['comment_count'] = stats.get('commentCount', '0')
                    
                    
                    final_video_list.append(details)
                else:
                     logging.warning(f"Could not fetch details for video ID: {video_id}")

        except Exception as e:
            logging.error(f"Error fetching/processing video details: {str(e)}")
            # Fallback: return list without detailed filtering if details fetch fails
            final_video_list = list(video_details_map.values()) # These won't have stats

    # --- Construct final response dictionary ---
    total_videos = len(final_video_list)
    logging.info(f"Final video count: {total_videos}")

    # Return the structured dictionary
    return {
        "total_videos": total_videos,
        "video_list": final_video_list
    }
    
   