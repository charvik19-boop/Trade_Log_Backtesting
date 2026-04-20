import sqlite3
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List, Optional
from trade_log import get_connection, init_db, calculate_pnl_metrics, DATABASE_URL, ORACLE_DSN, get_active_db_type

try:
    import psycopg2
except ImportError:
    class psycopg2: Error = Exception

try:
    import oracledb
except ImportError:
    class oracledb: Error = Exception

def get_excel_source_options() -> Dict[str, List[str]]:
    """
    Reads Source_Data.xlsx and returns unique values for dropdowns.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, "Source_Data.xlsx")
    options = {
        "strategies": [],
        "chart_patterns": [],
        "significant_candles": [],
        "sectors": [],
        "trade_types": [],
        "timeframes": []
    }
    
    if not os.path.exists(excel_path):
        return options

    try:
        df = pd.read_excel(excel_path)
        # Mapping per request: A=0, B=1, C=2, G=6, H=7
        options["strategies"] = df.iloc[:, 0].dropna().unique().tolist()
        options["chart_patterns"] = df.iloc[:, 1].dropna().unique().tolist()
        options["significant_candles"] = df.iloc[:, 2].dropna().unique().tolist()
        options["sectors"] = df.iloc[:, 6].dropna().unique().tolist()
        options["trade_types"] = df.iloc[:, 7].dropna().unique().tolist()
        options["timeframes"] = df.iloc[:, 5].dropna().unique().tolist()
    except PermissionError:
        print(f"Error: Permission denied for '{excel_path}'. Please close the file in Excel and restart the app.")
    except Exception as e:
        print(f"Error reading Excel source: {e}")
        
    return options

def add_backtest_trade(trade_data: Dict) -> int:
    """
    Inserts a backtest trade record.
    - Sets is_backtest = 1
    - Generates backtest_session if missing
    - Calculates PnL/R-Multiple automatically
    """
    trade_data['is_backtest'] = 1
    
    # Handle session naming
    if 'backtest_session' not in trade_data or not trade_data['backtest_session']:
        session_ts = datetime.now().strftime("%Y%m%d_%H%M")
        trade_data['backtest_session'] = f"Session_{session_ts}"

    if 'timestamp' not in trade_data or not trade_data['timestamp']:
        trade_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calculate metrics using shared logic
    trade_data = calculate_pnl_metrics(trade_data)

    columns = [
        'timestamp', 'is_backtest', 'symbol', 'direction', 'entry_price', 
        'stop_loss', 'take_profit', 'exit_price', 'exit_reason', 'position_size', 
        'risk_amount', 'pnl', 'r_multiple', 'strategy', 'timeframe', 
        'market_context', 'backtest_session', 'notes', 'screenshot_path'
    ] + [ 
        'capital_per_trade', 'stop_loss_price', 'max_qty_capital', 'max_profit', 
        'capital_required', 'exit_date', 'exit_time', 'pct_return', 'outcome', 'duration_candles'
    ] + [
        'sector', 'trade_type', 'chart_pattern', 'significant_candle', 'signal_date', 'signal_time',
        'tide_timeframe', 'wave_timeframe',
        'tide_upper_bb_challenge', 'tide_macd_tick', 'tide_macd_zeroline', 'tide_stochastic', 'tide_stochastic_val',
        'tide_rsi_threshold', 'tide_rsi_val', 'tide_price_above_50ema', 'wave_macd_tick', 'wave_macd_zeroline', 'wave_stochastic', 
        'wave_stochastic_val', 'wave_rsi_threshold', 'wave_rsi_val', 'wave_bb_challenge', 'wave_trendline_break',
        'wave_volume_above_avg', 'wave_shake_out', 'wave_two_higher_lows', 'wave_ema_pco', 'wave_price_above_50ema',
        'wave_adx_ungali', 'wave_adx_val', 'wave_di_crossover', 'wave_resistance', 'wave_itm_atm_ce_tmg',
        'wave_atm_pe_tmj', 'wave_future_buildup'
    ]

    db_type = get_active_db_type()
    if db_type == "ORACLE":
        placeholders = ", ".join([f":{i+1}" for i in range(len(columns))])
    else:
        placeholder = "%s" if db_type == "POSTGRES" else "?"
        placeholders = ", ".join([placeholder] * len(columns))

    data_to_insert = {col: trade_data.get(col) for col in columns}
    col_names = ", ".join(columns)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if db_type == "POSTGRES":
                # Standard Postgres approach using RETURNING
                query = f"INSERT INTO trades ({col_names}) VALUES ({placeholders}) RETURNING id"
                cursor.execute(query, tuple(data_to_insert.values()))
                new_id = cursor.fetchone()[0]
                conn.commit()
                return new_id
            
            query = f"INSERT INTO trades ({col_names}) VALUES ({placeholders})"
            cursor.execute(query, tuple(data_to_insert.values()))

            conn.commit()
            return cursor.lastrowid
    except (sqlite3.Error, psycopg2.Error, oracledb.Error) as e:
        print(f"Error adding backtest trade: {e}")
        return -1

def get_backtest_trades(session: str = None) -> pd.DataFrame:
    """
    Returns backtest trades as a DataFrame. Optionally filtered by session.
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
            # pd.read_sql_query handles the cursor internally
            if session:
                query = f"SELECT * FROM trades WHERE is_backtest = 1 AND backtest_session = {placeholder} ORDER BY timestamp DESC"
                return pd.read_sql_query(query, conn, params=(session,))
            query = "SELECT * FROM trades WHERE is_backtest = 1 ORDER BY timestamp DESC"
            return pd.read_sql_query(query, conn)
    except (sqlite3.Error, psycopg2.Error, pd.io.sql.DatabaseError) as e:
        print(f"Error fetching backtest trades: {e}")
        return pd.DataFrame()

def get_all_backtest_sessions() -> List[str]:
    """
    Returns a list of all unique backtest session names.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT backtest_session FROM trades WHERE is_backtest = 1")
            return [row[0] for row in cursor.fetchall() if row[0] is not None]
    except (sqlite3.Error, psycopg2.Error) as e:
        print(f"Error fetching sessions: {e}")
        return []

def calculate_backtest_metrics(session: str = None) -> Dict:
    """
    Calculates performance metrics for backtest trades.
    """
    df = get_backtest_trades(session)
    closed_trades = df[df['pnl'].notnull()].copy()
    
    if closed_trades.empty:
        return {
            "total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "profit_factor": 0.0, "expectancy": 0.0
        }

    total_trades = len(closed_trades)
    wins = closed_trades[closed_trades['pnl'] > 0]
    losses = closed_trades[closed_trades['pnl'] <= 0]
    
    win_rate = (len(wins) / total_trades) * 100
    total_pnl = closed_trades['pnl'].sum()
    avg_win = wins['pnl'].mean() if not wins.empty else 0.0
    avg_loss = losses['pnl'].mean() if not losses.empty else 0.0
    
    gross_profit = wins['pnl'].sum()
    gross_loss = abs(losses['pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    
    loss_rate = 1 - (win_rate / 100)
    expectancy = ((win_rate / 100) * avg_win) + (loss_rate * avg_loss)

    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 2)
    }

def delete_backtest_trade(trade_id: int):
    """
    Deletes a record only if it is marked as a backtest trade.
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
            # Safety check to ensure we only delete backtest records
            cursor.execute(f"DELETE FROM trades WHERE id = {placeholder}", (int(trade_id),))
            if cursor.rowcount == 0:
                print(f"No backtest trade found with ID {trade_id}.")
            else:
                conn.commit()
                print(f"Backtest trade ID {trade_id} deleted.")
    except (sqlite3.Error, psycopg2.Error) as e:
        print(f"Error deleting backtest trade: {e}")

# ==========================================
# EXAMPLE USAGE
# ==========================================
# if __name__ == "__main__":
#     init_db()
#
#     # 1. Add sample backtest trade
#     bt_trade = {
#         "symbol": "NIFTY",
#         "direction": "SHORT",
#         "entry_price": 19500.0,
#         "stop_loss": 19550.0,
#         "exit_price": 19400.0,
#         "risk_amount": 2000.0,
#         "backtest_session": "NIFTY_5min_April2026",
#         "strategy": "EMA Cross"
#     }
#     new_id = add_backtest_trade(bt_trade)
#
#     # 2. Get trades and sessions
#     print(f"Sessions: {get_all_backtest_sessions()}")
#     df_session = get_backtest_trades("NIFTY_5min_April2026")
#
#     # 3. Calculate metrics
#     stats = calculate_backtest_metrics("NIFTY_5min_April2026")
#     print(f"Backtest Stats: {stats}")