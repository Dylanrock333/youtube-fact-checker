from youtube_transcript_api import YouTubeTranscriptApi
from typing import Dict, Any, List, Optional
import googleapiclient.discovery
from app.config import get_settings
from youtube_transcript_api.proxies import WebshareProxyConfig
from dotenv import load_dotenv
import os
import logging
import time
import yt_dlp
import tempfile
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

load_dotenv()

# Configuration
MAX_RETRIES = 20

settings = get_settings()
# # Initialize ytt_api inside the function using settings
# ytt_api = YouTubeTranscriptApi(
#     proxy_config=WebshareProxyConfig(
#         proxy_username=settings.webshare_username,
#         proxy_password=settings.webshare_password,
#     )
# )

# def get_yt_transcript(video_id: str) -> List[Dict[str, Any]]: # Updated return type hint
#     """Retrieve transcript with timestamps and title from a YouTube video."""
    
#     for attempt in range(MAX_RETRIES):
#         try:
#             logging.info(f"getting transcript for video id: {video_id} (attempt {attempt + 1}/{MAX_RETRIES})")
            
#             raw_transcript = ytt_api.fetch(video_id)
#             formatted_transcript = raw_transcript.to_raw_data()

#             #TODO: Have a standart transcript format schema that is used for all video origins
#             logging.info(f"Successfully retrieved transcript for video id: {video_id}")
#             logging.info(f"formatted_transcript: {formatted_transcript}")
#             return formatted_transcript
            
#         except Exception as e:
#             logging.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for video id {video_id}: {e}")
            
#             # If this was the last attempt, log error and return None
#             if attempt == MAX_RETRIES - 1:
#                 logging.error(f"All {MAX_RETRIES} attempts failed for video id {video_id}. Final error: {e}")
#                 return None
            
#             # Wait a bit before retrying (exponential backoff)
#             wait_time = 2
#             logging.info(f"Waiting {wait_time} seconds before retry...")
#             time.sleep(wait_time)


# You can reuse this executor app-wide (best placed globally)
executor = ThreadPoolExecutor(max_workers=4)  # Keep small for 0.5 CPU

def _extract_transcript(video_id: str) -> Optional[List[Dict[str, Any]]]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'json3',
            'skip_download': True,
            'subtitleslangs': ['en'],
            'outtmpl': os.path.join(tmp_dir, '%(id)s.%(ext)s'),
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        subs = info.get("requested_subtitles", {})
        if not subs:
            logging.warning(f"No subtitles found for video: {video_id}")
            return None

        lang_key = next(iter(subs))
        ext = subs[lang_key]["ext"]
        json_path = os.path.join(tmp_dir, f"{video_id}.{lang_key}.{ext}")
        if not os.path.exists(json_path):
            logging.warning(f"Subtitle file not found at path: {json_path}")
            return None

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        formatted_transcript = []
        for event in data.get("events", []):
            if "segs" not in event:
                continue
            text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
            if not text:
                continue
            start = event["tStartMs"] / 1000
            duration = event.get("dDurationMs", 0) / 1000
            formatted_transcript.append({
                "text": text,
                "start": round(start, 2),
                "duration": round(duration, 2)
            })

        return formatted_transcript

# Public facing function with safety
def get_yt_transcript(video_id: str, timeout_seconds: int = 15) -> Optional[List[Dict[str, Any]]]:
    try:
        future = executor.submit(_extract_transcript, video_id)
        result = future.result(timeout=timeout_seconds)
        return result
    except FuturesTimeoutError:
        logging.error(f"Timeout while fetching transcript for video: {video_id}")
        return None
    except Exception as e:
        logging.exception(f"Error during transcript retrieval: {e}")
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
   