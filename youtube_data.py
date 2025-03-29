from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict, Any
import re
from pytube import YouTube
import subprocess
import json
#from googleapiclient.discovery import build
import googleapiclient.discovery
import os



google_api_key = os.getenv("GOOGLE_API_KEY")

def get_transcript(video_id: str) -> tuple[List[Dict[str, Any]], str]:
    """Retrieve transcript with timestamps and title from a YouTube video."""
    try:
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        try:
            #TODO: Remove this once we have a better way to get the title
            #TODO: also want to get the description and thumbnail

            video_info = get_video_info(video_id)

            
            print(video_info)
            
            video_title = video_info.get("title")
                
        except Exception as e:
            # Return a tuple with the transcript and an error message as the title
            return transcript, f"Unknown title (Error: {str(e)})"
        
        # Return the transcript and title
        return transcript, video_title
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None
 

def get_video_info(video_id):
    # Create a YouTube API service object
    #youtube = build('youtube', 'v3', developerKey=google_api_key)
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=google_api_key)
    
    try:
        video_response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        ).execute()
        print(video_response)
        # Rest of your code...
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
    video_info = {
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
        "thumbnails": video_data['snippet']['thumbnails']
    }
    
    return video_info 
   

def extract_youtube_video_id(input_string: str) -> str:
    """
    Extract YouTube video ID from various YouTube URL formats or return the ID if already provided.
    
    Handles formats like:
    - https://www.youtube.com/watch?v=n4aX3bwwPHc
    - https://youtu.be/n4aX3bwwPHc
    - n4aX3bwwPHc (direct ID)
    """
    # Pattern to match YouTube URLs and extract video ID
    youtube_regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    
    # Check if input is a URL
    match = re.search(youtube_regex, input_string)
    if match:
        return match.group(1)
    
    # Check if input is already a video ID (typically 11 characters)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', input_string):
        return input_string
    
    return None