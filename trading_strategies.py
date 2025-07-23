import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from numpy import datetime64
from numpy import timedelta64
import pyxirr

# Function to plot profits
def plot_profits(specific_period, dailyBuySell_profits, dailyBuySellSmart_profits, trendTrade_profits, method4_profits, ma60_profits, ticker):
    # Create date range for x-axis
    dates = specific_period.index
    
    # Calculate cumulative profits
    cumulative_profits1 = np.cumsum(dailyBuySell_profits)
    cumulative_profits2 = np.cumsum(dailyBuySellSmart_profits)
    cumulative_profits3 = np.cumsum(trendTrade_profits)
    cumulative_profits4 = method4_profits # no need to cumsum because it's just the difference between the current price and the initial price
    cumulative_profits5 = np.cumsum(ma60_profits)
    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(dates, cumulative_profits1, label='Method 1 - Daily Trading', color='blue')
    plt.plot(dates, cumulative_profits2, label='Method 2 - Smart Daily Trading', color='green')
    plt.plot(dates, cumulative_profits3, label='Method 3 - Trend Following', color='red')
    plt.plot(dates, cumulative_profits4, label='Method 4 - Passive Trade', color='purple')
    plt.plot(dates, cumulative_profits5, label='Method 5 - 60-day MA', color='orange')

    # Customize the plot
    plt.title(f'{ticker} Trading Strategy Comparison of Cumulative Profits')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Profit ($)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('profit_comparison.png')
    plt.close()

# Helper function to get daily interest rate for 4% annual, compounded daily
DAILY_INTEREST_RATE = (1 + 0.04) ** (1/365) - 1

#Method 1: just buy and sell as much as possible at the start and end of each day, netting the difference, begin with 1000
def dailyBuySell(specific_period, principal, ticker):
    balance = principal
    starting_balance = balance
    dailyBuySell_dailyProfits = np.zeros(len(specific_period))
    counter = 0
    for index, row in specific_period.iterrows():
        if row['Open'] <= 0:
            dailyBuySell_dailyProfits[counter] = 0
            counter+=1
            continue
        purchasedShares = balance/row['Open']
        dailyBuySell_dailyProfits[counter] = (purchasedShares * row['Close']) - balance
        balance += dailyBuySell_dailyProfits[counter]
        balance *= (1 + DAILY_INTEREST_RATE)
        dailyBuySell_dailyProfits[counter] += balance - (balance / (1 + DAILY_INTEREST_RATE))
        purchasedShares = 0
        counter+=1
    final_balance = balance
    profit = final_balance - starting_balance
    profit_percentage = profit / starting_balance
    summary = {
        'method': 'Daily trade',
        'ticker': ticker,
        'start': specific_period.index[0],
        'end': specific_period.index[-1],
        'starting_balance': starting_balance,
        'final_balance': final_balance,
        'profit': profit,
        'profit_percentage': profit_percentage
    }
    return dailyBuySell_dailyProfits, summary

#Method 2: Same as above, but only sell if the price is higher than open
def dailyBuySellSmart(specific_period, principal, ticker):
    balance = principal
    starting_balance = balance
    dailyBuySellSmart_dailyProfits = np.zeros(len(specific_period))
    counter = 0
    purchasedShares = 0
    pricePurchased = 0
    for index, row in specific_period.iterrows():
        if row['Open'] <= 0:
            dailyBuySellSmart_dailyProfits[counter] = 0
            counter+=1
            continue
        interest_earned = 0
        spent_and_regained = False
        if balance > 0:
            purchasedShares = balance/row['Open']
            pricePurchased = row['Open']
            balance = 0
        if(row['Close'] > row['Open']):
            balance = purchasedShares * row['Close']
            dailyBuySellSmart_dailyProfits[counter] = purchasedShares * (row['Close'] - pricePurchased)
            purchasedShares = 0
            spent_and_regained = True
        else:
            dailyBuySellSmart_dailyProfits[counter] = 0
        if spent_and_regained:
            interest_earned = balance * DAILY_INTEREST_RATE
            balance += interest_earned
            dailyBuySellSmart_dailyProfits[counter] += interest_earned
        counter+=1
    if purchasedShares > 0:
        final_price = specific_period['Close'].iloc[-1]
        balance = purchasedShares * final_price
        dailyBuySellSmart_dailyProfits[-1] += purchasedShares * (final_price - pricePurchased)
        purchasedShares = 0
    final_balance = balance
    profit = final_balance - starting_balance
    profit_percentage = profit / starting_balance
    summary = {
        'method': 'Smart daily trade',
        'ticker': ticker,
        'start': specific_period.index[0],
        'end': specific_period.index[-1],
        'starting_balance': starting_balance,
        'final_balance': final_balance,
        'profit': profit,
        'profit_percentage': profit_percentage
    }
    return dailyBuySellSmart_dailyProfits, summary

#Method 3: Use after hours data to determine trend for today:
#If the open price is higher than yesterday's close, then we should buy today if possible, and sell at close if profitable
#If the open price is lower than yesterday's close, then we should sell today if possible, and buy at close if profitable
#Do not do anything on first day. instead just use its closing price
#only acknowledge a trend as meaningful if it's a greater than 1% change
def trendTrade(specific_period, principal, ticker):
    balance = principal
    starting_balance = balance
    trendTrade_dailyProfits = np.zeros(len(specific_period))
    counter = 1
    prevClose = specific_period['Close'].iloc[0]
    purchasedShares = 0
    pricePurchased = 0
    for index, row in specific_period.iloc[1:].iterrows():
        if row['Open'] <= 0:
            trendTrade_dailyProfits[counter] = 0
            counter += 1
            continue
        interest_earned = 0
        spent_and_regained = False
        if row['Open'] > prevClose*1.01:
            if balance > 0:
                purchasedShares = balance/row['Open']
                pricePurchased = row['Open']
                balance = 0
                if row['Close'] > pricePurchased:
                    trendTrade_dailyProfits[counter] = purchasedShares * (row['Close'] - pricePurchased)
                    balance = purchasedShares*row['Close']
                    purchasedShares = 0
                    spent_and_regained = True
        elif row['Open'] < prevClose*0.99:
            if purchasedShares > 0:
                trendTrade_dailyProfits[counter] = purchasedShares * (row['Close'] - pricePurchased)
                balance = purchasedShares * row['Close']
                purchasedShares = 0
                spent_and_regained = True
                if row['Close'] < row['Open']:
                    purchasedShares = balance/row['Close']
                    pricePurchased = row['Close']
                    balance = 0
                    spent_and_regained = False
        if spent_and_regained:
            interest_earned = balance * DAILY_INTEREST_RATE
            balance += interest_earned
            trendTrade_dailyProfits[counter] += interest_earned
        prevClose = row['Close']
        counter += 1
    if purchasedShares > 0:
        final_price = specific_period['Close'].iloc[-1]
        trendTrade_dailyProfits[-1] = purchasedShares * (final_price - pricePurchased)
        purchasedShares = 0
        balance = purchasedShares * final_price
    final_balance = balance
    profit = final_balance - starting_balance
    profit_percentage = profit / starting_balance
    summary = {
        'method': 'Trend following',
        'ticker': ticker,
        'start': specific_period.index[0],
        'end': specific_period.index[-1],
        'starting_balance': starting_balance,
        'final_balance': final_balance,
        'profit': profit,
        'profit_percentage': profit_percentage
    }
    return trendTrade_dailyProfits, summary

#invest 1000 dollars at start
#See what the profit would be by selling at different times
#all we care about is final profit made at end of 10 year period
def passiveTrade(specific_period, principal, ticker):
    balance = principal
    starting_balance = balance
    initialPrice = specific_period['Open'].iloc[0]
    purchasedShares = balance/initialPrice
    passiveTrade_dailyProfits = np.zeros(len(specific_period))
    counter = 0
    interest_earned = balance * DAILY_INTEREST_RATE
    balance += interest_earned
    passiveTrade_dailyProfits[0] += interest_earned
    passiveTrade_dailyProfits[-1] = (specific_period['Close'].iloc[-1] - initialPrice) * purchasedShares
    balance = purchasedShares * specific_period['Close'].iloc[-1]
    final_balance = balance
    profit = final_balance - starting_balance
    profit_percentage = profit / starting_balance
    summary = {
        'method': 'Passive trade',
        'ticker': ticker,
        'start': specific_period.index[0],
        'end': specific_period.index[-1],
        'starting_balance': starting_balance,
        'final_balance': final_balance,
        'profit': profit,
        'profit_percentage': profit_percentage
    }
    return passiveTrade_dailyProfits, summary

def movingAverage60_strategy(specific_period, principal, ticker):
    balance = principal
    starting_balance = balance
    purchasedShares = 0
    pricePurchased = 0
    profits = np.zeros(len(specific_period))
    holding = False
    moving_avg = specific_period['Close'].rolling(window=60).mean()
    for i, (index, row) in enumerate(specific_period.iterrows()):
        if i < 59:
            interest_earned = balance * DAILY_INTEREST_RATE
            balance += interest_earned
            profits[i] += interest_earned
            continue
        ma = moving_avg.iloc[i]
        price = row['Close']
        interest_earned = 0
        if price > ma and not holding:
            purchasedShares = balance / price
            pricePurchased = price
            balance = 0
            holding = True
            profits[i] = 0
        elif price < ma and holding:
            proceeds = purchasedShares * price
            profits[i] = proceeds - (purchasedShares * pricePurchased)
            balance = proceeds
            purchasedShares = 0
            holding = False
            interest_earned = balance * DAILY_INTEREST_RATE
            balance += interest_earned
            profits[i] += interest_earned
        elif holding:
            profits[i] = 0
        elif not holding:
            interest_earned = balance * DAILY_INTEREST_RATE
            balance += interest_earned
            profits[i] += interest_earned
    if holding and purchasedShares > 0:
        final_price = specific_period['Close'].iloc[-1]
        profits[-1] += (final_price - pricePurchased) * purchasedShares
        balance = purchasedShares * final_price
        purchasedShares = 0
        holding = False
    final_balance = balance
    profit = final_balance - starting_balance
    profit_percentage = profit / starting_balance
    summary = {
        'method': '60-day MA',
        'ticker': ticker,
        'start': specific_period.index[0],
        'end': specific_period.index[-1],
        'starting_balance': starting_balance,
        'final_balance': final_balance,
        'profit': profit,
        'profit_percentage': profit_percentage
    }
    return profits, summary

def calculate_xirr(cashflows, dates):
    """
    Calculate XIRR using the pyxirr library.
    """
    # Convert dates to datetime.date
    dates = [pd.to_datetime(date).date() for date in dates]
    try:
        return pyxirr.xirr(dates, cashflows)
    except Exception as e:
        print(f"XIRR calculation failed: {e}")
        print(f"Cashflows: {cashflows}")
        print(f"Dates: {dates}")
        return None

def calculate_strategy_xirr(specific_period, daily_profits, initialInvestment):
    """
    Calculate XIRR for a trading strategy.
    
    XIRR (Extended Internal Rate of Return) calculates the annualized rate of return
    for a series of cashflows that occur at irregular intervals.
    
    For trading strategies:
    - Initial investment is a negative cashflow (money going out)
    - Final portfolio value is a positive cashflow (money coming in)
    - Intermediate cashflows (if any) represent additional investments or withdrawals
    
    Args:
        specific_period: DataFrame with trading data
        daily_profits: Array of daily profits/losses
        initialInvestment: Initial investment amount
    
    Returns:
        XIRR rate as a decimal (e.g., 0.15 for 15%) or None if calculation fails
    """
    # Calculate cumulative profits to get final portfolio value
    cumulative_profits = np.cumsum(daily_profits)
    final_value = initialInvestment + cumulative_profits[-1]
    
    # For XIRR, we need:
    # 1. Initial investment (negative cashflow)
    # 2. Final portfolio value (positive cashflow)
    cashflows = [-initialInvestment, final_value]
    dates = [specific_period.index[0], specific_period.index[-1]]
    
    # Calculate XIRR
    xirr_rate = calculate_xirr(cashflows, dates)
    
    return xirr_rate 