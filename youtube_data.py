from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict, Any

def get_transcript(video_id: str) -> tuple[List[Dict[str, Any]], str]:
    """Retrieve transcript with timestamps and title from a YouTube video."""
    try:
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # video_url = f"https://www.youtube.com/watch?v={video_id}"
        # yt = YouTube(video_url)
        # video_title = yt.title
        video_title = f"Video ID: {video_id}"
        # Just return the video ID as identifier if you don't need the actual title
        return transcript, video_title
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None