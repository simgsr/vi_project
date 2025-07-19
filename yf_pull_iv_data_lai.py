import os
import sys
import csv
import yfinance as yf
import pandas as pd
from tabulate import tabulate
from tqdm import tqdm
import threading
from datetime import datetime

OUTPUT_DIR = './output_reports/'
LOG_FILE = 'financials_log.txt'
SUPPORTED_SUFFIXES = ['.HK', '.SS', '.SZ', '.KS', '.T', '.L', '.AX', '.TO',
                      '.V', '.SI', '.NZ', '.MI', '.PA', '.F', '.DE', '.ST',
                      '.HE', '.SW', '.MC', '']  # Add more as needed

lock = threading.Lock()  # For thread-safe list/dict updates

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def is_supported_ticker(ticker):
    return any(ticker.endswith(suffix) for suffix in SUPPORTED_SUFFIXES)

def validate_ticker(ticker):
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        if info.get('regularMarketPrice') is None:
            return False
        return True
    except Exception as e:
        log(f"[ERROR] Exception for ticker {ticker}: {e}")
        return False

def fetch_financial_data(ticker_symbol):
    try:
        # Initialize yFinance Ticker
        ticker = yf.Ticker(ticker_symbol)

        # Fetch financial statements (Income, Balance Sheet, Cash Flow)
        income_stmt = ticker.financials
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow

        # Fetch key metrics from 'info'
        info = ticker.info
        beta = info.get('beta', None)
        current_price = info.get('currentPrice', None)
        shares_outstanding = info.get('sharesOutstanding', None)
        market_cap = info.get('marketCap', None)
        pe_ratio = info.get('trailingPE', None)
        forward_pe = info.get('forwardPE', None)
        dividend_rate = info.get('dividendRate', None)
        dividend_yield = info.get('dividendYield', None)
        roe = info.get('returnOnEquity', None)

        # Get financial metrics from statements
        free_cash_flow = cash_flow.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cash_flow.index else None
        net_income = income_stmt.loc['Net Income'].iloc[0] if 'Net Income' in income_stmt.index else None
        shares_outstanding_stmt = balance_sheet.loc['Share Issued'].iloc[0] if 'Share Issued' in balance_sheet.index else shares_outstanding
        eps = income_stmt.loc['Basic EPS'].iloc[0] if 'Basic EPS' in income_stmt.index else None
        total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else None
        total_equity = balance_sheet.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in balance_sheet.index else None
        bvps = total_equity / shares_outstanding_stmt if total_equity is not None and shares_outstanding_stmt is not None else None

        # Fetch historical data for the last 3 years
        current_year = datetime.now().year
        hist = ticker.history(start=f"{current_year - 3}-01-01", end=f"{current_year}-01-01")
        last_three_years_close = hist['Close'].iloc[-1]  # Last available close price from the last 3 years

        # Compile key metrics into summary DataFrame
        summary_data = {
            "Beta (β)": beta,
            "Current Price": current_price,
            "Market Cap": market_cap,
            "P/E Ratio": pe_ratio,
            "Forward P/E": forward_pe,
            "Dividend Rate": dividend_rate,
            "Dividend Yield": dividend_yield,
            "ROE": roe,
            "Free Cash Flow (FCF)": free_cash_flow,
            "Net Income": net_income,
            "Shares Outstanding": shares_outstanding_stmt,
            "EPS": eps,
            "Total Debt": total_debt,
            "Total Equity": total_equity,
            "BVPS": bvps,
            "Last 3 Years Close Price": last_three_years_close
        }

        # Convert to DataFrame with scalar values
        df = pd.DataFrame(list(summary_data.items()), columns=['Metric', 'Value'])
        df['Value'] = df['Value'].apply(lambda x: round(x, 2) if isinstance(x, (int, float)) else x)
        return df

    except Exception as e:
        log(f"[ERROR] fetch_financial_data for {ticker_symbol}: {e}")
        return None

def print_table(financial_data, ticker):
    print(f"\nFinancial Summary for {ticker}")
    # Convert DataFrame to list of lists for tabulate
    table_data = financial_data.values.tolist()
    print(tabulate(table_data, headers=['Metric', 'Value'], tablefmt="grid"))

def export_to_csv(ticker, financial_data):
    file_path = os.path.join(OUTPUT_DIR, f"{ticker}_financials.csv")
    financial_data.to_csv(file_path, index=False)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <ticker>")
        sys.exit(1)

    ticker = sys.argv[1]

    financial_data = fetch_financial_data(ticker)
    if financial_data is not None:
        print_table(financial_data, ticker)
        export_to_csv(ticker, financial_data)
    else:
        print("Failed to fetch financial data.")

if __name__ == "__main__":
    main()
