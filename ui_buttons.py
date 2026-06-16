"""Custom non-native buttons for offensive/defensive team modes and actions."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Callable, Literal

from themes import RED_OFFENSIVE, PURPLE_DEFENSIVE

TeamKind = Literal["red", "purple"]
ButtonVariant = Literal["primary", "ghost"]


class TeamModeButton(tk.Frame):
    """Always-themed offensive or defensive engagement toggle."""

    _PALETTES = {
        "red": {
            "glyph": RED_OFFENSIVE["glyph"],
            "title": "RED TEAM",
            "subtitle": "Offensive ops",
            "bg": RED_OFFENSIVE["btn_off_bg"],
            "bg_active": RED_OFFENSIVE["btn_off_bg_active"],
            "bg_hover": RED_OFFENSIVE["btn_off_bg_hover"],
            "border": RED_OFFENSIVE["btn_off_border"],
            "border_active": RED_OFFENSIVE["btn_off_border_active"],
            "fg": RED_OFFENSIVE["btn_off_fg"],
            "tag_active": RED_OFFENSIVE["btn_off_accent"],
        },
        "purple": {
            "glyph": PURPLE_DEFENSIVE["glyph"],
            "title": "PURPLE TEAM",
            "subtitle": "Defensive ops",
            "bg": PURPLE_DEFENSIVE["btn_def_bg"],
            "bg_active": PURPLE_DEFENSIVE["btn_def_bg_active"],
            "bg_hover": PURPLE_DEFENSIVE["btn_def_bg_hover"],
            "border": PURPLE_DEFENSIVE["btn_def_border"],
            "border_active": PURPLE_DEFENSIVE["btn_def_border_active"],
            "fg": PURPLE_DEFENSIVE["btn_def_fg"],
            "tag_active": PURPLE_DEFENSIVE["btn_def_accent"],
        },
    }

    def __init__(self, parent: tk.Widget, mode: TeamKind, command: Callable[[], None], **kwargs) -> None:
        self.mode = mode
        self._command = command
        self._active = False
        self._hover = False
        self._palette = self._PALETTES[mode]

        super().__init__(
            parent,
            bg=self._palette["bg"],
            highlightthickness=2,
            highlightbackground=self._palette["border"],
            cursor="hand2",
            **kwargs,
        )

        inner = tk.Frame(self, bg=self._palette["bg"])
        inner.pack(padx=14, pady=10)
        self._inner = inner

        top = tk.Frame(inner, bg=self._palette["bg"])
        self._top = top
        top.pack(anchor="w")

        self._glyph = tk.Label(
            top,
            text=self._palette["glyph"],
            bg=self._palette["bg"],
            fg=self._palette["fg"],
            font=("Segoe UI", 14),
        )
        self._glyph.pack(side=tk.LEFT, padx=(0, 8))

        text_col = tk.Frame(top, bg=self._palette["bg"])
        self._text_col = text_col
        text_col.pack(side=tk.LEFT)

        self._title = tk.Label(
            text_col,
            text=self._palette["title"],
            bg=self._palette["bg"],
            fg=self._palette["fg"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self._title.pack(anchor="w")

        self._subtitle = tk.Label(
            text_col,
            text=self._palette["subtitle"],
            bg=self._palette["bg"],
            fg=self._palette["fg"],
            font=("Segoe UI", 8),
            anchor="w",
        )
        self._subtitle.pack(anchor="w")

        self._tag = tk.Label(
            inner,
            text="",
            bg=self._palette["bg"],
            fg=self._palette["fg"],
            font=("Segoe UI", 7, "bold"),
            padx=6,
            pady=1,
        )
        self._tag.pack(anchor="w", pady=(6, 0))

        for widget in (self, self._inner, self._top, self._text_col, self._glyph, self._title, self._subtitle, self._tag):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, _event: object = None) -> None:
        self._hover = True
        self._paint()

    def _on_leave(self, _event: object = None) -> None:
        self._hover = False
        self._paint()

    def _on_click(self, _event: object = None) -> None:
        self._command()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._paint()

    def _paint(self) -> None:
        p = self._palette
        if self._active:
            bg = p["bg_active"]
            border = p["border_active"]
            tag_bg = p["tag_active"]
            tag_text = "  ACTIVE  "
        elif self._hover:
            bg = p["bg_hover"]
            border = p["border"]
            tag_bg = p["bg"]
            tag_text = ""
        else:
            bg = p["bg"]
            border = p["border"]
            tag_bg = p["bg"]
            tag_text = ""

        self.configure(bg=bg, highlightbackground=border, highlightthickness=3 if self._active else 2)
        for widget in (self._inner, self._top, self._text_col, self._glyph, self._title, self._subtitle):
            widget.configure(bg=bg)
        self._tag.configure(text=tag_text, bg=tag_bg if tag_text else bg, fg=self._palette["fg"])


class AppButton(tk.Frame):
    """Mode-aware action button with hover states."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        theme: dict,
        variant: ButtonVariant = "primary",
        **kwargs,
    ) -> None:
        self._command = command
        self._theme = theme
        self._variant = variant
        self._hover = False

        if variant == "primary":
            bg = theme["btn_action_primary"]
            hover = theme["btn_action_primary_hover"]
            border = theme["accent"]
            fg = theme["text"]
        else:
            bg = theme["btn_action_ghost"]
            hover = theme["btn_action_ghost_hover"]
            border = theme["card_border"]
            fg = theme["muted"]

        self._bg = bg
        self._hover_bg = hover
        self._border = border
        self._fg = fg

        super().__init__(
            parent,
            bg=bg,
            highlightthickness=1,
            highlightbackground=border,
            cursor="hand2",
            **kwargs,
        )

        self._label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=fg,
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=9,
        )
        self._label.pack()

        for widget in (self, self._label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, _event: object = None) -> None:
        self._hover = True
        self._paint()

    def _on_leave(self, _event: object = None) -> None:
        self._hover = False
        self._paint()

    def _on_click(self, _event: object = None) -> None:
        self._command()

    def apply_theme(self, theme: dict) -> None:
        self._theme = theme
        if self._variant == "primary":
            self._bg = theme["btn_action_primary"]
            self._hover_bg = theme["btn_action_primary_hover"]
            self._border = theme["accent"]
            self._fg = theme["text"]
        else:
            self._bg = theme["btn_action_ghost"]
            self._hover_bg = theme["btn_action_ghost_hover"]
            self._border = theme["card_border"]
            self._fg = theme["muted"]
        self._paint()

    def _paint(self) -> None:
        bg = self._hover_bg if self._hover else self._bg
        self.configure(bg=bg, highlightbackground=self._border)
        self._label.configure(bg=bg, fg=self._fg)


class FilterSelect(tk.Frame):
    """Custom-styled readonly filter dropdown."""

    def __init__(self, parent: tk.Widget, variable: tk.StringVar, values: list[str], on_change, theme: dict) -> None:
        super().__init__(parent, bg=theme["surface"], highlightthickness=0)
        self._variable = variable
        self._values = values
        self._on_change = on_change
        self._theme = theme
        self._open = False

        self._display = tk.Label(
            self,
            textvariable=variable,
            bg=theme["input_bg"],
            fg=theme["text"],
            font=("Segoe UI", 10),
            anchor="w",
            padx=12,
            pady=8,
            highlightthickness=1,
            highlightbackground=theme["card_border"],
            width=38,
            cursor="hand2",
        )
        self._display.pack(side=tk.LEFT)

        self._arrow = tk.Label(
            self,
            text="\u25be",
            bg=theme["input_bg"],
            fg=theme["muted"],
            font=("Segoe UI", 11, "bold"),
            padx=8,
            pady=8,
            highlightthickness=1,
            highlightbackground=theme["card_border"],
            cursor="hand2",
        )
        self._arrow.pack(side=tk.LEFT, padx=(2, 0))

        for widget in (self._display, self._arrow):
            widget.bind("<Button-1>", self._toggle_menu)

        self._menu: tk.Menu | None = None

    def apply_theme(self, theme: dict) -> None:
        self._theme = theme
        for widget in (self._display, self._arrow):
            widget.configure(
                bg=theme["input_bg"],
                highlightbackground=theme["card_border"],
            )
        self._display.configure(fg=theme["text"])
        self._arrow.configure(fg=theme["muted"])

    def _toggle_menu(self, _event: object = None) -> None:
        if self._menu and self._open:
            return
        t = self._theme
        self._menu = tk.Menu(
            self,
            tearoff=0,
            bg=t["card"],
            fg=t["text"],
            activebackground=t["accent"],
            activeforeground=t["text"],
            borderwidth=0,
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        for value in self._values:
            self._menu.add_command(label=value, command=lambda v=value: self._pick(v))
        x = self._display.winfo_rootx()
        y = self._display.winfo_rooty() + self._display.winfo_height()
        self._open = True
        self._menu.post(x, y)
        self.after(200, self._reset_menu)

    def _reset_menu(self) -> None:
        self._open = False

    def _pick(self, value: str) -> None:
        self._variable.set(value)
        self._on_change()
