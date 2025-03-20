from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict, Any
import re
from pytube import YouTube

def get_transcript(video_id: str) -> tuple[List[Dict[str, Any]], str]:
    """Retrieve transcript with timestamps and title from a YouTube video."""
    try:
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        try:
            #TODO: Remove this once we have a better way to get the title
            #TODO: also want to get the description and thumbnail
            yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
            video_title = yt.title
        except Exception as e:
            # Return a tuple with the transcript and an error message as the title
            return transcript, f"Unknown title (Error: {str(e)})"
        
        # Return the transcript and title
        return transcript, video_title
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None
    

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