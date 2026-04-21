import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import trade_log
import backtest_log
from typing import Dict, Optional, Any
from fpdf import FPDF

def calculate_advanced_metrics(is_backtest: bool = False, session: str = None, df: pd.DataFrame = None) -> Dict:
    """
    Calculates a comprehensive suite of performance metrics.
    """
    if df is None:
        # Fetch backtest data if no dataframe is provided
        df = backtest_log.get_backtest_trades(session)

    # Only analyze closed trades with PnL data
    df = df[df['pnl'].notnull()].copy()
    if df.empty:
        return {}

    # Sort by timestamp to ensure chronological streak/drawdown calculation
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

    pnl = df['pnl']
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]

    # Basic Metrics
    total_trades = len(df)
    win_rate = (len(wins) / total_trades) * 100
    total_pnl = pnl.sum()
    avg_win = wins.mean() if not wins.empty else 0
    avg_loss = losses.mean() if not losses.empty else 0
    
    # Profit Factor & Expectancy
    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    expectancy = ( (win_rate/100) * avg_win ) + ( (1 - win_rate/100) * avg_loss )

    # Sharpe Ratio (Simplified Annualized) - Added protection against zero standard deviation
    if len(pnl) > 1 and pnl.std() > 1e-6:
        sharpe_ratio = (pnl.mean() / pnl.std()) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    # Dynamic Drawdown Calculation: Use the capital of the first trade or fallback to 10k
    initial_capital = df['capital_per_trade'].iloc[0] if 'capital_per_trade' in df.columns and df['capital_per_trade'].iloc[0] > 0 else 10000
    equity_curve = initial_capital + pnl.cumsum()
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    max_drawdown_pct = drawdown.min() * 100

    # Streaks
    def get_max_streak(series):
        if series.empty: return 0
        # Compare each element with the previous one to find where the sign changes
        is_win = series > 0
        runs = (is_win != is_win.shift()).cumsum()
        win_streaks = is_win.groupby(runs).sum()
        loss_streaks = (~is_win).groupby(runs).sum()
        return int(win_streaks.max()), int(loss_streaks.max())

    win_streak, loss_streak = get_max_streak(pnl)

    # Monthly Returns
    df.set_index('timestamp', inplace=True)
    monthly_returns = df['pnl'].resample('ME').sum()

    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "win_streak": win_streak,
        "loss_streak": loss_streak,
        "best_trade": round(pnl.max(), 2),
        "worst_trade": round(pnl.min(), 2),
        "monthly_returns": monthly_returns
    }

def generate_equity_curve(is_backtest: bool = False, session: str = None, df: pd.DataFrame = None) -> plt.Figure:
    """
    Generates a professional equity curve with an underwater drawdown area chart.
    """
    if df is None:
        df = backtest_log.get_backtest_trades(session)

    df = df[df['pnl'].notnull()].copy()
    if df.empty: return None

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # Match the dynamic capital logic used in calculate_advanced_metrics
    initial_capital = df['capital_per_trade'].iloc[0] if 'capital_per_trade' in df.columns and df['capital_per_trade'].iloc[0] > 0 else 10000
    cum_pnl = df['pnl'].cumsum()
    equity = initial_capital + cum_pnl
    peak = equity.cummax()
    drawdown = equity - peak

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, 
                                   gridspec_kw={'height_ratios': [3, 1]})
    
    # Plot Equity Curve (INR)
    ax1.plot(df['timestamp'], equity, label='Equity Curve', color='#2ecc71', linewidth=2)
    ax1.fill_between(df['timestamp'], initial_capital, equity, color='#2ecc71', alpha=0.1)
    ax1.set_title(f"Backtest Equity Curve {f'({session})' if session else ''}", 
                  fontsize=14, fontweight='bold')
    ax1.set_ylabel("Account Value (₹)")
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend()
    # Plot Underwater Drawdown (INR)
    ax2.fill_between(df['timestamp'], 0, drawdown, color='#e74c3c', alpha=0.3, label='Drawdown')
    ax2.plot(df['timestamp'], drawdown, color='#e74c3c', linewidth=1)
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Drawdown (₹)")
    ax2.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    return fig

def plot_performance_by_strategy(is_backtest: bool = False, session: str = None, df: pd.DataFrame = None):
    """
    Generates a grouped bar chart visualizing strategy performance.
    """
    if df is None:
        df = backtest_log.get_backtest_trades(session)

    df = df[df['pnl'].notnull()].copy()
    if df.empty: return None

    # Group and aggregate
    strat_stats = df.groupby('strategy').agg(
        total_pnl=('pnl', 'sum'),
        win_rate=('pnl', lambda x: (x > 0).mean() * 100)
    ).reset_index()
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(strat_stats['strategy']))
    width = 0.35

    # PnL Bars
    bars1 = ax1.bar(x - width/2, strat_stats['total_pnl'], width, label='Total PnL', color='#3498db')
    ax1.set_ylabel('Total PnL (₹)', color='#3498db', fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(strat_stats['strategy'], rotation=45)

    # Win Rate Axis
    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width/2, strat_stats['win_rate'], width, label='Win Rate %', color='#f1c40f', alpha=0.7)
    ax2.set_ylabel('Win Rate (%)', color='#f39c12', fontsize=12)
    ax2.set_ylim(0, 100)

    plt.title("Performance Analysis by Strategy", fontsize=14)
    fig.tight_layout()
    return fig

def compare_live_vs_backtest() -> Dict:
    """
    Compares key performance metrics between live and backtest trading.
    """
    live_metrics = calculate_advanced_metrics(is_backtest=False)
    bt_metrics = calculate_advanced_metrics(is_backtest=True)

    if not live_metrics or not bt_metrics:
        print("Insufficient data for comparison.")
        return {}

    comparison = {
        "Metric": ["Win Rate (%)", "Profit Factor", "Expectancy", "Sharpe Ratio"],
        "Live": [live_metrics['win_rate'], live_metrics['profit_factor'], live_metrics['expectancy'], live_metrics['sharpe_ratio']],
        "Backtest": [bt_metrics['win_rate'], bt_metrics['profit_factor'], bt_metrics['expectancy'], bt_metrics['sharpe_ratio']]
    }

    # Generate side-by-side plot
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(comparison['Metric']))
    width = 0.35

    ax.bar(x - width/2, comparison['Live'], width, label='Live', color='#2ecc71')
    ax.bar(x + width/2, comparison['Backtest'], width, label='Backtest', color='#9b59b6')

    ax.set_ylabel('Value')
    ax.set_title('Live vs. Backtest Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(comparison['Metric'])
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    return comparison, fig

def save_chart(fig: plt.Figure, filename: str):
    """
    Saves a matplotlib figure as a PNG file.
    """
    if fig:
        try:
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Chart saved successfully as {filename}")
        except Exception as e:
            print(f"Error saving chart: {e}")
    else:
        print("No figure provided to save.")

def generate_pdf_report(metrics: Dict[str, Any], filter_info: str = "All Data") -> bytes:
    """
    Generates a PDF report containing the analysis metrics.
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 15, "Trading Performance Analysis Report", ln=True, align='C')
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.cell(0, 10, f"Filters Applied: {filter_info}", ln=True, align='C')
    pdf.ln(10)

    # Metrics Table
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Key Performance Indicators", ln=True)
    pdf.set_font("Arial", "", 12)
    
    # Table styling logic
    for key, value in metrics.items():
        if key == 'monthly_returns':
            continue
        
        display_key = key.replace('_', ' ').title()
        if isinstance(value, float):
            display_val = f"{value:,.2f}"
        else:
            display_val = str(value)
            
        pdf.cell(100, 10, f"{display_key}:", border=1)
        pdf.cell(0, 10, display_val, border=1, ln=True)

    # Return as bytes (fpdf2 returns bytearray by default; convert to bytes for Streamlit)
    return bytes(pdf.output())

# ==========================================
# EXAMPLE USAGE
# ==========================================
# if __name__ == "__main__":
#     # 1. Advanced Metrics for Live Trades
#     live_adv = calculate_advanced_metrics(is_backtest=False)
#     print("\n--- Advanced Live Metrics ---")
#     for k, v in live_adv.items():
#         if k != 'monthly_returns': print(f"{k}: {v}")
#
#     # 2. Generate and Save Equity Curve for Live Trades
#     fig_equity = generate_equity_curve(is_backtest=False)
#     save_chart(fig_equity, "live_equity_curve.png")
#
#     # 3. Generate Equity Curve for a Specific Backtest Session
#     sessions = backtest_log.get_all_backtest_sessions()
#     if sessions:
#         fig_bt = generate_equity_curve(is_backtest=True, session=sessions[0])
#         save_chart(fig_bt, f"backtest_{sessions[0]}_equity.png")
#
#     # 4. Strategy Analysis
#     fig_strat = plot_performance_by_strategy(is_backtest=False)
#     save_chart(fig_strat, "strategy_performance.png")
#
#     # 5. Live vs Backtest Comparison
#     comp_data, fig_comp = compare_live_vs_backtest()
#     if comp_data:
#         save_chart(fig_comp, "live_vs_backtest_comparison.png")
#         print("\n--- Comparison Data ---")
#         print(pd.DataFrame(comp_data))

    # plt.show() # Uncomment to view charts immediately