import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import logging
import os
import sys
import json
import signal
import subprocess
from datetime import datetime, timedelta

# Internal Imports
from core.factory import get_platform_managers
from .overlay import OverlayController
# Placeholder imports for logic we still need to port/connect
# from logic.media import MediaQueue 

class VideoAlarmMainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Apply Modern Theme
        from core.config import get_config
        from .theme import apply_theme
        config = get_config()
        self.current_theme = config.get("ui", "theme") or "Twilight"
        self.style = apply_theme(self, self.current_theme)
        
        # State for editing alarms
        self.editing_alarm = None # Stores {"sequence": str, "time": str} when editing
        
        # Initialize Platform Managers
        self.power_mgr = None
        self.display_mgr = None
        try:
            self.power_mgr, self.display_mgr = get_platform_managers()
        except Exception as e:
            logging.error(f"Failed to initialize platform managers: {e}")
            # Don't show messagebox here - window isn't ready yet
            # Error will be shown when user tries to use the feature
        
        self.overlay_controller = OverlayController(self, on_close=self.on_overlay_closed)
        self.keep_awake_enabled = False
        
        self.title("PyCron Video Alarm")
        self.geometry("920x800") # Slightly larger default PX size dimensions
        
        # Set window icon — works with .png, .ico, or both present
        # Supports both development (relative to source) and PyInstaller (sys._MEIPASS)
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller: bundled data is in sys._MEIPASS
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
            
            png_path = os.path.join(base_dir, "alarm_icon7.png")
            ico_path = os.path.join(base_dir, "alarm_icon7.ico")
            
            if sys.platform == "win32":
                # Windows: prefer .ico (native), fall back to .png via Pillow
                if os.path.exists(ico_path):
                    self.iconbitmap(ico_path)
                elif os.path.exists(png_path):
                    from PIL import Image, ImageTk
                    img = Image.open(png_path)
                    photo = ImageTk.PhotoImage(img)
                    self.iconphoto(True, photo)
                    self._icon_ref = photo
            else:
                # Linux: prefer .png (native for iconphoto), fall back to .ico via Pillow
                icon_file = png_path if os.path.exists(png_path) else ico_path
                if os.path.exists(icon_file):
                    from PIL import Image, ImageTk
                    img = Image.open(icon_file)
                    photo = ImageTk.PhotoImage(img)
                    self.iconphoto(True, photo)
                    self._icon_ref = photo
        except Exception as e:
            logging.debug(f"Could not set window icon: {e}")
        
        # --- UI LAYOUT ---
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.BOTH, expand=True)

        # Sleep Mode State
        self.sleep_mode_enabled = False

        # Notebook
        self.notebook = ttk.Notebook(top_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Tabs
        self.alarms_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.alarms_frame, text="ALARMS")
        
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="SEQUENCES")
        
        self.help_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.help_frame, text="HELP")

        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="SETTINGS")

        # Init Tab Content
        self.init_alarms_tab()
        self.init_main_tab()
        self.init_help_tab()
        self.init_settings_tab()

        # Initialize empty sequence
        try:
            from logic.sequence import AlarmSequence
            self.current_sequence = AlarmSequence("New Sequence")
            self.new_sequence() 
        except Exception as e:
            logging.error(f"Failed to init sequence: {e}")

        # Ensure MPV is installed
        from logic.media_utils import check_mpv_installed
        if not check_mpv_installed():
            self.after(1000, self.show_mpv_error)

    def show_mpv_error(self):
        import platform
        import shutil
        import subprocess
        import webbrowser
        
        dialog = tk.Toplevel(self)
        dialog.title("MPV Player Required")
        dialog.geometry("600x320")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Apply theme colors
        from .theme import COLORS
        dialog.configure(bg=COLORS.get('bg_dark', '#1e1e2e'))
        
        content_frame = ttk.Frame(dialog, padding="20 20 20 20")
        content_frame.pack(fill=tk.BOTH, expand=True)

        warn_label = ttk.Label(
            content_frame, 
            text="⚠️ MPV Media Player is Missing",
            font=("Segoe UI", 16, "bold"),
            foreground=COLORS.get('error', '#ff5555')
        )
        warn_label.pack(anchor=tk.W, pady=(0, 10))

        desc_label = ttk.Label(
            content_frame,
            text=("MPV is required for video and audio playback but was not found on your system.\n\n"
                  "Please install it so the alarm sequences can play media files correctly."),
            wraplength=550,
            font=("Segoe UI", 11)
        )
        desc_label.pack(anchor=tk.W, pady=(0, 20))

        # Button Frame
        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(fill=tk.X, expand=True, side=tk.BOTTOM)

        system = platform.system()

        def auto_install_linux():
            if shutil.which("apt"):
                cmd = "sudo apt update && sudo apt install -y mpv"
            elif shutil.which("apt-get"):  # Fallback for older Debian/Ubuntu
                cmd = "sudo apt-get update && sudo apt-get install -y mpv"
            elif shutil.which("dnf"):
                cmd = "sudo dnf install -y mpv"
            elif shutil.which("pacman"):
                cmd = "sudo pacman -S --noconfirm mpv"
            elif shutil.which("zypper"):
                cmd = "sudo zypper install -y mpv"
            else:
                messagebox.showerror("Error", "Could not detect a supported package manager. Please install mpv manually.", parent=dialog)
                return

            terminals = ["x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "xterm", "lxterminal"]
            term_exe = next((t for t in terminals if shutil.which(t)), None)
            
            if term_exe:
                try:
                    # Provide an interactive prompt in case sudo needs a password, then wait.
                    full_cmd = f"bash -c '{cmd}; echo \"\"; echo \"Press Enter to close this window...\"; read'"
                    if term_exe == "gnome-terminal":
                        subprocess.Popen([term_exe, "--", "bash", "-c", full_cmd])
                    else:
                        subprocess.Popen([term_exe, "-e", full_cmd])
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to launch terminal for installation: {e}", parent=dialog)
            else:
                # Fallback to pure subprocess if no terminal emulator is found (which is rare on desktop but just in case)
                try:
                    subprocess.Popen(["sh", "-c", f"xterm -e \"{cmd}\""])
                except:
                    messagebox.showerror("Error", f"Could not open a terminal to run: {cmd}\nPlease run it manually.", parent=dialog)

        def auto_install_windows():
            try:
                # Open a Command Prompt and run winget, then pause so the user can see what happened.
                cmd = "winget install Shinchiro.mpv && echo. && echo Finished! Note: You may need to restart the application to detect MPV. && pause"
                subprocess.Popen(["cmd.exe", "/c", cmd])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run winget install: {e}\n\nPlease install manually.", parent=dialog)

        # OS Specific Install Buttons
        if system == "Linux":
            ttk.Button(btn_frame, text="Auto Install (Terminal)", command=auto_install_linux).pack(side=tk.LEFT, padx=5)
        elif system == "Windows":
            ttk.Button(btn_frame, text="Install via Winget", command=auto_install_windows).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Download from mpv.io", command=lambda: webbrowser.open("https://mpv.io/installation/")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)


    def init_settings_tab(self):
        """Initialize the Settings tab."""
        # Create a canvas and scrollbar for the settings tab
        self.settings_canvas = tk.Canvas(self.settings_frame, borderwidth=0, highlightthickness=0)
        self.settings_scrollbar = ttk.Scrollbar(self.settings_frame, orient="vertical", command=self.settings_canvas.yview)
        
        settings_container = ttk.Frame(self.settings_canvas, padding=20)
        
        # Configure the canvas
        settings_container.bind(
            "<Configure>",
            lambda e: self.settings_canvas.configure(
                scrollregion=self.settings_canvas.bbox("all")
            )
        )
        
        self.settings_canvas.create_window((0, 0), window=settings_container, anchor="nw", width=self.settings_frame.winfo_width())
        self.settings_canvas.configure(yscrollcommand=self.settings_scrollbar.set)
        
        # Update canvas window width on resize
        self.settings_canvas.bind(
            "<Configure>",
            lambda e: self.settings_canvas.itemconfig(
                "all", width=e.width
            )
        )
        
        self.settings_canvas.pack(side="left", fill="both", expand=True)
        self.settings_scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            # For Windows/Linux
            if event.num == 4 or event.delta > 0:
                self.settings_canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                self.settings_canvas.yview_scroll(1, "units")
                
        self.settings_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.settings_canvas.bind_all("<Button-4>", _on_mousewheel)
        self.settings_canvas.bind_all("<Button-5>", _on_mousewheel)

        # Version display
        try:
            from core.version import get_build_version
            ver = get_build_version()
        except Exception:
            ver = "Unknown"
        ttk.Label(settings_container, text=f"Version: {ver}",
                  font=("Segoe UI", 8), foreground="#888888").pack(anchor=tk.E, pady=(0, 4))

        # Theme Settings
        theme_frame = ttk.LabelFrame(settings_container, text="Appearance", padding=10)
        theme_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT, padx=5)
        
        from .theme import THEMES
        theme_names = list(THEMES.keys())
        
        # Get current theme from config
        from core.config import get_config
        config = get_config()
        current_theme = config.get("ui", "theme") or "Twilight"
        
        self.theme_var = tk.StringVar(value=current_theme)
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=theme_names, state="readonly", width=25)
        theme_combo.pack(side=tk.LEFT, padx=10)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # Time Format Settings
        ttk.Label(theme_frame, text="Time Format:").pack(side=tk.LEFT, padx=(20, 5))
        self.time_format_var = tk.StringVar(value=config.get("ui", "time_format") or "12h")
        ttk.Radiobutton(theme_frame, text="12h", variable=self.time_format_var, value="12h", command=self.change_time_format).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(theme_frame, text="24h", variable=self.time_format_var, value="24h", command=self.change_time_format).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(theme_frame, text="Both", variable=self.time_format_var, value="Both", command=self.change_time_format).pack(side=tk.LEFT, padx=5)
        
        # System Settings (Placeholder for now, redirect to json)
        sys_frame = ttk.LabelFrame(settings_container, text="System Configuration", padding=10)
        sys_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(sys_frame, text="For advanced system settings (brightness methods, etc.), please edit settings.json").pack(side=tk.LEFT)
        ttk.Button(sys_frame, text="Open settings.json", command=self.open_settings_file).pack(side=tk.RIGHT)
        
        # Logging Settings
        logging_frame = ttk.LabelFrame(settings_container, text="Logging", padding=10)
        logging_frame.pack(fill=tk.X, pady=10)
        
        # Toggle row
        toggle_row = ttk.Frame(logging_frame)
        toggle_row.pack(fill=tk.X, pady=5)
        
        self.file_logging_var = tk.BooleanVar()
        from core.config import get_config
        config = get_config()
        self.file_logging_var.set(config.get("logging", "file_logging_enabled") or False)
        
        logging_toggle = ttk.Checkbutton(
            toggle_row, 
            text="Enable File Logging", 
            variable=self.file_logging_var,
            command=self.toggle_file_logging
        )
        logging_toggle.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toggle_row, text="Open Logs Folder", command=self.open_logs_folder).pack(side=tk.RIGHT, padx=5)
        
        # Log file path display
        self.log_path_label = ttk.Label(logging_frame, text="", font=("Consolas", 8))
        self.log_path_label.pack(anchor=tk.W, padx=5, pady=5)
        self.update_log_path_display()
        
        # Sleep Cycle Offset
        sleep_offset_frame = ttk.LabelFrame(settings_container, text="Sleep Cycles", padding=5)
        sleep_offset_frame.pack(fill=tk.X, pady=5)

        # Remove extra inner padding so the box components are co-located appropriately
        sleep_offset_row = ttk.Frame(sleep_offset_frame)
        sleep_offset_row.pack(fill=tk.X, pady=2)

        ttk.Label(sleep_offset_row, text="Fall-asleep offset:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=5)

        current_offset = config.get("alarms", "sleep_offset_minutes")
        if current_offset is None:
            current_offset = 15
        self.sleep_offset_var = tk.IntVar(value=int(current_offset))

        offset_spin = ttk.Spinbox(
            sleep_offset_row,
            from_=-120, to=120, increment=1,
            textvariable=self.sleep_offset_var,
            width=6,
            font=("Segoe UI", 12, "bold")
        )
        offset_spin.pack(side=tk.LEFT, padx=10)
        ttk.Label(sleep_offset_row, text="minutes  (time added before each sleep cycle button)", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)

        def save_sleep_offset():
            try:
                val = int(self.sleep_offset_var.get())
                val = max(-120, min(120, val))
                self.sleep_offset_var.set(val)
                config.set("alarms", "sleep_offset_minutes", val)
                config.save()
                # Refresh the info label on the Alarms tab if it exists
                if hasattr(self, 'sleep_cycle_info_label'):
                    self.sleep_cycle_info_label.config(
                        text=self._sleep_cycle_info_text()
                    )
                # Refresh the buttons as well
                if hasattr(self, 'update_sleep_cycle_buttons'):
                    self.update_sleep_cycle_buttons()
                logging.info(f"Sleep cycle offset saved: {val} min")
            except (ValueError, TypeError):
                pass

        ttk.Button(sleep_offset_row, text="Save", command=save_sleep_offset).pack(side=tk.LEFT, padx=10)

        # System Test Controls

        test_frame = ttk.LabelFrame(settings_container, text="System Tests", padding=10)
        test_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(test_frame, text="Test individual system features:").pack(anchor=tk.W, pady=(0, 5))
        
        test_buttons = ttk.Frame(test_frame)
        test_buttons.pack(fill=tk.X)
        
        ttk.Button(test_buttons, text="Keep Awake", command=self.toggle_keep_awake).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_buttons, text="Black Box", command=self.toggle_black_overlay).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_buttons, text="Dim Display", command=self.test_dim_display).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_buttons, text="Party Mode", command=self.party_mode).pack(side=tk.LEFT, padx=5)

        # Install Section (frozen builds only)
        if getattr(sys, 'frozen', False):
            install_frame = ttk.LabelFrame(settings_container, text="Install", padding=10)
            install_frame.pack(fill=tk.X, pady=10)

            install_row = ttk.Frame(install_frame)
            install_row.pack(fill=tk.X)

            if sys.platform.startswith('linux'):
                try:
                    from platforms.linux.linux_install import is_registered
                    already = is_registered()
                except Exception:
                    already = False
                btn_label = "✓ Already in Applications" if already else "Add to Applications"
                ttk.Label(install_row,
                          text="Register the app so it appears in your app launcher with the correct icon.").pack(anchor=tk.W, pady=(0, 6))
                self.install_btn = ttk.Button(install_row, text=btn_label, command=self._install_linux)
                self.install_btn.pack(anchor=tk.W)

            elif sys.platform == "win32":
                ttk.Label(install_row,
                          text="Add a shortcut to the Windows Start Menu.").pack(anchor=tk.W, pady=(0, 6))
                self.install_btn = ttk.Button(install_row, text="Add to Start Menu", command=self._install_windows)
                self.install_btn.pack(anchor=tk.W)

        # Support Section
        support_frame = ttk.LabelFrame(settings_container, text="Support", padding=10)
        support_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(support_frame, text="If this app helped you wake up on time, consider supporting the project:").pack(anchor=tk.W, pady=(0, 5))
        ttk.Button(support_frame, text="🍕 Support on Ko-fi", command=self.open_kofi).pack(anchor=tk.W)

    def open_kofi(self):
        """Open the Ko-fi support page in the default web browser."""
        import webbrowser
        webbrowser.open("https://ko-fi.com/juke32")

    def _read_license(self) -> str:
        """Read LICENSE from bundle or project root."""
        candidates = []
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), "LICENSE"))
            if hasattr(sys, '_MEIPASS'):
                candidates.append(os.path.join(sys._MEIPASS, "LICENSE"))
        candidates.append(os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "LICENSE")
        ))
        for path in candidates:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                continue
        return "LICENSE file not found."

    def change_theme(self, event=None):
        """Apply selected theme."""
        selected_theme = self.theme_var.get()
        from .theme import apply_theme, COLORS
        apply_theme(self, selected_theme)
        
        # Force refresh of non-ttk widgets (Text, Listbox, etc.)
        self.refresh_non_ttk_widgets(self)
        
        # Save to config
        from core.config import get_config
        config = get_config()
        config.set("ui", "theme", selected_theme)
        config.save()
        
    def refresh_non_ttk_widgets(self, widget):
        """Recursively refresh non-ttk widgets that don't auto-update with style."""
        from .theme import COLORS
        
        try:
            # Handle ScrolledText (which contains a Text widget)
            if isinstance(widget, scrolledtext.ScrolledText):
                widget.configure(bg=COLORS['bg_light'], fg=COLORS['text_main'], insertbackground=COLORS['text_main'])
                
            # Handle standard Tk widgets
            elif isinstance(widget, tk.Text):
                widget.configure(bg=COLORS['bg_light'], fg=COLORS['text_main'], insertbackground=COLORS['text_main'])
            elif isinstance(widget, tk.Listbox):
                widget.configure(bg=COLORS['bg_light'], fg=COLORS['text_main'], selectbackground=COLORS['primary_var'], selectforeground=COLORS['text_main'])
            elif isinstance(widget, tk.Entry) and not isinstance(widget, ttk.Entry):
                widget.configure(bg=COLORS['bg_light'], fg=COLORS['text_main'], insertbackground=COLORS['text_main'])
            elif isinstance(widget, tk.Canvas):
                widget.configure(bg=COLORS['bg_dark'])
            elif isinstance(widget, tk.Frame):
                widget.configure(bg=COLORS['bg_dark'])
            elif isinstance(widget, (tk.Tk, tk.Toplevel)):
                widget.configure(bg=COLORS['bg_dark'])
                
            # Recursively update children
            for child in widget.winfo_children():
                self.refresh_non_ttk_widgets(child)
        except Exception as e:
            # Ignore errors for widgets that might depend on system theme or are destroyed
            pass

    def change_time_format(self):
        """Handle 12h/24h/Both format change."""
        new_format = self.time_format_var.get()
        from core.config import get_config
        config = get_config()
        config.set("ui", "time_format", new_format)
        config.save()
        
        # Refresh Alarms UI components if they exist
        if hasattr(self, 'ampm_container') and hasattr(self, 'mil_container'):
            # Clear separators or other ephemeral widgets in container
            for child in self.time_input_container.winfo_children():
                child.pack_forget()

            if new_format == "12h":
                self.ampm_container.pack(side=tk.LEFT, padx=10)
                # Ensure 24h is hidden
                self.mil_container.pack_forget()
            elif new_format == "24h":
                self.mil_label.config(text="Hour:", font=('Arial', 12))
                self.mil_container.pack(side=tk.LEFT, padx=10)
                # Ensure 12h is hidden
                self.ampm_container.pack_forget()
                for widget in (self.military_hour, self.military_minute):
                    widget.configure(font=('Arial', 48))
            else: # "Both"
                self.ampm_container.pack(side=tk.LEFT, padx=10)
                # Add separator label
                sep = ttk.Label(self.time_input_container, text="=", font=('Arial', 48))
                sep.pack(side=tk.LEFT, padx=10)
                self.mil_label.config(text="", font=('Arial', 1)) # Hide label effectively
                self.mil_container.pack(side=tk.LEFT, padx=10)
                for widget in (self.military_hour, self.military_minute):
                    widget.configure(font=('Arial', 48))

        messagebox.showinfo("Info", f"Time format changed to {new_format}. Some changes may require tab refresh.")

    def open_settings_file(self):
        """Open settings.json in default editor."""
        import webbrowser
        from core.config import get_app_data_dir
        settings_path = os.path.join(get_app_data_dir(), "settings.json")
        if os.path.exists(settings_path):
            webbrowser.open(settings_path)
        else:
            messagebox.showinfo("Info", "settings.json not found (will be created on save).")
    
    def toggle_file_logging(self):
        """Toggle file logging on/off."""
        try:
            from core.config import get_config
            from core.logging_utils import setup_file_logging, remove_file_logging
            
            config = get_config()
            enabled = self.file_logging_var.get()
            
            # Update config
            config.set("logging", "file_logging_enabled", enabled)
            config.save()
            
            # Enable or disable file logging
            if enabled:
                if setup_file_logging():
                    logging.info("File logging enabled from UI")
                    messagebox.showinfo("Success", "File logging enabled")
                else:
                    messagebox.showerror("Error", "Failed to enable file logging")
                    self.file_logging_var.set(False)
            else:
                if remove_file_logging():
                    logging.info("File logging disabled from UI")
                    messagebox.showinfo("Success", "File logging disabled")
                else:
                    messagebox.showerror("Error", "Failed to disable file logging")
                    self.file_logging_var.set(True)
            
            # Update display
            self.update_log_path_display()
            
        except Exception as e:
            logging.error(f"Error toggling file logging: {e}")
            messagebox.showerror("Error", f"Failed to toggle file logging: {e}")
    
    def update_log_path_display(self):
        """Update the log file path label."""
        try:
            from core.logging_utils import get_log_file_path, is_file_logging_enabled
            
            if is_file_logging_enabled():
                log_path = get_log_file_path()
                self.log_path_label.config(text=f"Log file: {log_path}")
            else:
                self.log_path_label.config(text="File logging is disabled")
        except Exception as e:
            logging.error(f"Error updating log path display: {e}")
            self.log_path_label.config(text="")
    
    def open_logs_folder(self):
        """Open the logs folder in file explorer."""
        try:
            from core.config import get_config
            import platform
            
            config = get_config()
            log_dir = config.get("logging", "log_directory") or "logs"
            
            # Ensure directory exists
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Open in file explorer based on platform
            system = platform.system()
            if system == "Windows":
                os.startfile(log_dir)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", log_dir])
            else:  # Linux
                subprocess.run(["xdg-open", log_dir])
            
            logging.info(f"Opened logs folder: {log_dir}")
        except Exception as e:
            logging.error(f"Error opening logs folder: {e}")
            messagebox.showerror("Error", f"Failed to open logs folder: {e}")

    def _install_linux(self):
        """Register the app with the Linux desktop (Settings button handler)."""
        try:
            from platforms.linux.linux_install import install
            success, msg = install()
            if success:
                messagebox.showinfo("Added to Applications", msg)
                if hasattr(self, 'install_btn'):
                    self.install_btn.config(text="✓ Already in Applications", state="disabled")
            else:
                messagebox.showerror("Registration Failed", msg)
        except Exception as e:
            logging.error(f"Linux install failed: {e}")
            messagebox.showerror("Error", str(e))

    def _install_windows(self):
        """Create a Start Menu shortcut (Settings button handler)."""
        try:
            exe_path = os.path.abspath(sys.executable)
            start_menu = os.path.join(
                os.environ.get("APPDATA", ""),
                r"Microsoft\Windows\Start Menu\Programs"
            )
            shortcut_path = os.path.join(start_menu, "PyCron Video Alarm.lnk")

            # Try win32com first (available when pywin32 is installed)
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.TargetPath = exe_path
                shortcut.WorkingDirectory = os.path.dirname(exe_path)
                shortcut.Description = "PyCron Video Alarm"
                # Try to set icon
                ico = os.path.join(os.path.dirname(exe_path), "alarm_icon7.ico")
                if os.path.exists(ico):
                    shortcut.IconLocation = ico
                shortcut.save()
            except ImportError:
                # Fallback: use winshell if available
                import winshell
                with winshell.shortcut(shortcut_path) as s:
                    s.path = exe_path
                    s.working_directory = os.path.dirname(exe_path)
                    s.description = "PyCron Video Alarm"

            messagebox.showinfo(
                "Added to Start Menu",
                f"Shortcut created:\n{shortcut_path}\n\n"
                "PyCron Video Alarm now appears in your Start Menu."
            )
            if hasattr(self, 'install_btn'):
                self.install_btn.config(text="✓ Added to Start Menu", state="disabled")

        except Exception as e:
            logging.error(f"Windows Start Menu install failed: {e}")
            messagebox.showerror(
                "Installation Failed",
                f"Could not create Start Menu shortcut:\n{e}\n\n"
                "You can manually pin the executable to your Start Menu by right-clicking it."
            )

    def init_help_tab(self):
        """Initialize the Help tab with usage instructions and debug info."""
        from .components import ScrollableFrame
        
        # Main Container
        self.help_scroll = ScrollableFrame(self.help_frame)
        self.help_scroll.pack(fill=tk.BOTH, expand=True)
        
        main_layout = self.help_scroll.scrollable_frame

        # Help Text Container
        help_container = ttk.Frame(main_layout)
        help_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        instructions = """
Juke32 - PyCron Video Alarm Manager
Info: juke32/PyCronVideoAlarm

1. Setting Alarms
   - Go to the 'Alarms' tab.
   - Enter time in 12-hour or 24-hour format.
   - Use 'Sleep Cycles' to calculate optimal wake times.
   - Click 'SET ALARM' to schedule.

2. Creating Sequences
   - Go to the 'Sequences' tab.
   - Click 'New' to start fresh.
   - Add actions like 'play_video', 'open_url', etc.
   - Click 'Save' to store your sequence.
   - Click 'Test' to try it immediately.

3. Features
   - Keep Awake: Prevent computer from sleeping.
   - Black Screen / Dim Display: Manage screen during sleep.
   - Party Mode: Instant random video playback!

Support the project: https://ko-fi.com/juke32

Enjoy your wake-up experience!
        """
        num_lines = len(instructions.strip().split('\n'))
        help_text = tk.Text(help_container, wrap=tk.WORD, font=('Arial', 11), height=num_lines, relief="flat", borderwidth=0)
        help_text.pack(fill=tk.BOTH, expand=True)
        
        help_text.insert(tk.END, instructions.strip())
        help_text.configure(state='disabled') # Read-only
        
        # Debug Footer
        debug_frame = ttk.LabelFrame(main_layout, text="Debug Information", padding=10)
        debug_frame.pack(fill=tk.X, padx=10, pady=10)
        
        import platform
        debug_info = [
            f"OS: {platform.system()} {platform.release()}",
            f"Python: {sys.version.split()[0]}",
            f"Directory: {os.getcwd()}",
            f"User: {os.getlogin()}"
        ]
        
        for info in debug_info:
            ttk.Label(debug_frame, text=info, font=("Consolas", 8)).pack(anchor=tk.W)
            
        ttk.Button(debug_frame, text="Show Scheduler Debug Info", command=self._show_scheduler_debug).pack(anchor=tk.W, pady=5)

    def init_main_tab(self):
        """Initialize the main tab with modern accordion layout."""
        from .components import ScrollableFrame, ActionCard
        
        # Top Control Bar (Name, Save, Load)
        control_bar = ttk.Frame(self.main_frame, style='Card.TFrame', padding=10)
        control_bar.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Right-aligned buttons (Pack these first so they stay visible)
        btn_container = ttk.Frame(control_bar, style='Card.TFrame')
        btn_container.pack(side=tk.RIGHT, padx=5)
        
        # Removed Duplicate button as requested. Compact buttons.
        ttk.Button(btn_container, text="▶ Test", width=8, command=self.test_sequence).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_container, text="Save", width=6, command=self.save_sequence).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_container, text="Load", width=6, command=self.load_sequence).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_container, text="New", width=6, command=self.new_sequence).pack(side=tk.RIGHT, padx=2)

        # Left-aligned Name Input (Takes remaining space)
        ttk.Label(control_bar, text="Sequence Name:", style='Card.TLabel').pack(side=tk.LEFT, padx=5)
        self.sequence_name = ttk.Entry(control_bar, font=("Segoe UI", 12))
        self.sequence_name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Footer -> Moved to Top: Add New Action
        add_frame = ttk.Frame(self.main_frame, style='Card.TFrame', padding=10)
        add_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(add_frame, text="Add Action:", style='Card.TLabel').pack(side=tk.LEFT)
        
        self.action_type = ttk.Combobox(add_frame, state="readonly", width=20)
        try:
            from logic.actions import ACTION_TYPES
            self.action_type['values'] = ACTION_TYPES
            self.action_type.set(ACTION_TYPES[0] if ACTION_TYPES else "")
        except ImportError:
            self.action_type['values'] = ["play_video", "open_url"]
            
        self.action_type.pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="+ Add to End", command=self.add_action).pack(side=tk.LEFT)

        # Main Content Area (Split: List on Left/Center, "Add New" tools on bottom or side?)
        # User requested: "One screen where you can see actions... one open at a time"
        # We'll use a Scrollable Vertical List of ActionCards.
        
        list_container = ttk.Frame(self.main_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # The Scrollable Area
        self.action_scroll = ScrollableFrame(list_container)
        self.action_scroll.pack(fill=tk.BOTH, expand=True)

    def render_action_list(self):
        """Re-render the list of ActionCards based on current_sequence."""
        from .components import ActionCard
        
        # Temporarily hide the scrollable area to reduce flickering
        self.action_scroll.canvas.pack_forget()
        
        # Clear existing
        for widget in self.action_scroll.scrollable_frame.winfo_children():
            widget.destroy()
            
        if not self.current_sequence:
            self.action_scroll.canvas.pack(side="left", fill="both", expand=True)
            return

        callbacks = {
            'play': self.play_action_by_index,
            'update': self.update_action_from_card,
            'remove': self.remove_action_by_index,
            'move_up': self.move_action_up_by_index,
            'move_down': self.move_action_down_by_index,
            'move_to': self.move_action_to_index,
            'duplicate': self.duplicate_action_by_index,
            'play_from': self.play_sequence_from_index
        }
        
        for i, action in enumerate(self.current_sequence.actions):
            card = ActionCard(
                self.action_scroll.scrollable_frame,
                action_index=i,
                action_data={'type': action.action_type, 'config': action.config},
                callbacks=callbacks
            )
            card.pack(fill=tk.X, pady=2)
        
        # Update layout and show the canvas again
        self.action_scroll.scrollable_frame.update_idletasks()
        self.action_scroll.canvas.pack(side="left", fill="both", expand=True)

    # --- Accordion Callbacks ---
    def play_action_by_index(self, index):
        """Play a single action by index."""
        if 0 <= index < len(self.current_sequence.actions):
            action = self.current_sequence.actions[index]
            import threading
            from logic.actions import execute_action
            threading.Thread(
                target=lambda: execute_action(action.action_type, action.config),
                daemon=True
            ).start()
    
    def update_action_from_card(self, index, new_config):
        if 0 <= index < len(self.current_sequence.actions):
            self.current_sequence.actions[index].config = new_config
            # Re-render to show updated summary? Or just flash?
            # Re-rendering might close the accordion, which is annoying.
            # ideally updates summary label.
            # For now, let's just log and maybe update title if possible, or just leave it.
            logging.info(f"Updated action {index}")
            self.refresh_action_list() # This WILL close the accordion... trade-off.
            
    def remove_action_by_index(self, index):
        self.current_sequence.remove_action(index)
        self.refresh_action_list()
        
    def move_action_up_by_index(self, index):
        if index > 0:
            self.current_sequence.move_action(index, index - 1)
            self.refresh_action_list()
            
    def move_action_down_by_index(self, index):
        if index < len(self.current_sequence.actions) - 1:
            self.current_sequence.move_action(index, index + 1)
            self.refresh_action_list()

    def move_action_to_index(self, from_index, to_index):
        """Move an action from one index to another."""
        if 0 <= from_index < len(self.current_sequence.actions) and \
           0 <= to_index < len(self.current_sequence.actions):
            self.current_sequence.move_action(from_index, to_index)
            self.refresh_action_list()

            self.refresh_action_list()

    def duplicate_action_by_index(self, index):
        """Duplicate an action and insert it after the original."""
        if 0 <= index < len(self.current_sequence.actions):
            original = self.current_sequence.actions[index]
            # Deep copy config to avoid reference issues
            import copy
            new_config = copy.deepcopy(original.config)
            self.current_sequence.insert_action(index + 1, original.action_type, new_config)
            self.refresh_action_list()

    def play_sequence_from_index(self, index):
        """Play sequence starting from the given index."""
        if not self.current_sequence or index < 0 or index >= len(self.current_sequence.actions):
            return
            
        logging.info(f"Playing sequence from index {index}")
        import threading
        def run_partial():
            from logic.actions import execute_action
            # Slice the actions list from index to end
            actions_to_run = self.current_sequence.actions[index:]
            for action in actions_to_run:
                execute_action(action.action_type, action.config)
        
        threading.Thread(target=run_partial, daemon=True).start()

    # --- Legacy Adaptors ---
    def refresh_action_list(self):
        """Legacy name, forwards to render_action_list"""
        self.render_action_list()

    def add_action(self):
        """Add action from the footer combo."""
        action_type = self.action_type.get()
        if not action_type or not self.current_sequence: return
        
        from logic.actions import get_action_template
        config = get_action_template(action_type)
        
        self.current_sequence.add_action(action_type, config)
        self.render_action_list()

    # --- Unused Legacy D&D Handlers (Removed) ---
    def on_action_click(self, event): pass
    def on_action_drag(self, event): pass
    def on_action_drop(self, event): pass
    def show_action_context_menu(self, event): pass
    def play_selected_action(self): pass
    def play_from_selected(self): pass


    def init_alarms_tab(self):
        control_frame = ttk.Frame(self.alarms_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        # Sleep Cycles
        sleep_frame = ttk.LabelFrame(control_frame, text="Sleep Cycles")
        sleep_frame.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        
        self.sleep_cycle_info_label = ttk.Label(sleep_frame, text=self._sleep_cycle_info_text(), wraplength=600)
        self.sleep_cycle_info_label.grid(row=0, column=0, columnspan=7, padx=5, pady=5)
        
        self.sleep_cycle_buttons = []
        # Cycle hours are exactly 1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5
        # The offset is added on top of that logic
        base_cycles = [
            (1, 1.5), (2, 3.0), (3, 4.5), (4, 6.0),
            (5, 7.5), (6, 9.0), (7, 10.5)
        ]
        
        for i, (cycle_num, cycle_hours) in enumerate(base_cycles):
            btn = ttk.Button(sleep_frame, text="", command=lambda h=cycle_hours: self.set_sleep_cycle(h))
            btn.grid(row=1, column=i, padx=1, pady=1, sticky="ew")
            sleep_frame.grid_columnconfigure(i, weight=1)
            self.sleep_cycle_buttons.append({"btn": btn, "cycle_num": cycle_num, "cycle_hours": cycle_hours})
            
        self.update_sleep_cycle_buttons()

        # --- Row 1: Alarm Time (No Box, Big) ---
        input_row = ttk.Frame(control_frame)
        input_row.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)
        
        from core.config import get_config
        config = get_config()
        format = config.get("ui", "time_format") or "12h"
        
        # Time Frame (No Box)
        time_frame = ttk.Frame(input_row)
        time_frame.pack(expand=True, fill=tk.NONE)
        
        ttk.Label(time_frame, text="Alarm Time", font=("Segoe UI", 12, "bold")).pack(pady=(0, 2))
        
        self.time_input_container = ttk.Frame(time_frame)
        self.time_input_container.pack()
        
        big_font = ('Arial', 48)
        
        # 12-hour
        self.ampm_container = ttk.Frame(self.time_input_container)
        if format in ("12h", "Both"):
            self.ampm_container.pack(side=tk.LEFT, padx=10)
        
        self.ampm_hour = ttk.Entry(self.ampm_container, width=3, font=big_font)
        self.ampm_hour.pack(side=tk.LEFT)
        ttk.Label(self.ampm_container, text=":", font=big_font).pack(side=tk.LEFT)
        self.ampm_minute = ttk.Entry(self.ampm_container, width=3, font=big_font)
        self.ampm_minute.pack(side=tk.LEFT)
        
        ampm_radio_frame = ttk.Frame(self.ampm_container)
        ampm_radio_frame.pack(side=tk.LEFT, padx=5)
        self.time_format = tk.StringVar(value="AM")
        ttk.Radiobutton(ampm_radio_frame, text="AM", variable=self.time_format, value="AM", command=self.handle_ampm_change).pack(side=tk.TOP)
        ttk.Radiobutton(ampm_radio_frame, text="PM", variable=self.time_format, value="PM", command=self.handle_ampm_change).pack(side=tk.BOTTOM)
        
        if format == "Both":
            ttk.Label(self.time_input_container, text="=", font=big_font).pack(side=tk.LEFT, padx=15)

        # 24-hour
        self.mil_container = ttk.Frame(self.time_input_container)
        if format in ("24h", "Both"):
            self.mil_container.pack(side=tk.LEFT, padx=10)
        
        self.mil_label = ttk.Label(self.mil_container, text="24-Hour:" if format in ("24h", "Both") else "", font=('Arial', 12) if format in ("24h", "Both") else None)
        self.mil_label.pack(side=tk.LEFT)
        
        self.military_hour = ttk.Entry(self.mil_container, width=3, font=big_font)
        self.military_hour.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.mil_container, text=":", font=big_font).pack(side=tk.LEFT)
        self.military_minute = ttk.Entry(self.mil_container, width=3, font=big_font)
        self.military_minute.pack(side=tk.LEFT, padx=2)
        
        # --- Row 2: Sequence (One Line) ---
        seq_frame = ttk.Frame(control_frame)
        seq_frame.grid(row=2, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="ew")
        
        ttk.Label(seq_frame, text="Sequence to Play:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=(5, 10))
        
        self.sequence_var = tk.StringVar()
        self.sequence_combo = ttk.Combobox(seq_frame, textvariable=self.sequence_var, state="readonly", font=('Arial', 12))
        self.sequence_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.refresh_sequence_list()
        
        # --- Row 3: Days ---
        # Use LabelFrame to restart the box border
        days_frame = ttk.LabelFrame(control_frame, text="Recurring Days (no days selected = one-time alarm)")
        days_frame.grid(row=3, column=0, columnspan=4, padx=5, pady=20, sticky="ew")

        # Inner label removed (merged into frame title) or kept if we want extra styling?
        # User wanted "Recurring days ... one time alarm" above the days.
        # Putting it in the title achieves this with the box.

        self.day_vars = {}
        days_list = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        
        # Configure style for larger checkboxes
        s = ttk.Style()
        s.configure("Big.TCheckbutton", font=("Segoe UI", 11, "bold"))
        
        for i, day in enumerate(days_list):
            var = tk.BooleanVar(value=False)
            self.day_vars[day] = var
            # Use the custom style
            ttk.Checkbutton(days_frame, text=day, variable=var, style="Big.TCheckbutton").grid(row=0, column=i, padx=2, pady=5)
            
        # Daily Shortcut
        ttk.Button(days_frame, text="Select All/Daily", command=self.toggle_all_days).grid(row=0, column=7, padx=10, pady=5)


        # Action Frame for set alarm
        action_frame = ttk.Frame(control_frame)
        action_frame.grid(row=4, column=0, columnspan=4, pady=10)

        # Sleep Mode Button
        self.sleep_mode_button = ttk.Button(action_frame, text="Sleep Mode is Off", command=self.toggle_sleep_mode)
        self.sleep_mode_button.pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(action_frame, orient='vertical').pack(side=tk.LEFT, fill='y', padx=10, pady=5)
        

        # Set Alarm Button and Controls        
        self.set_alarm_btn = ttk.Button(action_frame, text="SET ALARM", command=self.set_alarm, style='Header.TButton')
        self.set_alarm_btn.pack(side=tk.LEFT, padx=5)


        # Duplicate button removed as requested
        # ttk.Button(action_frame, text="DUPLICATE", command=self.duplicate_selected_alarm).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="DELETE", command=self.delete_selected_alarm).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="REFRESH", command=self.refresh_alarm_list).pack(side=tk.LEFT, padx=5)
        
        self.cancel_edit_btn = ttk.Button(action_frame, text="CANCEL EDIT", command=self.cancel_edit)
        
        # Init Defaults
        self.ampm_hour.insert(0, "07")
        self.ampm_minute.insert(0, "30")
        self.military_hour.insert(0, "07")
        self.military_minute.insert(0, "30")
        
        # Bindings
        self.bind_time_entry_events(self.military_hour, 23, is_hour=True, is_24hour=True)
        self.bind_time_entry_events(self.military_minute, 59)
        self.bind_time_entry_events(self.ampm_hour, 12, is_hour=True)
        self.bind_time_entry_events(self.ampm_minute, 59)
        
        for widget in (self.ampm_hour, self.ampm_minute, self.military_hour, self.military_minute):
            widget.bind('<FocusOut>', self.sync_time_formats)
            widget.bind('<Return>', self.sync_time_formats)

        # Alarm List
        list_frame = ttk.Frame(self.alarms_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.alarm_list = ttk.Treeview(list_frame, columns=("time", "sequence", "days", "enabled"), show="headings")
        self.alarm_list.heading("time", text="Time")
        self.alarm_list.heading("sequence", text="Sequence")
        self.alarm_list.heading("days", text="Days")
        self.alarm_list.heading("enabled", text="Status")
        self.alarm_list.column("enabled", width=100, anchor=tk.CENTER)
        self.alarm_list.pack(fill=tk.BOTH, expand=True)
        
        # Next Alarm Ticker
        self.next_alarm_var = tk.StringVar(value="Next Alarm: None")
        ttk.Label(list_frame, textvariable=self.next_alarm_var, font=("Segoe UI", 10, "bold"), foreground="#007ACC").pack(anchor=tk.W, pady=5)
        
        # Initial load
        self.refresh_alarm_list()
        
        # Bind single-click to edit (User Request: "click any alarm and it pulls up")
        self.alarm_list.bind("<<TreeviewSelect>>", self.edit_selected_alarm)


    def init_help_tab(self):
        """Initialize the Help tab with subtabs."""
        # Create Notebook for Subtabs
        help_notebook = ttk.Notebook(self.help_frame)
        help_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 1. Overview Tab
        overview_frame = ttk.Frame(help_notebook)
        help_notebook.add(overview_frame, text="Overview")
        self.init_help_overview(overview_frame)
        
        # 2. System Info Tab
        sysbox_frame = ttk.Frame(help_notebook)
        help_notebook.add(sysbox_frame, text="System Info")
        self.init_help_system_info(sysbox_frame)
        
        # 3. Troubleshooting Tab
        trouble_frame = ttk.Frame(help_notebook)
        help_notebook.add(trouble_frame, text="Troubleshooting")
        self.init_help_troubleshooting(trouble_frame)

        # 4. License Tab
        license_frame = ttk.Frame(help_notebook)
        help_notebook.add(license_frame, text="License")
        self.init_help_license(license_frame)

    def init_help_overview(self, parent):
        from .theme import COLORS
        import tkinter.scrolledtext as scrolledtext
        
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_text = scrolledtext.ScrolledText(
            container, 
            wrap=tk.WORD, 
            font=('Arial', 11), 
            bg=COLORS['bg_light'], 
            fg=COLORS['text_main'], 
            insertbackground=COLORS['text_main']
        )
        help_text.pack(fill=tk.BOTH, expand=True)
        
        instructions = """
Quickstart Guide

1. Create a Sequence  (SEQUENCES tab)
   - Click 'New' to start a fresh sequence.
   - Select an action from the dropdown (e.g. 'play_video') and click '+ Add to End'.
   - Configure the action — choose a video file, URL, etc.
   - Click 'Save', then '▶ Test' to verify it works.

2. Set Your Alarm  (ALARMS tab)
   - Select your saved sequence from the dropdown.
   - Enter your wake-up time (12h or 24h — set your preference in Settings).
   - Choose recurring days, or leave blank for a one-time alarm.
   - Click 'SET ALARM'. The alarm is now registered with your OS scheduler.

3. Important: Power & Session
   - Your computer must be ON and logged in for alarms to fire.
   - Linux: keep the app open to prevent the computer from sleeping (Sleep Mode).
   - Windows: may run a missed alarm at next boot if the PC was off at alarm time.

4. First Time Setup
   - MPV will automatically prompt for installation if not found (Linux/Windows via winget).
   - Go to Settings → Install → 'Add to Applications' (Linux) or 'Add to Start Menu' (Windows)
     to register the app with your launcher and give it the correct icon.
   - Your build version is shown at the top of the Settings tab.
        """
        help_text.insert(tk.END, instructions.strip())
        help_text.configure(state='disabled')

    def init_help_system_info(self, parent):
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        import platform, sys
        try:
            from core.version import get_build_version
            app_version = get_build_version()
        except Exception:
            app_version = "Unknown"

        info = [
            ("App Version", app_version),
            ("OS Platform", platform.platform()),
            ("OS Release", platform.release()),
            ("Python Version", sys.version.split()[0]),
            ("Processor", platform.processor()),
            ("Machine", platform.machine()),
            ("App Location", os.getcwd())
        ]
        
        ttk.Label(container, text="System Information", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W, pady=(0, 20))
        
        for label, value in info:
            row = ttk.Frame(container)
            row.pack(fill=tk.X, pady=5)
            lbl = ttk.Label(row, text=f"{label}:", width=15, font=("Segoe UI", 10, "bold"))
            lbl.pack(side=tk.LEFT)
            val = ttk.Label(row, text=value, font=("Consolas", 10))
            val.pack(side=tk.LEFT)

        # Archive Name — pre-baked at build time, click to copy
        try:
            from core.version import get_archive_name
            dated_name = get_archive_name() or "N/A (dev build)"
        except Exception:
            dated_name = "N/A (dev build)"

        archive_row = ttk.Frame(container)
        archive_row.pack(fill=tk.X, pady=5)
        ttk.Label(archive_row, text="Archive Name:", width=15, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        copy_lbl = ttk.Label(archive_row, text=dated_name, font=("Consolas", 10), cursor="hand2", foreground="#4FC3F7")
        copy_lbl.pack(side=tk.LEFT)
        ttk.Label(archive_row, text=" ← click to copy", font=("Segoe UI", 8), foreground="#888").pack(side=tk.LEFT, padx=(4, 0))

        def _copy_archive(e, name=dated_name, lbl=copy_lbl):
            self.clipboard_clear()
            self.clipboard_append(name)
            lbl.config(text="✓ Copied!")
            self.after(1500, lambda: lbl.config(text=name))

        copy_lbl.bind("<Button-1>", _copy_archive)

        # Directories Section
        ttk.Label(container, text="System Directories", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, pady=(20, 10))
        from core.config import get_app_data_dir
        
        dirs = [
             ("App Root", os.getcwd()),
             ("Videos", os.path.join(os.getcwd(), "video")),
             ("Sequences", os.path.join(get_app_data_dir(), "sequences")),
             ("Journals", os.path.join(os.getcwd(), "journals")),
             ("Captures", os.path.join(os.getcwd(), "captures")),
             ("Audio/Notes", os.path.join(os.getcwd(), "audio")) # Assuming audio dir exists or is desired
        ]
        
        for label, path in dirs:
            row = ttk.Frame(container)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=f"{label}:", width=15, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
            
            # Clickable path?
            path_lbl = ttk.Label(row, text=path, font=("Consolas", 9), cursor="hand2")
            path_lbl.pack(side=tk.LEFT)
            
            def open_dir(p=path):
                import webbrowser
                if os.path.exists(p):
                    webbrowser.open(p)
                else:
                    try:
                        os.makedirs(p)
                        webbrowser.open(p)
                    except: pass
                    
            path_lbl.bind("<Button-1>", lambda e, p=path: open_dir(p))
            
    def init_help_license(self, parent):
        """Display the LICENSE file in the Help → License sub-tab."""
        container = ttk.Frame(parent, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        license_text = scrolledtext.ScrolledText(
            container, wrap=tk.WORD,
            font=("Consolas", 9), state="normal"
        )
        license_text.pack(fill=tk.BOTH, expand=True)
        license_text.insert(tk.END, self._read_license())
        license_text.configure(state="disabled")

    def init_help_troubleshooting(self, parent):
        from .theme import COLORS
        import webbrowser
        
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(container, text="Troubleshooting & Support", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W, pady=(0, 20))
        
        # Common Fixes
        fixes_frame = ttk.LabelFrame(container, text="Common Fixes", padding=10)
        fixes_frame.pack(fill=tk.X, pady=10)
        
        common_text = """
• Video won't play? Ensure mpv is installed and working: run 'mpv --version' in a terminal.
• No alarms firing? Check the 'Next Alarm' text on the ALARMS tab. If it says 'None', try re-setting the alarm.
• Linux - Cron issues? Ensure crontab access by running 'crontab -l' in a terminal.
  - 'no crontab for user' = you have access (no entries yet).
  - 'permission denied' = run: echo $USER | sudo tee -a /etc/cron.allow
• Windows - Scheduler issues? Verify tasks exist in Task Scheduler under the 'PyCronVideoAlarm' folder.
• Audio too quiet? Test the 'set_system_volume' action in your sequence. On Linux ensure your user has audio device access.
• App has wrong icon or doesn't appear in launcher? Go to Settings → Install → 'Add to Applications'.
• Not sure what version you have? Check the top of the Settings tab.
        """
        ttk.Label(fixes_frame, text=common_text.strip(), wraplength=700, justify=tk.LEFT).pack(anchor=tk.W)

        # NirCmd Section
        nir_frame = ttk.LabelFrame(container, text="Windows Automation (NirCmd)", padding=10)
        nir_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(nir_frame, text="For advanced features like Monitor Control or Volume on Windows, you need nircmd.exe.", wraplength=700).pack(anchor=tk.W)
        
        link_box = tk.Label(nir_frame, bg="#444444", padx=10, pady=5, cursor="hand2")
        link_box.pack(anchor=tk.W, pady=10)
        link_nir = tk.Label(link_box, text="Download NirCmd (launcher.nirsoft.net)", fg="#4FC3F7", bg="#444444", font=("Segoe UI", 10, "bold"))
        link_nir.pack()
        
        def open_nir(e): webbrowser.open("https://launcher.nirsoft.net/downloads/index.html")
        link_box.bind("<Button-1>", open_nir)
        link_nir.bind("<Button-1>", open_nir)
        
        ttk.Label(nir_frame, text="Instructions: Place 'nircmd.exe' in the 'bin' folder of the app directory.", wraplength=700).pack(anchor=tk.W)

        # Support Section
        sup_frame = ttk.LabelFrame(container, text="Report Bugs & Support", padding=10)
        sup_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(sup_frame, text="Need more help or found a bug?", wraplength=700).pack(anchor=tk.W)
        
        gh_box = tk.Label(sup_frame, bg="#444444", padx=10, pady=5, cursor="hand2")
        gh_box.pack(anchor=tk.W, pady=10)
        link_gh = tk.Label(gh_box, text="Open GitHub Issues", fg="#4FC3F7", bg="#444444", font=("Segoe UI", 10, "bold"))
        link_gh.pack()
        
        def open_gh(e): webbrowser.open("https://github.com/juke32/PyCronVideoAlarm/issues")
        gh_box.bind("<Button-1>", open_gh)
        link_gh.bind("<Button-1>", open_gh)

    def test_alarm(self):
        """Alias for CLI testing flag to trigger current sequence."""
        self.test_sequence()

    def test_sequence(self):
        """Test the current sequence immediately via a temporary file."""
        if not self.current_sequence:
            messagebox.showwarning("Warning", "No sequence loaded.")
            return

        temp_name = self.sequence_name.get().strip()
        if not temp_name:
            temp_name = "New Sequence"
            
        from core.config import get_app_data_dir
        temp_dir = os.path.join(get_app_data_dir(), "sequences", "temp")
        
        try:
            os.makedirs(temp_dir, exist_ok=True)
            self.current_sequence.save(temp_dir, filename=f"{temp_name}.json")
            logging.info(f"Saved temporary sequence for testing: temp/{temp_name}.json")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save temp sequence: {e}")
            return
            
        messagebox.showinfo("Temporary Run", 
                            "Temporarily running sequence...\n\n"
                            "This test is running from a temporary file to prevent overwriting your existing sequence.\n\n"
                            "Don't forget to click 'Save' if this works exactly how you would like!")

        # Run in a separate thread to spawn the subprocess
        import threading
        def run_test():
            try:
                from core.config import get_app_data_dir
                temp_file_path = os.path.join(get_app_data_dir(), "sequences", "temp", f"{temp_name}")
                
                cmd = [sys.executable, "src/main.py", "--execute-sequence", temp_file_path]
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, "--execute-sequence", temp_file_path]
                
                # Use subprocess.Popen so we don't block the UI while testing
                subprocess.Popen(cmd)
                logging.info(f"Spawned test subprocess for temp sequence {temp_name}")
            except Exception as e:
                # Catch unexpected top-level errors
                logging.error(f"Test sequence failed: {e}")
                self.after(0, lambda: messagebox.showerror("Test Error", f"Unexpected error:\n{str(e)}"))
        
        threading.Thread(target=run_test, daemon=True).start()

    def set_alarm(self):
        """Set an alarm for the current time and selected sequence."""
        sequence_name = self.sequence_var.get()
        if not sequence_name:
             messagebox.showerror("Error", "No sequence selected to set alarm for.")
             return
             
        try:
            h = int(self.military_hour.get())
            m = int(self.military_minute.get())
            
            # If editing, we keep the date/recurrence intact if possible, or just overwrite current day?
            # A simple approach: 
            # If One-Time: Use current date (or tomorrow if passed).
            # If Recurring: Just use the time + days.
            
            # Logic:
            alarm_time = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
            if alarm_time < datetime.now() and not self.editing_alarm:
                # Only Auto-increment day if NOT editing (or maybe if editing and time is past?)
                # If editing, user might mean "change time to 8am" (which is tomorrow).
                # Let's keep "Next valid time" logic.
                alarm_time += timedelta(days=1)
                
            # Get selected days
            selected_days = [day for day, var in self.day_vars.items() if var.get()]
            one_time = len(selected_days) == 0
            
            from logic.scheduler import AlarmScheduler
            scheduler = AlarmScheduler()
            
            # If editing, remove old one first -> REMOVED as per request to simplify
            # if self.editing_alarm: ...
            
            logging.info(f"Attempting to set alarm for {alarm_time.strftime('%Y-%m-%d %H:%M')} using sequence '{sequence_name}'")
            
            success, msg = scheduler.add_alarm(alarm_time, sequence_name, days=selected_days, one_time=one_time)
            if success:
                messagebox.showinfo("Success", msg)
                logging.info(f"Alarm successfully set via scheduler")
                self.after(500, self.refresh_alarm_list)
            else:
                messagebox.showerror("Error", f"Failed to set alarm:\n{msg}")
                logging.error(f"Scheduler failed to add alarm: {msg}")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid time")

    def edit_selected_alarm(self, event=None):
        """Populate inputs from selected alarm for editing."""
        selected = self.alarm_list.selection()
        if not selected: return
        
        item = self.alarm_list.item(selected[0])
        values = item['values']
        if not values: return
        
        
        time_str, seq_name, days_str, _ = values
        
        from core.config import get_app_data_dir
        # Validate Sequence Existence
        seq_path = os.path.join(get_app_data_dir(), "sequences", f"{seq_name}.json")
        if not os.path.exists(seq_path):
             messagebox.showwarning("Missing Sequence", f"The sequence '{seq_name}' was not found!\n\nYou can delete this alarm or select a valid sequence.")
        
        # 1. Set Time
        try:
            h, m = map(int, time_str.split(':'))
            self.military_hour.delete(0, tk.END); self.military_hour.insert(0, f"{h:02d}")
            self.military_minute.delete(0, tk.END); self.military_minute.insert(0, f"{m:02d}")
            self.sync_time_formats() # Update 12h view
        except ValueError:
            pass
            
        # 2. Set Sequence
        self.sequence_var.set(seq_name)
        
        # 3. Set Days
        # Reset all first
        for var in self.day_vars.values(): var.set(False)
        
        if "Daily" in days_str:
            for var in self.day_vars.values(): var.set(True)
        elif "Once" in days_str or not days_str:
            # No days checked
            pass 
        else:
            # Parse commas "MON, WED"
            for d in days_str.split(','):
                d = d.strip().upper()
                if d in self.day_vars:
                    self.day_vars[d].set(True)
                    
        # 4. Just Pre-fill (No Editing State)
        self.set_alarm_btn.config(text="SET ALARM")
        self.cancel_edit_btn.pack_forget()
        
        # We don't track editing_alarm anymore, so "Set Alarm" will always attempt to add new.
        # If user wants to "Update", they should Delete then Add.
        self.editing_alarm = None 
        
    def cancel_edit(self):
        """Clear inputs."""
        self.editing_alarm = None
        self.set_alarm_btn.config(text="SET ALARM")
        self.cancel_edit_btn.pack_forget()
        
        # Reset to defaults
        self.military_hour.delete(0, tk.END); self.military_hour.insert(0, "07")
        self.military_minute.delete(0, tk.END); self.military_minute.insert(0, "30")
        self.sync_time_formats()
        self.sequence_combo.current(0) if self.sequence_combo['values'] else None
        for var in self.day_vars.values(): var.set(False)



    def refresh_sequence_list(self):
        """Populate the sequence combobox with available sequences."""
        from core.config import get_app_data_dir
        seq_dir = os.path.join(get_app_data_dir(), "sequences")
        if not os.path.exists(seq_dir): os.makedirs(seq_dir)
        
        sequences = [f[:-5] for f in os.listdir(seq_dir) if f.endswith(".json")]
        self.sequence_combo['values'] = sequences
        if sequences and not self.sequence_var.get():
            self.sequence_combo.current(0)

    def toggle_all_days(self):
        """Toggle all day checkboxes (shortcut for Daily)."""
        all_checked = all(v.get() for v in self.day_vars.values())
        for var in self.day_vars.values():
            var.set(not all_checked)

    def refresh_alarm_list(self):
        """Refresh the Treeview with alarms from the scheduler."""
        for item in self.alarm_list.get_children():
            self.alarm_list.delete(item)
            
        from logic.scheduler import AlarmScheduler
        scheduler = AlarmScheduler()
        try:
            alarms = scheduler.list_alarms()
            for alarm in alarms:
                days_str = ", ".join(alarm['days']) if isinstance(alarm['days'], list) else alarm['days']
                enabled_str = "Enabled" if alarm.get('enabled', True) else "Disabled"
                self.alarm_list.insert("", tk.END, values=(alarm['time'], alarm['sequence'], days_str, enabled_str))
            
            # Update Next Alarm Ticker
            if alarms:
                # Sort alarms by time for a rough "next" estimate
                sorted_alarms = sorted(alarms, key=lambda x: x['time'])
                self.next_alarm_var.set(f"Next Alarm: {sorted_alarms[0]['time']} ({sorted_alarms[0]['sequence']})")
            else:
                self.next_alarm_var.set("Next Alarm: None")
        except Exception as e:
            logging.error(f"Failed to refresh alarm list: {e}")

    def on_tab_changed(self, event=None):
        """Handle notebook tab switches."""
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        if current_tab == "ALARMS":
            self.refresh_sequence_list()
            self.refresh_alarm_list()
        elif current_tab == "SEQUENCES":
            self.refresh_action_list()
        elif current_tab == "SETTINGS":
            self.update_log_path_display()

    def _show_scheduler_debug(self):
        """Show detailed debug info from the scheduler."""
        from logic.scheduler import AlarmScheduler
        scheduler = AlarmScheduler()
        info = scheduler.get_debug_info()
        
        # Create a popup window
        top = tk.Toplevel(self)
        top.title("Scheduler Debug Info")
        top.geometry("600x400")
        
        text_area = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=('Consolas', 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_area.insert(tk.END, info)
        text_area.configure(state='disabled')

    def delete_selected_alarm(self):
        """Remove the selected alarm from scheduler and UI.
        
        BUG FIX (2026-02-15): This function was silently crashing because of a
        tuple unpacking mismatch. The Treeview has 4 columns (time, sequence, 
        days, enabled) but the old code tried to unpack into 3 variables:
            time_str, sequence, _ = values   # ValueError! 4 into 3
        Since there was no try/except, the function died with zero feedback.
        
        Fix: Use index access (values[0], values[1]) instead of unpacking,
        and always wrap Treeview value access in try/except.
        
        LESSON: When accessing Treeview row values, ALWAYS use index access.
        If columns are ever added/removed, index access only breaks at the
        specific index, not the entire function. And ALWAYS wrap in try/except.
        """
        selected = self.alarm_list.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an alarm to delete")
            return
            
        from logic.scheduler import AlarmScheduler
        scheduler = AlarmScheduler()
        for item in selected:
            try:
                values = self.alarm_list.item(item, 'values')
                logging.info(f"Delete button clicked. Values from Treeview: {values}")
                
                # Treeview columns: time, sequence, days, enabled (4 columns!)
                # NEVER use tuple unpacking here — use index access!
                time_str = values[0]
                sequence = values[1]
                days_str = values[2] if len(values) > 2 else ""
                
                logging.info(f"Attempting to remove alarm: sequence='{sequence}', time='{time_str}', days='{days_str}'")
                
                success, msg = scheduler.remove_alarm(sequence, time_str, days_str=days_str)
                if success:
                     logging.info(f"Removed alarm: {sequence} at {time_str} - {msg}")
                else:
                     logging.error(f"Failed to remove alarm: {msg}")
                     messagebox.showerror("Error", f"Failed to remove alarm:\n{msg}")
            except Exception as e:
                logging.exception(f"Error in delete_selected_alarm for item {item}: {e}")
                messagebox.showerror("Error", f"Unexpected error deleting alarm:\n{str(e)}")
        
        self.refresh_alarm_list()


    def new_sequence(self):
        from logic.sequence import AlarmSequence
        self.current_sequence = AlarmSequence("New Sequence")
        self.sequence_name.delete(0, tk.END)
        self.sequence_name.insert(0, "New Sequence")
        # Legacy cleanup not needed for new UI
        # self.action_list.delete(0, tk.END)
        # self.config_text.delete(1.0, tk.END)
        # self.action_type.set("")
        self.refresh_action_list()

    def load_sequence(self):
        # TODO: Define sequence directory
        from core.config import get_app_data_dir
        seq_dir = os.path.join(get_app_data_dir(), "sequences")
        if not os.path.exists(seq_dir): os.makedirs(seq_dir)
        
        file_path = filedialog.askopenfilename(initialdir=seq_dir, filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                from logic.sequence import AlarmSequence
                self.current_sequence = AlarmSequence.load(file_path)
                self.sequence_name.delete(0, tk.END)
                self.sequence_name.insert(0, self.current_sequence.name)
                self.refresh_action_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {e}")

    def duplicate_sequence(self):
        """Duplicate the current sequence."""
        if not self.current_sequence: return
        self.current_sequence.name = f"{self.current_sequence.name} (Copy)"
        self.sequence_name.delete(0, tk.END)
        self.sequence_name.insert(0, self.current_sequence.name)
        messagebox.showinfo("Info", "Sequence duplicated. Don't forget to save it!")

    def save_sequence(self):
        if not self.current_sequence: return
        try:
            name = self.sequence_name.get().strip()
            if not name:
                messagebox.showerror("Error", "Enter a sequence name")
                return
            self.current_sequence.name = name
            
            from core.config import get_app_data_dir
            seq_dir = os.path.join(get_app_data_dir(), "sequences")
            self.current_sequence.save(seq_dir)
            messagebox.showinfo("Success", "Sequence saved")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def add_action(self):
        """Add action from the footer combo."""
        action_type = self.action_type.get()
        if not action_type or not self.current_sequence: return
        
        from logic.actions import get_action_template
        config = get_action_template(action_type)
        
        self.current_sequence.add_action(action_type, config)
        self.render_action_list()

    # Legacy config text parser (replaced by individual cards)
    def legacy_add_action(self): pass

    # --- Legacy Methods (Removed/Replaced) ---
    def update_action(self): pass
    def remove_action(self): pass
    def move_action_up(self): pass
    def move_action_down(self): pass
    def on_action_select(self, event=None): pass

    def on_action_type_selected(self, event):
        # Only used in legacy split view
        pass

    # refresh_action_list is redefined in "Legacy Adaptors" section above to point to render_action_list
    # ensuring no duplicates.

    def bind_time_entry_events(self, entry, max_value, is_hour=False, is_24hour=False):
        """Bind events for time entry fields."""
        def on_focus_in(event):
            if event.widget.get():
                event.widget.select_range(0, tk.END)
            return "break"
            
        def on_key_press(event):
            if event.keysym in ('BackSpace', 'Delete', 'Left', 'Right'):
                return
            if not event.char.isdigit():
                return "break"
            
            current = event.widget.get()
            cursor_pos = event.widget.index(tk.INSERT)
            
            if cursor_pos == 0 and current:
                event.widget.icursor(len(current))
                return "break"
                
            if len(current) >= 2 and not event.widget.selection_present():
                return "break"
        
        def validate_and_adjust(event=None):
            try:
                value = event.widget.get() if event and event.widget else entry.get()
                if not value:
                    if event and event.type == '10':  # FocusOut
                        entry.delete(0, tk.END)
                        entry.insert(0, "00")
                    return
                
                value = ''.join(filter(str.isdigit, value))
                num = int(value)
                
                if is_hour:
                    if is_24hour:
                        while num >= 24: num -= 24
                    else:
                        while num > 12: num -= 12
                        if num == 0: num = 12
                else:
                    extra_hours = 0
                    while num >= 60:
                        num -= 60
                        extra_hours += 1
                    
                    if extra_hours > 0:
                        try:
                            # Simple increment for now, full sync handles the rest
                            pass 
                        except ValueError:
                            pass
                
                entry.delete(0, tk.END)
                entry.insert(0, f"{num:02d}")
                
            except ValueError:
                if event and event.type == '10':
                    entry.delete(0, tk.END)
                    entry.insert(0, "00")
        
        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<KeyPress>', on_key_press)
        entry.bind('<FocusOut>', validate_and_adjust)
        entry.bind('<Return>', validate_and_adjust)
        entry.bind('<Tab>', validate_and_adjust)

    def sync_time_formats(self, event=None):
        try:
            if event and event.widget in (self.ampm_hour, self.ampm_minute):
                # 12h -> 24h
                h = int(self.ampm_hour.get() or 12)
                m = int(self.ampm_minute.get() or 0)
                
                # Normalize
                if h < 1: h = 12
                elif h > 12: h = h % 12
                if h == 0: h = 12
                if m > 59: m = 59
                
                self.ampm_hour.delete(0, tk.END); self.ampm_hour.insert(0, f"{h:02d}")
                self.ampm_minute.delete(0, tk.END); self.ampm_minute.insert(0, f"{m:02d}")
                
                # Convert
                h24 = h
                if self.time_format.get() == "PM" and h < 12: h24 += 12
                elif self.time_format.get() == "AM" and h == 12: h24 = 0
                
                self.military_hour.delete(0, tk.END); self.military_hour.insert(0, f"{h24:02d}")
                self.military_minute.delete(0, tk.END); self.military_minute.insert(0, f"{m:02d}")
            else:
                # 24h -> 12h
                h = int(self.military_hour.get() or 0)
                m = int(self.military_minute.get() or 0)
                
                if h > 23: h %= 24
                if m > 59: m = 59
                
                self.military_hour.delete(0, tk.END); self.military_hour.insert(0, f"{h:02d}")
                self.military_minute.delete(0, tk.END); self.military_minute.insert(0, f"{m:02d}")
                
                if h >= 12:
                    self.time_format.set("PM")
                    if h > 12: h -= 12
                else:
                    self.time_format.set("AM")
                    if h == 0: h = 12
                
                self.ampm_hour.delete(0, tk.END); self.ampm_hour.insert(0, f"{h:02d}")
                self.ampm_minute.delete(0, tk.END); self.ampm_minute.insert(0, f"{m:02d}")
                
        except ValueError:
            pass

    def handle_ampm_change(self):
        try:
            h = int(self.ampm_hour.get() or 12)
            if h < 1: h = 12
            elif h > 12: h %= 12
            if h == 0: h = 12
            
            self.ampm_hour.delete(0, tk.END); self.ampm_hour.insert(0, f"{h:02d}")
            
            h24 = h
            if self.time_format.get() == "PM" and h < 12: h24 += 12
            elif self.time_format.get() == "AM" and h == 12: h24 = 0
            
            self.military_hour.delete(0, tk.END); self.military_hour.insert(0, f"{h24:02d}")
        except ValueError:
            pass

    def _sleep_cycle_info_text(self):
        """Return the info string for the Sleep Cycles section, using the configured offset."""
        from core.config import get_config
        offset = get_config().get("alarms", "sleep_offset_minutes")
        if offset is None:
            offset = 15
        
        if offset >= 0:
            return (f"SleepCalculator.com inspired — adds {offset} min to fall asleep, "
                    "then full 90-min cycles based on your chosen wake time.")
        else:
            return (f"SleepCalculator.com inspired — subtracts {abs(offset)} min, "
                    "then full 90-min cycles based on your chosen wake time.")

    def update_sleep_cycle_buttons(self):
        """Update the button text to show the correct total hours including the offset."""
        if not hasattr(self, 'sleep_cycle_buttons'):
            return
            
        from core.config import get_config
        offset = get_config().get("alarms", "sleep_offset_minutes")
        if offset is None:
            offset = 15
            
        for data in self.sleep_cycle_buttons:
            cycle_num = data["cycle_num"]
            cycle_hours = data["cycle_hours"]
            # Add offset (in hours)
            total_time = cycle_hours + (offset / 60.0)
            
            cycle_text = "Cycle" if cycle_num == 1 else "Cycles"
            btn_text = f"{cycle_num} {cycle_text}\n({total_time:.2f} hours)"
            data["btn"].config(text=btn_text)

    def set_sleep_cycle(self, hours):
        """Calculate alarm time based on current time + sleep cycle offset + cycle hours."""
        try:
            from core.config import get_config
            offset = get_config().get("alarms", "sleep_offset_minutes")
            if offset is None:
                offset = 15
            offset = int(offset)

            now = datetime.now()
            wake_time = now + timedelta(minutes=offset) + timedelta(hours=hours)

            h = wake_time.hour
            m = wake_time.minute

            self.military_hour.delete(0, tk.END); self.military_hour.insert(0, f"{h:02d}")
            self.military_minute.delete(0, tk.END); self.military_minute.insert(0, f"{m:02d}")

            # Sync to update 12h display
            self.sync_time_formats()

            logging.info(f"Sleep Cycle Set: Alarm set for {wake_time.strftime('%I:%M %p')} (in {hours}h + {offset}m)")
        except Exception as e:
            logging.error(f"Error setting sleep cycle: {e}")

    def toggle_sleep_mode(self):
        """Toggle sleep mode (Keep Awake + Dim Display + Black Box)."""
        self.sleep_mode_enabled = not self.sleep_mode_enabled
        
        if self.sleep_mode_enabled:
            # Enable sleep mode
            success = True
            
            # 1. Enable Keep Awake
            if self.power_mgr:
                try:
                    self.power_mgr.inhibit_sleep()
                    self.keep_awake_enabled = True
                    logging.info("Sleep Mode: Keep Awake enabled")
                except Exception as e:
                    logging.error(f"Sleep Mode: Failed to enable Keep Awake: {e}")
                    success = False
            else:
                logging.warning("Sleep Mode: Power manager not available")
                success = False
            
            # 2. Dim Display
            if self.display_mgr:
                try:
                    self.display_mgr.set_brightness(1)  # 1% brightness (min safe)
                    logging.info("Sleep Mode: Display dimmed to 1%")
                except Exception as e:
                    logging.error(f"Sleep Mode: Failed to dim display: {e}")
            
            # 3. Show Black Box
            try:
                self.overlay_controller.show_overlay()
                logging.info("Sleep Mode: Black box overlay shown")
            except Exception as e:
                logging.error(f"Sleep Mode: Failed to show overlay: {e}")
            
            if success:
                self.sleep_mode_button.config(text="Sleep Mode is ON")
            else:
                self.sleep_mode_button.config(text="Sleep Mode (Limited)")
        else:
            # Disable sleep mode
            # 1. Disable Keep Awake
            if self.power_mgr:
                try:
                    self.power_mgr.uninhibit_sleep()
                    self.keep_awake_enabled = False
                    logging.info("Sleep Mode: Keep Awake disabled")
                except Exception as e:
                    logging.error(f"Sleep Mode: Failed to disable Keep Awake: {e}")
            
            # 2. Restore brightness (to 100%)
            if self.display_mgr:
                try:
                    self.display_mgr.set_brightness(100)
                    logging.info("Sleep Mode: Display brightness restored")
                except Exception as e:
                    logging.error(f"Sleep Mode: Failed to restore brightness: {e}")
            
            # 3. Hide Black Box
            try:
                self.overlay_controller.hide_overlay()
                logging.info("Sleep Mode: Black box overlay hidden")
            except Exception as e:
                logging.error(f"Sleep Mode: Failed to hide overlay: {e}")
            
            self.sleep_mode_button.config(text="Sleep Mode is Off")

    def test_dim_display(self):
        """Test dimming the display to 10%."""
        if self.display_mgr:
            try:
                self.display_mgr.set_brightness(10)
                messagebox.showinfo("Dim Display", "Display dimmed to 10%.\n\nClick OK to restore brightness.")
                self.display_mgr.set_brightness(100)
            except Exception as e:
                logging.error(f"Failed to dim display: {e}")
                messagebox.showerror("Dim Display Error", f"Failed to dim display:\n{e}")
        else:
            messagebox.showwarning("Display Manager Unavailable", 
                "Display management is not available on this system.")

    def toggle_keep_awake(self):
        """Toggle the keep awake state."""
        if not self.power_mgr:
            messagebox.showerror("Keep Awake Unavailable", 
                "Power management is not available.\n\n"
                "This could be due to:\n"
                "• Missing system dependencies (DBus on Linux)\n"
                "• Insufficient permissions\n"
                "• Unsupported platform\n\n"
                "Check the console for detailed error messages.")
            return
        
        self.keep_awake_enabled = not self.keep_awake_enabled
        
        try:
            if self.keep_awake_enabled:
                self.power_mgr.inhibit_sleep()
                logging.info("Keep Awake enabled")
            else:
                self.power_mgr.uninhibit_sleep()
                logging.info("Keep Awake disabled")
        except Exception as e:
            logging.error(f"Failed to toggle keep awake: {e}")
            self.keep_awake_enabled = not self.keep_awake_enabled # Revert
            messagebox.showerror("Keep Awake Error", 
                f"Failed to {'enable' if not self.keep_awake_enabled else 'disable'} Keep Awake:\n\n{e}\n\n"
                f"Platform: {sys.platform}\n"
                f"Check logs for more details.")

    def on_overlay_closed(self):
        """Callback for when the overlay is closed externally (e.g. by signal or Escape key)."""
        logging.info("Overlay closed externally. Syncing UI state.")
        # Only toggle if we think it's still enabled
        if self.sleep_mode_enabled:
            # This will set sleep_mode_enabled to False and run cleanup (undim, uninhibit, update UI)
            # The 'hide_overlay' call inside it will be safe because OverlayController clears self.overlay first.
            self.toggle_sleep_mode()

    def set_brightness(self, level):
        """Set the display brightness."""
        if self.display_mgr:
            try:
                self.display_mgr.set_brightness(level)
            except Exception as e:
                logging.error(f"Failed to set brightness: {e}")
        else:
            logging.warning("Display management not available.")

    def turn_off_display(self):
        """Turn off the display."""
        if self.display_mgr:
            try:
                self.display_mgr.turn_off()
            except Exception as e:
                logging.error(f"Failed to turn off display: {e}")
        else:
             logging.warning("Display management not available.")

    def toggle_black_overlay(self):
        """Toggle the black screen overlay."""
        if self.overlay_controller:
            self.overlay_controller.toggle()

    def party_mode(self):
        """Play a random video from the video directory!"""
        try:
            video_dir = os.path.join(os.getcwd(), "video")
            if not os.path.exists(video_dir):
                os.makedirs(video_dir)
                messagebox.showinfo("Party Mode", "Video directory created! Add some videos to 'video' folder to party!")
                return
            
            # Simple random video playback
            from logic.actions import execute_action
            config = {"directory": "video", "file_types": ["mp4", "mkv", "webm", "avi"]}
            
            # Run in thread
            import threading
            threading.Thread(target=lambda: execute_action("play_random_video", config), daemon=True).start()
            
        except Exception as e:
            logging.error(f"Party Mode failed: {e}")
            messagebox.showerror("Error", f"Party Mode failed: {e}")

if __name__ == "__main__":
    app = VideoAlarmMainWindow()
    app.mainloop()
