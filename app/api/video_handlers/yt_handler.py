from youtube_transcript_api import YouTubeTranscriptApi
from typing import Dict, Any, List, Optional
import googleapiclient.discovery
from app.config import get_settings
from youtube_transcript_api.proxies import WebshareProxyConfig
from dotenv import load_dotenv
import os
import logging
import re
from datetime import datetime
import time
import yt_dlp
import tempfile
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from urllib.parse import quote_plus

load_dotenv()

# Configuration
MAX_RETRIES_YT_TRANSCRIPT_API = 4

#transcript handling
MAX_DURATION = 13.0  # max combined duration in seconds
MAX_CHARS = 750     # optional limit for character count

                
settings = get_settings()

# Initialize ytt_api inside the function using settings
ytt_api = YouTubeTranscriptApi(
    proxy_config=WebshareProxyConfig(
        proxy_username=settings.webshare_username,
        proxy_password=settings.webshare_password,
    )
)

# Global YouTube API client to prevent memory leaks from creating new clients
_youtube_client = None

def get_youtube_client():
    """Get or create the global YouTube API client."""
    global _youtube_client
    if _youtube_client is None:
        google_yt_api_key = settings.google_yt_api_key
        _youtube_client = googleapiclient.discovery.build('youtube', 'v3', developerKey=google_yt_api_key)
    return _youtube_client

def extract_transcript_YouTubeTranscriptApi(video_id: str) -> List[Dict[str, Any]]: # Updated return type hint
    """Retrieve transcript with timestamps and title from a YouTube video."""
    
    for attempt in range(MAX_RETRIES_YT_TRANSCRIPT_API):
        try:
            logging.info(f"Attempting to retrieve a transcript for video id: {video_id} on YouTubeTranscriptApi (attempt {attempt + 1}/{MAX_RETRIES_YT_TRANSCRIPT_API})")
            
            raw_transcript = ytt_api.fetch(video_id)
            formatted_transcript = raw_transcript.to_raw_data()

            #TODO: Have a standart transcript format schema that is used for all video origins
            logging.info(f"Successfully retrieved transcript for video id: {video_id}")
            return formatted_transcript
            
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1}/{MAX_RETRIES_YT_TRANSCRIPT_API} failed for video id {video_id}: {e}")
            
            if "This video is private" in str(e):
                logging.error(f"Video is private: {video_id}")
                return {"code": 403, "message": "Video is private"}
            
            # If this was the last attempt, log error and return None
            if attempt == MAX_RETRIES_YT_TRANSCRIPT_API - 1:
                logging.error(f"All {MAX_RETRIES_YT_TRANSCRIPT_API} attempts failed for video id {video_id}. Final error: {e}")
                return None
            
            # Wait a bit before retrying 
            wait_time = 2
            logging.info(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)


# Global executor with proper cleanup management
_executor = None

def get_executor():
    """Get or create the global ThreadPoolExecutor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4)  # Keep small for 0.5 CPU
    return _executor

def shutdown_executor():
    """Properly shutdown the global ThreadPoolExecutor."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None

def _extract_transcript_yt_dlp(video_id: str) -> Optional[List[Dict[str, Any]]]:
    """Extract transcript with timestamps and title from a YouTube video using yt-dlp."""
    logging.info(f"Attempting to extract transcript for video id: {video_id} on yt-dlp")
    settings = get_settings()
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

        # Only use the proxy in the production environment
        if settings.environment.lower() == 'prod':
            logging.info(f"Production environment detected. Using proxy with user: '{settings.webshare_username}'")
            # URL-encode credentials to handle special characters safely
            encoded_user = quote_plus(settings.webshare_username)
            encoded_password = quote_plus(settings.webshare_password)
            # Build proxy URL with the encoded credentials
            proxy_url = f"http://{encoded_user}:{encoded_password}@{settings.webshare_proxy_host}:{settings.webshare_proxy_port}"
            ydl_opts['proxy'] = proxy_url
        else:
            logging.info("Development environment detected. Skipping proxy.")


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
        buffer_text = ""
        buffer_start = None
        buffer_duration = 0.0

        for event in data.get("events", []):
            if "segs" not in event:
                continue
            text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
            if not text:
                continue

            start = event["tStartMs"] / 1000
            duration = event.get("dDurationMs", 0) / 1000

            # Initialize buffer
            if buffer_start is None:
                buffer_start = start

            # Check if adding this would exceed max limits
            if (buffer_duration + duration > MAX_DURATION) or (len(buffer_text) + len(text) > MAX_CHARS):
                formatted_transcript.append({
                    "text": buffer_text.strip(),
                    "start": round(buffer_start, 2),
                    "duration": round(buffer_duration, 2)
                })
                # Reset buffer
                buffer_text = text
                buffer_start = start
                buffer_duration = duration
            else:
                buffer_text += " " + text
                buffer_duration += duration

        # Add any remaining buffer after the loop
        if buffer_text:
            formatted_transcript.append({
                "text": buffer_text.strip(),
                "start": round(buffer_start, 2),
                "duration": round(buffer_duration, 2)
            })

        return formatted_transcript

# Public facing function with safety
def get_yt_transcript(video_id: str, timeout_seconds: int = 20) -> Optional[List[Dict[str, Any]]]:
    try:
        
        youtube_transcript = extract_transcript_YouTubeTranscriptApi(video_id)
        if youtube_transcript:
            return youtube_transcript
        else:
            logging.warning(f"YouTubeTranscriptApi failed for video: {video_id}")
            logging.info(f"Attempting to extract transcript with yt-dlp for video: {video_id}")
            future = get_executor().submit(_extract_transcript_yt_dlp, video_id)
            result = future.result(timeout=timeout_seconds)
            if result:
                return result
            else:
                logging.error(f"yt-dlp failed to extract transcript for video: {video_id}")
                return None
            
        
    except FuturesTimeoutError:
        logging.error(f"Timeout while fetching transcript for video: {video_id}")
        return None
    except Exception as e:
        logging.exception(f"Error during transcript retrieval: {e}")
        return None
    
    
async def get_yt_video_info(video_id):
    youtube = get_youtube_client()  # Use the global reusable client
    
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
        "duration": "Unknown duration",
        "thumbnail": "Unknown thumbnail",
        "description": "Unknown description"
    }
    
    youtube_video_data["title"] = youtube_video_info.get("title")
    youtube_video_data["tags"] = youtube_video_info.get("tags")
    youtube_video_data["channel_title"] = youtube_video_info.get("channel_title")
    
    # Format view count with default locale
    raw_view_count = youtube_video_info.get("view_count", 0)
    youtube_video_data["view_count"] = f"{int(raw_view_count):,}"
    
    # Format published date with default format
    raw_published_at = youtube_video_info.get("published_at", "")
    try:
        dt = datetime.fromisoformat(raw_published_at.replace('Z', '+00:00'))
        youtube_video_data["published_at"] = dt.strftime('%Y-%m-%d')
    except:
        youtube_video_data["published_at"] = raw_published_at
    
    # Format duration to standard format
    raw_duration = youtube_video_info.get("duration", "")
    youtube_video_data["duration"] = format_duration(raw_duration)
    
    youtube_video_data["thumbnail"] = youtube_video_info.get("thumbnails", {}).get("high", {}).get("url", "Unknown thumbnail")
    youtube_video_data["description"] = youtube_video_info.get("description", "Unknown description")
    
    #TODO: Fix duration format 
    
    youtube_video_data["title"] = youtube_video_info.get("title")

    return youtube_video_data

        
def format_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration (PT10M30S) to standard format (10:30)"""
    try:
        # Parse ISO 8601 duration format
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, iso_duration)
        
        if not match:
            return iso_duration
            
        hours, minutes, seconds = match.groups()
        hours = int(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        seconds = int(seconds) if seconds else 0
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    except:
        return iso_duration
    
def timestamp_format(timestamp: str) -> str:
    """
    Formats timestamps for consistency.

    - Strips decimal subseconds (e.g., "13:12.3" → "13:12")
    - Converts HH:MM:SS to MM:SS if the hour is 00.
    - Converts MM:SS to H:MM:SS if minutes are 60 or more.
    - Handles various timestamp formats from video transcripts.
    """
    # Convert to string and strip decimal subseconds if present
    timestamp_str = str(timestamp)
    if '.' in timestamp_str:
        timestamp_str = timestamp_str.split('.')[0]

    parts = timestamp_str.split(':')

    if len(parts) == 3:
        # Format HH:MM:SS
        if parts[0] == '00' or parts[0] == '0':
            # Strip leading zeros from minutes
            try:
                minutes = int(parts[1])
                return f"{minutes}:{parts[2]}"
            except ValueError:
                return f"{parts[1]}:{parts[2]}"
        else:
            return timestamp_str

    elif len(parts) == 2:
        # Format MM:SS
        try:
            minutes = int(parts[0])
            seconds = parts[1]
            if minutes >= 60:
                hours = minutes // 60
                remaining_minutes = minutes % 60
                return f"{hours}:{remaining_minutes:02d}:{seconds}"
            else:
                return timestamp_str
        except ValueError:
            # Handle cases where conversion to int fails
            return timestamp_str

    return timestamp_str
