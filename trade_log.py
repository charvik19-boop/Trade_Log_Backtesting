import sqlite3
try:
    import psycopg2
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

HAS_ORACLE = False # Logic for Oracle remains local-only for now

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Union
import os
from pathlib import Path
from dotenv import load_dotenv

# Try to import supabase for cloud storage
try:
    from supabase import create_client, Client
except ImportError:
    Client = None

# Database Configuration
BASE_DIR = Path(__file__).resolve().parent
if (BASE_DIR / ".env").exists():
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

LOCAL_DB_PATH = os.path.join(BASE_DIR, "trading_journal.db")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Force Local Mode
FORCE_LOCAL = os.getenv("FORCE_LOCAL", "True").lower() == "true"
SUPABASE_MODE = os.getenv("SUPABASE_MODE", "LOCAL")
DATABASE_URL = os.getenv("DATABASE_URL")
ORACLE_DSN = os.getenv("ORACLE_DSN")

def get_supabase_client() -> Optional[Client]:
    if SUPABASE_URL and SUPABASE_KEY and Client:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

def get_active_db_type():
    """Helper to determine which database is currently active."""
    if FORCE_LOCAL:
        return "SQLITE"
    if ORACLE_DSN:
        return "ORACLE"
    if DATABASE_URL:
        return "POSTGRES"
    return "SQLITE"

def get_connection():
    """
    Returns a database connection.
    Supports:
    - Oracle Cloud (via ORACLE_DSN)
    - PostgreSQL (via DATABASE_URL: GCP Cloud SQL, Supabase, Neon)
    - Local SQLite (Fallback)
    """
    db_type = get_active_db_type()
    if db_type == "POSTGRES" and HAS_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(LOCAL_DB_PATH)

def init_db():
    """
    Initializes the SQLite database and creates the trades table if it doesn't exist.
    """
    db_type = get_active_db_type()
    
    # Dynamic syntax based on database engine
    if db_type == "POSTGRES":
        id_type = "SERIAL PRIMARY KEY"
        created_at_def = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    else:
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        created_at_def = "TEXT DEFAULT CURRENT_TIMESTAMP"

    text_type = "TEXT"
    real_type = "REAL"
    int_type = "INTEGER"
    if_not_exists = "IF NOT EXISTS"
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            sql = f"""
                CREATE TABLE {if_not_exists} trades (
                    id {id_type},
                    timestamp {text_type} NOT NULL,
                    is_backtest {int_type} DEFAULT 0,
                    symbol {text_type} NOT NULL,
                    direction {text_type} NOT NULL,
                    entry_price {real_type} NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    exit_price REAL,
                    exit_reason TEXT,
                    position_size REAL,
                    risk_amount REAL,
                    pnl REAL,
                    r_multiple REAL,
                    capital_per_trade REAL,
                    tide_timeframe TEXT,
                    wave_timeframe TEXT,
                    stop_loss_price REAL,
                    max_qty_capital INTEGER,
                    max_profit REAL,
                    capital_required REAL,
                    exit_date TEXT,
                    exit_time TEXT,
                    pct_return REAL,
                    outcome TEXT,
                    duration_candles INTEGER,
                    strategy TEXT,
                    timeframe TEXT,
                    market_context TEXT,
                    backtest_session TEXT,
                    notes TEXT,
                    screenshot_path TEXT,
                    sector TEXT,
                    trade_type TEXT,
                    chart_pattern TEXT,
                    significant_candle TEXT,
                    signal_date TEXT,
                    signal_time TEXT,
                    tide_upper_bb_challenge TEXT,
                    tide_macd_tick TEXT,
                    tide_macd_zeroline TEXT,
                    tide_stochastic TEXT,
                    tide_stochastic_val REAL,
                    tide_rsi_threshold TEXT,
                    tide_rsi_val REAL,
                    tide_price_above_50ema TEXT,
                    wave_macd_tick TEXT,
                    wave_macd_zeroline TEXT,
                    wave_stochastic TEXT,
                    wave_stochastic_val REAL,
                    wave_rsi_threshold TEXT,
                    wave_rsi_val REAL,
                    wave_bb_challenge TEXT,
                    wave_trendline_break TEXT,
                    wave_volume_above_avg TEXT,
                    wave_shake_out TEXT,
                    wave_two_higher_lows TEXT,
                    wave_ema_pco TEXT,
                    wave_price_above_50ema TEXT,
                    wave_adx_ungali TEXT,
                    wave_adx_val REAL,
                    wave_di_crossover TEXT,
                    wave_resistance TEXT,
                    wave_itm_atm_ce_tmg TEXT,
                    wave_atm_pe_tmj TEXT,
                    wave_future_buildup TEXT,
                    created_at {created_at_def}
                )
            """
            
            cursor.execute(sql)

            # --- Migration Logic ---
            if db_type != "SQLITE": return # Skip PRAGMA checks for cloud DBs
            
            cursor.execute("PRAGMA table_info(trades)")
            existing_cols = [row[1] for row in cursor.fetchall()]
            
            new_cols = [
                ("sector", text_type),
                ("trade_type", text_type),
                ("chart_pattern", text_type),
                ("significant_candle", text_type),
                ("signal_date", text_type),
                ("signal_time", text_type),
                ("capital_per_trade", real_type),
                ("tide_timeframe", text_type),
                ("wave_timeframe", text_type),
                ("stop_loss_price", real_type),
                ("max_qty_capital", int_type),
                ("max_profit", real_type),
                ("capital_required", real_type),
                ("exit_date", text_type),
                ("exit_time", text_type),
                ("pct_return", real_type),
                ("outcome", text_type),
                ("duration_candles", int_type),
                ("tide_upper_bb_challenge", text_type),
                ("tide_macd_tick", text_type),
                ("tide_macd_zeroline", text_type),
                ("tide_stochastic", text_type),
                ("tide_stochastic_val", real_type),
                ("tide_rsi_threshold", text_type),
                ("tide_rsi_val", real_type),
                ("tide_price_above_50ema", text_type),
                ("wave_macd_tick", text_type),
                ("wave_macd_zeroline", text_type),
                ("wave_stochastic", text_type),
                ("wave_stochastic_val", real_type),
                ("wave_rsi_threshold", text_type),
                ("wave_rsi_val", real_type),
                ("wave_bb_challenge", text_type),
                ("wave_trendline_break", text_type),
                ("wave_volume_above_avg", text_type),
                ("wave_shake_out", text_type),
                ("wave_two_higher_lows", text_type),
                ("wave_ema_pco", text_type),
                ("wave_price_above_50ema", text_type),
                ("wave_adx_ungali", text_type),
                ("wave_adx_val", real_type),
                ("wave_di_crossover", text_type),
                ("wave_resistance", text_type),
                ("wave_itm_atm_ce_tmg", text_type),
                ("wave_atm_pe_tmj", text_type),
                ("wave_future_buildup", text_type)
            ]
            
            for col_name, col_type in new_cols:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
            
            # Ensure is_backtest is never NULL for existing records
            # This fixes the issue where trades are visible but 'not found' during delete/edit
            cursor.execute("UPDATE trades SET is_backtest = 1 WHERE is_backtest IS NULL")
            
            conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")

def calculate_pnl_metrics(trade_data: Dict) -> Dict:
    """
    Calculates PnL and R-Multiple based on entry/exit logic.
    """
    entry = trade_data.get('entry_price', 0.0)
    sl_points = trade_data.get('stop_loss', 0.0)
    target = trade_data.get('take_profit', 0.0)
    exit_p = trade_data.get('exit_price', 0.0)
    risk_amt = trade_data.get('risk_amount', 0.0)
    capital = trade_data.get('capital_per_trade', 0.0)
    direction = trade_data.get('direction', '').upper()

    # 1. SL Price and Max Qty Calculation
    if entry > 0:
        trade_data['max_qty_capital'] = int(capital / entry) if capital > 0 else 0
        if sl_points > 0:
            trade_data['stop_loss_price'] = entry - sl_points if direction == "LONG" else entry + sl_points
            # Tradable Quantity based on Max Risk
            trade_data['position_size'] = round(risk_amt / sl_points, 2) if sl_points > 0 else 0.0
            trade_data['capital_required'] = round(trade_data['position_size'] * entry, 2)

    # 2. Planning Metrics (RR and Max Profit)
    if entry > 0 and sl_points > 0 and target > 0:
        reward_points = abs(target - entry)
        trade_data['r_multiple'] = round(reward_points / sl_points, 2)
        if trade_data.get('position_size'):
            trade_data['max_profit'] = round(trade_data['position_size'] * reward_points, 2)

    # 3. Execution Metrics (PnL and % Return)
    if entry > 0 and sl_points > 0 and exit_p > 0:
        risk_per_unit = sl_points
        
        if direction == "LONG":
            actual_r = (exit_p - entry) / risk_per_unit
        else: # SHORT
            actual_r = (entry - exit_p) / risk_per_unit
        
        pnl = actual_r * risk_amt
        
        trade_data['pnl'] = round(pnl, 2)
        trade_data['pct_return'] = round((pnl / capital) * 100, 2) if capital > 0 else 0.0
    
    return trade_data

def get_trade_by_id(trade_id: int) -> Optional[Dict]:
    """
    Retrieves a single trade by its ID.
    """
    db_type = get_active_db_type()
    if db_type == "ORACLE":
        placeholder = ":1"
    elif db_type == "POSTGRES":
        placeholder = "%s"
    else:
        placeholder = "?"
    
    try:
        conn = get_connection() # Open connection
        if db_type == "SQLITE":
            conn.row_factory = sqlite3.Row
        
        with conn: # Manage transaction
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM trades WHERE id = {placeholder}", (int(trade_id),))
            row = cursor.fetchone()
            return dict(row) if row else None # Return result and exit
    except Exception as e:
        print(f"Error fetching trade ID {trade_id}: {e}")
        return None

def update_trade(trade_id: int, updated_data: Dict):
    """
    Updates an existing trade record. Recalculates metrics if prices are updated.
    """
    existing = get_trade_by_id(trade_id)
    if not existing:
        print(f"Trade ID {trade_id} not found.")
        return

    # Merge existing data with updates to ensure calculations have full context
    merged = {**existing, **updated_data}
    merged = calculate_pnl_metrics(merged)

    db_type = get_active_db_type()
    if db_type == "ORACLE":
        placeholder = ":1" # Note: Simple positional for update
    elif db_type == "POSTGRES":
        placeholder = "%s"
    else:
        placeholder = "?"

    # Exclude non-updatable internal columns
    updatable_cols = [k for k in merged.keys() if k not in ('id', 'created_at')]
    set_clause = ", ".join([f"{col} = {placeholder}" for col in updatable_cols])
    values = [merged[col] for col in updatable_cols]
    values.append(trade_id)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if db_type == "ORACLE":
                # Oracle needs names or specific positional indices for larger sets usually, 
                # but simple positional works if bound correctly.
                cursor.execute(f"UPDATE trades SET {set_clause} WHERE id = :{len(values)}", tuple(values))
            else:
                cursor.execute(f"UPDATE trades SET {set_clause} WHERE id = {placeholder}", tuple(values))
            conn.commit()
    except (sqlite3.Error, psycopg2.Error) as e:
        print(f"Error updating trade ID {trade_id}: {e}")

def delete_trade(trade_id: int):
    """
    Deletes a trade record by ID.
    """
    db_type = get_active_db_type()
    if db_type == "ORACLE":
        placeholder = ":1"
    elif db_type == "POSTGRES":
        placeholder = "%s"
    else:
        placeholder = "?"

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM trades WHERE id = {placeholder}", (trade_id,))
            conn.commit()
    except (sqlite3.Error, psycopg2.Error) as e:
        print(f"Error deleting trade ID {trade_id}: {e}")

def add_trade(trade_data: Dict) -> int:
    """Inserts a live trade record (is_backtest = 0)."""
    trade_data['is_backtest'] = 0
    if 'timestamp' not in trade_data or not trade_data['timestamp']:
        trade_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    trade_data = calculate_pnl_metrics(trade_data)
    
    columns = [
        'timestamp', 'is_backtest', 'symbol', 'direction', 'entry_price', 
        'stop_loss', 'take_profit', 'exit_price', 'exit_reason', 'position_size', 
        'risk_amount', 'pnl', 'r_multiple', 'strategy', 'timeframe', 
        'market_context', 'notes', 'screenshot_path', 'sector', 'trade_type'
    ]

    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(columns)
    data_to_insert = [trade_data.get(col) for col in columns]

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = f"INSERT INTO trades ({col_names}) VALUES ({placeholders})"
            cursor.execute(query, tuple(data_to_insert))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding live trade: {e}")
        return -1

def upload_to_supabase(file_path: str, filename: str) -> Optional[str]:
    """Uploads a local file to Supabase storage and returns the public URL."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        bucket = "screenshots"
        with open(file_path, 'rb') as f:
            # Upload the file
            client.storage.from_(bucket).upload(filename, f, {"content-type": "image/png"})
            
            # Get public URL
            res = client.storage.from_(bucket).get_public_url(filename)
            return res
    except Exception as e:
        print(f"Cloud Upload Error: {e}")
        return None


def get_live_trades() -> pd.DataFrame:
    """Returns all live trades (is_backtest = 0) as a DataFrame."""
    try:
        with get_connection() as conn:
            query = "SELECT * FROM trades WHERE is_backtest = 0 ORDER BY timestamp DESC"
            return pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"Error fetching live trades: {e}")
        return pd.DataFrame()

def calculate_live_metrics() -> Dict:
    """Calculates summary metrics for live trades."""
    df = get_live_trades()
    if df.empty:
        return {"total_trades": 0, "win_rate": 0, "total_pnl": 0}

    closed_trades = df[df['pnl'].notnull()]
    if closed_trades.empty:
        return {"total_trades": len(df), "win_rate": 0, "total_pnl": 0}

    total_trades = len(closed_trades)
    wins = len(closed_trades[closed_trades['pnl'] > 0])
    win_rate = (wins / total_trades) * 100
    total_pnl = closed_trades['pnl'].sum()

    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2)
    }
# ==========================================
# EXAMPLE USAGE
# ==========================================
# if __name__ == "__main__":
#     # 1. Initialize the Database
#     init_db()
#
#     # 2. Add a sample live trade
#     sample_trade = {
#         "symbol": "BTC/USDT",
#         "direction": "LONG",
#         "entry_price": 50000.0,
#         "stop_loss": 49000.0,
#         "take_profit": 53000.0,
#         "exit_price": 52500.0,  # Trade already closed
#         "exit_reason": "Manual",
#         "position_size": 0.1,
#         "risk_amount": 100.0,   # Risking $100
#         "strategy": "Mean Reversion",
#         "timeframe": "1H",
#         "market_context": "Oversold on RSI"
#     }
#     trade_id = add_trade(sample_trade)
#     print(f"Added trade with ID: {trade_id}")
#
#     # 3. Get all live trades and print metrics
#     trades_df = get_live_trades()
#     print("\n--- Live Trades ---")
#     print(trades_df)
#
#     metrics = calculate_live_metrics()
#     print("\n--- Live Performance Metrics ---")
#     for key, value in metrics.items():
#         print(f"{key.replace('_', ' ').title()}: {value}")
