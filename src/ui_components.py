import tkinter as tk

def get_pill_points(w, h, r, bw=1.5):
    r = min(r, h // 2, w // 2)
    return [
        r, bw,
        w - r, bw,
        w - bw, bw,
        w - bw, r,
        w - bw, h - r,
        w - bw, h - bw,
        w - r, h - bw,
        r, h - bw,
        bw, h - bw,
        bw, h - r,
        bw, r,
        bw, bw
    ]

class RoundedCard(tk.Canvas):
    def __init__(self, parent, bg="#07070a", fill="#101117", border="#aa8214", radius=18, border_w=1.5, **kwargs):
        super().__init__(parent, bg=bg, highlightthickness=0, **kwargs)
        self.fill = fill
        self.border = border
        self.radius = radius
        self.border_w = border_w
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10: return
        self.delete("bg")
        pts = get_pill_points(w, h, self.radius, self.border_w)
        self.create_polygon(pts, smooth=True, fill=self.fill, outline=self.border, width=self.border_w, tags="bg")
        self.tag_lower("bg")

class PillButton(tk.Canvas):
    def __init__(self, parent, text, command=None, bg="#101117", fill="#e5b842",
                 hover_fill="#fbe69b", fg="#000000", font=("Segoe UI", 9, "bold"),
                 height=34, radius=17, outline="#aa8214", cursor="hand2", **kwargs):
        super().__init__(parent, bg=bg, height=height, highlightthickness=0, cursor=cursor, **kwargs)
        self.text = text
        self.command = command
        self.normal_fill = fill
        self.hover_fill = hover_fill
        self.current_fill = fill
        self.fg = fg
        self.font = font
        self.radius = radius
        self.outline = outline

        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))
        self.bind("<Button-1>", lambda e: self.command() if self.command else None)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10: return
        pts = get_pill_points(w, h, self.radius, 1.5)
        self.create_polygon(pts, smooth=True, fill=self.current_fill, outline=self.outline, width=1.5)
        self.create_text(w // 2, h // 2, text=self.text, fill=self.fg, font=self.font)

    def _hover(self, active):
        self.current_fill = self.hover_fill if active else self.normal_fill
        self._draw()

    def set_style(self, text=None, fill=None, hover_fill=None, fg=None, outline=None):
        if text is not None: self.text = text
        if fill is not None: self.normal_fill = fill; self.current_fill = fill
        if hover_fill is not None: self.hover_fill = hover_fill
        if fg is not None: self.fg = fg
        if outline is not None: self.outline = outline
        self._draw()

class PillEntry(tk.Canvas):
    def __init__(self, parent, textvariable, height=32, bg="#15161f",
                 fill="#1e202e", outline="#aa8214", focus_outline="#e5b842",
                 fg="#ffffff", font=("Segoe UI", 9), show=None, **kwargs):
        super().__init__(parent, bg=bg, height=height, highlightthickness=0, **kwargs)
        self.textvariable = textvariable
        self.fill = fill
        self.normal_outline = outline
        self.focus_outline = focus_outline
        self.current_outline = outline
        self.radius = height // 2

        self.entry = tk.Entry(self, textvariable=self.textvariable, bg=fill, fg=fg,
                              insertbackground="#e5b842", relief=tk.FLAT, bd=0,
                              font=font, show=show)
        self.win_id = self.create_window(0, 0, window=self.entry)

        self.bind("<Configure>", self._draw)
        self.entry.bind("<FocusIn>", lambda e: self._focus(True))
        self.entry.bind("<FocusOut>", lambda e: self._focus(False))

    def _draw(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10: return
        self.delete("bg")
        pts = get_pill_points(w, h, self.radius, 1.5)
        self.create_polygon(pts, smooth=True, fill=self.fill, outline=self.current_outline, width=1.5, tags="bg")
        self.tag_lower("bg")
        self.coords(self.win_id, w // 2, h // 2)
        chars = max(4, (w - 28) // 8)
        self.entry.config(width=chars)

    def _focus(self, is_focused):
        self.current_outline = self.focus_outline if is_focused else self.normal_outline
        self._draw()
