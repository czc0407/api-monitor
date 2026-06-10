"""tkinter frameless desktop widget — macOS-inspired UI with native rounded corners."""
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime


def _apply_native_corners(root, radius: int = 16, attempt: int = 0):
    """Use PyObjC to round the NSWindow contentView + hide white corner bleed."""
    if attempt >= 5:
        return
    try:
        from AppKit import NSApp, NSColor
        root.update_idletasks()
        for win in NSApp.windows():
            if win.title() == "API Monitor" and win.isVisible():
                # make window background transparent so rounded corners don't show white
                win.setOpaque_(False)
                win.setBackgroundColor_(NSColor.clearColor())
                win.setHasShadow_(False)
                # round the content view
                cv = win.contentView()
                cv.setWantsLayer_(True)
                cv.layer().setCornerRadius_(float(radius))
                cv.layer().setMasksToBounds_(True)
                return
    except Exception:
        pass
    root.after(150, lambda: _apply_native_corners(root, radius, attempt + 1))


from api_clients import BalanceSnapshot


class DesktopWidget:
    def __init__(self, cfg: dict):
        ui = cfg.get("ui", {})
        self.root = tk.Tk()
        self.root.title("API Monitor")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", 1)

        w = ui.get("width", 340)
        h = 310
        self.root.geometry(f"{w}x{h}+100+100")

        # macOS dark palette
        self.BG = ui.get("bg_color", "#1c1c1e")
        self.TB = ui.get("titlebar_color", "#2c2c2e")
        self.FG = ui.get("fg_color", "#f5f5f7")
        self.SEC = ui.get("secondary_color", "#98989d")
        self.ACC = ui.get("accent_color", "#0a84ff")
        self.ERR = ui.get("error_color", "#ff453a")
        self.OK = ui.get("success_color", "#30d158")
        self.SEP = ui.get("separator_color", "#38383a")

        # fonts
        families = [f.strip() for f in ui.get("font_family", "Menlo").split(",")]
        available = set(tkfont.families(self.root))
        chosen = next((f for f in families if f in available), "Menlo")
        self.FONT = (chosen, 13)
        self.FONT_TITLE = (chosen, 14)
        self.FONT_SMALL = (chosen, 11)
        self.FONT_BOLD = (chosen, 13, "bold")
        self.FONT_BTN = (chosen, 18, "bold")

        self.root.configure(bg=self.BG)
        self._on_refresh = lambda: None

        self._build_titlebar()
        self._build_content()
        self._build_footer()

        # drag bindings
        self._drag = {"x": 0, "y": 0}
        for w in (self._titlebar, self._title_lbl, self._status_dot, self._fill):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_motion)

        # context menu
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="Refresh Now", command=self._on_refresh)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="Quit", command=self.root.destroy)
        for tgt in (self.root, self._content, self._footer):
            tgt.bind("<Button-2>", self._context)
            tgt.bind("<Button-3>", self._context)

        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Command-r>", lambda e: self._on_refresh())

        # apply native rounded corners via PyObjC once window is visible
        self.root.after(300, lambda: _apply_native_corners(self.root, 16))

    # ───────────── titlebar ─────────────

    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=self.TB, height=40)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        self._fill = tk.Label(bar, text="  ", bg=self.TB, font=self.FONT_SMALL)
        self._fill.pack(side=tk.LEFT)

        self._status_dot = tk.Label(bar, text="●", fg=self.OK, bg=self.TB,
                                    font=(self.FONT[0], 11))
        self._status_dot.pack(side=tk.LEFT, padx=(0, 8))

        self._title_lbl = tk.Label(bar, text="API Monitor", fg=self.FG, bg=self.TB,
                                   font=self.FONT_TITLE)
        self._title_lbl.pack(side=tk.LEFT)

        # refresh
        self._refresh_btn = tk.Label(bar, text="↻", fg=self.ACC, bg=self.TB,
                                     font=self.FONT_BTN, cursor="hand2")
        self._refresh_btn.pack(side=tk.RIGHT, padx=(0, 4))
        self._refresh_btn.bind("<Button-1>", lambda e: self._on_refresh())
        self._refresh_btn.bind("<Enter>", lambda e: self._refresh_btn.config(fg="#6ab3ff"))
        self._refresh_btn.bind("<Leave>", lambda e: self._refresh_btn.config(fg=self.ACC))

        # close
        self._close_btn = tk.Label(bar, text="✕", fg=self.FG, bg=self.TB,
                                   font=(self.FONT[0], 15), cursor="hand2")
        self._close_btn.pack(side=tk.RIGHT, padx=(0, 10))
        self._close_btn.bind("<Button-1>", lambda e: self.root.destroy())
        self._close_btn.bind("<Enter>", lambda e: self._close_btn.config(fg=self.ERR))
        self._close_btn.bind("<Leave>", lambda e: self._close_btn.config(fg=self.FG))

        self._titlebar = bar

    # ───────────── content ─────────────

    def _build_content(self):
        self._content = tk.Frame(self.root, bg=self.BG)
        self._content.pack(fill=tk.BOTH, expand=True, padx=18, pady=(10, 0))

        # DeepSeek
        tk.Label(self._content, text="DeepSeek", fg=self.ACC, bg=self.BG,
                 font=self.FONT_BOLD, anchor=tk.W).pack(fill=tk.X)
        self.ds_balance = tk.Label(self._content, text="Balance  —", fg=self.FG,
                                   bg=self.BG, font=self.FONT, anchor=tk.W)
        self.ds_balance.pack(fill=tk.X, pady=(4, 0))
        self.ds_detail = tk.Label(self._content, text="", fg=self.SEC, bg=self.BG,
                                  font=self.FONT_SMALL, anchor=tk.W)
        self.ds_detail.pack(fill=tk.X)
        self.ds_rate = tk.Label(self._content, text="", fg=self.SEC, bg=self.BG,
                                font=self.FONT_SMALL, anchor=tk.W)
        self.ds_rate.pack(fill=tk.X)
        self.ds_error = tk.Label(self._content, text="", fg=self.ERR, bg=self.BG,
                                 font=self.FONT_SMALL, anchor=tk.W, wraplength=304)
        self.ds_error.pack(fill=tk.X)

        tk.Frame(self._content, bg=self.SEP, height=1).pack(fill=tk.X, pady=(8, 10))

        # OpenKey
        tk.Label(self._content, text="OpenKey", fg=self.ACC, bg=self.BG,
                 font=self.FONT_BOLD, anchor=tk.W).pack(fill=tk.X)
        self.ok_acct = tk.Label(self._content, text="Account  —", fg=self.FG,
                                bg=self.BG, font=self.FONT, anchor=tk.W)
        self.ok_acct.pack(fill=tk.X, pady=(4, 0))
        self.ok_acct_detail = tk.Label(self._content, text="", fg=self.SEC, bg=self.BG,
                                       font=self.FONT_SMALL, anchor=tk.W)
        self.ok_acct_detail.pack(fill=tk.X)
        self.ok_token = tk.Label(self._content, text="Token    —", fg=self.FG,
                                 bg=self.BG, font=self.FONT, anchor=tk.W)
        self.ok_token.pack(fill=tk.X, pady=(6, 0))
        self.ok_token_detail = tk.Label(self._content, text="", fg=self.SEC, bg=self.BG,
                                        font=self.FONT_SMALL, anchor=tk.W)
        self.ok_token_detail.pack(fill=tk.X)
        self.ok_rate = tk.Label(self._content, text="", fg=self.SEC, bg=self.BG,
                                font=self.FONT_SMALL, anchor=tk.W)
        self.ok_rate.pack(fill=tk.X)
        self.ok_error = tk.Label(self._content, text="", fg=self.ERR, bg=self.BG,
                                 font=self.FONT_SMALL, anchor=tk.W, wraplength=304)
        self.ok_error.pack(fill=tk.X)

    # ───────────── footer ─────────────

    def _build_footer(self):
        self._footer = tk.Frame(self.root, bg=self.BG)
        self._footer.pack(fill=tk.X, side=tk.BOTTOM, padx=18, pady=(4, 10))
        tk.Frame(self._footer, bg=self.SEP, height=1).pack(fill=tk.X, pady=(0, 6))
        self.footer_label = tk.Label(
            self._footer, text="Last update  —  |  Next  —",
            fg=self.SEC, bg=self.BG, font=self.FONT_SMALL, anchor=tk.W,
        )
        self.footer_label.pack(fill=tk.X)

    # ───────────── events ─────────────

    def _context(self, event):
        self.ctx_menu.tk_popup(event.x_root, event.y_root)

    def _drag_start(self, event):
        self._drag["x"] = event.x_root - self.root.winfo_x()
        self._drag["y"] = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event):
        self.root.geometry(f"+{event.x_root - self._drag['x']}+{event.y_root - self._drag['y']}")

    # ───────────── public ─────────────

    def set_on_refresh(self, fn):
        self._on_refresh = fn

    def refresh(self, snapshots: list[BalanceSnapshot], interval: int):
        ds = ok = None
        for s in snapshots:
            if s.service == "deepseek":
                ds = s
            elif s.service == "openkey":
                ok = s

        self._show_deepseek(ds)
        self._show_openkey(ok)

        has_err = any(s and s.error for s in (ds, ok))
        self._status_dot.config(fg=self.ERR if has_err else self.OK)

        now = datetime.now().strftime("%H:%M:%S")
        self.footer_label.config(text=f"Last update  {now}  |  Next  {interval}s")

    def _show_deepseek(self, s: BalanceSnapshot | None):
        if s is None or s.error:
            self.ds_balance.config(text="Balance  —")
            self.ds_detail.config(text="")
            self.ds_rate.config(text="")
            self.ds_error.config(text=s.error if s else "")
            return
        self.ds_error.config(text="")
        self.ds_balance.config(text=f"Balance  ¥{s.total_balance:.2f}" if s.total_balance is not None else "Balance  —")
        parts = []
        if s.granted_balance is not None:
            parts.append(f"Granted  ¥{s.granted_balance:.2f}")
        if s.topped_up_balance is not None:
            parts.append(f"Topped  ¥{s.topped_up_balance:.2f}")
        self.ds_detail.config(text="  ".join(parts))
        self._set_rate(self.ds_rate, s.rate, "CNY")

    def _show_openkey(self, s: BalanceSnapshot | None):
        if s is None or s.error:
            self.ok_acct.config(text="Account  —")
            self.ok_acct_detail.config(text="")
            self.ok_token.config(text="Token    —")
            self.ok_token_detail.config(text="")
            self.ok_rate.config(text="")
            self.ok_error.config(text=s.error if s else "")
            return
        cur = s.currency or "USD"
        self.ok_error.config(text="")
        self.ok_acct.config(text=f"Account  {cur}${s.remained_cash:.2f}" if s.remained_cash is not None else "Account  —")
        if s.remained_cash is not None and s.used_cash is not None:
            self.ok_acct_detail.config(text=f"Used  {cur}${s.used_cash:.2f}    Total  {cur}${s.remained_cash + s.used_cash:.2f}")
        self.ok_token.config(text=f"Token    {cur}${s.token_remained_cash:.2f}" if s.token_remained_cash is not None else "Token    —")
        if s.token_remained_cash is not None and s.token_used_cash is not None:
            self.ok_token_detail.config(text=f"Used  {cur}${s.token_used_cash:.2f}    Total  {cur}${s.token_remained_cash + s.token_used_cash:.2f}")
        else:
            self.ok_token_detail.config(text="")
        self._set_rate(self.ok_rate, s.rate, "USD")

    @staticmethod
    def _set_rate(label: tk.Label, rate: dict | None, currency: str):
        if rate is None:
            label.config(text="")
            return
        mps = rate["money_per_second"]
        tps = rate["tokens_per_second"]
        sym = "¥" if currency == "CNY" else "$"
        if tps >= 1000:
            label.config(text=f"Rate  {sym}{mps:.6f}/s  (~{tps/1000:.0f}k tok/s)")
        else:
            label.config(text=f"Rate  {sym}{mps:.6f}/s  (~{tps:.0f} tok/s)")

    def mainloop(self):
        self.root.mainloop()

    def after(self, ms: int, callback, *args):
        return self.root.after(ms, callback, *args)

    def cancel_timer(self, token: str):
        self.root.after_cancel(token)
