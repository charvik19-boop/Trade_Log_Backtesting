"""
Trading Journal - Live Trades & Backtesting System

Required libraries:
pip install pandas matplotlib pillow ttkbootstrap

How to run:
python trading_journal_gui.py
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from PIL import Image, ImageTk
import pandas as pd
import threading
from datetime import datetime
from pathlib import Path
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import project modules
import trade_log
import backtest_log
import screenshot_utils
import analytics
import csv_handler

class TradingJournalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Journal - Live Trades & Backtesting System")
        self.root.geometry("1400x900")
        
        # Initialize Database
        trade_log.init_db()
        
        # State variables
        self.bt_screenshot_path = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        
        self._setup_styles()
        self._create_widgets()
        self._load_initial_data()

    def _setup_styles(self):
        self.style = ttk.Style(theme="darkly")
        
    def _create_widgets(self):
        # Main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=BOTH, expand=YES)
        
        # Create Tabs
        self.bt_tab = ttk.Frame(self.notebook)
        self.analytics_tab = ttk.Frame(self.notebook)
        self.import_export_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.bt_tab, text="Backtesting System")
        self.notebook.add(self.analytics_tab, text="Dashboard & Analytics")
        self.notebook.add(self.import_export_tab, text="Import / Export")
        
        # Setup individual tabs
        self._setup_backtest_tab()
        self._setup_analytics_tab()
        self._setup_import_export_tab()
        
        # Status Bar
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=SUNKEN, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X)

    # --- BACKTEST TAB SETUP ---
    def _setup_backtest_tab(self):
        """Advanced Backtesting Journal with Adjustable Panes and Dynamic Criteria"""
        self.bt_notebook = ttk.Notebook(self.bt_tab)
        self.bt_notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # --- Tab 1: Trade Entry ---
        entry_tab = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(entry_tab, text="Trade Entry")

        self.bt_form_entries = {}
        excel_opts = backtest_log.get_excel_source_options()

        # (1) & (2) Top Horizontal Header Section with Save Button
        top_header = ttk.Frame(entry_tab)
        top_header.pack(fill=X, padx=10, pady=5)
        
        def make_searchable(cb, original_values):
            def on_key(event):
                val = cb.get().lower()
                if val == '': cb['values'] = original_values
                else: cb['values'] = [item for item in original_values if val in item.lower()]
            cb.bind("<KeyRelease>", on_key)
        
        top_fields = [
            ("Strategy", "strategy", "dropdown", excel_opts.get('strategies', [])),
            ("Symbol", "symbol", "entry", None),
            ("Sector", "sector", "dropdown", excel_opts.get('sectors', [])),
            ("Trade Type", "trade_type", "dropdown", excel_opts.get('trade_types', [])),
            ("Chart Pattern", "chart_pattern", "dropdown", excel_opts.get('chart_patterns', [])),
            ("Signif. Candle", "significant_candle", "dropdown", excel_opts.get('significant_candles', [])),
            ("Signal Date", "signal_date", "date", None),
            ("Signal Time", "signal_time", "time", None)
        ]

        for i, (lbl_txt, key, f_type, opts) in enumerate(top_fields):
            f = ttk.Frame(top_header)
            f.grid(row=0, column=i, padx=5, sticky=EW)
            ttk.Label(f, text=lbl_txt, font=("Helvetica", 9, "bold")).pack(anchor=W)
            if f_type == "dropdown":
                w_width = 25 if key == "significant_candle" else 12
                w = ttk.Combobox(f, values=opts, width=w_width)
                make_searchable(w, opts)
                if key in ["strategy", "trade_type"]:
                    w.bind("<<ComboboxSelected>>", lambda e: self._update_dynamic_criteria())
            elif f_type == "date":
                w = ttk.DateEntry(f)
            elif f_type == "time":
                w_frame = ttk.Frame(f)
                w_frame.pack(fill=X)
                h = ttk.Spinbox(w_frame, from_=0, to=23, width=3, format="%02.0f")
                h.pack(side=LEFT); h.set("09")
                ttk.Label(w_frame, text=":").pack(side=LEFT)
                m = ttk.Spinbox(w_frame, from_=0, to=59, width=3, format="%02.0f")
                m.pack(side=LEFT); m.set("15")
                w = (h, m) # Store tuple
            else:
                w = ttk.Entry(f, width=12)
            if not isinstance(w, tuple): w.pack(fill=X, pady=2)
            self.bt_form_entries[key] = w

        # Header Save Button
        ttk.Button(top_header, text="Save Header", bootstyle=SUCCESS, 
                   command=self._save_backtest_trade).grid(row=0, column=8, padx=10, pady=(15,0))

        for i in range(9): top_header.columnconfigure(i, weight=1)

        # (4) Middle Section: Adjustable Paned Window
        mid_scroll = ScrolledFrame(entry_tab, autohide=True)
        mid_scroll.pack(fill=BOTH, expand=YES, padx=10)

        self.bt_paned = ttk.Panedwindow(mid_scroll, orient=HORIZONTAL)
        self.bt_paned.pack(fill=BOTH, expand=YES)

        self.tide_container = ttk.LabelFrame(self.bt_paned, text="TIDE Criteria")
        self.wave_container = ttk.LabelFrame(self.bt_paned, text="WAVE Criteria")
        self.entry_details_container = ttk.LabelFrame(self.bt_paned, text="Entry Details")

        self.bt_paned.add(self.tide_container, weight=1)
        self.bt_paned.add(self.wave_container, weight=1)
        self.bt_paned.add(self.entry_details_container, weight=1)

        self._setup_entry_details_col()
        self._update_dynamic_criteria() # Initial draw

        # --- Tab 2: Trade History ---
        history_tab = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(history_tab, text="Trade History")

        # Session Filter
        session_frame = ttk.Frame(history_tab)
        session_frame.pack(fill=X, pady=5)
        ttk.Label(session_frame, text="Session Filter:").pack(side=LEFT, padx=5)
        self.bt_session_filter = ttk.Combobox(session_frame)
        self.bt_session_filter.pack(side=LEFT, padx=5)
        self.bt_session_filter.bind("<<ComboboxSelected>>", lambda e: self._refresh_backtest_table())

        cols = ("ID", "Timestamp", "Symbol", "Direction", "Entry", "Exit", "PnL", "R", "Session")
        self.bt_tree = ttk.Treeview(history_tab, columns=cols, show="headings", bootstyle=INFO)
        for col in cols:
            self.bt_tree.heading(col, text=col)
            self.bt_tree.column(col, width=100, anchor=CENTER)
        self.bt_tree.pack(fill=BOTH, expand=YES)

        action_frame = ttk.Frame(history_tab)
        action_frame.pack(fill=X, pady=10)
        ttk.Button(action_frame, text="Delete Selected", bootstyle=DANGER, command=self._delete_bt_trade).pack(side=LEFT, padx=5)
        ttk.Button(action_frame, text="Preview Screenshot", command=lambda: self._preview_selected(self.bt_tree)).pack(side=LEFT, padx=5)
        ttk.Button(action_frame, text="Refresh", command=self._refresh_backtest_table).pack(side=LEFT, padx=5)

        # --- Tab 3: Session Analysis ---
        analysis_tab = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(analysis_tab, text="Session Analysis")

        analysis_container = ttk.Frame(analysis_tab)
        analysis_container.pack(fill=BOTH, expand=YES, padx=20, pady=20)

        selector_frame = ttk.Frame(analysis_container)
        selector_frame.pack(fill=X, pady=10)
        
        ttk.Label(selector_frame, text="Select Session to Analyze:").pack(side=LEFT, padx=5)
        self.bt_analysis_session_selector = ttk.Combobox(selector_frame)
        self.bt_analysis_session_selector.pack(side=LEFT, padx=5)
        self.bt_analysis_session_selector.bind("<<ComboboxSelected>>", lambda e: self._refresh_bt_analysis())
        
        ttk.Button(selector_frame, text="Refresh Session Stats", command=self._refresh_bt_analysis).pack(side=LEFT, padx=5)
        self.bt_session_metrics = self._create_metric_group(analysis_container, "SESSION PERFORMANCE SUMMARY", side=TOP)

    def _setup_entry_details_col(self):
        for child in self.entry_details_container.winfo_children(): child.destroy()
        fields = [
            ("Session", "backtest_session", "session"),
            ("Direction", "direction", "dropdown"),
            ("Entry Price", "entry_price", "entry"),
            ("Stop Loss", "stop_loss", "entry"),
            ("Exit Price", "exit_price", "entry"),
            ("Risk Amount", "risk_amount", "entry"),
        ]
        for lbl, key, f_type in fields:
            row = ttk.Frame(self.entry_details_container)
            row.pack(fill=X, pady=2, padx=10)
            ttk.Label(row, text=lbl, width=20, anchor=W).pack(side=LEFT)
            if f_type == "entry":
                w = ttk.Entry(row, width=25)
            elif f_type == "dropdown":
                w = ttk.Combobox(row, values=["LONG", "SHORT"], width=23)
            else: # session
                w = ttk.Combobox(row, width=23)
            w.pack(side=LEFT, padx=10)
            self.bt_form_entries[key] = w
        
        btn_row = ttk.Frame(self.entry_details_container)
        btn_row.pack(pady=10)
        ttk.Button(btn_row, text="Save Entry", bootstyle=(INFO, OUTLINE), 
                   command=self._save_backtest_trade).pack(side=LEFT, padx=2)
        entry_keys = [f[1] for f in fields]
        ttk.Button(btn_row, text="Clear", bootstyle=(SECONDARY, OUTLINE),
                   command=lambda: self._clear_specific_fields(entry_keys)).pack(side=LEFT, padx=2)

    def _update_dynamic_criteria(self):
        strat = self.bt_form_entries['strategy'].get()
        ttype = self.bt_form_entries['trade_type'].get()
        
        is_bull = (strat == "Bullish Momentum" and ttype == "Bullish Momentum")
        is_bear = (strat == "Bearish Momentum" and ttype == "Bearish Momentum")

        # (TIDE Criteria Generation)
        for child in self.tide_container.winfo_children(): child.destroy()
        tide_fields = []
        if is_bull:
            tide_fields = [
                ("Upper BB Challenge", "tide_upper_bb_challenge", "yn"),
                ("MACD Uptick", "tide_macd_tick", "yn"),
                ("MACD Above Zeroline", "tide_macd_zeroline", "yn"),
                ("Stochastic", "tide_stochastic", ["PCO", "NCO", "OSZ", "OBZ", "Flat"]),
                ("Stochastic Value", "tide_stochastic_val", "entry"),
                ("RSI > 60", "tide_rsi_threshold", "yn"),
                ("RSI Value", "tide_rsi_val", "entry"),
                ("Price Above 50 EMA", "tide_price_above_50ema", "yn")
            ]
        elif is_bear:
            tide_fields = [
                ("Lower BB Challenge", "tide_upper_bb_challenge", "yn"),
                ("MACD Downtick", "tide_macd_tick", "yn"),
                ("MACD Below Zeroline", "tide_macd_zeroline", "yn"),
                ("Stochastic", "tide_stochastic", ["PCO", "NCO", "OSZ", "OBZ", "Flat"]),
                ("Stochastic Value", "tide_stochastic_val", "entry"),
                ("RSI < 40", "tide_rsi_threshold", "yn"),
                ("RSI Value", "tide_rsi_val", "entry"),
                ("Price Below 50 EMA", "tide_price_above_50ema", "yn")
            ]
        self._render_criteria_rows(self.tide_container, tide_fields, "Save TIDE")

        # (WAVE Criteria Generation)
        for child in self.wave_container.winfo_children(): child.destroy()
        wave_fields = []
        if is_bull:
            wave_fields = [
                ("Upper BB Challenge", "wave_bb_challenge", "yn"),
                ("MACD Uptick", "wave_macd_tick", "yn"),
                ("MACD Above Zeroline", "wave_macd_zeroline", "yn"),
                ("Stochastic", "wave_stochastic", ["PCO", "NCO", "OSZ", "OBZ", "Flat"]),
                ("Stochastic Value", "wave_stochastic_val", "entry"),
                ("RSI > 60", "wave_rsi_threshold", "yn"),
                ("RSI Value", "wave_rsi_val", "entry"),
                ("Price Above 50 EMA", "wave_price_above_50ema", "yn"),
                ("Trendline Breakout", "wave_trendline_break", "yn"),
                ("Breakout Candle Volumes above Average", "wave_volume_above_avg", "yn"),
                ("Shake Out Before Breakout", "wave_shake_out", "yn"),
                ("At least Two Higher Low Prior to BB Challenge on line chart", "wave_two_higher_lows", "yn"),
                ("5 EMA PCO 13 or 26 EMA prior to last three period", "wave_ema_pco", "yn"),
                ("ADX Ungali > 15", "wave_adx_ungali", "yn"),
                ("ADX Value", "wave_adx_val", "entry"),
                ("+DI or -DI", "wave_di_crossover", ["PCO", "NCO", "Converging", "Diverging"]),
                ("No Immediate Major Resistance", "wave_resistance", "yn")
            ]
        elif is_bear:
            wave_fields = [
                ("Lower BB Challenge", "wave_bb_challenge", "yn"),
                ("MACD Downtick", "wave_macd_tick", "yn"),
                ("MACD Below Zeroline", "wave_macd_zeroline", "yn"),
                ("Stochastic", "wave_stochastic", ["PCO", "NCO", "OSZ", "OBZ", "Flat"]),
                ("Stochastic Value", "wave_stochastic_val", "entry"),
                ("RSI < 40", "wave_rsi_threshold", "yn"),
                ("RSI Value", "wave_rsi_val", "entry"),
                ("Price Below 50 EMA", "wave_price_above_50ema", "yn"),
                ("Trendline Breakdown", "wave_trendline_break", "yn"),
                ("Breakout Candle Volumes above Average", "wave_volume_above_avg", "yn"),
                ("Shake Out Before Breakdown", "wave_shake_out", "yn"),
                ("At least Two Lower High Prior to BB Challenge on line chart", "wave_two_higher_lows", "yn"),
                ("5 EMA NCO 13 or 26 EMA prior to last three period", "wave_ema_pco", "yn"),
                ("ADX Ungali > 15", "wave_adx_ungali", "yn"),
                ("ADX Value", "wave_adx_val", "entry"),
                ("+DI or -DI", "wave_di_crossover", ["PCO", "NCO", "Converging", "Diverging"]),
                ("No Immediate Major Resistance", "wave_resistance", "yn")
            ]
        self._render_criteria_rows(self.wave_container, wave_fields, "Save WAVE")

    def _render_criteria_rows(self, parent, fields, btn_text):
        def add_row(parent, label, key, f_type):
            row = ttk.Frame(parent)
            row.pack(fill=X, pady=1)
            ttk.Label(row, text=label, width=60, font=("Helvetica", 9), anchor=W).pack(side=LEFT, padx=5)
            if f_type == "entry":
                w = ttk.Entry(row, width=20)
            elif isinstance(f_type, list):
                w = ttk.Combobox(row, values=f_type, width=20)
            else:
                w = ttk.Combobox(row, values=["YES", "NO"], width=20)
            w.pack(side=LEFT, padx=10)
            self.bt_form_entries[key] = w
        
        for l, k, t in fields: add_row(parent, l, k, t)
        btn_row = ttk.Frame(parent)
        btn_row.pack(pady=5)
        ttk.Button(btn_row, text=btn_text, bootstyle=(INFO, OUTLINE), command=self._save_backtest_trade).pack(side=LEFT, padx=2)
        field_keys = [f[1] for f in fields]
        ttk.Button(btn_row, text="Clear", bootstyle=(SECONDARY, OUTLINE), 
                   command=lambda: self._clear_specific_fields(field_keys)).pack(side=LEFT, padx=2)

    # --- ANALYTICS TAB SETUP ---
    def _setup_analytics_tab(self):
        self.analytics_scroll = ScrolledFrame(self.analytics_tab, autohide=True)
        self.analytics_scroll.pack(fill=BOTH, expand=YES)
        
        # Metrics Header
        metrics_container = ttk.Frame(self.analytics_scroll)
        metrics_container.pack(fill=X, padx=10, pady=10)
        
        self.bt_metric_cards = self._create_metric_group(metrics_container, "OVERALL BACKTEST PERFORMANCE", side=TOP)
        
        # Charts Section
        chart_control = ttk.Frame(self.analytics_scroll)
        chart_control.pack(fill=X, pady=10)
        ttk.Button(chart_control, text="Refresh All Analytics", bootstyle=PRIMARY, command=self._refresh_analytics).pack(side=TOP, pady=5)
        
        self.chart_container = ttk.Frame(self.analytics_scroll)
        self.chart_container.pack(fill=BOTH, expand=YES)
        
    # --- IMPORT/EXPORT TAB SETUP ---
    def _setup_import_export_tab(self):
        container = ttk.Frame(self.import_export_tab)
        container.pack(expand=YES)
        
        export_frame = ttk.LabelFrame(container, text="Data Export")
        export_frame.grid(row=0, column=0, padx=20, pady=20)
        
        ttk.Button(export_frame, text="Export All Backtests (CSV)", width=30, command=csv_handler.export_backtest_to_csv).pack(pady=10, padx=10)
        
        import_frame = ttk.LabelFrame(container, text="Data Import")
        import_frame.grid(row=0, column=1, padx=20, pady=20)
        
        ttk.Button(import_frame, text="Import CSV to Backtest", width=30, command=lambda: self._handle_import(True)).pack(pady=10, padx=10)
        
        template_frame = ttk.LabelFrame(container, text="Templates")
        template_frame.grid(row=1, column=0, columnspan=2, sticky=EW, padx=20, pady=20)
        
        ttk.Button(template_frame, text="Download Backtest Template", command=lambda: csv_handler.get_sample_csv_template(True)).pack(side=LEFT, padx=10, expand=YES)

    # --- WIDGET HELPERS ---
    def _create_trade_form(self, parent, is_backtest):
        entries = {}
        # Backtest form is now handled directly in _setup_backtest_tab for specific layout
        if not is_backtest:
            fields = [
                ("Symbol", "symbol", "entry"),
                ("Direction", "direction", "dropdown"),
                ("Entry Price", "entry_price", "entry"),
                ("Stop Loss", "stop_loss", "entry"),
                ("Take Profit", "take_profit", "entry"),
                ("Exit Price", "exit_price", "entry"),
                ("Position Size", "position_size", "entry"),
                ("Risk Amount", "risk_amount", "entry"),
                ("Strategy", "strategy", "entry"),
                ("Timeframe", "timeframe", "entry"),
                ("Notes", "notes", "text")
            ]
            for label, key, f_type in fields:
                row = ttk.Frame(parent)
                row.pack(fill=X, pady=2)
                ttk.Label(row, text=label, width=15).pack(side=LEFT)
                if f_type == "entry":
                    w = ttk.Entry(row); w.pack(side=RIGHT, fill=X, expand=YES); entries[key] = w
                elif f_type == "dropdown":
                    w = ttk.Combobox(row, values=["LONG", "SHORT"]); w.pack(side=RIGHT, fill=X, expand=YES); entries[key] = w
                elif f_type == "text":
                    w = tk.Text(row, height=3); w.pack(side=RIGHT, fill=X, expand=YES); entries[key] = w
        
        return entries

    def _create_metric_group(self, parent, title, side):
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(side=side, fill=BOTH, expand=YES, padx=5)
        
        cards = {}
        metrics = ["Total Trades", "Win Rate %", "Total PnL", "Expectancy", "Profit Factor", "Max Drawdown"]
        for m in metrics:
            row = ttk.Frame(frame)
            row.pack(fill=X, pady=5, padx=10)
            ttk.Label(row, text=m).pack(side=LEFT)
            val = ttk.Label(row, text="--", font=("Helvetica", 10, "bold"), bootstyle=INFO)
            val.pack(side=RIGHT)
            cards[m] = val
        return cards

    # --- FORM LOGIC ---
    def _on_price_change(self, is_backtest):
        entries = self.bt_form_entries if is_backtest else self.live_form_entries
        try:
            data = {
                "entry_price": float(entries["entry_price"].get()),
                "stop_loss": float(entries["stop_loss"].get()),
                "exit_price": float(entries["exit_price"].get()),
                "risk_amount": float(entries["risk_amount"].get()),
                "direction": entries["direction"].get()
            }
            result = trade_log.calculate_pnl_metrics(data)
            self.status_var.set(f"Estimated PnL: {result.get('pnl', 0)} | R: {result.get('r_multiple', 0)}")
        except (ValueError, ZeroDivisionError):
            pass

    def _handle_attach_screenshot(self, is_backtest):
        # We need a trade ID to attach. This is usually done for existing trades.
        # For new trades, we store path in temp and update after save.
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if path:
            if is_backtest: self.bt_screenshot_path.set(path)
            messagebox.showinfo("Ready", "Screenshot will be attached upon saving.")

    def _save_backtest_trade(self):
        data = self._get_form_data(self.bt_form_entries, True)
        if not data['symbol']: return
        
        trade_id = backtest_log.add_backtest_trade(data)
        if self.bt_screenshot_path.get():
            # Custom logic to use selected file from dialog
            screenshot_utils.update_trade(trade_id, {'screenshot_path': self.bt_screenshot_path.get()})
            
        self._refresh_backtest_table()
        messagebox.showinfo("Success", "Backtest trade saved.")

    def _clear_form(self, entries, screenshot_var):
        for k, v in entries.items():
            if k == "notes": v.delete("1.0", END)
            elif isinstance(v, ttk.Combobox): v.set("")
            else: v.delete(0, END)
        screenshot_var.set("")

    def _clear_specific_fields(self, keys):
        for k in keys:
            v = self.bt_form_entries.get(k)
            if not v: continue
            if isinstance(v, (ttk.Entry, ttk.Spinbox)):
                v.delete(0, END)
            elif isinstance(v, ttk.Combobox):
                v.set("")
            elif isinstance(v, tk.Text):
                v.delete("1.0", END)
            elif isinstance(v, tuple): # For signal_time (h, m)
                v[0].set("09")
                v[1].set("15")
            elif hasattr(v, 'entry'): # For DateEntry
                v.entry.delete(0, END)

    # --- TABLE LOGIC ---
    def _refresh_backtest_table(self):
        for item in self.bt_tree.get_children(): self.bt_tree.delete(item)
        session = self.bt_session_filter.get()
        df = backtest_log.get_backtest_trades(session if session else None)
        
        for _, row in df.iterrows():
            self.bt_tree.insert("", END, values=(
                row['id'], row['timestamp'], row['symbol'], row['direction'],
                row['entry_price'], row['exit_price'], row['pnl'], row['r_multiple'], row['backtest_session']
            ))
        # Refresh session lists
        sessions = backtest_log.get_all_backtest_sessions()
        self.bt_session_filter['values'] = sessions
        self.bt_analysis_session_selector['values'] = sessions
        self.bt_form_entries['backtest_session']['values'] = sessions
        self._update_status()

    def _delete_bt_trade(self):
        selected = self.bt_tree.selection()
        if not selected: return
        trade_id = self.bt_tree.item(selected[0])['values'][0]
        if messagebox.askyesno("Confirm", "Delete backtest record?"):
            backtest_log.delete_backtest_trade(trade_id)
            self._refresh_backtest_table()

    def _refresh_bt_analysis(self):
        session = self.bt_analysis_session_selector.get()
        if not session:
            return
        
        # Fetch advanced metrics for the specific backtest session
        adv = analytics.calculate_advanced_metrics(is_backtest=True, session=session)
        if adv:
            self.bt_session_metrics["Total Trades"].config(text=str(adv['total_trades']))
            self.bt_session_metrics["Win Rate %"].config(text=f"{adv['win_rate']}%")
            self.bt_session_metrics["Total PnL"].config(text=f"${adv['total_pnl']}")
            self.bt_session_metrics["Expectancy"].config(text=str(adv['expectancy']))
            self.bt_session_metrics["Profit Factor"].config(text=str(adv['profit_factor']))
            self.bt_session_metrics["Max Drawdown"].config(text=f"{adv['max_drawdown_pct']}%")
        else:
            for label in self.bt_session_metrics.values():
                label.config(text="--")

    # --- SCREENSHOT PREVIEW ---
    def _preview_selected(self, tree):
        selected = tree.selection()
        if not selected: return
        trade_id = tree.item(selected[0])['values'][0]
        path = screenshot_utils.get_screenshot_path(trade_id)
        
        if not path or not Path(path).exists():
            messagebox.showwarning("Missing", "No screenshot file found for this trade.")
            return
            
        self._open_image_window(path)

    def _open_image_window(self, path):
        top = tk.Toplevel()
        top.title("Screenshot Preview")
        
        img = Image.open(path)
        # Resize to fit screen roughly
        img.thumbnail((1000, 700))
        photo = ImageTk.PhotoImage(img)
        
        lbl = ttk.Label(top, image=photo)
        lbl.image = photo # Keep reference
        lbl.pack(padx=10, pady=10)
        
        ttk.Button(top, text="Close", command=top.destroy).pack(pady=5)

    # --- ANALYTICS LOGIC ---
    def _refresh_analytics(self):
        threading.Thread(target=self._update_analytics_worker).start()

    def _update_analytics_worker(self):
        self.status_var.set("Generating analytics charts...")
        
        # 1. Update Metrics
        bt_adv = analytics.calculate_advanced_metrics(True)
        
        def update_ui():
            # Update BT Cards
            if bt_adv:
                self.bt_metric_cards["Total Trades"].config(text=str(bt_adv['total_trades']))
                self.bt_metric_cards["Win Rate %"].config(text=f"{bt_adv['win_rate']}%")
                self.bt_metric_cards["Total PnL"].config(text=f"${bt_adv['total_pnl']}")
                self.bt_metric_cards["Expectancy"].config(text=str(bt_adv['expectancy']))
                self.bt_metric_cards["Profit Factor"].config(text=str(bt_adv['profit_factor']))
                self.bt_metric_cards["Max Drawdown"].config(text=f"{bt_adv['max_drawdown_pct']}%")

            # 2. Update Charts
            for widget in self.chart_container.winfo_children(): widget.destroy()
            
            # Equity Curve
            fig_equity = analytics.generate_equity_curve(True)
            if fig_equity:
                canvas = FigureCanvasTkAgg(fig_equity, master=self.chart_container)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=BOTH, expand=YES, pady=10)
            
            # Strategy Chart
            fig_strat = analytics.plot_performance_by_strategy(False)
            if fig_strat:
                canvas2 = FigureCanvasTkAgg(fig_strat, master=self.chart_container)
                canvas2.draw()
                canvas2.get_tk_widget().pack(fill=BOTH, expand=YES, pady=10)
            
            self.status_var.set("Analytics updated.")
            self._update_status()

        self.root.after(0, update_ui)

    # --- MISC ---
    def _handle_import(self, is_backtest):
        count = csv_handler.import_trades_from_csv(is_backtest=is_backtest)
        if count > 0:
            self._refresh_backtest_table()
            messagebox.showinfo("Imported", f"Successfully imported {count} trades.")

    def _load_initial_data(self):
        self._refresh_backtest_table()
        self._refresh_analytics()

    def _update_status(self):
        bt_count = len(self.bt_tree.get_children())
        self.status_var.set(f"{bt_count} backtest trades loaded")

if __name__ == "__main__":
    root = ttk.Window()
    app = TradingJournalApp(root)
    root.mainloop()