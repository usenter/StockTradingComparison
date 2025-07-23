import yfinance as yf
import pandas as pd
import numpy as np
from trading_strategies import (
    plot_profits, 
    dailyBuySell, 
    dailyBuySellSmart, 
    trendTrade, 
    passiveTrade, 
    calculate_strategy_xirr,
    movingAverage60_strategy
)
import concurrent.futures

# Configuration
ticker = "VOO" # ticker for Vanguard S&P 500 ETF
initialInvestment = 1000

# Data source configuration
USE_CSV = True  # Set to True to use CSV file instead of yfinance
CSV_FILE_PATH = "VOOstock.csv"  # Path to your CSV file

# Data setup
if USE_CSV:
    # Load data from CSV file
    try:
        specific_period = pd.read_csv(CSV_FILE_PATH)
        # Convert Date column to datetime and set as index
        specific_period['Date'] = pd.to_datetime(specific_period['Date'])
        specific_period.set_index('Date', inplace=True)
        print(f"Loaded data from {CSV_FILE_PATH}")
        print(f"Data range: {specific_period.index[0]} to {specific_period.index[-1]}")
        print(f"Number of trading days: {len(specific_period)}")
    except FileNotFoundError:
        print(f"CSV file {CSV_FILE_PATH} not found. Please ensure the file exists.")
        exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        exit(1)
else:
    # Load data from yfinance (original method)
    stock = yf.Ticker(ticker)
    specific_period = stock.history(period = "10y", interval = "1h")
    print(f"Loaded 1-hour data for {ticker} from yfinance")
    # Create daily summary for daily strategies
    daily_period = specific_period.resample('1D').agg({'Open': 'first', 'Close': 'last'})
    # Remove days with missing data (e.g., weekends)
    daily_period = daily_period.dropna()

# Verify data has required columns
required_columns = ['Open', 'Close']
if USE_CSV:
    missing_columns = [col for col in required_columns if col not in specific_period.columns]
    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        print(f"Available columns: {list(specific_period.columns)}")
        exit(1)
else:
    missing_columns = [col for col in required_columns if col not in daily_period.columns]
    if missing_columns:
        print(f"Error: Missing required columns in daily_period: {missing_columns}")
        print(f"Available columns: {list(daily_period.columns)}")
        exit(1)

# Run all methods and plot results
if USE_CSV:
    strategy_args = [
        (dailyBuySell, specific_period, initialInvestment, ticker),
        (dailyBuySellSmart, specific_period, initialInvestment, ticker),
        (trendTrade, specific_period, initialInvestment, ticker),
        (passiveTrade, specific_period, initialInvestment, ticker),
        (movingAverage60_strategy, specific_period, initialInvestment, ticker)
    ]
else:
    strategy_args = [
        (dailyBuySell, daily_period, initialInvestment, ticker),
        (dailyBuySellSmart, daily_period, initialInvestment, ticker),
        (trendTrade, daily_period, initialInvestment, ticker),
        (passiveTrade, daily_period, initialInvestment, ticker),
        (movingAverage60_strategy, specific_period, initialInvestment, ticker)
    ]

results = [None]*5
summaries = [None]*5
xirrs = [None]*5

with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_idx = {executor.submit(fn, *args): i for i, (fn, *args) in enumerate(strategy_args)}
    for future in concurrent.futures.as_completed(future_to_idx):
        idx = future_to_idx[future]
        profits, summary = future.result()
        results[idx] = profits
        summaries[idx] = summary

# Calculate XIRR in parallel
if USE_CSV:
    xirr_args = [
        (specific_period, results[0], initialInvestment),
        (specific_period, results[1], initialInvestment),
        (specific_period, results[2], initialInvestment),
        (specific_period, results[3], initialInvestment),
        (specific_period, results[4], initialInvestment)
    ]
else:
    xirr_args = [
        (daily_period, results[0], initialInvestment),
        (daily_period, results[1], initialInvestment),
        (daily_period, results[2], initialInvestment),
        (daily_period, results[3], initialInvestment),
        (specific_period, results[4], initialInvestment)
    ]
with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_idx = {executor.submit(calculate_strategy_xirr, *args): i for i, args in enumerate(xirr_args)}
    for future in concurrent.futures.as_completed(future_to_idx):
        idx = future_to_idx[future]
        xirrs[idx] = future.result()

# Print XIRR results
labels = [
    "Daily Buy/Sell Strategy XIRR:",
    "Smart Daily Buy/Sell Strategy XIRR:",
    "Trend Following Strategy XIRR:",
    "Passive Investment Strategy XIRR:",
    "60-day MA Strategy XIRR:"
]
for label, xirr in zip(labels, xirrs):
    print(f"{label} {xirr:.2%}" if xirr else f"{label} Could not calculate")

# Write summary to file
with open('RetrospectiveStrategiesResults.txt', 'w') as file:
    for summary in summaries:
        file.write(f"{summary['method']} for {summary['ticker']} from {summary['start']} to {summary['end']} \n")
        file.write(f"Starting balance: ${summary['starting_balance']:.2f}\n")
        file.write(f"Final balance: ${summary['final_balance']:.2f}\n")
        file.write(f"Profit: ${summary['profit']:.2f}\n")
        file.write(f"Profit percentage: {summary['profit_percentage']:.2%}\n\n")

# Create and save the plot
if USE_CSV:
    plot_profits(specific_period, *results, ticker)
else:
    plot_profits(daily_period, *results, ticker)

print(f"Analysis complete for {ticker}")
print("Results saved to RetrospectiveStrategiesResults.txt")
print("Plot saved to profit_comparison.png")

# stock.history() format:
# Open
# Close
# not used:
# Volume 
# Dividends
# High
# Low
# Stock Splits


