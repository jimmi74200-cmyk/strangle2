# This script will backtest the 15-minute Supertrend strategy on historical data
# for NIFTY futures.
import pandas as pd
import pandas_ta as ta
import time
from py5paisa import FivePaisaClient
from historical_data import fetch_historical_data
import config
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Client Initialization ---
client = FivePaisaClient(cred={
    "APP_NAME": config.APP_NAME,
    "APP_SOURCE": config.APP_SOURCE,
    "USER_ID": config.USER_ID,
    "PASSWORD": config.PASSWORD,
    "USER_KEY": config.USER_KEY,
    "ENCRYPTION_KEY": config.ENCRYPTION_KEY
})
if config.ACCESS_TOKEN != "YOUR_ACCESS_TOKEN":
    client.set_access_token(config.ACCESS_TOKEN, config.CLIENT_CODE)
else:
    logging.error("Access Token not found. Please run an authentication script first.")

# --- Backtesting Functions ---

def get_full_historical_dataset(exch, exch_type, scrip_code, months=12):
    """
    Fetches a large 1-minute dataset for backtesting, fetching month by month.
    """
    try:
        logging.info(f"Fetching historical data for the last {months} months for ScripCode: {scrip_code}")
        all_candles = []

        # Loop through the last N months to fetch data in chunks
        for i in range(months, 0, -1):
            to_date = datetime.now() - timedelta(days=(i-1)*30)
            from_date = datetime.now() - timedelta(days=i*30)
            from_date_str = from_date.strftime('%Y-%m-%d')
            to_date_str = to_date.strftime('%Y-%m-%d')

            logging.info(f"Fetching data from {from_date_str} to {to_date_str}...")
            candles = fetch_historical_data(exch, exch_type, scrip_code, '1m', from_date_str, to_date_str)
            if candles:
                all_candles.extend(candles)
            time.sleep(1) # Be respectful to the API rate limits

        if not all_candles:
            logging.error("Could not fetch any historical data for the given period.")
            return None

        df = pd.DataFrame(all_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df.set_index('Timestamp', inplace=True)
        df = df.drop_duplicates().sort_index() # Clean and sort the data

        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col])

        logging.info(f"Successfully fetched a total of {len(df)} 1-minute candles.")
        return df

    except Exception as e:
        logging.error(f"An error occurred while fetching the full historical dataset: {e}")
        return None

def get_supertrend_signal(df):
    """Calculates the Supertrend on a given 15-min DataFrame and returns the latest signal."""
    try:
        if df.empty or len(df) < 2:
            return 'none'
        df.ta.supertrend(length=7, multiplier=3, append=True)
        latest_signal = df['SUPERTd_7_3.0'].iloc[-2]
        if latest_signal == 1:
            return 'buy'
        elif latest_signal == -1:
            return 'sell'
        return 'none'
    except Exception as e:
        logging.error(f"Error calculating Supertrend: {e}")
        return 'none'

def simulate_trade(signal, day_data, entry_time):
    """
    Simulates a single trade for a given day and returns the result.
    """
    sl_points = 40
    target_points = 120

    # Get the data for the trading session (after entry time)
    trade_session_data = day_data.loc[day_data.index >= entry_time]
    if trade_session_data.empty:
        return None # No data to trade on

    entry_price = trade_session_data['Open'].iloc[0]

    if signal == 'buy':
        stop_loss_price = entry_price - sl_points
        target_price = entry_price + target_points
    else: # sell
        stop_loss_price = entry_price + sl_points
        target_price = entry_price - target_points

    exit_time = datetime.combine(entry_time.date(), datetime.strptime("15:15", "%H:%M").time())

    for index, candle in trade_session_data.iterrows():
        # Check for EOD exit
        if index.time() >= exit_time.time():
            exit_price = candle['Close']
            exit_reason = 'EOD'
            break

        # Check for SL/TP hit
        if signal == 'buy':
            if candle['Low'] <= stop_loss_price:
                exit_price = stop_loss_price
                exit_reason = 'SL'
                break
            elif candle['High'] >= target_price:
                exit_price = target_price
                exit_reason = 'TP'
                break
        else: # sell
            if candle['High'] >= stop_loss_price:
                exit_price = stop_loss_price
                exit_reason = 'SL'
                break
            elif candle['Low'] <= target_price:
                exit_price = target_price
                exit_reason = 'TP'
                break
    else:
        # If the loop finishes without a break, it means no SL/TP/EOD hit, use last candle
        exit_price = trade_session_data['Close'].iloc[-1]
        exit_reason = 'EOD (Loop End)'

    # Calculate P/L
    if signal == 'buy':
        pnl = exit_price - entry_price
    else: # sell
        pnl = entry_price - exit_price

    return {
        'date': entry_time.date(),
        'signal': signal,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'exit_reason': exit_reason,
        'pnl': pnl
    }

def run_backtest(full_data):
    """
    The main function to execute the backtesting loop over the entire dataset.
    """
    if full_data.empty:
        logging.error("Cannot run backtest on empty data.")
        return []

    logging.info("--- Starting Backtest Loop ---")
    trades = []

    # Group the 1-minute data by day
    daily_groups = full_data.groupby(full_data.index.date)

    for day, day_data in daily_groups:
        logging.info(f"Processing data for {day}")

        entry_time = datetime.combine(day, datetime.strptime("09:17", "%H:%M").time())
        data_for_signal = day_data.loc[day_data.index < entry_time]

        if data_for_signal.empty:
            logging.warning(f"No data available before 09:17 on {day}. Skipping.")
            continue

        ohlc_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
        df_15min = data_for_signal.resample('15min').apply(ohlc_dict).dropna()

        signal = get_supertrend_signal(df_15min)

        # --- Enhanced Logging ---
        # Log the signal for every day to see what's happening.
        logging.info(f"Signal for {day}: {signal}")

        if signal in ['buy', 'sell']:
            logging.info(f"Trade triggered on {day}. Simulating...")
            trade_result = simulate_trade(signal, day_data, entry_time)
            if trade_result:
                trades.append(trade_result)
                logging.info(f"Trade Result: P/L = {trade_result['pnl']:.2f}, Exit Reason: {trade_result['exit_reason']}")

    logging.info("--- Backtest Loop Finished ---")
    return trades

def print_results(trades):
    """Calculates and prints the final performance metrics from the trade log."""
    if not trades:
        logging.warning("No trades were executed during the backtest period.")
        return

    logging.info("--- Backtest Results ---")

    results_df = pd.DataFrame(trades)
    lot_size = 50 # NIFTY Futures Lot Size

    total_trades = len(results_df)
    winning_trades = results_df[results_df['pnl'] > 0]
    losing_trades = results_df[results_df['pnl'] < 0]

    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0

    total_gross_pnl_points = results_df['pnl'].sum()
    total_net_pnl = total_gross_pnl_points * lot_size

    avg_pnl_points = results_df['pnl'].mean()
    avg_net_pnl = avg_pnl_points * lot_size

    max_profit_points = results_df['pnl'].max()
    max_loss_points = results_df['pnl'].min()

    print("\n" + "="*40)
    print("      Strategy Performance Summary")
    print("="*40)
    print(f" Total Trades: {total_trades}")
    print(f" Winning Trades: {len(winning_trades)}")
    print(f" Losing Trades: {len(losing_trades)}")
    print(f" Win Rate: {win_rate:.2f}%")
    print("-" * 40)
    print(f" Total Gross P/L (Points): {total_gross_pnl_points:.2f}")
    print(f" Total Net P/L (Rupees):   ₹{total_net_pnl:,.2f}")
    print("-" * 40)
    print(f" Average P/L (Points): {avg_pnl_points:.2f}")
    print(f" Average Net P/L (Rupees):   ₹{avg_net_pnl:,.2f}")
    print("-" * 40)
    print(f" Max Profit on a Trade (Points): {max_profit_points:.2f}")
    print(f" Max Loss on a Trade (Points):   {max_loss_points:.2f}")
    print("="*40 + "\n")

    # Optional: Print a summary of trades by exit reason
    print("Exit Reason Breakdown:")
    print(results_df['exit_reason'].value_counts())
    print("="*40 + "\n")


if __name__ == "__main__":
    logging.info("--- Starting Supertrend Strategy Backtest ---")

    # --- Gather User Inputs ---
    exch = input("Enter Exchange (e.g., N for NSE, B for BSE): ").upper()
    exch_type = input("Enter Exchange Type (e.g., C for Cash, D for Derivatives): ").upper()
    scrip_code = input("Please enter the scrip code you want to backtest: ")

    # --- Input Validation ---
    if exch not in ['N', 'B', 'M']:
        logging.error("Invalid Exchange. Please enter N, B, or M.")
    elif exch_type not in ['C', 'D', 'U', 'X', 'Y']:
         logging.error("Invalid Exchange Type. Please enter C, D, U, X, or Y.")
    elif not scrip_code.isdigit():
        logging.error("Invalid scrip code. Please enter a valid numeric scrip code.")
    else:
        # Fetch data for the last 3 months for a quicker test run
        full_data = get_full_historical_dataset(exch, exch_type, scrip_code, months=3)
        if full_data is not None and not full_data.empty:
            trade_log = run_backtest(full_data)
            print_results(trade_log)
        else:
            logging.error(f"Could not fetch data for Scrip {scrip_code} on {exch}/{exch_type}.")