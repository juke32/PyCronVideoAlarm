import tkinter as tk
from tkinter import ttk
import logging
import sys
import os

class BlackBoxOverlay(tk.Toplevel):
    def __init__(self, master, on_close=None, opacity=1.0):
        super().__init__(master)
        self.on_close_callback = on_close
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.config(bg='black', cursor='none')
        
        # Windows specific fix for fullscreen coverage
        if hasattr(sys, 'platform') and sys.platform == 'win32':
             self.state('zoomed')
             self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
             self.overrideredirect(True)
        
        # Opacity handling (Windows/Linux support varies)
        try:
            self.attributes('-alpha', opacity)
        except Exception:
            logging.warning("Opacity adjustment not supported on this platform/configuration")

        # Bindings to close (Emergency Exit)
        self.bind('<Escape>', self.close_overlay)
        self.bind('<Button-1>', self.close_overlay) # Click to exit
        self.bind('<Shift_L>', self.close_overlay) # Shift key to exit
        self.bind('<Shift_R>', self.close_overlay) # Right Shift too
        
        # Prevent closing via Alt+F4 easily
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Start checking for kill signal
        try:
            from core.utils import get_signal_file_path
            logging.info(f"BlackBoxOverlay watching for signal at: {get_signal_file_path()}")
        except ImportError:
            logging.error("Could not import get_signal_file_path")

        # Give it a moment before checking (avoid race conditions with cleanup)
        self.after(2000, self.check_kill_signal)

    def show(self):
        """Show the overlay and ensure it is visible."""
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.update_idletasks()
            
            # Re-apply fullscreen to ensure it sticks
            self.attributes('-fullscreen', True)
            self.attributes('-topmost', True)
            
            # Windows specific re-application
            if hasattr(sys, 'platform') and sys.platform == 'win32':
                 self.state('zoomed')
                 self.overrideredirect(True)
                 
        except Exception as e:
            logging.error(f"Error showing overlay: {e}")

    def check_kill_signal(self):
        """Check for a signal file to close the overlay."""
        try:
            from core.utils import get_signal_file_path
            signal_file = get_signal_file_path()
            if os.path.exists(signal_file):
                logging.info(f"Kill signal detected at {signal_file}")
                
                # Try to remove or consume the file
                try:
                    os.remove(signal_file)
                except Exception as e:
                    logging.error(f"Failed to remove signal file: {e}")
                    # Try to empty it at least, so we don't loop forever on next run
                    try:
                        with open(signal_file, 'w') as f: f.write("")
                    except: pass
                
                # Always close if signal found
                logging.info("Closing overlay due to signal.")
                self.close_overlay()
                return
                
        except Exception as e:
            logging.error(f"Error checking kill signal: {e}")
        
        # Check again in 500ms
        self.after(500, self.check_kill_signal)

    def set_opacity(self, value):
        try:
            self.attributes('-alpha', float(value))
        except:
            pass

    def close_overlay(self, event=None):
        if self.on_close_callback:
            try:
                self.on_close_callback()
            except Exception as e:
                logging.error(f"Error in on_close_callback: {e}")
        self.destroy()

class OverlayController:
    def __init__(self, root, on_close=None):
        self.root = root
        self.overlay = None
        self.on_close = on_close

    def show_overlay(self):
        if not self.overlay or not self.overlay.winfo_exists():
            # --- FIX: AGGRESSIVE CLEANUP ---
            # Remove any stale signal file from previous runs to prevent "Suicide on Launch"
            try:
                from core.utils import get_signal_file_path
                signal_file = get_signal_file_path()
                if os.path.exists(signal_file):
                    os.remove(signal_file)
                    logging.info("OverlayController: Removed stale signal file before launch.")
            except Exception as e:
                logging.warning(f"OverlayController: Failed to clean signal file: {e}")
                
            self.overlay = BlackBoxOverlay(self.root, on_close=self._handle_overlay_closing)
            try:
                # Force overlay to top and give focus
                self.overlay.show()
                self.overlay.update()
            except Exception as e:
                logging.warning(f"Overlay mapping warning: {e}")
            logging.info("Black Box Overlay activated")
        else:
             # Already exists, just make sure it's shown
             self.overlay.show()
             logging.info("Black Box Overlay reactivated")

    def _handle_overlay_closing(self):
        """Called when BlackBoxOverlay is closing (e.g. signal or Escape)."""
        logging.info("OverlayController received closing notification.")
        self.overlay = None
        if self.on_close:
            self.on_close()

    def hide_overlay(self):
        if self.overlay and self.overlay.winfo_exists():
            self.overlay.destroy()
            self.overlay = None
            logging.info("Black Box Overlay deactivated")

    def toggle(self):
        if self.overlay and self.overlay.winfo_exists():
            self.hide_overlay()
        else:
            self.show_overlay()
