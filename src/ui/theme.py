
import tkinter as tk
from tkinter import ttk


THEMES = {
    "Light": {
        "bg_dark": "#F5F5F5",
        "bg_card": "#FAFAFA",
        "bg_light": "#E0E0E0",
        "primary": "#6200EE",
        "primary_var": "#3700B3",
        "secondary": "#03DAC6",
        "error": "#B00020",
        "text_main": "#000000",
        "text_dim": "#666666",
        "border": "#CCCCCC",
        "accent_audio": "#F5D9FF",
        "accent_video": "#C8FBFB"
    },
    "Legacy": {
        "bg_dark": "#C0C0C0",        # Classic Grey
        "bg_card": "#DFDFDF",        # Slightly lighter for cards
        "bg_light": "#FFFFFF",       # White fields
        "primary": "#000080",        # Navy Blue
        "primary_var": "#000040",    # Darker Navy
        "secondary": "#008080",      # Teal
        "error": "#FF0000",
        "text_main": "#000000",
        "text_dim": "#404040",
        "border": "#808080",         # Dark Grey border
        "accent_audio": "#E0E0E0",
        "accent_video": "#D0D0D0"
    },
    "Twilight": {
        "bg_dark": "#282C34",        # One Dark bg
        "bg_card": "#3E4451",        # Lighter grey
        "bg_light": "#21252B",       # Darker for inputs
        "primary": "#61AFEF",        # Soft Blue
        "primary_var": "#528BFF",
        "secondary": "#98C379",      # Green
        "error": "#E06C75",          # Soft Red
        "text_main": "#ABB2BF",      # Main text
        "text_dim": "#5C6370",       # Comments/Dim
        "border": "#181A1F",
        "accent_audio": "#475459",    # default 353b45
        "accent_video": "#474653"    # default 454552
    },
    "Midnight Blue": {
        "bg_dark": "#050A14",
        "bg_card": "#0F1A32",
        "bg_light": "#142850",
        "primary": "#4FC3F7",
        "primary_var": "#0277BD",
        "secondary": "#FFCA28",
        "error": "#E57373",
        "text_main": "#E1F5FE",
        "text_dim": "#B0BEC5",
        "border": "#1A237E",
        "accent_audio": "#1A1432",
        "accent_video": "#0F1E32"
    },
    "DarkPurple": {
        "bg_dark": "#0A0A0A",       # Main Window Background
        "bg_card": "#1A1A1A",       # Card/Panel Background (Grouped content)
        "bg_light": "#1F1F1F",      # Input Fields, Text Areas, Lists
        "primary": "#8B72DE",       # Main Buttons, Highlights
        "primary_var": "#120CAE",   # Active/Pressed Button state, Selection
        "secondary": "#03DAC6",     # Subheaders, Special Accents
        "error": "#CF6679",         # Error Text/Icons
        "text_main": "#E0E0E0",     # Primary Text Color
        "text_dim": "#A0A0A0",      # Secondary/Comment Text Color
        "border": "#2A2A2A",        # Borders, Separators
        "accent_audio": "#221A2A",  # Special card background for Audio items
        "accent_video": "#1A232A"   # Special card background for Video items
    },
    "High Contrast": {
        "bg_dark": "#000000",
        "bg_card": "#1A1A1A",
        "bg_light": "#000000",
        "primary": "#FFFF00",
        "primary_var": "#FFCC00",
        "secondary": "#00FFFF",
        "error": "#FF0000",
        "text_main": "#FFFFFF",
        "text_dim": "#FFFFFF",
        "border": "#FFFFFF",
        "accent_audio": "#2A2A00",
        "accent_video": "#002A2A"
    },
    "PyCron": {
        "bg_dark": "#1A1A14",        # Main Window Background (Very Dark Olive)
        "bg_card": "#2A2A1F",        # Card/Panel Background (Original Olive) - Lighter than BG
        "bg_light": "#12120E",       # Input Fields (Deep Dark) - High contrast for text
        "primary": "#38382A",        # Main Buttons (Olive Drab)
        "primary_var": "#464636",    # Active/Hover (Olive Gray - Lighter)
        "secondary": "#464636",      # Accents/Subheaders
        "error": "#FF6B6B",          # Soft Red
        "text_main": "#FFFFFF",      # Primary Text
        "text_dim": "#A0A090",       # Dim Text (Warm Grey)
        "border": "#38382A",         # Borders match buttons
        "accent_audio": "#25251C",   # Slightly different shade for audio
        "accent_video": "#25251C"    # Slightly different shade for video
    }
}

# Current active colors
COLORS = THEMES["Twilight"]

FONTS = {
    "h1": ("Segoe UI", 16, "bold"),
    "h2": ("Segoe UI", 12, "bold"),
    "body": ("Segoe UI", 10),
    "mono": ("Consolas", 10)
}

def apply_theme(root, theme_name="Twilight"):
    """Apply the selected theme to the global ttk style."""
    global COLORS
    
    # Fallback if theme_name is invalid or None
    if theme_name not in THEMES:
        # Use the first available theme as fallback
        theme_name = "Twilight"
        
    COLORS = THEMES[theme_name]
        
    style = ttk.Style(root)
    style.theme_use('clam') 

    # General Frame/Label
    style.configure('.', background=COLORS['bg_dark'], foreground=COLORS['text_main'], font=FONTS['body'])
    style.configure('TFrame', background=COLORS['bg_dark'])
    style.configure('Card.TFrame', background=COLORS['bg_card'], relief="flat")
    style.configure('AudioCard.TFrame', background=COLORS.get('accent_audio', COLORS['bg_card']), relief="flat")
    style.configure('VideoCard.TFrame', background=COLORS.get('accent_video', COLORS['bg_card']), relief="flat")
    
    # Labels
    style.configure('TLabel', background=COLORS['bg_dark'], foreground=COLORS['text_main'])
    style.configure('Card.TLabel', background=COLORS['bg_card'], foreground=COLORS['text_main'])
    style.configure('AudioCard.TLabel', background=COLORS.get('accent_audio', COLORS['bg_card']), foreground=COLORS['text_main'])
    style.configure('VideoCard.TLabel', background=COLORS.get('accent_video', COLORS['bg_card']), foreground=COLORS['text_main'])
    style.configure('Header.TLabel', font=FONTS['h1'], foreground=COLORS['primary'])
    style.configure('Subheader.TLabel', font=FONTS['h2'], foreground=COLORS['secondary'])
    
    # Buttons
    style.configure('TButton', 
        background=COLORS['primary'], 
        foreground=COLORS['bg_dark'], 
        borderwidth=0, 
        font=("Segoe UI", 10, "bold"),
        padding=(10, 5)
    )
    style.map('TButton', 
        background=[('active', COLORS['bg_light']), ('pressed', COLORS['primary_var'])],
        foreground=[('active', COLORS['text_main'])]
    )
    
    # Action/Icon Buttons (smaller, darker)
    style.configure('Icon.TButton', 
        background=COLORS['bg_light'], 
        foreground=COLORS['text_main'],
        padding=(4, 2)
    )
    style.map('Icon.TButton', background=[('active', COLORS['border'])])

    # Inputs
    style.configure('TEntry', 
        fieldbackground=COLORS['bg_light'], 
        foreground=COLORS['text_main'], 
        insertcolor=COLORS['text_main'],
        borderwidth=1,
        relief="flat"
    )
    
    # Notebook
    style.configure('TNotebook', background=COLORS['bg_dark'], borderwidth=0)
    style.configure('TNotebook.Tab', 
        background=COLORS['bg_card'], 
        foreground=COLORS['text_dim'],
        padding=(15, 8), # Larger click area
        font=FONTS['h2']
    )
    style.map('TNotebook.Tab', 
        background=[('selected', COLORS['primary']), ('active', COLORS['bg_light'])],
        foreground=[('selected', COLORS['bg_dark']), ('active', COLORS['text_main'])]
    )

    # Treeview (Alarms List, File Lists)
    style.configure('Treeview', 
        background=COLORS['bg_light'], 
        foreground=COLORS['text_main'], 
        fieldbackground=COLORS['bg_light'],
        borderwidth=0,
        font=FONTS['body']
    )
    style.map('Treeview', 
        background=[('selected', COLORS['primary_var'])], 
        foreground=[('selected', COLORS['text_main'])]
    )
    style.configure('Treeview.Heading', 
        background=COLORS['bg_card'], 
        foreground=COLORS['text_main'], 
        font=("Segoe UI", 10, "bold"),
        relief="flat"
    )
    style.map('Treeview.Heading', background=[('active', COLORS['bg_light'])])

    # Combobox
    style.configure('TCombobox', 
        fieldbackground=COLORS['bg_light'], 
        background=COLORS['bg_card'], 
        foreground=COLORS['text_main'],
        arrowcolor=COLORS['text_main'],
        borderwidth=1
    )
    style.map('TCombobox', 
        fieldbackground=[('readonly', COLORS['bg_light'])], 
        selectbackground=[('readonly', COLORS['primary'])], 
        selectforeground=[('readonly', COLORS['bg_dark'])]
    )

    # Scrollbars (Darker)
    style.configure("Vertical.TScrollbar", 
        background=COLORS['bg_card'], 
        troughcolor=COLORS['bg_dark'], 
        bordercolor=COLORS['bg_dark'], 
        arrowcolor=COLORS['text_main']
    )

    # Global Tkinter defaults
    root.configure(bg=COLORS['bg_dark'])
    root.option_add('*background', COLORS['bg_dark'])
    root.option_add('*foreground', COLORS['text_main'])
    root.option_add('*Entry.background', COLORS['bg_light'])
    root.option_add('*Entry.foreground', COLORS['text_main'])
    root.option_add('*Entry.insertBackground', COLORS['text_main']) # Cursor color
    root.option_add('*Text.background', COLORS['bg_light'])
    root.option_add('*Text.foreground', COLORS['text_main'])
    root.option_add('*Text.insertBackground', COLORS['text_main']) # Cursor color
    root.option_add('*Listbox.background', COLORS['bg_light'])
    root.option_add('*Listbox.foreground', COLORS['text_main'])
    
    return style
