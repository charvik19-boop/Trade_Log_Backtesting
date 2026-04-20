import trade_log
import backtest_log
import pandas as pd

def run_demonstration():
    """
    Demonstrates the functionality of the Trade Log and Backtest Log systems.
    """
    # 1. Initialize the shared Database
    # This creates the 'trades' table in 'trading_journal.db' if it doesn't exist.
    trade_log.init_db()

    # 2. Add Live Trades
    # Metrics like PnL and R-Multiple are auto-calculated because exit_price and risk_amount are provided.
    print("\nAdding live trades...")
    live_trades = [
        {
            "symbol": "NVDA",
            "direction": "LONG",
            "entry_price": 900.0,
            "stop_loss": 880.0,
            "exit_price": 950.0,
            "risk_amount": 1000.0,
            "strategy": "Trend Continuation",
            "timeframe": "1D"
        },
        {
            "symbol": "AAPL",
            "direction": "SHORT",
            "entry_price": 180.0,
            "stop_loss": 185.0,
            "exit_price": 170.0,
            "risk_amount": 500.0,
            "strategy": "Mean Reversion",
            "timeframe": "1H"
        }
    ]
    for trade in live_trades:
        trade_log.add_trade(trade)

    # 3. Add Backtest Trades across different sessions
    print("Adding backtest trades...")
    backtest_trades = [
        {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 60000.0,
            "stop_loss": 58000.0,
            "exit_price": 65000.0,
            "risk_amount": 200.0,
            "backtest_session": "Crypto_Swing_Q1",
            "strategy": "MA Cross"
        },
        {
            "symbol": "BTCUSDT",
            "direction": "SHORT",
            "entry_price": 68000.0,
            "stop_loss": 70000.0,
            "exit_price": 72000.0,  # A loss
            "risk_amount": 200.0,
            "backtest_session": "Crypto_Swing_Q1",
            "strategy": "MA Cross"
        },
        {
            "symbol": "EURUSD",
            "direction": "LONG",
            "entry_price": 1.0800,
            "stop_loss": 1.0750,
            "exit_price": 1.0900,
            "risk_amount": 100.0,
            "backtest_session": "Forex_Scalping_April",
            "strategy": "RSI Oversold"
        }
    ]
    for bt_trade in backtest_trades:
        backtest_log.add_backtest_trade(bt_trade)

    # 4. Display Live Trades
    print("\n=== LIVE TRADES ===")
    live_df = trade_log.get_live_trades()
    if not live_df.empty:
        print(live_df[['timestamp', 'symbol', 'direction', 'entry_price', 'exit_price', 'pnl', 'r_multiple']].to_string(index=False))

    # 5. Display Backtest Sessions
    print("\n=== BACKTEST SESSIONS ===")
    sessions = backtest_log.get_all_backtest_sessions()
    for session_name in sessions:
        print(f"Session: {session_name}")

    # 6. Performance Comparison
    print("\n=== PERFORMANCE COMPARISON ===")
    
    live_stats = trade_log.calculate_live_metrics()
    print(f"\n[ Live Performance ]\nTotal Trades: {live_stats['total_trades']} | Win Rate: {live_stats['win_rate']}% | Total PnL: ${live_stats['total_pnl']}")

    overall_bt_stats = backtest_log.calculate_backtest_metrics()
    print(f"[ Overall Backtest ]\nTotal Trades: {overall_bt_stats['total_trades']} | Win Rate: {overall_bt_stats['win_rate']}% | Total PnL: ${overall_bt_stats['total_pnl']}")

    if sessions:
        specific_session = sessions[0]
        session_stats = backtest_log.calculate_backtest_metrics(specific_session)
        print(f"[ Session: {specific_session} ]\nTotal Trades: {session_stats['total_trades']} | Win Rate: {session_stats['win_rate']}% | Profit Factor: {session_stats['profit_factor']}")

if __name__ == "__main__":
    run_demonstration()