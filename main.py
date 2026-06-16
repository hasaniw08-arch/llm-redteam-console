"""LLM Red / Purple Team Workbench — modern SaaS-style GUI."""

from __future__ import annotations

import threading
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

from network_info import collect_network_info
from prompt_engine import (
    FILTER_ALL,
    MAX_PROMPTS,
    engine_status,
    format_prompt_output,
    generate_prompt_ideas,
    list_category_filters,
    load_repositories,
)
from themes import get_theme
from ui_buttons import AppButton, FilterSelect, TeamModeButton

TARGET_HINT = (
    "Describe engagement scope: target LLM, system prompt, RAG pipeline, "
    "agent tools, or test objective (e.g. OWASP LLM01 prompt injection)."
)
APP_VERSION = "1.1.0"


class SaaSApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("LLM Red / Purple Team Workbench")
        self.geometry("1240x880")
        self.minsize(1000, 720)

        self.team_mode = tk.StringVar(value="red")
        self.category_filter = tk.StringVar(value=FILTER_ALL)
        self.status_var = tk.StringVar()
        self._theme = get_theme("red")
        self._last_output = ""
        self._text_widgets: list[scrolledtext.ScrolledText] = []
        self._cards: list[tk.Frame] = []
        self._card_wraps: list[tk.Frame] = []
        self._chips: list[tk.Label] = []
        self._team_buttons: dict[str, TeamModeButton] = {}
        self._action_buttons: list[AppButton] = []
        self._themed_widgets: list[tuple[tk.Widget, dict]] = []
        self._target_has_hint = True

        self._title_font = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self._badge_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self._chip_font = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self._btn_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")

        self._set_window_icon()
        self._build_ui()
        self._bind_shortcuts()
        self._apply_theme("red")
        self._refresh_network()

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-g>", lambda _e: self._generate())
        self.bind("<Control-G>", lambda _e: self._generate())
        self.bind("<Control-Shift-C>", lambda _e: self._copy_output())
        self.bind("<Control-e>", lambda _e: self._export_output())
        self.bind("<Control-E>", lambda _e: self._export_output())
        self.bind("<Control-l>", lambda _e: self._clear_output())
        self.bind("<Control-L>", lambda _e: self._clear_output())
        self.bind("<Control-1>", lambda _e: self._set_mode("red"))
        self.bind("<Control-2>", lambda _e: self._set_mode("purple"))

    def _update_window_title(self) -> None:
        tag = "OFFENSIVE" if self.team_mode.get() == "red" else "DEFENSIVE"
        self.title(f"[{tag}] LLM Red / Purple Team Workbench v{APP_VERSION}")

    def _flash_status(self, message: str, restore_after_ms: int = 3500) -> None:
        self.status_var.set(message)
        if restore_after_ms > 0:
            self.after(restore_after_ms, self._update_status)

    def _icon_path(self) -> Path | None:
        import sys

        roots = []
        if getattr(sys, "frozen", False):
            roots.append(Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)))
        roots.append(Path(__file__).resolve().parent)
        for root in roots:
            p = root / "assets" / "app_icon.ico"
            if p.is_file():
                return p
        return None

    def _set_window_icon(self) -> None:
        icon = self._icon_path()
        if icon:
            try:
                self.iconbitmap(default=str(icon))
            except tk.TclError:
                pass

    def _card(self, parent: tk.Widget, title: str, subtitle: str = "") -> tuple[tk.Frame, tk.Frame]:
        wrap = tk.Frame(parent, bg=self._theme["bg"])
        card = tk.Frame(
            wrap,
            bg=self._theme["card"],
            highlightthickness=1,
            highlightbackground=self._theme["card_border"],
        )
        card.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self._cards.append(card)

        head = tk.Frame(card, bg=self._theme["card"])
        head.pack(fill=tk.X, padx=16, pady=(14, 4))
        title_lbl = tk.Label(
            head,
            text=title,
            bg=self._theme["card"],
            fg=self._theme["text"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        )
        title_lbl.pack(anchor="w")
        self._themed_widgets.append((title_lbl, {"bg": "card", "fg": "text"}))

        if subtitle:
            sub = tk.Label(
                head,
                text=subtitle,
                bg=self._theme["card"],
                fg=self._theme["muted"],
                font=("Segoe UI", 9),
                anchor="w",
                justify=tk.LEFT,
            )
            sub.pack(anchor="w", pady=(2, 0))
            self._themed_widgets.append((sub, {"bg": "card", "fg": "muted"}))

        body = tk.Frame(card, bg=self._theme["card"])
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 14))
        self._themed_widgets.append((body, {"bg": "card"}))
        return wrap, body

    def _action_button(
        self, parent: tk.Widget, text: str, command, variant: str = "primary", **pack_kwargs
    ) -> AppButton:
        btn = AppButton(parent, text, command, self._theme, variant=variant)
        btn.pack(**pack_kwargs)
        self._action_buttons.append(btn)
        return btn

    def _text_widget(self, parent: tk.Widget, height: int, readonly: bool = False) -> scrolledtext.ScrolledText:
        widget = scrolledtext.ScrolledText(
            parent,
            height=height,
            wrap=tk.WORD,
            bg=self._theme["input_bg"],
            fg=self._theme["text"],
            insertbackground=self._theme["text"],
            selectbackground=self._theme["accent"],
            relief=tk.FLAT,
            font=("Consolas", 10),
            padx=10,
            pady=10,
            highlightthickness=1,
            highlightbackground=self._theme["card_border"],
            highlightcolor=self._theme["accent"],
        )
        if readonly:
            widget.configure(state=tk.DISABLED)
        self._text_widgets.append(widget)
        return widget

    def _build_chip_grid(self, parent: tk.Widget, labels: list[str], columns: int = 3) -> tk.Frame:
        frame = tk.Frame(parent, bg=self._theme["card"])
        for i, label in enumerate(labels):
            row, col = divmod(i, columns)
            chip = tk.Label(
                frame,
                text=label,
                bg=self._theme["chip_bg"],
                fg=self._theme["chip_fg"],
                font=self._chip_font,
                padx=10,
                pady=4,
                highlightthickness=1,
                highlightbackground=self._theme["chip_border"],
            )
            chip.grid(row=row, column=col, padx=4, pady=4, sticky="w")
            self._chips.append(chip)
        return frame

    def _apply_theme(self, mode: str) -> None:
        self._theme = get_theme(mode)
        t = self._theme

        self.configure(bg=t["bg"])
        self._hero.configure(bg=t["banner"])
        self._hero_stripe.configure(bg=t["banner_accent"])
        self._badge.configure(
            text=f"  {t['glyph']}  {t['label']}  ",
            bg=t["badge_bg"],
            fg=t["badge_fg"],
            highlightbackground=t["badge_border"],
        )
        self._title_lbl.configure(bg=t["banner"], fg=t["text"])
        self._subtitle_lbl.configure(text=t["subtitle"], bg=t["banner"], fg=t["muted"])
        self._mode_desc_lbl.configure(text=t["mode_desc"], bg=t["surface"], fg=t["muted"])

        for widget, roles in self._themed_widgets:
            bg_key = roles.get("bg", "bg")
            bg = t.get(bg_key, t["bg"])
            opts: dict = {"bg": bg}
            if "fg" in roles:
                opts["fg"] = t[roles["fg"]]
            widget.configure(**opts)

        for frame in (self._hero_inner, self._hero_top):
            frame.configure(bg=t["banner"])

        for card in self._cards:
            card.configure(bg=t["card"], highlightbackground=t["card_border"])

        for wrap in self._card_wraps:
            wrap.configure(bg=t["bg"])

        for chip in self._chips:
            chip.configure(
                bg=t["chip_bg"],
                fg=t["chip_fg"],
                highlightbackground=t["chip_border"],
            )

        for mode_key, btn in self._team_buttons.items():
            btn.set_active(mode_key == mode)

        for btn in self._action_buttons:
            btn.apply_theme(t)

        if hasattr(self, "_filter_select"):
            self._filter_select.apply_theme(t)

        for widget in self._text_widgets:
            widget.configure(
                bg=t["input_bg"],
                fg=t["text"],
                insertbackground=t["text"],
                selectbackground=t["accent"],
                highlightbackground=t["card_border"],
                highlightcolor=t["accent"],
            )
        if self._target_has_hint and self.target_text:
            self.target_text.configure(fg=t["muted"])

        self._surface.configure(bg=t["surface"])
        self._body.configure(bg=t["bg"])
        self._right_col.configure(bg=t["bg"])
        self._footer.configure(bg=t["bg"])
        self._footer_lbl.configure(bg=t["bg"], fg=t["muted"])
        self._status_lbl.configure(bg=t["surface"], fg=t["muted"])
        self._filter_label.configure(bg=t["surface"], fg=t["text"])
        if hasattr(self, "_toggle_row"):
            self._toggle_row.configure(bg=t["surface"])
        self._update_status()
        self._update_window_title()

    def _set_mode(self, mode: str) -> None:
        self.team_mode.set(mode)
        self._apply_theme(mode)
        self._update_window_title()

    def _update_status(self) -> None:
        self.status_var.set(engine_status(self.team_mode.get(), self.category_filter.get()))

    def _on_filter_change(self, _event: object = None) -> None:
        self._update_status()

    def _build_ui(self) -> None:
        self._hero = tk.Frame(self, bg=get_theme("red")["banner"], height=88)
        self._hero.pack(fill=tk.X)
        self._hero_stripe = tk.Frame(self._hero, bg=get_theme("red")["banner_accent"], height=3)
        self._hero_stripe.pack(fill=tk.X, side=tk.BOTTOM)

        hero_inner = tk.Frame(self._hero, bg=get_theme("red")["banner"])
        hero_inner.pack(fill=tk.X, padx=24, pady=16)
        self._hero_inner = hero_inner

        top_row = tk.Frame(hero_inner, bg=get_theme("red")["banner"])
        top_row.pack(fill=tk.X)
        self._hero_top = top_row

        self._badge = tk.Label(
            top_row,
            text="  OFFENSIVE  ",
            bg=get_theme("red")["badge_bg"],
            fg=get_theme("red")["badge_fg"],
            font=self._badge_font,
            padx=8,
            pady=4,
            highlightthickness=1,
            highlightbackground=get_theme("red")["badge_border"],
        )
        self._badge.pack(side=tk.LEFT)

        self._title_lbl = tk.Label(
            top_row,
            text="LLM Red / Purple Team Workbench",
            bg=get_theme("red")["banner"],
            fg=get_theme("red")["text"],
            font=self._title_font,
        )
        self._title_lbl.pack(side=tk.LEFT, padx=(14, 0))

        self._subtitle_lbl = tk.Label(
            hero_inner,
            text=get_theme("red")["subtitle"],
            bg=get_theme("red")["banner"],
            fg=get_theme("red")["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        )
        self._subtitle_lbl.pack(anchor="w", pady=(8, 0))

        self._surface = tk.Frame(self, bg=get_theme("red")["surface"], padx=24, pady=14)
        self._surface.pack(fill=tk.X)

        mode_row = tk.Frame(self._surface, bg=get_theme("red")["surface"])
        mode_row.pack(fill=tk.X)

        mode_lbl = tk.Label(
            mode_row,
            text="Engagement mode",
            bg=get_theme("red")["surface"],
            fg=get_theme("red")["text"],
            font=("Segoe UI", 10, "bold"),
        )
        mode_lbl.pack(anchor="w", pady=(0, 10))
        self._themed_widgets.append((mode_lbl, {"bg": "surface", "fg": "text"}))

        toggle_row = tk.Frame(mode_row, bg=get_theme("red")["surface"])
        toggle_row.pack(fill=tk.X)
        self._toggle_row = toggle_row
        self._themed_widgets.append((toggle_row, {"bg": "surface"}))

        red_btn = TeamModeButton(toggle_row, "red", lambda: self._set_mode("red"))
        red_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._team_buttons["red"] = red_btn

        purple_btn = TeamModeButton(toggle_row, "purple", lambda: self._set_mode("purple"))
        purple_btn.pack(side=tk.LEFT)
        self._team_buttons["purple"] = purple_btn

        self._mode_desc_lbl = tk.Label(
            self._surface,
            text=get_theme("red")["mode_desc"],
            bg=get_theme("red")["surface"],
            fg=get_theme("red")["muted"],
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
        )
        self._mode_desc_lbl.pack(anchor="w", pady=(8, 0))

        filter_row = tk.Frame(self._surface, bg=get_theme("red")["surface"])
        filter_row.pack(fill=tk.X, pady=(12, 0))
        self._filter_label = tk.Label(
            filter_row,
            text="Technique filter",
            bg=get_theme("red")["surface"],
            fg=get_theme("red")["text"],
            font=("Segoe UI Semibold", 10),
        )
        self._filter_label.pack(side=tk.LEFT, padx=(0, 10))

        self._filter_select = FilterSelect(
            filter_row,
            self.category_filter,
            list_category_filters(),
            self._on_filter_change,
            get_theme("red"),
        )
        self._filter_select.pack(side=tk.LEFT)

        self._status_lbl = tk.Label(
            self._surface,
            textvariable=self.status_var,
            bg=get_theme("red")["surface"],
            fg=get_theme("red")["muted"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        self._status_lbl.pack(anchor="w", pady=(8, 0))

        body = tk.Frame(self, bg=get_theme("red")["bg"], padx=24, pady=8)
        body.pack(fill=tk.BOTH, expand=True)
        self._body = body
        body.columnconfigure(0, weight=1, minsize=300)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        net_wrap, net_body = self._card(body, "Network posture", "LAN, DHCP, and connectivity for scoped testing")
        net_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._card_wraps.append(net_wrap)
        self.network_text = self._text_widget(net_body, height=20, readonly=True)
        self.network_text.pack(fill=tk.BOTH, expand=True)
        self._action_button(net_body, "Refresh network", self._refresh_network, variant="ghost", fill=tk.X, pady=(10, 0))

        right = tk.Frame(body, bg=self._theme["bg"])
        right.grid(row=0, column=1, sticky="nsew")
        self._right_col = right
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        target_wrap, target_body = self._card(
            right,
            "Target {Context}",
            "Define the LLM surface under authorized assessment.",
        )
        target_wrap.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._card_wraps.append(target_wrap)

        self.target_text = self._text_widget(target_body, height=5)
        self.target_text.pack(fill=tk.X)
        self.target_text.insert("1.0", TARGET_HINT)
        self.target_text.configure(fg=self._theme["muted"])
        self.target_text.bind("<FocusIn>", self._clear_target_hint)
        self.target_text.bind("<FocusOut>", self._restore_target_hint)

        fw_lbl = tk.Label(
            target_body,
            text="Framework references",
            bg=self._theme["card"],
            fg=self._theme["muted"],
            font=("Segoe UI", 9),
        )
        fw_lbl.pack(anchor="w", pady=(12, 4))
        self._themed_widgets.append((fw_lbl, {"bg": "card", "fg": "muted"}))

        self._chip_grid_frame = tk.Frame(target_body, bg=self._theme["card"])
        self._chip_grid_frame.pack(anchor="w", fill=tk.X)
        self._themed_widgets.append((self._chip_grid_frame, {"bg": "card"}))
        repo_names = [r["name"] for r in load_repositories()]
        self._chip_grid = self._build_chip_grid(self._chip_grid_frame, repo_names, columns=3)
        self._chip_grid.pack(anchor="w")

        btn_row = tk.Frame(target_body, bg=self._theme["card"])
        btn_row.pack(fill=tk.X, pady=(14, 0))
        self._themed_widgets.append((btn_row, {"bg": "card"}))
        self._action_button(
            btn_row,
            f"Generate prompts (max {MAX_PROMPTS})  [Ctrl+G]",
            self._generate,
            variant="primary",
            side=tk.LEFT,
        )
        self._action_button(btn_row, "Clear output", self._clear_output, variant="ghost", side=tk.LEFT, padx=(8, 0))

        out_wrap, out_body = self._card(right, "Prompt ideas", "Bundled adversarial templates mapped to your target")
        out_wrap.grid(row=1, column=0, sticky="nsew")
        self._card_wraps.append(out_wrap)

        out_btns = tk.Frame(out_body, bg=self._theme["card"])
        out_btns.pack(fill=tk.X, pady=(0, 8))
        self._themed_widgets.append((out_btns, {"bg": "card"}))
        self._action_button(out_btns, "Copy all", self._copy_output, variant="primary", side=tk.LEFT)
        self._action_button(out_btns, "Export .txt", self._export_output, variant="ghost", side=tk.LEFT, padx=(8, 0))

        self.output_text = self._text_widget(out_body, height=20, readonly=True)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        self._set_readonly(self.output_text, "Select mode, set filter, enter target context, then generate.")

        self._footer = tk.Frame(self, bg=get_theme("red")["bg"], padx=24, pady=10)
        self._footer.pack(fill=tk.X)
        self._footer_lbl = tk.Label(
            self._footer,
            text=(
                f"v{APP_VERSION}  \u00b7  Ctrl+G generate  \u00b7  Ctrl+Shift+C copy  \u00b7  "
                "Ctrl+E export  \u00b7  Ctrl+1 red  \u00b7  Ctrl+2 purple"
            ),
            bg=get_theme("red")["bg"],
            fg=get_theme("red")["muted"],
            font=("Segoe UI", 9),
        )
        self._footer_lbl.pack(anchor="w")

    def _clear_target_hint(self, _event: object = None) -> None:
        if self._target_has_hint:
            self.target_text.delete("1.0", tk.END)
            self.target_text.configure(fg=self._theme["text"])
            self._target_has_hint = False

    def _restore_target_hint(self, _event: object = None) -> None:
        if not self.target_text.get("1.0", tk.END).strip():
            self.target_text.insert("1.0", TARGET_HINT)
            self.target_text.configure(fg=self._theme["muted"])
            self._target_has_hint = True

    def _target_context(self) -> str:
        if self._target_has_hint:
            return ""
        return self.target_text.get("1.0", tk.END).strip()

    def _get_output_text(self) -> str:
        return self.output_text.get("1.0", tk.END).strip()

    def _set_readonly(self, widget: scrolledtext.ScrolledText, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)

    def _copy_output(self) -> None:
        text = self._get_output_text()
        if not text or text.startswith("Select mode"):
            self._flash_status("Nothing to copy — generate prompts first.", 2500)
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._flash_status("Copied prompt pack to clipboard.")

    def _export_output(self) -> None:
        text = self._get_output_text()
        if not text or text.startswith("Select mode"):
            self._flash_status("Nothing to export — generate prompts first.", 2500)
            return
        mode = self.team_mode.get()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Export Prompt Pack",
            defaultextension=".txt",
            initialfile=f"llm_{mode}_team_prompts_{stamp}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(text, encoding="utf-8")
        self._flash_status(f"Exported to {Path(path).name}")

    def _refresh_network(self) -> None:
        def work() -> None:
            snap = collect_network_info()
            text = "\n".join(snap.summary_lines)
            self.after(0, lambda: self._set_readonly(self.network_text, text))

        threading.Thread(target=work, daemon=True).start()

    def _generate(self) -> None:
        context = self._target_context()
        if not context:
            messagebox.showwarning("Target Required", "Enter a target context before generating prompts.")
            return

        mode = self.team_mode.get()
        category = self.category_filter.get()
        self.status_var.set("Generating prompts...")
        self._set_readonly(self.output_text, "Generating prompt ideas...")

        def work() -> None:
            ideas = generate_prompt_ideas(context, limit=MAX_PROMPTS, team_mode=mode, category_filter=category)
            output = format_prompt_output(ideas, team_mode=mode)
            status = engine_status(mode, category)
            self.after(0, lambda: self._on_generated(output, status))

        threading.Thread(target=work, daemon=True).start()

    def _on_generated(self, output: str, status: str) -> None:
        self._last_output = output
        self._set_readonly(self.output_text, output)
        self.status_var.set(status)

    def _clear_output(self) -> None:
        self._last_output = ""
        self._set_readonly(self.output_text, "")


def main() -> None:
    app = SaaSApp()
    app.mainloop()


if __name__ == "__main__":
    main()
