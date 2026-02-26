import os
import random
import webbrowser
import logging
from typing import List

class MediaQueue:
    def __init__(self, local_video_dir: str):
        self.local_video_dir = local_video_dir
        self.web_videos = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", # Placeholder
            "https://www.youtube.com/watch?v=KxGRhd_iWuE"  # Placeholder
        ]
    
    def get_next_local_video(self) -> str:
        """Get a random video file from the local directory."""
        if not os.path.exists(self.local_video_dir):
            logging.error(f"Video directory not found: {self.local_video_dir}")
            return ""
            
        videos = [f for f in os.listdir(self.local_video_dir) if f.endswith(('.mp4', '.mkv', '.avi'))]
        if not videos:
            logging.warning("No videos found in directory.")
            return ""
            
        return os.path.join(self.local_video_dir, random.choice(videos))

    def get_next_web_video(self) -> str:
        """Get a random web video URL."""
        return random.choice(self.web_videos)

class ShoveManager:
    def __init__(self, target_url: str = "https://www.stretching.name/"):
        self.target_url = target_url

    def execute_shove(self):
        """Force open the browser to the target URL."""
        logging.info(f"Executing The Shove: Opening {self.target_url}")
        webbrowser.open(self.target_url)
