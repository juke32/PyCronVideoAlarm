
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
        self._scrollbar_visible = True

        # Auto-hide the scrollbar when all content fits
        self.scrollable_frame.bind("<Configure>", self._maybe_hide_scrollbar, add="+")

        # Bind enter/leave events to enable/disable scrolling
        self.canvas.bind('<Enter>', self._bound_to_mousewheel)
        self.canvas.bind('<Leave>', self._unbound_to_mousewheel)

    def _maybe_hide_scrollbar(self, event=None):
        """Hide the scrollbar when content fits, show it when it overflows."""
        try:
            if not self.canvas.winfo_exists() or not self.scrollbar.winfo_exists():
                return
            bbox = self.canvas.bbox("all")
            if bbox is None:
                return
            need = bbox[3] > self.canvas.winfo_height() + 1
            if need and not self._scrollbar_visible:
                self.scrollbar.pack(side="right", fill="y")
                self._scrollbar_visible = True
            elif not need and self._scrollbar_visible:
                self.scrollbar.pack_forget()
                self._scrollbar_visible = False
        except tk.TclError:
            pass

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
        self._maybe_hide_scrollbar(event)

    def _on_mousewheel(self, event):
        """Cross-platform mousewheel scrolling (pixel-based)."""
        if self.canvas.winfo_exists():
            # Scroll roughly 20 lines (pixels) per click
            scroll_amount = 20
            if event.num == 5 or event.delta == -120:
                self.canvas.yview_scroll(scroll_amount, "units")
            elif event.num == 4 or event.delta == 120:
                self.canvas.yview_scroll(-scroll_amount, "units")

_TYPE_LABELS = {
    "play_video": "Play Video",
    "play_audio": "Play Audio",
    "play_random_video": "Random Video",
    "play_random_audio": "Random Audio",
    "open_url": "Open URL",
    "wait_action": "Wait",
    "set_system_volume": "Set Volume",
    "set_brightness": "Brightness",
    "kill_black_screen": "Kill Black Screen",
    "monitor_control": "Monitor",
    "run_command": "Run Command",
    "open_journal": "Journal",
    "take_photo": "Photo",
    "record_audio": "Record Audio",
}

def _humanize_type(action_type):
    return _TYPE_LABELS.get(action_type, action_type.replace("_", " ").title())

def _summarize(action_type, config):
    """Build a short human-readable summary for a card header."""
    action_type = action_type or ""
    cfg = config or {}
    if action_type in ("play_video", "play_audio", "play_random_video", "play_random_audio"):
        target = cfg.get("file") or cfg.get("directory") or ""
        parts = []
        if target:
            parts.append(target)
        if cfg.get("system_volume") is not None:
            parts.append(f"vol {cfg.get('system_volume')}%")
        if cfg.get("from") not in (None, "", "00:00"):
            parts.append(f"{cfg.get('from')}→{cfg.get('to', 'end')}")
        if action_type in ("play_video", "play_random_video"):
            parts.append("fullscreen" if cfg.get("fullscreen") else "window")
        return "  ·  ".join(parts) if parts else (cfg.get("#comment") or "")
    if action_type == "open_url":
        browser = cfg.get("browser", "default")
        url = cfg.get("url", "")
        return f"{url}  ({browser})" if url else (cfg.get("#comment") or "")
    if action_type == "wait_action":
        return f"Wait {cfg.get('duration', 0)}s"
    if action_type == "set_system_volume":
        return f"Set volume to {cfg.get('volume', 50)}%"
    if action_type == "set_brightness":
        return f"Set brightness to {cfg.get('level', 100)}%"
    if action_type == "monitor_control":
        return f"Turn monitor {cfg.get('state', 'off')}"
    if action_type == "record_audio":
        return f"Record {cfg.get('duration', 10)}s of audio"
    return cfg.get("#comment") or ""

class ActionCard(ttk.Frame):
    """
    An accordion-style card representing a single action.
    Has a summary header and an expanding body for editing.
    The header doubles as a smooth drag handle for reordering.
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
        label_style = card_style.replace('.TFrame', '.TLabel')

        # Drag state (live, animated reordering)
        self._drag_active = False
        self._drag_start_index = None
        self._drag_visual_pos = None

        # --- Header ---
        self.header_frame = ttk.Frame(self, style=card_style)
        self.header_frame.pack(fill=tk.X, padx=2, pady=2)

        # Drag handle (also make the whole header draggable)
        self.drag_handle = ttk.Label(self.header_frame, text="≡", style=label_style,
                                     font=("Segoe UI", 11, "bold"))
        self.drag_handle.pack(side=tk.LEFT, padx=(2, 0))

        # Index badge
        self.index_lbl = ttk.Label(self.header_frame, text=f"{action_index + 1}", style=label_style,
                                   width=2)
        self.index_lbl.pack(side=tk.LEFT, padx=2)

        # Icon/Type
        type_lbl = ttk.Label(self.header_frame, text=_humanize_type(action_type),
                             font=("Segoe UI", 10, "bold"), style=label_style)
        type_lbl.pack(side=tk.LEFT, padx=5)

        # Summary text
        config = action_data.get('config', {})
        summary_text = _summarize(action_type, config)
        summary_lbl = ttk.Label(self.header_frame, text=summary_text, style=label_style)
        summary_lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        # Keep references so the drag highlight can restyle them consistently
        self._drag_styled_labels = (self.drag_handle, self.index_lbl, type_lbl, summary_lbl)

        # Right-aligned controls
        controls = ttk.Frame(self.header_frame, style=card_style)
        controls.pack(side=tk.RIGHT)

        ttk.Button(controls, text="▶", width=2, style='Icon.TButton',
                   command=lambda: callbacks['play'](self.index)).pack(side=tk.LEFT, padx=1)
        self.expand_btn = ttk.Button(controls, text="✎", width=2, style='Icon.TButton',
                                     command=self.toggle_expand)
        self.expand_btn.pack(side=tk.LEFT, padx=1)
        ttk.Button(controls, text="🗑", width=2, style='Icon.TButton',
                   command=lambda: callbacks['remove'](self.index)).pack(side=tk.LEFT, padx=1)

        # --- Right-click context menu on the whole header ---
        for w in (self.header_frame, self.drag_handle, self.index_lbl, type_lbl, summary_lbl):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<Button-3>", self.show_context_menu)

        # --- Body (Hidden by default, lazy loaded) ---
        self.body_frame = ttk.Frame(self, style=card_style)
        # Content will be lazy-loaded in toggle_expand

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

    # --- Smooth Drag and Drop ---
    def _drag_canvas(self):
        """The canvas that scrolls our card list (master of the scrollable frame)."""
        try:
            return self.master.master
        except Exception:
            return None

    def _drag_siblings(self):
        """All draggable cards in our list, ordered by on-screen position."""
        cards = [w for w in self.master.winfo_children() if isinstance(w, ActionCard)]
        cards.sort(key=lambda w: w.winfo_rooty())
        return cards

    def _start_drag(self, event):
        """Begin a drag operation. Motion is captured on the toplevel so the drag
        stays smooth even when the pointer crosses over neighbouring cards."""
        if isinstance(event.widget, (ttk.Button, tk.Button)):
            return

        self._drag_active = True
        self._drag_start_index = self.index
        self._drag_start_slot = self.index
        self._drag_slot = self.index
        self._drag_pointer_y = event.y_root
        self._drag_autoscroll_job = None

        # Highlight the card being dragged so it is unmistakable among similar
        # looking siblings while the pointer moves it.
        self.configure(style='DragCard.TFrame')
        self.header_frame.configure(style='DragCard.TFrame')
        try:
            for lbl in self._drag_styled_labels:
                lbl.configure(style='DragCard.TLabel')
        except AttributeError:
            pass

        toplevel = self.winfo_toplevel()
        toplevel.bind('<B1-Motion>', self._drag_motion)
        toplevel.bind('<ButtonRelease-1>', self._end_drag)

    def _drag_motion(self, event):
        """Smooth drag: the card physically follows the pointer. The list is only
        repacked when the drop slot actually changes (so ordinary motion stays
        cheap), and it auto-scrolls ONLY while the pointer is pressed against the
        top/bottom edge band — the list otherwise stays put."""
        if not self._drag_active:
            return
        self._drag_pointer_y = event.y_root
        self._move_to_pointer_slot()

        canvas = self._drag_canvas()
        if canvas is None:
            return
        try:
            top = canvas.winfo_rooty()
            height = canvas.winfo_height()
            edge = 40
            if event.y_root < top + edge:
                depth = (top + edge - event.y_root) / float(edge)
                self._start_autoscroll(canvas, -1, depth)
            elif event.y_root > top + height - edge:
                depth = (event.y_root - (top + height - edge)) / float(edge)
                self._start_autoscroll(canvas, 1, depth)
            else:
                self._stop_autoscroll()
        except Exception:
            pass

    def _slot_from_pointer(self):
        """Target slot (gap between other cards) the card would land in right
        now, based on the last known pointer root-Y. Other cards' slots are the
        gaps; the dragged card itself is skipped."""
        pos = 0
        for c in self._drag_siblings():
            if c is self:
                continue
            cy = c.winfo_rooty() + c.winfo_height() // 2
            if self._drag_pointer_y > cy:
                pos += 1
        return pos

    def _move_to_pointer_slot(self):
        """Repack the dragged card so it visually tracks the pointer. Only does
        real layout work when the target slot changes (the cheap path)."""
        cards = self._drag_siblings()
        pos = self._drag_slot_from_pointer(cards)
        if pos == self._drag_slot:
            return
        self._drag_slot = pos
        self._repack_at_slot(cards, pos)

    def _repack_at_slot(self, cards, pos):
        parent = self.master
        others = [c for c in cards if c is not self]
        if pos >= len(others):
            # Move to the end (below every sibling)
            self.pack(fill=tk.X, pady=1)
        else:
            self.pack(fill=tk.X, pady=1, before=others[pos])
        try:
            parent.update_idletasks()
        except Exception:
            pass

    def _start_autoscroll(self, canvas, direction, depth):
        """Smooth auto-scroll loop while the pointer hovers in the edge band.
        Velocity grows with pointer depth; the loop self-cancels once the pointer
        leaves the band or the drag ends."""
        if self._drag_autoscroll_job is not None:
            return
        def _tick():
            if not self._drag_active:
                self._drag_autoscroll_job = None
                return
            try:
                top = canvas.winfo_rooty()
                height = canvas.winfo_height()
                edge = 40
                py = self._drag_pointer_y or 0
                if direction < 0 and py < top + edge:
                    depth = (top + edge - py) / float(edge)
                elif direction > 0 and py > top + height - edge:
                    depth = (py - (top + height - edge)) / float(edge)
                else:
                    self._drag_autoscroll_job = None
                    return
                speed = max(1, int(depth * 6))
                canvas.yview_scroll(direction * speed, "units")
                # The list moved under the pointer — re-slot so the dragged card
                # keeps following even while the band auto-scrolls.
                cards = self._drag_siblings()
                self._repack_at_slot(cards, self._drag_slot_from_pointer(cards))
            except Exception:
                self._drag_autoscroll_job = None
                return
            self._drag_autoscroll_job = canvas.after(12, _tick)
        self._drag_autoscroll_job = canvas.after(12, _tick)

    def _stop_autoscroll(self):
        if self._drag_autoscroll_job is not None:
            try:
                canvas = self._drag_canvas()
                if canvas is not None:
                    canvas.after_cancel(self._drag_autoscroll_job)
            except Exception:
                pass
            self._drag_autoscroll_job = None

    def _end_drag(self, event):
        """End drag: restore the card's look, then commit the reorder if it
        changed. A click without real movement toggles the editor instead."""
        toplevel = self.winfo_toplevel()
        toplevel.unbind('<B1-Motion>')
        toplevel.unbind('<ButtonRelease-1>')
        self._stop_autoscroll()

        if not self._drag_active:
            return
        self._drag_active = False

        # Restore the card's normal colors
        self.configure(style=self.card_style)
        self.header_frame.configure(style=self.card_style)
        try:
            label_style = self.card_style.replace('.TFrame', '.TLabel')
            for lbl in self._drag_styled_labels:
                lbl.configure(style=label_style)
        except AttributeError:
            pass

        start = self._drag_start_index
        target = self._drag_slot
        self._drag_start_index = None
        self._drag_slot = None
        self._drag_pointer_y = None

        # A click without real movement toggles the editor
        if target == start:
            self.toggle_expand()
            return

        if target is not None and target != start and 'move_to' in self.callbacks:
            self.callbacks['move_to'](start, target)

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
