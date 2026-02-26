#!/usr/bin/env python3

import os
import sys
import subprocess
import logging
import time as time_module
import threading
import shutil


def ensure_time_format(time_value):
    """
    Ensure time is in the proper format for VLC (seconds as string).
    """
    if not time_value:
        return None
        
    try:
        # If it's already in MM:SS format, convert to seconds
        if isinstance(time_value, str) and ':' in time_value:
            parts = time_value.split(':')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                minutes = int(parts[0])
                seconds = int(parts[1])
                return str(minutes * 60 + seconds)
        
        return f"{float(time_value):.2f}"
    except (ValueError, TypeError):
        logging.warning(f"Invalid time format: {time_value}, using as-is")
        return str(time_value)

def play_audio_with_retry(file_path, duration=None, gain=0, system_volume=None, retries=3):
    """Play audio file using prioritized media players (same as video)."""
    return execute_media(file_path, config=duration if isinstance(duration, dict) else None)


def get_player_priority(file_path):
    """Get the prioritized list of players (Forced MPV only now)."""
    return ["mpv"]

def execute_media(file_path, config=None):
    """
    Play media file (audio/video) using MPV exclusively.
    """
    if not os.path.exists(file_path):
        logging.error(f"Media file not found: {file_path}")
        return False

    success = False
    try:
        success = play_video_mpv(file_path, config)
        if success:
            logging.info(f"Successfully played using mpv")
            return True
        else:
            logging.warning(f"mpv failed.")
            return False
    except Exception as e:
        logging.error(f"Error with player mpv: {e}")
        return False

# Alias for backward compatibility
execute_video = execute_media

def check_mpv_installed():
    """Verify strictly if MPV is installed."""
    return shutil.which("mpv") is not None

def detect_available_players():
    """
    Detect which video players are installed on the system.
    Returns: ['mpv'] if installed, else []
    """
    available = []
    
    # Check for MPV
    if check_mpv_installed():
        available.append("mpv")
        
    return available

def play_video_mpv(file_path, config=None):
    """Play video file using mpv."""
    mpv_path = shutil.which("mpv")
    if not mpv_path:
        logging.error("mpv executable not found.")
        return False
        
    try:
        fullscreen = True
        gain = 0
        system_volume = None
        start_time = None
        end_time = None
        
        if config:
            fullscreen = config.get("fullscreen", True)
            gain = config.get("gain", 0)
            system_volume = config.get("system_volume")
            if "from" in config: start_time = ensure_time_format(config["from"])
            if "to" in config: end_time = ensure_time_format(config["to"])

        # Set system volume if requested
        if system_volume is not None:
             try:
                 from logic.actions import handle_set_system_volume
                 handle_set_system_volume({"volume": system_volume})
             except Exception as e:
                 logging.warning(f"Failed to set system volume: {e}")

        cmd = [mpv_path, file_path]
        
        # Flags
        if fullscreen:
            cmd.append("--fs")
            # Linux specific fixes for fullscreen rendering bugs (transparent/missing black borders)
            if sys.platform.startswith('linux'):
                cmd.append("--geometry=100%x100%")
                cmd.append("--x11-bypass-compositor=no")  # Prevents compositor from breaking fullscreen opaqueness
        
        cmd.append("--no-terminal")
        
        # On Linux, combining --fs and --ontop causes many Window Managers to incorrectly
        # size the window or omit the black background. We only use ontop if not fullscreen or not Linux.
        if not (sys.platform.startswith('linux') and fullscreen):
            cmd.append("--ontop") # Ensure video plays above everything
        
        # Start/End time
        if start_time and float(start_time) > 0:
            cmd.append(f"--start={start_time}")
        if end_time and float(end_time) > 0:
            cmd.append(f"--end={end_time}")
            
        # Audio gain
        if gain is not None and gain != 0:
            # mpv volume is 0-100+, but gain in dB is different.
            # mpv supports --af=volume=value:replaygain-noclip=no
            # value is in dB if no suffix? No, volume is usually %, replaygain is dB.
            # safe way: --af=volume=<v>dB
            cmd.append(f"--af=volume={float(gain):.1f}dB")

        logging.info(f"Launching mpv: {cmd}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"mpv exited with code {result.returncode}")
            logging.error(f"mpv stdout: {result.stdout}")
            logging.error(f"mpv stderr: {result.stderr}")
            return False
            
        return True
        
    except Exception as e:
        logging.error(f"mpv playback error: {e}")
        return False



def get_video_duration_ffprobe(file_path):
    """Get video duration using ffprobe."""
    try:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return 0
            
        cmd = [
            ffprobe, 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                val = float(result.stdout.strip())
                return val
            except ValueError:
                pass
            
    except Exception as e:
        logging.warning(f"ffprobe duration check failed: {e}")
        
    return 0

def get_video_duration(file_path):
    """Get video duration using OpenCV with fallback to ffprobe."""
    duration = 0
    
    # Try OpenCV
    try:
        import cv2
        cap = cv2.VideoCapture(file_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            
            if fps > 0 and frame_count > 0:
                duration = frame_count / fps
                return duration
    except ImportError:
        logging.debug("OpenCV not found, skipping...")
    except Exception as e:
        logging.warning(f"Failed to get video duration via OpenCV: {e}")

    # Fallback to ffprobe
    if duration <= 0:
        duration = get_video_duration_ffprobe(file_path)
        
    return duration
