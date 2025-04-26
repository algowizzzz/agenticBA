import sqlite3
import pandas as pd
import logging
import os

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "data", "financial_data.db") # Relative path to DB
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, "db_verification_log.txt") # Log file in the same dir as script
EXPECTED_TICKERS = sorted(['AAPL', 'AMD', 'AMZN', 'ASML', 'CSCO', 'GOOGL', 'INTC', 'MSFT', 'MU', 'NVDA'])

# --- Logging Setup ---
log_formatter = logging.Formatter('%(levelname)s: %(message)s')
logger = logging.getLogger() # Get root logger
logger.setLevel(logging.INFO)

# Clear existing handlers (if any)
if logger.hasHandlers():
    logger.handlers.clear()
    
# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# File Handler
try:
    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='w') # Overwrite log each time
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    print(f"INFO: Logging verification results to: {LOG_FILE_PATH}") # Print info about log file
except Exception as e:
    print(f"ERROR: Could not set up file logger: {e}")

def run_query(conn, query, params=None):
    """ Helper function to run a query and fetch all results """
    # Log the query and parameters before execution
    log_message = f"Executing query: {query}"
    if params:
        log_message += f" | Params: {params}"
    logging.info(log_message)
    
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Query failed: {query} | Error: {e}")
        return None
    finally:
        if cursor:
            cursor.close()

def verify_database(db_path):
    """ Runs verification queries against the database """
    if not os.path.exists(db_path):
        logging.error(f"Database file not found at {db_path}")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        logging.info(f"Connected to database: {db_path}")

        # --- Verification Queries ---
        logging.info("\n--- Running Verification Queries ---")

        # 1. Company Count & List
        logging.info("\n1. Checking Companies...")
        companies = run_query(conn, "SELECT ticker FROM companies ORDER BY ticker")
        if companies is not None:
            company_list = [c[0] for c in companies]
            logging.info(f"  Found {len(company_list)} companies.")
            if company_list == EXPECTED_TICKERS:
                logging.info(f"  PASS: Company list matches expected tickers.")
            else:
                logging.warning(f"  FAIL: Company list mismatch! Expected: {EXPECTED_TICKERS}, Found: {company_list}")
        else:
             logging.warning("  FAIL: Could not query companies table.")

        # 2. Stock Price Count per Ticker
        logging.info("\n2. Checking Stock Price Counts...")
        price_counts = run_query(conn, "SELECT ticker, COUNT(*) FROM daily_stock_prices GROUP BY ticker ORDER BY ticker")
        if price_counts is not None:
            logging.info(f"  Stock price rows per ticker:")
            all_counts_good = True
            for ticker, count in price_counts:
                logging.info(f"    {ticker}: {count}")
                if count < 1000: # Expecting >1000 days for 2016-2020
                    logging.warning(f"    WARN: Low row count for {ticker}.")
                    all_counts_good = False
            if all_counts_good:
                 logging.info("  PASS: Stock price counts seem reasonable.")
        else:
             logging.warning("  FAIL: Could not query stock prices.")

        # 3. Dividend Check
        logging.info("\n3. Checking Dividends...")
        aapl_div = run_query(conn, "SELECT COUNT(*) FROM dividends WHERE ticker = ?", ('AAPL',))
        googl_div = run_query(conn, "SELECT COUNT(*) FROM dividends WHERE ticker = ?", ('GOOGL',))
        if aapl_div is not None and googl_div is not None:
            logging.info(f"  AAPL dividend entries: {aapl_div[0][0]}")
            logging.info(f"  GOOGL dividend entries: {googl_div[0][0]}")
            if aapl_div[0][0] > 0 and googl_div[0][0] == 0:
                logging.info("  PASS: Dividend counts look correct for samples.")
            else:
                logging.warning("  FAIL: Dividend counts unexpected for samples.")
        else:
            logging.warning("  FAIL: Could not query dividends table.")
            
        # 4. Stock Split Check (AAPL 2020)
        logging.info("\n4. Checking Stock Splits...")
        aapl_split = run_query(conn, "SELECT date, split_ratio FROM stock_splits WHERE ticker = ? AND date LIKE '2020-%'", ('AAPL',))
        if aapl_split is not None:
            if len(aapl_split) == 1 and aapl_split[0][0] == '2020-08-31' and aapl_split[0][1] == '4.0':
                 logging.info(f"  Found AAPL split: {aapl_split}")
                 logging.info("  PASS: AAPL 2020 split correctly recorded.")
            else:
                 logging.warning(f"  FAIL: AAPL 2020 split data incorrect or missing. Found: {aapl_split}")
        else:
             logging.warning("  FAIL: Could not query stock splits table.")
             
        # 5. Quarterly Financials Count Check
        logging.info("\n5. Checking Quarterly Financials Counts...")
        income_counts = run_query(conn, "SELECT ticker, COUNT(*) FROM quarterly_income_statement GROUP BY ticker ORDER BY ticker")
        balance_counts = run_query(conn, "SELECT ticker, COUNT(*) FROM quarterly_balance_sheet GROUP BY ticker ORDER BY ticker")
        if income_counts is not None and balance_counts is not None:
            logging.info("  Quarterly Income Statement row counts:")
            for ticker, count in income_counts:
                logging.info(f"    {ticker}: {count}")
            logging.info("  Quarterly Balance Sheet row counts:")
            for ticker, count in balance_counts:
                logging.info(f"    {ticker}: {count}")
            # Simple check if counts are non-zero and roughly similar
            if len(income_counts) == len(EXPECTED_TICKERS) and len(balance_counts) == len(EXPECTED_TICKERS):
                 logging.info("  PASS: Quarterly report counts seem reasonable.")
            else:
                 logging.warning("  FAIL: Unexpected number of tickers found in quarterly reports.")
        else:
            logging.warning("  FAIL: Could not query quarterly financials tables.")
            
        # 6. Sample Financial Data Check
        logging.info("\n6. Checking Sample Quarterly Financial Data (NVDA 2024-07-31 report)...")
        nvda_income = run_query(conn, "SELECT total_revenue, net_income FROM quarterly_income_statement WHERE ticker = ? AND report_date = ?", ('NVDA', '2024-07-31'))
        nvda_balance = run_query(conn, "SELECT total_assets, stockholders_equity FROM quarterly_balance_sheet WHERE ticker = ? AND report_date = ?", ('NVDA', '2024-07-31'))
        if nvda_income and nvda_balance:
             logging.info(f"  NVDA Income (Revenue, Net Income): {nvda_income[0]}")
             logging.info(f"  NVDA Balance (Assets, Equity): {nvda_balance[0]}")
             # Check if the primary values are not None
             if nvda_income[0][0] is not None and nvda_balance[0][0] is not None:
                  logging.info("  PASS: Sample NVDA financial data found.")
             else:
                  logging.warning("  FAIL: Sample NVDA financial data values are missing/Null.")
        else:
             # Check if the query execution failed or just returned no rows
             if nvda_income is None or nvda_balance is None:
                 logging.warning("  FAIL: Could not execute query for sample NVDA financial data.")
             else:
                 logging.warning(f"  FAIL: No NVDA financial data found for report_date = '2024-07-31'.")

        logging.info("\n--- Verification Finished ---")

    except sqlite3.Error as e:
        logging.error(f"Database error during verification: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

# --- Main Execution ---
if __name__ == "__main__":
    # Log initial message
    logger.info("Starting database verification...")
    verify_database(DB_PATH)
    logger.info("Verification script finished.") 