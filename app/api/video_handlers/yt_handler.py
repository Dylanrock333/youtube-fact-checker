from youtube_transcript_api import YouTubeTranscriptApi
from typing import Dict, Any, List
import googleapiclient.discovery
import os
from app.config import get_settings

def get_transcript(video_id: str) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Retrieve transcript with timestamps and title from a YouTube video."""
    try:
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        youtube_video_data = {
            "title": None,
            "tags": None,
            "channel_title": None,
            "view_count": None,
            "published_at": None
        }
        
        try:

            youtube_video_info = get_video_info(video_id)  #TODO: Remove this and have the function call done in the parent function. This has nothing to do with the transcript
            
            youtube_video_data["title"] = youtube_video_info.get("title")
            youtube_video_data["tags"] = youtube_video_info.get("tags")
            youtube_video_data["view_count"] = youtube_video_info.get("view_count")
            youtube_video_data["channel_title"] = youtube_video_info.get("channel_title")
            youtube_video_data["published_at"] = youtube_video_info.get("published_at")
                
        except Exception as e:
            # Set title to error message
            youtube_video_data["title"] = f"Unknown title (Error: {str(e)})"
        
        # Return the combined data structure
        return youtube_video_data, transcript
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
    
def get_video_info(video_id):
    settings = get_settings()
    google_api_key = settings.google_api_key
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=google_api_key)
    
    try:
        video_response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        ).execute()
        
    except Exception as e:
        print(f"API Error: {str(e)}")
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
    
    return youtube_video_info
   