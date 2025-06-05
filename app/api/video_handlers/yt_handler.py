from youtube_transcript_api import YouTubeTranscriptApi
from typing import Dict, Any, List
import googleapiclient.discovery
from app.config import get_settings
from youtube_transcript_api.proxies import WebshareProxyConfig
from dotenv import load_dotenv
import os
import logging
from app.api.video_handlers.translate import translate_full_prompt
import re
from datetime import datetime
from babel.numbers import format_decimal
from babel.dates import format_date
from babel import Locale

load_dotenv()

settings = get_settings()
# Initialize ytt_api inside the function using settings
ytt_api = YouTubeTranscriptApi(
    proxy_config=WebshareProxyConfig(
        proxy_username=settings.webshare_username,
        proxy_password=settings.webshare_password,
    )
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
    
    
async def get_yt_video_info(video_id, language):
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
    youtube_video_data["channel_title"] = youtube_video_info.get("channel_title")
    
    # Format view count according to locale
    raw_view_count = youtube_video_info.get("view_count", 0)
    youtube_video_data["view_count"] = format_view_count(int(raw_view_count), language)
    
    # Format published date according to locale
    raw_published_at = youtube_video_info.get("published_at", "")
    youtube_video_data["published_at"] = format_published_date(raw_published_at, language)
    
    # Format duration to standard format
    raw_duration = youtube_video_info.get("duration", "")
    youtube_video_data["duration"] = format_duration(raw_duration)
    
    #TODO: Fix duration format 
    
    try:
        logging.info(f"Translating title to {language}")
        translated_title = await translate_full_prompt(youtube_video_info.get("title"), language)
        youtube_video_data["title"] = translated_title
    except Exception as e:
        logging.error(f"Error translating title: {e}")
    

    return youtube_video_data

def format_view_count(view_count: int, language: str) -> str:
    """Format view count according to locale conventions"""
    try:
        locale = Locale(language)
        return format_decimal(view_count, locale=locale)
    except:
        # Fallback to English formatting
        return f"{view_count:,}"

def format_published_date(iso_date: str, language: str) -> str:
    """Format published date according to locale conventions"""
    try:
        # Parse ISO 8601 date
        dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
        locale = Locale(language)
        return format_date(dt, locale=locale)
    except:
        # Fallback to simple format
        try:
            dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            return iso_date
        
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
   