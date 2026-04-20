import pandas as pd
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
from pathlib import Path
from typing import Optional
import trade_log
import backtest_log

def export_live_trades_to_csv(filename: str = "live_trades_export.csv"):
    """
    Fetches all live trades from the database and exports them to a CSV file.
    """
    df = trade_log.get_live_trades()
    if df.empty:
        print("No live trades found in the database to export.")
        return
    
    df.to_csv(filename, index=False)
    print(f"Successfully exported {len(df)} live trades to '{filename}'.")

def export_backtest_to_csv(session: str = None, filename: str = None):
    """
    Exports backtest trades to CSV. 
    - If session is provided, filters for that session.
    - If filename is not provided, generates one based on the session and timestamp.
    """
    df = backtest_log.get_backtest_trades(session)
    if df.empty:
        msg = f"session '{session}'" if session else "any session"
        print(f"No backtest trades found for {msg} to export.")
        return

    if not filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        sess_name = session if session else "all_sessions"
        filename = f"backtest_export_{sess_name}_{ts}.csv"

    df.to_csv(filename, index=False)
    print(f"Successfully exported {len(df)} backtest trades to '{filename}'.")

def import_trades_from_csv(file_path: Optional[str] = None, is_backtest: bool = False) -> int:
    """
    Imports trades from a CSV file. 
    If file_path is None, opens a file selection dialog.
    Maps common CSV headers to database columns and validates required fields.
    """
    if file_path is None:
        root = tk.Tk()
        root.withdraw()  # Hide the main tkinter window
        file_path = filedialog.askopenfilename(
            title="Select Trade CSV for Import",
            filetypes=[("CSV files", "*.csv")]
        )
        root.destroy()

    if not file_path or not Path(file_path).exists():
        print("No valid file selected for import.")
        return 0

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return 0

    # Column synonyms mapping: {CSV_Header: DB_Column}
    mapping = {
        'symbol': ['symbol', 'ticker', 'pair', 'instrument'],
        'direction': ['direction', 'side', 'type', 'action'],
        'entry_price': ['entry_price', 'entry', 'price', 'buy_price', 'sell_price'],
        'stop_loss': ['stop_loss', 'sl', 'stop'],
        'take_profit': ['take_profit', 'tp', 'target'],
        'exit_price': ['exit_price', 'exit', 'close_price'],
        'exit_reason': ['exit_reason', 'reason', 'close_reason'],
        'position_size': ['position_size', 'size', 'qty', 'quantity', 'units'],
        'risk_amount': ['risk_amount', 'risk', 'risk_usd', 'risk_amt'],
        'strategy': ['strategy', 'setup', 'system'],
        'timeframe': ['timeframe', 'tf', 'interval'],
        'market_context': ['market_context', 'context', 'bias'],
        'backtest_session': ['backtest_session', 'session'],
        'notes': ['notes', 'comment', 'remarks']
    }

    success_count = 0
    required_fields = ['symbol', 'direction', 'entry_price']

    # Helper to find column in DF based on synonyms
    def find_col(db_field):
        for synonym in mapping[db_field]:
            for col in df.columns:
                if col.strip().lower() == synonym.lower():
                    return col
        return None

    for _, row in df.iterrows():
        trade_data = {}
        for db_field in mapping.keys():
            col_name = find_col(db_field)
            if col_name is not None:
                val = row[col_name]
                # Basic cleanup: handle NaNs from pandas
                trade_data[db_field] = val if pd.notnull(val) else None

        # Validation: check required fields
        if not all(trade_data.get(f) for f in required_fields):
            continue

        try:
            if is_backtest:
                backtest_log.add_backtest_trade(trade_data)
            else:
                trade_log.add_trade(trade_data)
            success_count += 1
        except Exception as e:
            print(f"Failed to import row {row.get('symbol', 'Unknown')}: {e}")

    print(f"Import process complete. Successfully imported {success_count} trades.")
    return success_count

def get_sample_csv_template(is_backtest: bool = False) -> str:
    """
    Creates a sample CSV template with proper headers and one example row.
    Returns the generated filename.
    """
    headers = [
        "symbol", "direction", "entry_price", "stop_loss", "take_profit",
        "exit_price", "exit_reason", "position_size", "risk_amount",
        "strategy", "timeframe", "market_context", "notes"
    ]
    if is_backtest:
        headers.append("backtest_session")
        data = ["BTCUSDT", "LONG", 65000.0, 64000.0, 70000.0, 68000.0, "Target Hit", 0.5, 500.0, "Breakout", "4H", "Bullish", "High volume", "Q2_Testing"]
        filename = "sample_backtest_template.csv"
    else:
        data = ["AAPL", "SHORT", 190.0, 195.0, 175.0, 182.0, "Manual", 100, 500.0, "Mean Reversion", "1H", "Overbought", "RSI divergence", ""]
        filename = "sample_live_template.csv"

    df = pd.DataFrame([data], columns=headers)
    df.to_csv(filename, index=False)
    print(f"Template created: {filename}")
    return filename

# ==========================================
# EXAMPLE USAGE
# ==========================================
# if __name__ == "__main__":
#     # 1. Export all live trades to a custom CSV
#     export_live_trades_to_csv("my_live_trades_backup.csv")
#
#     # 2. Export a specific backtest session
#     # Assuming a session named 'NIFTY_April' exists
#     export_backtest_to_csv(session="NIFTY_April", filename="nifty_results.csv")
#
#     # 3. Create a template and then import from it
#     # Live Import
#     template_path = get_sample_csv_template(is_backtest=False)
#     import_trades_from_csv(template_path, is_backtest=False)
#
#     # Backtest Import (This will open a dialog if file_path is omitted)
#     # import_trades_from_csv(is_backtest=True)