import sqlite3
import datetime
import os

# --- Configuration ---
DB_FILENAME = "ccr_reporting.db"

# --- Schema Definition ---
SCHEMA_SQL = """
DROP TABLE IF EXISTS report_limit_utilization;
DROP TABLE IF EXISTS report_daily_exposures;
DROP TABLE IF EXISTS report_limits;
DROP TABLE IF EXISTS report_products;
DROP TABLE IF EXISTS report_counterparties;

CREATE TABLE report_counterparties (
    counterparty_id BIGINT PRIMARY KEY,
    counterparty_legal_name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100),
    region VARCHAR(50),
    country_of_domicile VARCHAR(3),
    internal_rating VARCHAR(10),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE report_products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    product_type VARCHAR(100),
    asset_class VARCHAR(50),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE report_limits (
    report_limit_id BIGINT PRIMARY KEY,
    counterparty_id BIGINT NOT NULL REFERENCES report_counterparties(counterparty_id),
    limit_type VARCHAR(100) NOT NULL,
    limit_amount DECIMAL(22, 4) NOT NULL,
    limit_currency VARCHAR(3) NOT NULL,
    limit_effective_date DATE NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE report_daily_exposures (
    exposure_snapshot_id BIGINT PRIMARY KEY,
    report_date DATE NOT NULL,
    counterparty_id BIGINT NOT NULL REFERENCES report_counterparties(counterparty_id),
    exposure_type VARCHAR(100) NOT NULL,
    exposure_amount DECIMAL(22, 4) NOT NULL,
    exposure_currency VARCHAR(3) NOT NULL,
    calculation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Optional: Add product_id BIGINT REFERENCES report_products(product_id)
);

CREATE TABLE report_limit_utilization (
    utilization_snapshot_id BIGINT PRIMARY KEY,
    report_date DATE NOT NULL,
    counterparty_id BIGINT NOT NULL REFERENCES report_counterparties(counterparty_id),
    limit_type VARCHAR(100) NOT NULL,
    exposure_amount DECIMAL(22, 4),
    exposure_currency VARCHAR(3),
    limit_amount DECIMAL(22, 4),
    limit_currency VARCHAR(3),
    limit_utilization_percent DECIMAL(7, 4),
    limit_breach_status VARCHAR(20) NOT NULL,
    calculation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# --- Sample Data ---
# Using a fixed date for consistency in linked data
TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)
LAST_YEAR = TODAY - datetime.timedelta(days=365)

counterparties_data = [
    (101, 'Hedge Fund Alpha Inc.', 'HF Alpha', 'North America', 'USA', 'A-', TODAY.isoformat()),
    (102, 'Global Pension Plan Beta', 'Pension B', 'North America', 'CAN', 'AA', TODAY.isoformat()),
    (103, 'European Bank Gamma', 'EuroBank G', 'Europe', 'DEU', 'A+', TODAY.isoformat()),
    (104, 'Sovereign Wealth Fund Delta', 'SWF Delta', 'Asia', 'SGP', 'AAA', TODAY.isoformat()),
    (105, 'Regional Bank Epsilon', 'Region E', 'North America', 'USA', 'BBB+', TODAY.isoformat())
]

products_data = [
    (5001, 'USD/CAD FX Spot', 'FX Spot', 'FX', TODAY.isoformat()),
    (5002, 'USD/CAD FX Forward 3M', 'FX Forward', 'FX', TODAY.isoformat()),
    (5003, 'CAD IRS 5Y Fixed Receive', 'Interest Rate Swap', 'Rates', TODAY.isoformat()),
    (5004, 'AAPL Equity Option Call ExpDec24', 'Equity Option', 'Equity', TODAY.isoformat()),
    (5005, 'Govt of Canada Bond 2.5% 2030', 'Government Bond', 'Fixed Income', TODAY.isoformat()),
    (5006, 'US Treasury Bond 3.0% 2034', 'Government Bond', 'Fixed Income', TODAY.isoformat())
]

# Limits for counterparties
limits_data = [
    # HF Alpha (101)
    (2001, 101, 'Net MTM', 5000000.00, 'USD', LAST_YEAR.isoformat(), TODAY.isoformat()),
    (2002, 101, 'Settlement Risk', 10000000.00, 'USD', LAST_YEAR.isoformat(), TODAY.isoformat()),
    # Pension B (102)
    (2003, 102, 'Gross Exposure', 150000000.00, 'CAD', LAST_YEAR.isoformat(), TODAY.isoformat()),
    (2004, 102, 'PFE 95%', 25000000.00, 'CAD', LAST_YEAR.isoformat(), TODAY.isoformat()),
    # EuroBank G (103)
    (2005, 103, 'Net MTM', 20000000.00, 'EUR', LAST_YEAR.isoformat(), TODAY.isoformat()),
    (2006, 103, 'Settlement Risk', 50000000.00, 'EUR', LAST_YEAR.isoformat(), TODAY.isoformat()),
    # SWF Delta (104)
    (2007, 104, 'Gross Exposure', 500000000.00, 'USD', LAST_YEAR.isoformat(), TODAY.isoformat()),
    # Region E (105)
    (2008, 105, 'Net MTM', 2500000.00, 'USD', LAST_YEAR.isoformat(), TODAY.isoformat())
]

# Exposures calculated for YESTERDAY's date
exposures_data = [
    # HF Alpha (101)
    (3001, YESTERDAY.isoformat(), 101, 'Net MTM', 4500000.00, 'USD', TODAY.isoformat()), # High Util
    (3002, YESTERDAY.isoformat(), 101, 'Settlement Risk', 8000000.00, 'USD', TODAY.isoformat()), # OK Util
    # Pension B (102)
    (3003, YESTERDAY.isoformat(), 102, 'Gross Exposure', 90000000.00, 'CAD', TODAY.isoformat()), # OK Util
    (3004, YESTERDAY.isoformat(), 102, 'PFE 95%', 15000000.00, 'CAD', TODAY.isoformat()), # OK Util
    # EuroBank G (103)
    (3005, YESTERDAY.isoformat(), 103, 'Net MTM', 21000000.00, 'EUR', TODAY.isoformat()), # Breach!
    (3006, YESTERDAY.isoformat(), 103, 'Settlement Risk', 15000000.00, 'EUR', TODAY.isoformat()), # OK Util
    # SWF Delta (104)
    (3007, YESTERDAY.isoformat(), 104, 'Gross Exposure', 300000000.00, 'USD', TODAY.isoformat()), # OK Util
    # Region E (105)
    (3008, YESTERDAY.isoformat(), 105, 'Net MTM', 2400000.00, 'USD', TODAY.isoformat()) # Advisory Breach?
]

# Utilization calculated based on YESTERDAY's exposures and active limits
# Note: Assumes currency matches or conversion happened prior to this step
utilization_data = [
    # HF Alpha (101) - Net MTM (High Util)
    (4001, YESTERDAY.isoformat(), 101, 'Net MTM', 4500000.00, 'USD', 5000000.00, 'USD', 90.0000, 'Advisory Breach', TODAY.isoformat()),
    # HF Alpha (101) - Settlement Risk (OK Util)
    (4002, YESTERDAY.isoformat(), 101, 'Settlement Risk', 8000000.00, 'USD', 10000000.00, 'USD', 80.0000, 'OK', TODAY.isoformat()),
    # Pension B (102) - Gross Exposure (OK Util)
    (4003, YESTERDAY.isoformat(), 102, 'Gross Exposure', 90000000.00, 'CAD', 150000000.00, 'CAD', 60.0000, 'OK', TODAY.isoformat()),
    # Pension B (102) - PFE 95% (OK Util)
    (4004, YESTERDAY.isoformat(), 102, 'PFE 95%', 15000000.00, 'CAD', 25000000.00, 'CAD', 60.0000, 'OK', TODAY.isoformat()),
     # EuroBank G (103) - Net MTM (Breach!)
    (4005, YESTERDAY.isoformat(), 103, 'Net MTM', 21000000.00, 'EUR', 20000000.00, 'EUR', 105.0000, 'Hard Breach', TODAY.isoformat()),
    # EuroBank G (103) - Settlement Risk (OK Util)
    (4006, YESTERDAY.isoformat(), 103, 'Settlement Risk', 15000000.00, 'EUR', 50000000.00, 'EUR', 30.0000, 'OK', TODAY.isoformat()),
    # SWF Delta (104) - Gross Exposure (OK Util)
    (4007, YESTERDAY.isoformat(), 104, 'Gross Exposure', 300000000.00, 'USD', 500000000.00, 'USD', 60.0000, 'OK', TODAY.isoformat()),
    # Region E (105) - Net MTM (Advisory Breach)
    (4008, YESTERDAY.isoformat(), 105, 'Net MTM', 2400000.00, 'USD', 2500000.00, 'USD', 96.0000, 'Advisory Breach', TODAY.isoformat())
]

# --- Database Creation and Population ---
def create_and_populate_db():
    """Creates the SQLite DB, defines the schema, and populates tables."""
    # Remove existing DB file if it exists
    if os.path.exists(DB_FILENAME):
        os.remove(DB_FILENAME)
        print(f"Removed existing database file: {DB_FILENAME}")

    conn = None
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        print(f"Database file created: {DB_FILENAME}")

        # Create Tables
        cursor.executescript(SCHEMA_SQL)
        print("Schema created successfully.")

        # Insert Data
        cursor.executemany("INSERT INTO report_counterparties VALUES (?, ?, ?, ?, ?, ?, ?)", counterparties_data)
        print(f"Inserted {len(counterparties_data)} rows into report_counterparties.")

        cursor.executemany("INSERT INTO report_products VALUES (?, ?, ?, ?, ?)", products_data)
        print(f"Inserted {len(products_data)} rows into report_products.")

        cursor.executemany("INSERT INTO report_limits VALUES (?, ?, ?, ?, ?, ?, ?)", limits_data)
        print(f"Inserted {len(limits_data)} rows into report_limits.")

        cursor.executemany("INSERT INTO report_daily_exposures VALUES (?, ?, ?, ?, ?, ?, ?)", exposures_data)
        print(f"Inserted {len(exposures_data)} rows into report_daily_exposures.")

        cursor.executemany("INSERT INTO report_limit_utilization VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", utilization_data)
        print(f"Inserted {len(utilization_data)} rows into report_limit_utilization.")

        # Commit changes
        conn.commit()
        print("Data committed successfully.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        # Rollback changes if error occurs
        if conn:
            conn.rollback()
            print("Changes rolled back.")
    finally:
        # Close connection
        if conn:
            conn.close()
            print("Database connection closed.")

# --- Main Execution ---
if __name__ == "__main__":
    create_and_populate_db() 