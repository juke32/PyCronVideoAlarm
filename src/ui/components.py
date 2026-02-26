
import tkinter as tk
from tkinter import ttk
from .theme import COLORS, FONTS


class ScrollableFrame(ttk.Frame):
    """
    A scrollable frame that automatically manages a canvas and scrollbar.
    Use .scrollable_frame as the parent for your widgets.
    """
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Canvas and Scrollbar
        self.canvas = tk.Canvas(self, bg=COLORS['bg_dark'], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # The scrollable frame (content area)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.configure(style='TFrame')

        # Construct the scroll window
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure canvas resize
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self.canvas.configure(yscrollcommand=self.scrollbar.set, yscrollincrement='1')

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind enter/leave events to enable/disable scrolling
        self.canvas.bind('<Enter>', self._bound_to_mousewheel)
        self.canvas.bind('<Leave>', self._unbound_to_mousewheel)

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_canvas_configure(self, event):
        """Fit the inner frame to the canvas width."""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def _on_mousewheel(self, event):
        """Cross-platform mousewheel scrolling (pixel-based)."""
        if self.canvas.winfo_exists():
            # Scroll roughly 20 lines (pixels) per click
            scroll_amount = 20
            if event.num == 5 or event.delta == -120:
                self.canvas.yview_scroll(scroll_amount, "units")
            elif event.num == 4 or event.delta == 120:
                self.canvas.yview_scroll(-scroll_amount, "units")

class ActionCard(ttk.Frame):
    """
    An accordion-style card representing a single action.
    Has a summary header and an expanding body for editing.
    """
    current_menu = None  # Track currently open menu

    def __init__(self, parent, action_index, action_data, callbacks):
        """
        callbacks: dict with keys 'update', 'remove', 'move_up', 'move_down', 'move_to'
        """
        super().__init__(parent, padding=2, relief='solid', borderwidth=0)
        
        self.index = action_index
        self.action_data = action_data
        self.callbacks = callbacks
        self.is_expanded = False
        self.body_created = False
        
        # Set background color based on action type
        action_type = action_data.get('type', '').lower()
        if 'audio' in action_type or 'sound' in action_type or 'play_audio' in action_type:
            card_style = 'AudioCard.TFrame'
        elif 'video' in action_type or 'play_video' in action_type:
            card_style = 'VideoCard.TFrame'
        elif action_type == 'wait' or 'delay' in action_type:
            card_style = 'WaitCard.TFrame'
        else:
            card_style = 'Card.TFrame'
        
        self.configure(style=card_style)
        self.card_style = card_style
        
        # --- Header ---
        self.header_frame = ttk.Frame(self, style=card_style)
        self.header_frame.pack(fill=tk.X, padx=2, pady=2)
        
        # Drag and Drop Bindings (Handle Click via Release check)
        # We'll use the header as the handle
        self.header_frame.bind("<ButtonPress-1>", self._start_drag)
        self.header_frame.bind("<B1-Motion>", self._drag_motion)
        self.header_frame.bind("<ButtonRelease-1>", self._end_drag)
        self.header_frame.bind("<Button-3>", self.show_context_menu) # Right-click context menu

        # Icon/Type
        label_style = card_style.replace('.TFrame', '.TLabel')
        
        # --- Buttons (Left Aligned for left-to-right user mapping) ---
        # Order: Play, Edit, Delete, Up, Down
        
        ttk.Button(self.header_frame, text="▶ Play", width=6, style='Icon.TButton',
                 command=lambda: callbacks['play'](self.index)).pack(side=tk.LEFT, padx=2)
                 
        self.expand_btn = ttk.Button(self.header_frame, text="Edit", width=6, style='Icon.TButton',
                                   command=self.toggle_expand)
        self.expand_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(self.header_frame, text="X", width=2, style='Icon.TButton',
                 command=lambda: callbacks['remove'](self.index)).pack(side=tk.LEFT, padx=2)

        ttk.Button(self.header_frame, text="▲", width=2, style='Icon.TButton',
                 command=lambda: callbacks['move_up'](self.index)).pack(side=tk.LEFT, padx=1)
                 
        ttk.Button(self.header_frame, text="▼", width=2, style='Icon.TButton',
                 command=lambda: callbacks['move_down'](self.index)).pack(side=tk.LEFT, padx=1)

        # --- Labels (Left Aligned - Fill remaining space) ---
        # 1. Name/Type
        type_lbl = ttk.Label(self.header_frame, text=action_data.get('type', 'Unknown'), 
                           font=FONTS['h2'], style=label_style, width=15)
        type_lbl.pack(side=tk.LEFT, padx=5)
        type_lbl.bind("<ButtonPress-1>", self._start_drag)
        type_lbl.bind("<B1-Motion>", self._drag_motion)
        type_lbl.bind("<ButtonRelease-1>", self._end_drag)
        type_lbl.bind("<Button-3>", self.show_context_menu)
        
        # 2. Comment / Summary text
        config = action_data.get('config', {})
        summary_text = config.get('#comment', str(config))
        # Ensure label wraps and stretches across screen without getting cut off
        summary_lbl = ttk.Label(self.header_frame, text=summary_text, style=label_style, wraplength=800)
        summary_lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        summary_lbl.bind("<ButtonPress-1>", self._start_drag)
        summary_lbl.bind("<B1-Motion>", self._drag_motion)
        summary_lbl.bind("<ButtonRelease-1>", self._end_drag)
        summary_lbl.bind("<Button-3>", self.show_context_menu)
        
        # --- Body (Hidden by default, lazy loaded) ---
        self.body_frame = ttk.Frame(self, style=card_style)
        # Content will be lazy-loaded in toggle_expand

        # State for Drag
        self._drag_data = {"x": 0, "y": 0, "start_index": None}

    def _create_body(self):
        """Lazy load the body content."""
        if self.body_created: return
        
        config = self.action_data.get('config', {})
        
        # We need a text editor for the JSON config
        import json
        json_str = json.dumps(config, indent=2)
        initial_lines = json_str.count('\n') + 1
        # Limit initial height (min 3, max 30)
        initial_height = max(3, min(30, initial_lines))
        
        self.json_text = tk.Text(self.body_frame, height=initial_height, width=50, bg=COLORS['bg_light'], 
                                fg=COLORS['text_main'], insertbackground=COLORS['text_main'], relief="flat")
        self.json_text.insert("1.0", json_str)
        self.json_text.pack(fill=tk.X, padx=10, pady=5)
        
        # Auto-resize binding
        self.json_text.bind('<KeyRelease>', self._adjust_height)
        
        # Save Button inside the card
        # On click, we parse the JSON and trigger the 'update' callback
        btn_row = ttk.Frame(self.body_frame, style='Card.TFrame')
        btn_row.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_row, text="Apply Changes", command=self.save_changes).pack(side=tk.RIGHT)
        
        self.body_created = True

    def toggle_expand(self):
        if self.is_expanded:
            self.body_frame.pack_forget()
            self.expand_btn.config(text="Edit")
        else:
            self._create_body() # Ensure body is created
            self.body_frame.pack(fill=tk.X, padx=5, pady=0)
            self.expand_btn.config(text="Close")
        self.is_expanded = not self.is_expanded

    def _adjust_height(self, event=None):
        """Auto-resize the text widget to fit content."""
        try:
            # Count lines
            content = self.json_text.get("1.0", "end-1c")
            lines = content.count('\n') + 1
            # Clamp height
            new_height = max(3, min(30, lines))
            
            if int(self.json_text.cget('height')) != new_height:
                self.json_text.configure(height=new_height)
        except Exception: 
            pass

    def save_changes(self):
        import json
        from tkinter import messagebox
        try:
            raw = self.json_text.get("1.0", tk.END).strip()
            new_config = json.loads(raw)
            # Callback to parent to update logic
            self.callbacks['update'](self.index, new_config)
            # Flash success?
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON", f"Syntax Error: {e}")

    # --- Drag and Drop Logic ---
    def _start_drag(self, event):
        """Begin drag operation."""
        # prevent dragging if clicking a button
        widget = event.widget
        if isinstance(widget, ttk.Button): return

        self._drag_data["x"] = event.x_root
        self._drag_data["y"] = event.y_root
        self._drag_data["start_index"] = self.index
        # Visual feedback? Maybe change cursor or relief
        self.configure(relief="raised", borderwidth=3)
        self.lift()

    def _drag_motion(self, event):
        """Handle dragging."""
        pass

    def _end_drag(self, event):
        """End drag and calculate drop position."""
        self.configure(relief='solid', borderwidth=0)
        
        if self._drag_data["start_index"] is None: return
        
        # Check if it was just a click (small movement)
        dx = abs(event.x_root - self._drag_data["x"])
        dy = abs(event.y_root - self._drag_data["y"])
        
        if dx < 5 and dy < 5:
            self.toggle_expand()
            self._drag_data["start_index"] = None
            return

        # Calculate where we dropped
        # y_root of release
        y_root = event.y_root
        
        # Iterate over all siblings (ActionCards) in the parent
        parent = self.master
        target_index = -1
        
        # Find which card we are over
        for child in parent.winfo_children():
            if isinstance(child, ActionCard):
                cx, cy = child.winfo_rootx(), child.winfo_rooty()
                ch, cw = child.winfo_height(), child.winfo_width()
                
                if cy <= y_root <= cy + ch:
                    target_index = child.index
                    break
        
        # If we dropped below the last one
        if target_index == -1:
            # Check if we are below the last one
            if parent.winfo_children():
                last_child = parent.winfo_children()[-1]
                if y_root > last_child.winfo_rooty() + last_child.winfo_height():
                    target_index = len(parent.winfo_children()) - 1 # Move to end
        
        # Perform move if valid and different
        if target_index != -1 and target_index != self.index:
            # Call move_to
             if 'move_to' in self.callbacks:
                 self.callbacks['move_to'](self.index, target_index)

        self._drag_data["start_index"] = None

    # --- Context Menu ---
    def show_context_menu(self, event):
        """Show right-click context menu."""
        # 1. Close any existing menu
        if ActionCard.current_menu:
            try:
                ActionCard.current_menu.unpost()
            except: pass
        
        # 2. Clear any existing global bindings to prevent ghost clicks
        try:
             self.winfo_toplevel().unbind_all("<Button-1>")
        except: pass

        menu = tk.Menu(self, tearoff=0)
        ActionCard.current_menu = menu
        
        def close_menu(e=None):
            if e:
                # Check if click is inside the menu
                try:
                    mx = menu.winfo_rootx()
                    my = menu.winfo_rooty()
                    mw = menu.winfo_width()
                    mh = menu.winfo_height()
                    # Add a small buffer just in case
                    if mx <= e.x_root <= mx + mw and my <= e.y_root <= my + mh:
                        return # Click is inside menu, let it handle the command
                except: pass

            menu.unpost()
            if ActionCard.current_menu == menu:
                ActionCard.current_menu = None
            try:
                self.winfo_toplevel().unbind_all("<Button-1>")
            except: pass

        # Helper to ensure menu closes when an item is clicked
        def command_wrapper(func):
            def wrapper():
                func()
                close_menu()
            return wrapper

        menu.add_command(label="Duplicate Action", command=command_wrapper(lambda: self.callbacks.get('duplicate', lambda i: None)(self.index)))
        menu.add_separator()
        menu.add_command(label="Play This Action", command=command_wrapper(lambda: self.callbacks['play'](self.index)))
        menu.add_command(label="Play Sequence From Here", command=command_wrapper(lambda: self.callbacks.get('play_from', lambda i: None)(self.index)))
        menu.add_separator()
        menu.add_command(label="Delete Action", command=command_wrapper(lambda: self.callbacks['remove'](self.index)))
        
        # Auto-hide after 16 seconds
        self.after(16000, close_menu)

        # Bind global click to close method
        # Using bind_all on the toplevel to catch clicks anywhere in the app
        self.winfo_toplevel().bind_all("<Button-1>", close_menu, add="+")

        # Use post instead of tk_popup to avoid grabbing focus, allowing the bind_all to work
        menu.post(event.x_root, event.y_root)
