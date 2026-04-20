import streamlit as st
import pandas as pd
import backtest_log
import analytics
import trade_log
import os
from pathlib import Path
from datetime import datetime

# Set page config for wide layout (similar to your 1400x900 Tkinter setup)
st.set_page_config(layout="wide", page_title="Backtesting Journal Web")

# Compatibility for older Streamlit versions (st.dialog was introduced in 1.34.0)
if not hasattr(st, "dialog"):
    if hasattr(st, "experimental_dialog"):
        st.dialog = st.experimental_dialog
    else:
        st.error("This app requires Streamlit 1.34.0 or higher. Please run: `pip install --upgrade streamlit`")
        st.stop()

# Inject CSS to ensure both horizontal and vertical browser scrollbars are visible when needed
st.markdown("""
    <style>
    .main .block-container {
        overflow-x: auto !important;
        overflow-y: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

@st.dialog("📸 Screenshot View", width="large")
def show_screenshot_popup(img_path, sr_no):
    """Displays the screenshot in a modal popup."""
    # Inject CSS for resizability and JS for draggability
    st.markdown("""
        <style>
        /* Make the dialog container resizable */
        div[data-testid="stDialog"] > div:first-child {
            resize: both;
            overflow: auto;
            min-width: 400px;
            min-height: 300px;
            max-width: 95vw;
            max-height: 95vh;
        }
        /* Change cursor on the header to indicate it is draggable */
        div[data-testid="stDialog"] h1 {
            cursor: move;
            user-select: none;
        }
        </style>

        <script>
        // Dragging Logic
        var mainDoc = window.parent.document;
        var dialog = mainDoc.querySelector('div[data-testid="stDialog"] > div:first-child');
        var header = mainDoc.querySelector('div[data-testid="stDialog"] h1');

        if (dialog && header) {
            var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
            header.onmousedown = dragMouseDown;

            function dragMouseDown(e) {
                e = e || window.event;
                e.preventDefault();
                pos3 = e.clientX;
                pos4 = e.clientY;
                mainDoc.onmouseup = closeDragElement;
                mainDoc.onmousemove = elementDrag;
            }

            function elementDrag(e) {
                e = e || window.event;
                e.preventDefault();
                pos1 = pos3 - e.clientX;
                pos2 = pos4 - e.clientY;
                pos3 = e.clientX;
                pos4 = e.clientY;
                dialog.style.position = 'absolute';
                dialog.style.top = (dialog.offsetTop - pos2) + "px";
                dialog.style.left = (dialog.offsetLeft - pos1) + "px";
                dialog.style.margin = '0'; // Remove centering margins when dragging
            }

            function closeDragElement() {
                mainDoc.onmouseup = null;
                mainDoc.onmousemove = null;
            }
        }
        </script>
    """, unsafe_allow_html=True)

    if not img_path:
        st.warning("No screenshot attached to this trade.")
        return

    # Check if it's a URL (Cloud) or local path
    if img_path.startswith("http") or os.path.exists(img_path):
        st.image(img_path, width='stretch', caption=f"Screenshot for Trade Sr.No: {sr_no}")
    else:
        st.error(f"Screenshot file not found for Sr.No {sr_no}")

@st.dialog("📝 Edit Backtest Trade", width="large")
def show_edit_popup(trade_id):
    """Dialog to edit and update an existing trade."""
    trade = trade_log.get_trade_by_id(trade_id)
    if not trade:
        st.error("Trade not found.")
        return

    st.subheader(f"Editing Trade ID: {trade_id} ({trade.get('symbol')})")
    
    e_tab1, e_tab2, e_tab3, e_tab4 = st.tabs(["Basic Info", "TIDE Criteria", "WAVE Criteria", "Entry & Outcome"])
    
    updated_data = {}
    
    def get_idx(val, options):
        try: return options.index(val)
        except: return 0

    yn = ["YES", "NO"]
    stoch_opts = ["PCO", "NCO", "OSZ", "OBZ", "Flat"]
    di_opts = ["PCO", "NCO", "Converging", "Diverging"]

    with e_tab1:
        c1, c2 = st.columns(2)
        updated_data['strategy'] = c1.selectbox("Strategy", opts.get('strategies', []), index=get_idx(trade.get('strategy'), opts.get('strategies', [])))
        updated_data['symbol'] = c2.text_input("Symbol", value=trade.get('symbol'))
        updated_data['sector'] = c1.selectbox("Sector", opts.get('sectors', []), index=get_idx(trade.get('sector'), opts.get('sectors', [])))
        updated_data['trade_type'] = c2.selectbox("Trade Type", opts.get('trade_types', []), index=get_idx(trade.get('trade_type'), opts.get('trade_types', [])))
        updated_data['chart_pattern'] = c1.selectbox("Chart Pattern", opts.get('chart_patterns', []), index=get_idx(trade.get('chart_pattern'), opts.get('chart_patterns', [])))
        updated_data['significant_candle'] = c2.selectbox("Significant Candle", opts.get('significant_candles', []), index=get_idx(trade.get('significant_candle'), opts.get('significant_candles', [])))
        
        # Signal Date/Time
        try: sd = datetime.strptime(trade.get('signal_date', ''), "%Y-%m-%d") if trade.get('signal_date') else datetime.now()
        except: sd = datetime.now()
        updated_data['signal_date'] = str(c1.date_input("Signal Date", sd))
        
        try: stm = datetime.strptime(trade.get('signal_time', ''), "%H:%M:%S").time() if trade.get('signal_time') else datetime.now().time()
        except: stm = datetime.now().time()
        updated_data['signal_time'] = str(c2.time_input("Signal Time", stm))

    with e_tab2:
        c1, c2 = st.columns(2)
        updated_data['tide_timeframe'] = c1.selectbox("Tide Timeframe", opts.get('timeframes', []), index=get_idx(trade.get('tide_timeframe'), opts.get('timeframes', [])))
        updated_data['tide_upper_bb_challenge'] = c2.selectbox("BB Challenge (Tide)", yn, index=get_idx(trade.get('tide_upper_bb_challenge'), yn))
        updated_data['tide_macd_tick'] = c1.selectbox("MACD Tick (Tide)", yn, index=get_idx(trade.get('tide_macd_tick'), yn))
        updated_data['tide_macd_zeroline'] = c2.selectbox("MACD Zeroline (Tide)", yn, index=get_idx(trade.get('tide_macd_zeroline'), yn))
        updated_data['tide_stochastic'] = c1.selectbox("Stochastic (Tide)", stoch_opts, index=get_idx(trade.get('tide_stochastic'), stoch_opts))
        updated_data['tide_stochastic_val'] = c2.number_input("Stochastic Val (Tide)", value=float(trade.get('tide_stochastic_val') or 0))
        updated_data['tide_rsi_threshold'] = c1.selectbox("RSI Threshold (Tide)", yn, index=get_idx(trade.get('tide_rsi_threshold'), yn))
        updated_data['tide_rsi_val'] = c2.number_input("RSI Val (Tide)", value=float(trade.get('tide_rsi_val') or 0))
        updated_data['tide_price_above_50ema'] = st.selectbox("Price vs 50 EMA (Tide)", yn, index=get_idx(trade.get('tide_price_above_50ema'), yn))

    with e_tab3:
        c1, c2 = st.columns(2)
        updated_data['wave_timeframe'] = c1.selectbox("Wave Timeframe", opts.get('timeframes', []), index=get_idx(trade.get('wave_timeframe'), opts.get('timeframes', [])))
        updated_data['wave_bb_challenge'] = c2.selectbox("BB Challenge (Wave)", yn, index=get_idx(trade.get('wave_bb_challenge'), yn))
        updated_data['wave_macd_tick'] = c1.selectbox("MACD Tick (Wave)", yn, index=get_idx(trade.get('wave_macd_tick'), yn))
        updated_data['wave_macd_zeroline'] = c2.selectbox("MACD Zeroline (Wave)", yn, index=get_idx(trade.get('wave_macd_zeroline'), yn))
        updated_data['wave_stochastic'] = c1.selectbox("Stochastic (Wave)", stoch_opts, index=get_idx(trade.get('wave_stochastic'), stoch_opts))
        updated_data['wave_stochastic_val'] = c2.number_input("Stochastic Val (Wave)", value=float(trade.get('wave_stochastic_val') or 0))
        updated_data['wave_rsi_threshold'] = c1.selectbox("RSI Threshold (Wave)", yn, index=get_idx(trade.get('wave_rsi_threshold'), yn))
        updated_data['wave_rsi_val'] = c2.number_input("RSI Val (Wave)", value=float(trade.get('wave_rsi_val') or 0))
        updated_data['wave_trendline_break'] = c1.selectbox("Trendline Break", yn, index=get_idx(trade.get('wave_trendline_break'), yn))
        updated_data['wave_volume_above_avg'] = c2.selectbox("Volume Above Avg", yn, index=get_idx(trade.get('wave_volume_above_avg'), yn))
        updated_data['wave_shake_out'] = c1.selectbox("Shake Out", yn, index=get_idx(trade.get('wave_shake_out'), yn))
        updated_data['wave_two_higher_lows'] = c2.selectbox("2 Higher Lows/Lower Highs", yn, index=get_idx(trade.get('wave_two_higher_lows'), yn))
        updated_data['wave_ema_pco'] = c1.selectbox("EMA PCO/NCO", yn, index=get_idx(trade.get('wave_ema_pco'), yn))
        updated_data['wave_adx_ungali'] = c2.selectbox("ADX Ungali > 15", yn, index=get_idx(trade.get('wave_adx_ungali'), yn))
        updated_data['wave_adx_val'] = c1.number_input("ADX Value", value=float(trade.get('wave_adx_val') or 0))
        updated_data['wave_di_crossover'] = c2.selectbox("+DI / -DI", di_opts, index=get_idx(trade.get('wave_di_crossover'), di_opts))

    with e_tab4:
        c1, c2 = st.columns(2)
        updated_data['direction'] = c1.selectbox("Direction", ["LONG", "SHORT"], index=get_idx(trade.get('direction'), ["LONG", "SHORT"]))
        updated_data['capital_per_trade'] = c2.number_input("Capital (₹)", value=float(trade.get('capital_per_trade') or 0))
        updated_data['risk_amount'] = c1.number_input("Max Risk (₹)", value=float(trade.get('risk_amount') or 0))
        updated_data['entry_price'] = c2.number_input("Entry Price", value=float(trade.get('entry_price') or 0))
        updated_data['stop_loss'] = c1.number_input("Stop Loss (Points)", value=float(trade.get('stop_loss') or 0))
        updated_data['take_profit'] = c2.number_input("Target Price", value=float(trade.get('take_profit') or 0))
        updated_data['exit_price'] = c1.number_input("Exit Price", value=float(trade.get('exit_price') or 0))
        
        # Real-time calculated Read-only values in Edit Mode
        ep = updated_data['entry_price']
        sl = updated_data['stop_loss']
        tp = updated_data['take_profit']
        if ep > 0 and sl > 0:
            sl_p = ep - sl if updated_data['direction'] == "LONG" else ep + sl
            rr = round((abs(tp - ep) / sl), 2) if tp > 0 else 0
            st.info(f"💡 **Calculated SL Price:** {sl_p:.2f} | **Target RR:** {rr}")

        try: ed = datetime.strptime(trade.get('exit_date', ''), "%Y-%m-%d") if trade.get('exit_date') else datetime.now()
        except: ed = datetime.now()
        updated_data['exit_date'] = str(c2.date_input("Exit Date", ed))
        
        try: etm = datetime.strptime(trade.get('exit_time', ''), "%H:%M:%S").time() if trade.get('exit_time') else datetime.now().time()
        except: etm = datetime.now().time()
        updated_data['exit_time'] = str(c1.time_input("Exit Time", etm))
        
        out_opts = ["WIN", "LOSS", "BREAKEVEN", "PENDING"]
        updated_data['outcome'] = c2.selectbox("Outcome", out_opts, index=get_idx(trade.get('outcome'), out_opts))
        updated_data['duration_candles'] = c1.number_input("Duration (Candles)", value=int(trade.get('duration_candles') or 0))
        updated_data['exit_reason'] = st.text_area("Exit Reason", value=trade.get('exit_reason') or "")
        updated_data['notes'] = st.text_area("General Notes", value=trade.get('notes') or "")

    if st.button("🚀 Update Trade", type="primary", width='stretch'):
        trade_log.update_trade(trade_id, updated_data) # This button is inside a dialog, use_container_width is not directly applicable here.
        st.success("Trade updated successfully!")
        st.rerun()

@st.dialog("⚠️ Confirm Deletion")
def confirm_delete_dialog(trade_id, symbol):
    st.warning(f"Are you sure you want to permanently delete the trade for **{symbol}** (ID: {trade_id})?")
    st.info("This action cannot be undone.")
    if st.button("🔥 Yes, Delete Permanently", type="primary", width="stretch"):
        backtest_log.delete_backtest_trade(trade_id)
        st.success("Trade deleted.")
        st.rerun()

def clear_section_keys(prefix):
    """Clears all session state keys starting with a specific prefix."""
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith(prefix)]
    for k in keys_to_delete:
        del st.session_state[k]
    
    # Special case for 'last_session' to keep it persistent if desired, 
    # otherwise delete it too.
    st.rerun()

# Initialize Database Connection
trade_log.init_db()

# Initialize Session State for Selection Tracking
if 'last_bt_sel' not in st.session_state:
    st.session_state.last_bt_sel = None

# Fetch options from Excel once for all modules that need it
opts = backtest_log.get_excel_source_options()

st.title("📈 Pro Backtesting Journal")

# Sidebar for navigation
menu = st.sidebar.selectbox("Module", ["Trade Entry", "Trade History", "Analytics"])
db_type = trade_log.get_active_db_type()
if db_type == "POSTGRES" and trade_log.DATABASE_URL:
    # Extract host from URL to show in sidebar
    host = trade_log.DATABASE_URL.split('@')[-1].split(':')[0]
    st.sidebar.success(f"🚀 {db_type} | {host}")
else:
    st.sidebar.info(f"🏠 {db_type} ({trade_log.SUPABASE_MODE})")

if menu == "Trade Entry":
    st.header("New Backtest Entry")
    
    # (1) Horizontal Header Section
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        strategy = st.selectbox("Strategy", opts.get('strategies', []))
        symbol = st.text_input("Symbol")
    with col2:
        sector = st.selectbox("Sector", opts.get('sectors', []))
        trade_type = st.selectbox("Trade Type", opts.get('trade_types', []))
    with col3:
        pattern = st.selectbox("Chart Pattern", opts.get('chart_patterns', []))
        candle = st.selectbox("Significant Candle", opts.get('significant_candles', []))
    with col4:
        signal_date = st.date_input("Signal Date", datetime.now(), format="DD-MM-YYYY")
        signal_time = st.time_input("Signal Time", datetime.now())

    # (1.5) Top Level Action Buttons
    top_btn1, top_btn2, _ = st.columns([1, 1, 4])
    with top_btn1:
        save_main = st.button("💾 Save Full Trade", type="primary", width='stretch')
    with top_btn2: # This button is inside a column, use_container_width is not directly applicable here.
        if st.button("🧹 Clear All Fields", width='stretch'):
            st.session_state.clear()
            st.rerun()

    st.divider()

    # (2) 3-Column Adjustable Layout (TIDE / WAVE / Entry)
    left_col, mid_col, right_col = st.columns([1, 1, 0.8]) # Adjust column widths for better layout

    is_bull = (strategy == "Bullish Momentum" and trade_type == "Bullish Momentum")
    is_bear = (strategy == "Bearish Momentum" and trade_type == "Bearish Momentum")

    # Define TIDE Criteria Fields
    tide_fields = []
    if is_bull:
        tide_fields = [
            ("Timeframe", "tide_timeframe", opts.get('timeframes', [])),
            ("Upper BB Challenge", "tide_upper_bb_challenge", ["YES", "NO"]),
            ("MACD Uptick", "tide_macd_tick", ["YES", "NO"]),
            ("MACD Above Zeroline", "tide_macd_zeroline", ["YES", "NO"]),
            ("Stochastic", "tide_stochastic", ["PCO", "NCO", "OSZ", "OBZ", "Flat"]),
            ("Stochastic Value", "tide_stochastic_val", "number_input"),
            ("RSI > 60", "tide_rsi_threshold", ["YES", "NO"]),
            ("RSI Value", "tide_rsi_val", "number_input"),
            ("Price Above 50 EMA", "tide_price_above_50ema", ["YES", "NO"])
        ]
    elif is_bear:
        tide_fields = [
            ("Timeframe", "tide_timeframe", opts.get('timeframes', [])),
            ("Lower BB Challenge", "tide_upper_bb_challenge", ["YES", "NO"]),
            ("MACD Downtick", "tide_macd_tick", ["YES", "NO"]),
            ("MACD Below Zeroline", "tide_macd_zeroline", ["YES", "NO"]),
            ("Stochastic", "tide_stochastic", ["PCO", "NCO", "OSZ", "OBZ", "Flat"]),
            ("Stochastic Value", "tide_stochastic_val", "number_input"),
            ("RSI < 40", "tide_rsi_threshold", ["YES", "NO"]),
            ("RSI Value", "tide_rsi_val", "number_input"),
            ("Price Below 50 EMA", "tide_price_above_50ema", ["YES", "NO"])
        ]

    # Define WAVE Criteria Fields
    wave_fields = []
    if is_bull:
        wave_fields = [
            ("Timeframe", "wave_timeframe", opts.get('timeframes', [])),
            ("Upper BB Challenge", "wave_bb_challenge", ["YES", "NO"]),
            ("MACD Uptick", "wave_macd_tick", ["YES", "NO"]),
            ("MACD Above Zeroline", "wave_macd_zeroline", ["YES", "NO"]),
            ("Stochastic", "wave_stochastic", ["PCO", "NCO", "OSZ", "OBZ", "Flat"]),
            ("Stochastic Value", "wave_stochastic_val", "number_input"),
            ("RSI > 60", "wave_rsi_threshold", ["YES", "NO"]),
            ("RSI Value", "wave_rsi_val", "number_input"),
            ("Price Above 50 EMA", "wave_price_above_50ema", ["YES", "NO"]),
            ("Trendline Breakout", "wave_trendline_break", ["YES", "NO"]),
            ("Breakout Candle Volumes above Average", "wave_volume_above_avg", ["YES", "NO"]),
            ("Shake Out Before Breakout", "wave_shake_out", ["YES", "NO"]),
            ("At least Two Higher Low Prior to BB Challenge on line chart", "wave_two_higher_lows", ["YES", "NO"]),
            ("5 EMA PCO 13 or 26 EMA prior to last three period", "wave_ema_pco", ["YES", "NO"]),
            ("ADX Ungali > 15", "wave_adx_ungali", ["YES", "NO"]),
            ("ADX Value", "wave_adx_val", "number_input"),
            ("+DI or -DI", "wave_di_crossover", ["PCO", "NCO", "Converging", "Diverging"]),
            ("No Immediate Major Resistance", "wave_resistance", ["YES", "NO"])
        ]
    elif is_bear:
        wave_fields = [
            ("Timeframe", "wave_timeframe", opts.get('timeframes', [])),
            ("Lower BB Challenge", "wave_bb_challenge", ["YES", "NO"]),
            ("MACD Downtick", "wave_macd_tick", ["YES", "NO"]),
            ("MACD Below Zeroline", "wave_macd_zeroline", ["YES", "NO"]),
            ("Stochastic", "wave_stochastic", ["PCO", "NCO", "OSZ", "OBZ", "Flat"]),
            ("Stochastic Value", "wave_stochastic_val", "number_input"),
            ("RSI < 40", "wave_rsi_threshold", ["YES", "NO"]),
            ("RSI Value", "wave_rsi_val", "number_input"),
            ("Price Below 50 EMA", "wave_price_above_50ema", ["YES", "NO"]),
            ("Trendline Breakdown", "wave_trendline_break", ["YES", "NO"]),
            ("Breakout Candle Volumes above Average", "wave_volume_above_avg", ["YES", "NO"]),
            ("Shake Out Before Breakdown", "wave_shake_out", ["YES", "NO"]),
            ("At least Two Lower High Prior to BB Challenge on line chart", "wave_two_higher_lows", ["YES", "NO"]),
            ("5 EMA NCO 13 or 26 EMA prior to last three period", "wave_ema_pco", ["YES", "NO"]),
            ("ADX Ungali > 15", "wave_adx_ungali", ["YES", "NO"]),
            ("ADX Value", "wave_adx_val", "number_input"),
            ("+DI or -DI", "wave_di_crossover", ["PCO", "NCO", "Converging", "Diverging"]),
            ("No Immediate Major Resistance", "wave_resistance", ["YES", "NO"])
        ]

    tide_data = {}
    wave_data = {}

    with left_col:
        st.subheader("TIDE Criteria")
        for label, key, f_type in tide_fields:
            if isinstance(f_type, list):
                tide_data[key] = st.selectbox(label, f_type, key=f"tide_{key}")
            elif f_type == "number_input":
                tide_data[key] = st.number_input(label, key=f"tide_{key}", value=0.0, format="%.2f")
            else: # Default to text input for now if other types are introduced
                tide_data[key] = st.text_input(label, key=f"tide_{key}")

        st.markdown("---")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            save_tide = st.button("Save TIDE", key="btn_save_tide", width='stretch')
        with t_col2:
            if st.button("Clear TIDE", key="btn_clear_tide", width='stretch'):
                clear_section_keys("tide_")


    with mid_col:
        st.subheader("WAVE Criteria")
        for label, key, f_type in wave_fields:
            if isinstance(f_type, list):
                wave_data[key] = st.selectbox(label, f_type, key=f"wave_{key}")
            elif f_type == "number_input":
                wave_data[key] = st.number_input(label, key=f"wave_{key}", value=0.0, format="%.2f")
            else: # Default to text input for now if other types are introduced
                wave_data[key] = st.text_input(label, key=f"wave_{key}")

        st.markdown("---")
        w_col1, w_col2 = st.columns(2)
        with w_col1:
            save_wave = st.button("Save WAVE", key="btn_save_wave", width='stretch')
        with w_col2:
            if st.button("Clear WAVE", key="btn_clear_wave", width='stretch'):
                clear_section_keys("wave_")

    with right_col:
        st.subheader("Entry Details")
        
        with st.expander("💼 Planning & Session", expanded=True):
            capital = st.number_input("Capital Per Trade (₹)", value=100000.0, step=1000.0)
            direction = st.selectbox("Direction", ["LONG", "SHORT"])
            risk_amt = st.number_input("Max Risk (₹)", value=1000.0, step=100.0)

        with st.expander("📊 Entry Logic", expanded=True):
            entry_p = st.number_input("Entry Price", format="%.2f", step=0.05)
            stop_l = st.number_input("Stop Loss (Points)", format="%.2f", step=0.05)
            target = st.number_input("Target Price", format="%.2f", step=0.05)
            
            # Real-time calculated Read-only values (Visual Aids)
            if entry_p > 0 and stop_l > 0:
                sl_price = entry_p - stop_l if direction == "LONG" else entry_p + stop_l
                t_qty = int(risk_amt / stop_l)
                cap_req = t_qty * entry_p
                rr_ratio = round((abs(target - entry_p) / stop_l), 2) if target > 0 else 0
                
                st.caption(f"**Calculated SL Price:** {sl_price:.2f}")
                st.caption(f"**Tradable Quantity:** {t_qty}")
                st.caption(f"**Capital Required:** ₹{cap_req:,.2f}")
                st.caption(f"**Planned RR:** {rr_ratio}")
            else:
                st.caption("Fill Entry and Stop Loss to see calculations")

        with st.expander("🏁 Trade Outcome", expanded=False):
            exit_p = st.number_input("Exit Price", format="%.2f", step=0.05)
            exit_date = st.date_input("Exit Date", datetime.now(), format="DD-MM-YYYY")
            exit_time = st.time_input("Exit Time", datetime.now())
            
            outcome = st.selectbox("Outcome of Trade", ["WIN", "LOSS", "BREAKEVEN", "PENDING"])
            duration = st.number_input("Trade Duration (Candles)", min_value=0, step=1)
            exit_reason = st.text_area("Reason for Exit", height=100)

        uploaded_file = st.file_uploader("📸 Attach Screenshot", type=['png', 'jpg', 'jpeg'], key="entry_screenshot")
        
        if st.button("Save Full Trade", type="primary", width='stretch') or save_tide or save_wave:
            screenshot_path = None
            if uploaded_file is not None:
                # Ensure screenshots directory exists
                local_folder = "screenshots"
                os.makedirs(local_folder, exist_ok=True)
                
                file_ext = Path(uploaded_file.name).suffix
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_symbol = "".join(c for c in symbol if c.isalnum() or c in ('_', '-')) or "UNKNOWN"
                filename = f"BT_{safe_symbol}_{ts}{file_ext}"
                local_path = os.path.join(local_folder, filename)
                
                # Save locally first
                with open(local_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # If Cloud Mode, upload and get URL
                if not trade_log.FORCE_LOCAL:
                    screenshot_path = trade_log.upload_to_supabase(local_path, filename)
                else:
                    screenshot_path = local_path

            full_data = {
                "strategy": strategy, "symbol": symbol, "sector": sector,
                "trade_type": trade_type, "chart_pattern": pattern,
                "significant_candle": candle, "signal_date": str(signal_date),
                "signal_time": str(signal_time), "entry_price": entry_p,
                "stop_loss": stop_l, "exit_price": exit_p, "risk_amount": risk_amt, # Ensure all are passed
                "direction": direction, "screenshot_path": screenshot_path,
                "capital_per_trade": capital, "take_profit": target, "exit_date": str(exit_date),
                "exit_time": str(exit_time), "outcome": outcome, "duration_candles": duration,
                "exit_reason": exit_reason,
                **tide_data, **wave_data
            }
            new_id = backtest_log.add_backtest_trade(full_data)
            if new_id != -1:
                st.balloons()
                st.success(f"Trade for {symbol} saved with ID: {new_id}")
                # Clear form fields after successful save (Streamlit reruns, so this is implicit for most)
                # For text_input, selectbox, number_input, changing state will reset them on rerun.
            else:
                st.error("Failed to save trade. Check logs.")

elif menu == "Trade History":
    st.header("Trade History")
    
    df = backtest_log.get_backtest_trades(None)
    
    # (3) Sidebar/Expandable Filters
    if not df.empty:
        with st.expander("🔍 Filter History Table", expanded=False):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            
            with f_col1:
                f_strat = st.multiselect("Strategy", sorted(df['strategy'].unique()))
                f_sym = st.multiselect("Stock (Symbol)", sorted(df['symbol'].unique()))
            with f_col2:
                f_sector = st.multiselect("Sector", sorted(df['sector'].unique().astype(str)))
                f_ttype = st.multiselect("Trade Type", sorted(df['trade_type'].unique().astype(str)))
            with f_col3:
                f_pattern = st.multiselect("Chart Pattern", sorted(df['chart_pattern'].unique().astype(str)))
                f_candle = st.multiselect("Significant Candle", sorted(df['significant_candle'].unique().astype(str)))
            with f_col4:
                # Convert signal_date strings to datetime for filtering if possible
                unique_dates = sorted(df['signal_date'].unique())
                f_dates = st.multiselect("Signal Date", unique_dates)
                f_times = st.multiselect("Signal Time", sorted(df['signal_time'].unique().astype(str)))

            # Apply Filters
            if f_strat: df = df[df['strategy'].isin(f_strat)]
            if f_sym: df = df[df['symbol'].isin(f_sym)]
            if f_sector: df = df[df['sector'].isin(f_sector)]
            if f_ttype: df = df[df['trade_type'].isin(f_ttype)]
            if f_pattern: df = df[df['chart_pattern'].isin(f_pattern)]
            if f_candle: df = df[df['significant_candle'].isin(f_candle)]
            if f_dates: df = df[df['signal_date'].isin(f_dates)]
            if f_times: df = df[df['signal_time'].isin(f_times)]

    if not df.empty:
        # 1. Add Sr.No Column
        df = df.reset_index(drop=True)
        df.insert(0, 'Sr.No', range(1, len(df) + 1))

        # 2. Define Section Groupings and Label Mapping
        sections = {
            "Basic Info": {
                "strategy": "Strategy", "symbol": "Symbol", "sector": "Sector", 
                "trade_type": "Trade Type", "chart_pattern": "Chart Pattern", 
                "significant_candle": "Significant Candle", "signal_date": "Signal Date", 
                "signal_time": "Signal Time"
            },
            "TIDE Criteria": {
                "tide_timeframe": "Timeframe", "tide_upper_bb_challenge": "Upper/Lower BB Challenge",
                "tide_macd_tick": "MACD Up/Downtick", "tide_macd_zeroline": "MACD Above/Below Zeroline",
                "tide_stochastic": "Stochastic", "tide_stochastic_val": "Stochastic Val",
                "tide_rsi_threshold": "RSI > 60 / < 40", "tide_rsi_val": "RSI Value",
                "tide_price_above_50ema": "Price Above/Below 50 EMA"
            },
            "WAVE Criteria": {
                "wave_timeframe": "Timeframe", "wave_bb_challenge": "Upper/Lower BB Challenge",
                "wave_macd_tick": "MACD Up/Downtick", "wave_macd_zeroline": "MACD Above/Below Zeroline",
                "wave_stochastic": "Stochastic", "wave_stochastic_val": "Stochastic Val",
                "wave_rsi_threshold": "RSI > 60 / < 40", "wave_rsi_val": "RSI Value",
                "wave_trendline_break": "Trendline Breakout/Breakdown",
                "wave_volume_above_avg": "Breakout Candle Volumes above Average",
                "wave_shake_out": "Shake Out Before Breakout/Breakdown",
                "wave_two_higher_lows": "At least Two Higher Low Prior to BB Challenge on line chart",
                "wave_ema_pco": "5 EMA PCO/NCO 13 or 26 EMA prior to last three period",
                "wave_price_above_50ema": "Price Above/Below 50 EMA",
                "wave_adx_ungali": "ADX Ungali > 15", "wave_adx_val": "ADX Val",
                "wave_di_crossover": "+DI / -DI"
            },
            "Entry Details": {
                "direction": "Direction", "capital_per_trade": "Capital Per Trade",
                "risk_amount": "Max Risk", "entry_price": "Entry Price",
                "stop_loss": "Stop Loss", "stop_loss_price": "SL Price",
                "take_profit": "Target Price", "position_size": "Tradable Quantity",
                "max_qty_capital": "Max Tradable Qty as per Capital",
                "max_profit": "Max Profit", "capital_required": "Capital Require",
                "exit_price": "Exit Price", "exit_date": "Exit Date",
                "exit_time": "Exit Time", "pnl": "P&L", "pct_return": "% Return or Loss",
                "r_multiple": "RR", "outcome": "Outcome of Trade", 
                "duration_candles": "Trade Duration in Candle", "exit_reason": "Reason For Exit the Trade"
            }
        }

        # 3. Build MultiIndex Columns
        mi_tuples = []
        # Keep Sr.No at the top level
        mi_tuples.append(("", "Sr.No"))
        
        # Map existing columns to sections
        cols_to_keep = ['Sr.No']
        for sec_name, col_map in sections.items():
            for db_col, label in col_map.items():
                if db_col in df.columns:
                    mi_tuples.append((sec_name, label))
                    cols_to_keep.append(db_col)
        
        # 4. Filter and Rename
        display_df = df[cols_to_keep].copy()
        display_df.columns = pd.MultiIndex.from_tuples(mi_tuples)

        # Build the format dictionary for numerical columns
        format_dict = {}
        for sec_name, col_map in sections.items():
            for db_col, label in col_map.items():
                # Format Date Columns to DD-MM-YYYY
                if db_col in df.columns and 'date' in db_col:
                    try:
                        display_df[(sec_name, label)] = pd.to_datetime(display_df[(sec_name, label)]).dt.strftime('%d-%m-%Y')
                    except Exception:
                        pass

                # Heuristic to identify numerical columns that need formatting
                # Exclude integer columns that don't need decimal formatting
                if db_col in df.columns and df[db_col].dtype in ['float64', 'int64'] and \
                   db_col not in ['max_qty_capital', 'duration_candles', 'Sr.No', 'id']:
                    # Apply currency format for specific financial columns, general .2f for others
                    if 'capital' in db_col or 'risk_amount' == db_col or 'pnl' == db_col or 'max_profit' == db_col:
                        format_dict[(sec_name, label)] = "₹{:,.2f}"
                    elif 'pct_return' == db_col:
                        format_dict[(sec_name, label)] = "{:,.2f}%"
                    else:
                        format_dict[(sec_name, label)] = "{:,.2f}"

        # 5. Render Table with Selection Enabled
        # height=600 utilizes more screen space while allowing scrollbars
        event = st.dataframe(
            display_df.style.format(format_dict).set_properties(**{'text-align': 'center'}),
            width='stretch', 
            hide_index=True,
            on_select="rerun",
            height=600,
            selection_mode="single-row"
        )

        # (5) Edit and Delete Buttons
        st.markdown("### Trade Actions")
        btn_col1, btn_col2, btn_col3 = st.columns([1.5, 1.5, 4])
        
        show_edit = False
        current_selection = event.selection.rows[0] if event.selection.rows else None

        with btn_col1:
            if st.button("📝 Edit Selected Trade", width='stretch', type="primary"):
                if current_selection is not None:
                    show_edit = True
                else:
                    st.warning("Please select a row in the table first.")

        # Handle Dialog Logic: Priority to Edit, otherwise Screenshot on new selection
        if show_edit:
            show_edit_popup(int(df.iloc[current_selection]['id']))
        elif current_selection is not None and current_selection != st.session_state.get('last_bt_sel'):
            selected_row = df.iloc[current_selection]
            show_screenshot_popup(selected_row['screenshot_path'], selected_row['Sr.No'])
        
        # Update session state to track the last selection
        st.session_state.last_bt_sel = current_selection

        with btn_col2:
            sel_sr_no = st.number_input("Enter Sr.No for Action", min_value=0, max_value=len(df), step=1)
            if st.button("Delete Trade", type="secondary", width='stretch'):
                if sel_sr_no > 0:
                    # Map Sr.No back to the actual database ID using the original dataframe
                    selected_trade = df.iloc[sel_sr_no - 1]
                    confirm_delete_dialog(int(selected_trade['id']), selected_trade['symbol'])
    else:
        st.info("No trades found for this session.")

elif menu == "Analytics":
    st.header("Performance Dashboard")
    
    # (1) Removed Analyze Session Selectbox.
    # (2) Analyze by Stock, Trade Type, Chart Pattern, Sector, Signal Date, Signal Time.
    df = backtest_log.get_backtest_trades(None)
    
    if not df.empty:
        with st.expander("🔍 Filter Dashboard Data", expanded=True):
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                f_sym = st.multiselect("Stock (Symbol)", sorted(df['symbol'].unique()))
                f_sector = st.multiselect("Sector", sorted(df['sector'].unique().astype(str)))
            with f_col2:
                f_ttype = st.multiselect("Trade Type", sorted(df['trade_type'].unique().astype(str)))
                f_pattern = st.multiselect("Chart Pattern", sorted(df['chart_pattern'].unique().astype(str)))
            with f_col3:
                f_dates = st.multiselect("Signal Date", sorted(df['signal_date'].unique()))
                f_times = st.multiselect("Signal Time", sorted(df['signal_time'].unique().astype(str)))

            # Apply Analysis Filters
            if f_sym: df = df[df['symbol'].isin(f_sym)]
            if f_sector: df = df[df['sector'].isin(f_sector)]
            if f_ttype: df = df[df['trade_type'].isin(f_ttype)]
            if f_pattern: df = df[df['chart_pattern'].isin(f_pattern)]
            if f_dates: df = df[df['signal_date'].isin(f_dates)]
            if f_times: df = df[df['signal_time'].isin(f_times)]

    # Header Actions
    act_col1, act_col2 = st.columns([1, 5])
    with act_col1:
        if st.button("🔄 Refresh", type="primary"):
            st.rerun()

    adv = analytics.calculate_advanced_metrics(is_backtest=True, df=df)
    
    if adv:
        # (3) Include the pdf Export for Analysis.
        with act_col2:
            filter_str = f"Stock: {f_sym or 'All'}, Type: {f_ttype or 'All'}, Sector: {f_sector or 'All'}"
            pdf_data = analytics.generate_pdf_report(adv, filter_str)
            st.download_button(
                label="📄 Export Analysis to PDF",
                data=pdf_data,
                file_name=f"trade_analysis_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

        st.subheader("Performance Metrics")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Total Trades", adv['total_trades'])
        m_col2.metric("Win Rate %", f"{adv['win_rate']}%")
        m_col3.metric("Total PnL", f"₹{adv['total_pnl']:,}")
        m_col4.metric("Profit Factor", adv['profit_factor'])

        m_col5, m_col6, m_col7, m_col8 = st.columns(4)
        m_col5.metric("Avg Win", f"₹{adv['avg_win']:,}")
        m_col6.metric("Avg Loss", f"₹{adv['avg_loss']:,}")
        m_col7.metric("Expectancy", f"₹{adv['expectancy']:,}")
        m_col8.metric("Sharpe Ratio", adv['sharpe_ratio'])

        m_col9, m_col10, m_col11, m_col12 = st.columns(4)
        m_col9.metric("Max Drawdown %", f"{adv['max_drawdown_pct']}%")
        m_col10.metric("Max Win Streak", adv['win_streak'])
        m_col11.metric("Max Loss Streak", adv['loss_streak'])
        m_col12.metric("Best Trade", f"₹{adv['best_trade']:,}")

        st.divider()

        st.subheader("Equity Curve")
        fig = analytics.generate_equity_curve(is_backtest=True, df=df)
        if fig:
            st.pyplot(fig)
        else:
            st.info("Not enough data to generate Equity Curve.")
        
        st.divider()

        # Strategy Analysis
        st.subheader("Strategy Performance")
        fig_strat = analytics.plot_performance_by_strategy(is_backtest=True, df=df)
        if fig_strat:
            st.pyplot(fig_strat)
        else:
            st.info("Not enough data to generate Strategy Performance chart.")

        # Monthly Returns (Optional, can be a table or another plot)
        if not adv['monthly_returns'].empty:
            st.subheader("Monthly Returns")
            st.dataframe(adv['monthly_returns'].to_frame(name='PnL').style.format("₹{:,.2f}"), width='stretch')

    else:
        st.info("No trade data available to generate analytics for the selected session.")