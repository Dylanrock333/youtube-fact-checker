from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict, Any
import re
import subprocess
import json


import os



#TODO: remoce this function and file(this function will be in the UI)

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