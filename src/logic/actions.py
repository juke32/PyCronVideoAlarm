
import logging
import sys
import time
import webbrowser
import os
import random
import random
import subprocess
from logic.media_utils import execute_media, play_audio_with_retry, get_clean_env

# List of supported action types
ACTION_TYPES = [
    "play_audio",
    "play_video",
    "play_random_audio",
    "play_random_video",
    "open_url",
    "wait_action",
    "set_brightness",
    "set_system_volume",
    "kill_black_screen",
    "monitor_control",
    "run_command",
    "open_journal",
    "take_photo",
    "record_audio"
]

def get_nircmd_path():
    """Find nircmd.exe in common locations or bundled paths."""
    from core.config import get_config
    cfg = get_config()
    nircmd_path = cfg.get("system", "windows_nircmd_path")
    
    if nircmd_path and os.path.exists(nircmd_path):
        return nircmd_path
        
    possible_paths = [
        "nircmd.exe", 
        "bin/nircmd.exe",
        os.path.join(os.getcwd(), "nircmd.exe"),
        os.path.join(os.getcwd(), "bin", "nircmd.exe"),
    ]
    
    # Check PyInstaller temp folder
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        possible_paths.append(os.path.join(base_path, "nircmd.exe"))
        possible_paths.append(os.path.join(base_path, "bin", "nircmd.exe"))
    else:
        # Src relative
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possible_paths.append(os.path.join(base_path, "bin", "nircmd.exe"))

    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    return "nircmd.exe" # Fallback to PATH

def handle_play_random_video(config):
    """Handle play_random_video action."""
    # Ensure randomness
    random.seed(time.time())
    
    directory = config.get("directory", "video")
    if not os.path.exists(directory):
         logging.warning(f"Random video directory not found: {directory}")
         return False
         
    extensions = tuple(config.get("file_types", ["mp4", "mkv", "webm", "avi"]))
    try:
        files = [f for f in os.listdir(directory) if f.lower().endswith(extensions)]
        
        # Filtering Logic
        include_filter = config.get("include_filter", "").strip()
        exclude_filter = config.get("exclude_filter", "").strip()
        
        if include_filter:
            files = [f for f in files if include_filter.lower() in f.lower()]
            
        if exclude_filter:
            files = [f for f in files if exclude_filter.lower() not in f.lower()]
            
        if not files:
            logging.warning(f"No video files found in {directory} matching filters (inc='{include_filter}', exc='{exclude_filter}')")
            return False
            
        video_file = os.path.join(directory, random.choice(files))
        logging.info(f"Playing random video: {video_file} (Selected from {len(files)} files)")
        return execute_media(video_file, config)
    except Exception as e:
        logging.error(f"Error in random video: {e}")
        return False


def handle_play_video(config):
    """Handle play_video action."""
    file_path = config.get("file")
    if file_path:
        return execute_media(file_path, config)
    return False

def handle_play_audio(config):
    """Handle play_audio action."""
    file_path = config.get("file")
    if file_path:
        # Use execute_media to leverage player priority
        return execute_media(file_path, config)
    return False

def handle_open_url(config):
    """Handle open_url action with browser selection.
    
    On Linux: uses xdg-open via subprocess (avoids PyInstaller PATH/LD_LIBRARY_PATH issues).
    On macOS: uses the 'open' command.
    On Windows: uses webbrowser module.
    All paths fall back to webbrowser if the native command fails.
    """
    url = config.get("url")
    if not url: return False

    browser_name = config.get("browser", "default").lower()

    # --- Native OS openers (more reliable than webbrowser from frozen apps) ---
    if browser_name == "default":
        try:
            if sys.platform.startswith("linux"):
                result = subprocess.run(
                    ["xdg-open", url],
                    capture_output=True, text=True,
                    env=get_clean_env()
                )
                if result.returncode == 0:
                    logging.info(f"Opened URL via xdg-open: {url}")
                    return True
                logging.warning(f"xdg-open failed (rc={result.returncode}): {result.stderr.strip()}")
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["open", url],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    logging.info(f"Opened URL via open: {url}")
                    return True
        except FileNotFoundError:
            pass  # Fall through to webbrowser
        except Exception as e:
            logging.warning(f"Native URL opener failed: {e}")

        # Fallback: webbrowser module
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logging.error(f"Failed to open URL: {e}")
            return False

    # --- Specific browser requested ---
    try:
        if browser_name == "chromium":
            # Try chromium, then chromium-browser (Ubuntu/Debian naming)
            for name in ["chromium", "chromium-browser"]:
                try:
                    if sys.platform.startswith("linux"):
                        r = subprocess.run([name, url], capture_output=True,
                                           env=get_clean_env())
                        if r.returncode == 0:
                            return True
                    else:
                        webbrowser.get(name).open(url)
                        return True
                except (FileNotFoundError, webbrowser.Error):
                    continue
        
        # Generic named browser
        if sys.platform.startswith("linux"):
            # Try as a direct command first
            try:
                r = subprocess.run([browser_name, url], capture_output=True,
                                   env=get_clean_env())
                if r.returncode == 0:
                    return True
            except FileNotFoundError:
                pass
        
        # Fallback to webbrowser
        try:
            webbrowser.get(browser_name).open(url)
            return True
        except webbrowser.Error:
            logging.warning(f"Browser '{browser_name}' not found, using default.")
            webbrowser.open(url)
            return True

    except Exception as e:
        logging.error(f"Failed to open URL: {e}")
        return False


def handle_wait_action(config):
    """Handle wait_action."""
    duration = config.get("duration", 0)
    try:
        time.sleep(float(duration))
        return True
    except ValueError:
        return True
    except ValueError:
        return False

def get_current_system_volume():
    """Get the current system volume (0-100)."""
    try:
        if sys.platform == "linux":
            # Try pactl first (PulseAudio)
            try:
                result = subprocess.run(
                    ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                    capture_output=True, text=True, check=True, env=get_clean_env()
                )
                # Parse output like "Volume: front-left: 65536 / 100% / 0.00 dB"
                for line in result.stdout.split('\n'):
                    if 'Volume:' in line:
                        # Extract percentage
                        import re
                        match = re.search(r'(\d+)%', line)
                        if match:
                            return int(match.group(1))
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            # Try amixer as fallback (ALSA)
            try:
                result = subprocess.run(
                    ["amixer", "get", "Master"],
                    capture_output=True, text=True, check=True, env=get_clean_env()
                )
                # Parse output like "[50%]"
                import re
                match = re.search(r'\[(\d+)%\]', result.stdout)
                if match:
                    return int(match.group(1))
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        elif sys.platform == "win32":
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                current_volume = volume.GetMasterVolumeLevelScalar()
                return int(current_volume * 100)
            except Exception:
                pass
        
        logging.warning("Could not get current system volume")
        return None
    except Exception as e:
        logging.error(f"Error getting system volume: {e}")
        return None

def handle_set_system_volume(config):
    """Handle set_system_volume action (Linux/Windows)."""
    volume = config.get("volume", 50)
    
    # Check config
    try:
        from core.config import get_config
        cfg = get_config()
        method = cfg.get("system", "volume_method") or "auto"
    except ImportError:
        method = "auto"

    try:
        # Linux (ALSA/PulseAudio via amixer)
        # Try both Master and Pulse, as some systems use one or the other
        if method in ["auto", "amixer_pulse"]:
            try:
                # -M for mapped volume is more natural
                subprocess.run(["amixer", "-D", "pulse", "set", "Master", f"{volume}%"], check=True, capture_output=True, env=get_clean_env())
                logging.info(f"Set system volume to {volume}% (Pulse)")
                return True
            except subprocess.CalledProcessError:
                if method != "auto": 
                     logging.warning("amixer pulse failed")
        
        if method in ["auto", "amixer_master"]:
            try:
                subprocess.run(["amixer", "set", "Master", f"{volume}%"], check=True, capture_output=True, env=get_clean_env())
                logging.info(f"Set system volume to {volume}% (ALSA Master)")
                return True
            except subprocess.CalledProcessError:
                 if method != "auto":
                     logging.warning("amixer master failed")
                     
        if method in ["auto", "pactl"]:
             # Basic pactl implementation
             try:
                 # sink @DEFAULT_SINK@
                 subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"], check=True, capture_output=True, env=get_clean_env())
                 logging.info(f"Set system volume to {volume}% (pactl)")
                 return True
             except (subprocess.CalledProcessError, FileNotFoundError):
                 pass

    except FileNotFoundError:
        pass
        
    # Windows Implementation
    if os.name == 'nt':
         # Strategy 1: pycaw (Best, if installed)
         if method in ["auto", "pycaw"]:
             try:
                 from ctypes import cast, POINTER
                 from comtypes import CLSCTX_ALL
                 from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                 
                 devices = AudioUtilities.GetSpeakers()
                 interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                 volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                 
                 # volume is scalar 0.0 to 1.0
                 volume_interface.SetMasterVolumeLevelScalar(volume / 100.0, None)
                 logging.info(f"Set system volume to {volume}% (pycaw)")
                 return True
             except ImportError:
                 if method == "pycaw": logging.warning("pycaw not installed")
             except Exception as e:
                 logging.error(f"pycaw volume execution failed: {e}")

         # Strategy 2: nircmd (External tool)
         if method in ["auto", "nircmd"]:
             nircmd_path = get_nircmd_path()

             # Convert 0-100 to 0-65535
             nircmd_vol = int(65535 * (volume / 100.0))
             try:
                 subprocess.run([nircmd_path, "setsysvolume", str(nircmd_vol)], check=True, creationflags=0x08000000, env=get_clean_env())
                 logging.info(f"Set system volume to {volume}% (nircmd at {nircmd_path})")
                 return True
             except FileNotFoundError:
                 if method == "nircmd": logging.warning(f"nircmd not found at {nircmd_path}")
             except Exception as e:
                 logging.error(f"nircmd execution failed: {e}")

                 
         # If all failed
         logging.error("Windows Volume control failed (pycaw missing, nircmd missing)")
         try:
             from tkinter import messagebox
             messagebox.showwarning("Action Failed", "Windows Volume Failed.\n\nOption 1: Install 'pycaw' (pip install pycaw comtypes)\nOption 2: Download 'nircmd.exe' and set path in settings.json")
         except: pass
    return False

def handle_set_brightness(config):
    """Handle set_brightness action."""
    level = config.get("level", 100)
    
    try:
        from core.factory import get_platform_managers
        _, display_mgr = get_platform_managers()
        if display_mgr:
            success = display_mgr.set_brightness(int(level))
            if not success:
                logging.warning("display_mgr failed to set brightness")
                try:
                     from tkinter import messagebox
                     messagebox.showwarning("Action Failed", "Failed to set brightness.\n\nEnsure 'brightnessctl' is installed or 'xrandr' is available.")
                except: pass
            return success
        else:
            logging.warning("Display manager not available for this platform.")
    except Exception as e:
        logging.error(f"Brightness action failed: {e}")
        try:
             from tkinter import messagebox
             messagebox.showerror("Action Error", f"Brightness Error: {e}")
        except: pass
    return False

def handle_play_random_audio(config):
    """Handle play_random_audio action."""
    directory = config.get("directory", "audio")
    if not os.path.exists(directory):
        logging.warning(f"Random audio directory not found: {directory}")
        return False
    
    extensions = tuple(config.get("file_types", ["mp3", "wav", "ogg", "flac"]))
    try:
        files = [f for f in os.listdir(directory) if f.lower().endswith(extensions)]
        if not files:
            logging.warning(f"No audio files found in {directory}")
            return False
        
        audio_file = os.path.join(directory, random.choice(files))
        logging.info(f"Playing random audio: {audio_file}")
        return execute_media(audio_file, config)
    except Exception as e:
        logging.error(f"Error in random audio: {e}")
        return False

def handle_kill_black_screen(config):
    """Handle kill_black_screen action - closes the black overlay via signal file.
    
    The overlay (BlackBoxOverlay) polls for a 'kill_overlay.signal' file
    every 500ms. We just create the file and the overlay closes itself.
    No xdotool, no pyautogui, no dialogs, no permissions needed.
    """
    try:
        from core.utils import get_signal_file_path
        signal_file = get_signal_file_path()
        
        with open(signal_file, "w") as f:
            f.write("kill")
        
        logging.info(f"Created kill signal at {signal_file}")
        time.sleep(1)  # Give overlay time to pick it up
        return True
        
    except Exception as e:
        logging.error(f"Failed to kill black screen: {e}")
        return False

# Registry for easy execution
# --- New Automation Actions ---

def handle_monitor_control(config):
    """Handle monitor_control action (Turn On/Off)."""
    state = config.get("state", "off").lower()
    
    if sys.platform == "win32":
        try:
            # Check for nircmd
            nircmd_path = get_nircmd_path()
            
            cmd = "monitor off" if state == "off" else "monitor on"
            subprocess.run(f'"{nircmd_path}" {cmd}', shell=True, check=False, env=get_clean_env())
            logging.info(f"Monitor control (Windows): {state}")
            return True
        except Exception as e:
            logging.error(f"Monitor control failed: {e}")
            return False
            
    elif sys.platform.startswith("linux"):
        try:
            if state == "off":
                subprocess.run(["xset", "dpms", "force", "off"], check=True, env=get_clean_env())
            else:
                subprocess.run(["xset", "dpms", "force", "on"], check=True, env=get_clean_env())
            logging.info(f"Monitor control (Linux): {state}")
            return True
        except Exception as e:
            logging.error(f"Monitor control failed: {e}")
            return False
    return False

def handle_run_command(config):
    """Handle run_command action."""
    command = config.get("command")
    if not command: return False
    
    try:
        logging.info(f"Running command: {command}")
        # Run in background?
        wait = config.get("wait", False)
        
        if wait:
            subprocess.run(command, shell=True, check=True, env=get_clean_env())
        else:
            subprocess.Popen(command, shell=True, env=get_clean_env())
        return True
    except Exception as e:
        logging.error(f"Command execution failed: {e}")
        return False

def handle_open_journal(config):
    """Handle open_journal action."""
    try:
        from datetime import datetime
        base_dir = config.get("directory", "journals")
        if not os.path.exists(base_dir): os.makedirs(base_dir)
        
        filename = datetime.now().strftime("%Y-%m-%d_Journal.md")
        filepath = os.path.join(base_dir, filename)
        
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                f.write(f"# Journal - {datetime.now().strftime('%A, %B %d, %Y')}\n\n")
        
        # Open default editor
        if sys.platform == "win32":
            os.startfile(filepath)
        else:
            opener = "xdg-open"
            subprocess.call([opener, filepath], env=get_clean_env())
            
        logging.info(f"Opened journal: {filepath}")
        return True
    except Exception as e:
        logging.error(f"Journal action failed: {e}")
        return False

def handle_take_photo(config):
    """Handle take_photo action using OpenCV."""
    try:
        import cv2
        camera_index = config.get("camera_index", 0)
        save_dir = config.get("directory", "captures")
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logging.error("Could not open camera")
            return False
            
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            from datetime import datetime
            filename = datetime.now().strftime("IMG_%Y%m%d_%H%M%S.jpg")
            filepath = os.path.join(save_dir, filename)
            cv2.imwrite(filepath, frame)
            logging.info(f"Photo taken: {filepath}")
            return True
        else:
            logging.error("Failed to capture frame")
            return False
    except ImportError:
        logging.error("OpenCV not installed (pip install opencv-python)")
        return False
    except Exception as e:
        logging.error(f"Take photo failed: {e}")
        return False

def handle_record_audio(config):
    """Handle record_audio action using sounddevice."""
    try:
        import sounddevice as sd
        import numpy as np
        from scipy.io.wavfile import write
        
        duration = config.get("duration", 10) # seconds
        fs = 44100  # Sample rate
        
        save_dir = config.get("directory", "captures")
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        
        from datetime import datetime
        filename = datetime.now().strftime("REC_%Y%m%d_%H%M%S.wav")
        filepath = os.path.join(save_dir, filename)
        
        logging.info(f"Recording audio for {duration} seconds...")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=2)
        sd.wait()  # Wait until recording is finished
        write(filepath, fs, recording)  # Save as WAV file 
        
        logging.info(f"Audio recorded: {filepath}")
        return True
        
    except ImportError:
        logging.error("sounddevice/scipy not installed")
        return False
    except Exception as e:
        logging.error(f"Record audio failed: {e}")
        return False

# Registry for easy execution
ACTION_HANDLERS = {
    "play_video": handle_play_video,
    "play_audio": handle_play_audio,
    "play_random_video": handle_play_random_video,
    "play_random_audio": handle_play_random_audio,
    "open_url": handle_open_url,
    "wait_action": handle_wait_action,
    "set_system_volume": handle_set_system_volume,
    "set_brightness": handle_set_brightness,
    "kill_black_screen": handle_kill_black_screen,
    "monitor_control": handle_monitor_control,
    "run_command": handle_run_command,
    "open_journal": handle_open_journal,
    "take_photo": handle_take_photo,
    "record_audio": handle_record_audio,
}

def execute_action(action_type, config):
    """Execute an action by type."""
    handler = ACTION_HANDLERS.get(action_type)
    if handler:
        try:
            logging.info(f"Executing action: {action_type}")
            return handler(config)
        except Exception as e:
            logging.error(f"Action execution failed: {e}")
            return False
    else:
        logging.warning(f"No handler for action type: {action_type}")
        return False


def get_action_template(action_type):
    """Get default configuration template for an action type."""
    templates = {
        "play_audio": {
            "file": "audio/example.mp3",
            "gain": 0,
            "system_volume": None,
            "from": "00:00",
            "to": "00:00",
            "#comment": "gain: Audio amplification in dB (-50 to +50). system_volume: set system vol (0-100, null=no change)"
        },
        "play_video": {
            "file": "video/example.mp4",
            "fullscreen": True,
            "gain": 0,
            "system_volume": None,
            "from": "00:00",
            "to": "00:00",
            "#comment": "gain: Audio amplification in dB (-50 to +50). system_volume: set system vol (0-100, null=no change)"
        },
        "play_random_audio": {
            "directory": "audio",
            "file_types": ["mp3", "wav", "ogg", "flac"],
            "gain": 0,
            "system_volume": None,
            "#comment": "gain: Audio amplification in dB. system_volume: set system vol (0-100, null=no change)"
        },
        "play_random_video": {
            "directory": "video",
            "file_types": ["mp4", "mkv", "webm", "avi"],
            "fullscreen": True,
            "gain": 0,
            "system_volume": None,
            "include_filter": "",
            "exclude_filter": "",
            "#comment": "filters: simple keyword matching in filename"
        },
        "open_url": {
            "url": "https://example.com",
            "browser": "default",
            "#comment": "Open a website"
        },
        "wait_action": {
            "duration": 5,
            "#comment": "Wait for X seconds"
        },
        "set_brightness": {
            "level": 100,
            "#comment": "Set screen brightness (0-100)"
        },
        "set_system_volume": {
            "volume": 50,
            "#comment": "Set system volume (0-100)"
        },
        "kill_black_screen": {
            "#comment": "Close the black overlay window"
        },
        "monitor_control": {
            "state": "off",
            "#comment": "Turn monitor 'on' or 'off'"
        },
        "run_command": {
            "command": "echo 'Hello'",
            "wait": False,
            "#comment": "Execute shell command. Use with caution!"
        },
        "open_journal": {
            "directory": "journals",
            "#comment": "Open/Create daily markdown journal"
        },
        "take_photo": {
            "directory": "captures",
            "camera_index": 0,
            "#comment": "Take photo from webcam"
        },
        "record_audio": {
            "directory": "captures",
            "duration": 10,
            "#comment": "Record X seconds of audio"
        }
    }
    return templates.get(action_type, {"#comment": "No template available"})
