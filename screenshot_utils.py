import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Optional

# Import necessary functions from trade_log.py for database interaction
from trade_log import DB_PATH, get_trade_by_id, update_trade

# Configuration
SCREENSHOTS_DIR = "screenshots"

def _sanitize_filename(filename: str) -> str:
    """Removes characters that are not allowed in filenames."""
    return "".join(c for c in filename if c.isalnum() or c in ('_', '-')).rstrip()

def attach_screenshot(trade_id: int, is_backtest: bool = False) -> Optional[str]:
    """
    Opens a file dialog to select an image, copies it to the screenshots folder,
    renames it intelligently, and updates the database.

    Args:
        trade_id (int): The ID of the trade to attach the screenshot to.
        is_backtest (bool): True if it's a backtest trade, False for live.

    Returns:
        str or None: The full path of the saved screenshot if successful, else None.
    """
    # Fetch trade details to generate intelligent filename
    trade = get_trade_by_id(trade_id)
    if not trade:
        messagebox.showerror("Error", f"Trade with ID {trade_id} not found.")
        return None

    file_path = filedialog.askopenfilename(
        title="Select Screenshot Image",
        filetypes=[("Image files", "*.png *.jpg *.jpeg")]
    )

    if not file_path:
        return None  # User cancelled the dialog

    # Ensure screenshots directory exists
    Path(SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)

    original_extension = Path(file_path).suffix
    symbol = _sanitize_filename(trade.get('symbol', 'UNKNOWN'))
    timestamp_obj = datetime.strptime(trade.get('timestamp'), "%Y-%m-%d %H:%M:%S")

    if is_backtest:
        session_name = _sanitize_filename(trade.get('backtest_session', 'NoSession'))
        date_str = timestamp_obj.strftime("%Y%m%d")
        new_filename = f"BT_{symbol}_{session_name}_{date_str}{original_extension}"
    else:
        time_str = timestamp_obj.strftime("%Y%m%d_%H%M%S")
        new_filename = f"LIVE_{symbol}_{time_str}{original_extension}"

    destination_path = Path(SCREENSHOTS_DIR) / new_filename

    try:
        shutil.copy(file_path, destination_path)
        # Update the database with the new screenshot path
        update_trade(trade_id, {'screenshot_path': str(destination_path)})
        messagebox.showinfo("Success", f"Screenshot attached and saved to {destination_path}")
        return str(destination_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to attach screenshot: {e}")
        return None

def get_screenshot_path(trade_id: int) -> Optional[str]:
    """
    Retrieves the screenshot path for a given trade ID from the database.

    Args:
        trade_id (int): The ID of the trade.

    Returns:
        str or None: The path to the screenshot if found, else None.
    """
    trade = get_trade_by_id(trade_id)
    if trade:
        return trade.get('screenshot_path')
    return None

def preview_screenshot(trade_id: int):
    """
    Opens the screenshot in the default system image viewer.

    Args:
        trade_id (int): The ID of the trade whose screenshot is to be previewed.
    """
    screenshot_path = get_screenshot_path(trade_id)

    if not screenshot_path:
        messagebox.showinfo("No Screenshot", f"No screenshot path found for trade ID {trade_id}.")
        return

    full_path = Path(screenshot_path)

    if not full_path.exists():
        messagebox.showerror("File Not Found", f"Screenshot file not found at: {full_path}")
        return
    
    # Ensure the path is a file and not a directory or a symbolic link to a sensitive area
    if not full_path.is_file():
        messagebox.showerror("Invalid File", "The screenshot path does not point to a valid file.")
        return

    try:
        if os.name == 'nt':  # Windows
            os.startfile(full_path)
        elif os.name == 'posix':  # macOS, Linux, Unix
            # Explicitly set shell=False to prevent terminal injection
            subprocess.run(['open', str(full_path)], shell=False) 
        else:
            messagebox.showwarning("Unsupported OS", "Automatic screenshot preview is not supported on this operating system.")
    except FileNotFoundError:
        messagebox.showerror("Error", "Default image viewer not found. Please open the file manually.")
    except Exception as e:
        messagebox.showerror("Error", f"Could not open screenshot: {e}")

# ==========================================
# EXAMPLE USAGE (Commented Out)
# ==========================================
# if __name__ == "__main__":
#     # This example assumes you have a 'trading_journal.db' with some trades
#     # and that you have an image file to attach.
#
#     # 1. Initialize the database (if not already done by main.py or trade_log.py)
#     # trade_log.init_db()
#
#     # 2. Add a dummy trade to attach a screenshot to
#     # This is just for demonstration; in a real app, you'd use an existing trade ID.
#     dummy_live_trade_data = {
#         "symbol": "TEST_LIVE",
#         "direction": "LONG",
#         "entry_price": 100.0,
#         "stop_loss": 99.0,
#         "risk_amount": 10.0,
#         "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     }
#     dummy_trade_id = trade_log.add_trade(dummy_live_trade_data)
#     print(f"Added dummy live trade with ID: {dummy_trade_id}")
#
#     if dummy_trade_id != -1:
#         # 3. Attach a screenshot to the dummy live trade
#         # This will open a file dialog. Select any image file.
#         # attached_path = attach_screenshot(dummy_trade_id, is_backtest=False)
#         # if attached_path:
#         #     print(f"Screenshot attached at: {attached_path}")
#         #
#         #     # 4. Preview the attached screenshot
#         #     preview_screenshot(dummy_trade_id)
#         # else:
#         #     print("No screenshot attached or an error occurred.")
#
#         # Example of previewing an existing screenshot (if you manually set one for a trade)
#         # For instance, if trade ID 1 has a screenshot:
#         # print("\nAttempting to preview screenshot for trade ID 1 (if exists)...")
#         # preview_screenshot(1)
#
#         # Clean up the dummy trade (optional)
#         # trade_log.delete_trade(dummy_trade_id)
#         # print(f"Dummy trade {dummy_trade_id} deleted.")