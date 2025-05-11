#!/usr/bin/env python3
"""
Bank SEC Filing Collector
This script extends the SEC feed collector to specifically target major global
and Canadian banks, downloading their regulatory filings from SEC.gov.
"""

import os
import sys
import datetime
import logging
import json
import argparse
from sec_feed_collector import (
    fetch_sec_feed, process_entry_for_company, save_company_filing,
    SEC_FEEDS, DATA_DIR, SEC_DIR, PROCESSED_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define major banks with their ticker symbols and aliases
GLOBAL_BANKS = {
    # US Banks
    "JPM": {
        "ticker": "JPM",
        "company": "JPMorgan Chase & Co.",
        "aliases": ["JPMorgan", "JPMorgan Chase", "JP Morgan", "Chase"]
    },
    "BAC": {
        "ticker": "BAC",
        "company": "Bank of America Corporation",
        "aliases": ["Bank of America", "BofA", "BoA"]
    },
    "C": {
        "ticker": "C",
        "company": "Citigroup Inc.",
        "aliases": ["Citigroup", "Citi", "Citibank"]
    },
    "WFC": {
        "ticker": "WFC",
        "company": "Wells Fargo & Company",
        "aliases": ["Wells Fargo", "Wells"]
    },
    "GS": {
        "ticker": "GS",
        "company": "Goldman Sachs Group Inc.",
        "aliases": ["Goldman Sachs", "Goldman", "Goldman Group"]
    },
    "MS": {
        "ticker": "MS",
        "company": "Morgan Stanley",
        "aliases": ["Morgan Stanley"]
    },
    # European Banks with ADRs
    "HSBC": {
        "ticker": "HSBC",
        "company": "HSBC Holdings plc",
        "aliases": ["HSBC", "HSBC Bank", "HSBC Holdings"]
    },
    "BCS": {
        "ticker": "BCS",
        "company": "Barclays PLC",
        "aliases": ["Barclays", "Barclays Bank"]
    },
    "DB": {
        "ticker": "DB",
        "company": "Deutsche Bank AG",
        "aliases": ["Deutsche Bank", "Deutsche"]
    },
    "UBS": {
        "ticker": "UBS",
        "company": "UBS Group AG",
        "aliases": ["UBS", "Union Bank of Switzerland"]
    },
    "CS": {
        "ticker": "CS",
        "company": "Credit Suisse Group AG",
        "aliases": ["Credit Suisse"]
    },
    # Asian Banks with ADRs
    "MUFG": {
        "ticker": "MUFG",
        "company": "Mitsubishi UFJ Financial Group, Inc.",
        "aliases": ["MUFG", "Mitsubishi UFJ", "Mitsubishi Bank"]
    },
    "SMFG": {
        "ticker": "SMFG",
        "company": "Sumitomo Mitsui Financial Group, Inc.",
        "aliases": ["SMFG", "Sumitomo Mitsui", "Sumitomo Bank"]
    },
    "IDCBY": {
        "ticker": "IDCBY",
        "company": "Industrial and Commercial Bank of China Limited",
        "aliases": ["ICBC", "Industrial and Commercial Bank of China"]
    },
    "MFG": {
        "ticker": "MFG",
        "company": "Mizuho Financial Group, Inc.",
        "aliases": ["Mizuho", "Mizuho Bank", "Mizuho Financial"]
    },
}

CANADIAN_BANKS = {
    "RY": {
        "ticker": "RY",
        "company": "Royal Bank of Canada",
        "aliases": ["Royal Bank", "RBC", "Royal Bank of Canada"]
    },
    "TD": {
        "ticker": "TD",
        "company": "The Toronto-Dominion Bank",
        "aliases": ["TD Bank", "Toronto-Dominion", "TD"]
    },
    "BNS": {
        "ticker": "BNS",
        "company": "The Bank of Nova Scotia",
        "aliases": ["Scotiabank", "Bank of Nova Scotia", "Scotia"]
    },
    "BMO": {
        "ticker": "BMO",
        "company": "Bank of Montreal",
        "aliases": ["BMO", "Bank of Montreal"]
    },
    "CM": {
        "ticker": "CM",
        "company": "Canadian Imperial Bank of Commerce",
        "aliases": ["CIBC", "Canadian Imperial", "Imperial Bank"]
    }
}

# Combine both dictionaries for processing
ALL_BANKS = {**GLOBAL_BANKS, **CANADIAN_BANKS}

def ensure_bank_directories():
    """Create necessary directories for bank data if they don't exist."""
    os.makedirs(SEC_DIR, exist_ok=True)
    
    # Create bank-specific directories
    for ticker in ALL_BANKS.keys():
        os.makedirs(os.path.join(PROCESSED_DIR, ticker), exist_ok=True)
    
    # Create separate directories for global and Canadian banks for easier access
    global_dir = os.path.join(PROCESSED_DIR, "global_banks")
    canadian_dir = os.path.join(PROCESSED_DIR, "canadian_banks")
    os.makedirs(global_dir, exist_ok=True)
    os.makedirs(canadian_dir, exist_ok=True)

def get_bank_info(ticker=None):
    """
    Get information for a specific bank or all banks.
    
    Args:
        ticker: Optional ticker symbol for a specific bank
        
    Returns:
        Dictionary with bank information or dict of all banks if ticker is None
    """
    if ticker:
        return ALL_BANKS.get(ticker)
    return ALL_BANKS

def process_feeds_for_banks(bank_type=None, filing_types=None, max_per_feed=100):
    """
    Process SEC feeds for selected banks.
    
    Args:
        bank_type: Optional filter for 'global' or 'canadian' banks
        filing_types: Optional list of filing types to filter for (e.g., ['8-K', '10-Q', '10-K'])
        max_per_feed: Maximum number of entries to process per feed
        
    Returns:
        Dictionary mapping bank tickers to number of filings collected
    """
    # Determine which banks to process
    banks_to_process = {}
    if bank_type == 'global':
        banks_to_process = GLOBAL_BANKS
    elif bank_type == 'canadian':
        banks_to_process = CANADIAN_BANKS
    else:
        banks_to_process = ALL_BANKS
    
    # Determine which feeds to process
    feeds_to_process = SEC_FEEDS
    if filing_types:
        feeds_to_process = {}
        for feed_name, feed_url in SEC_FEEDS.items():
            # Map feed names to filing types
            if feed_name == 'company_announcements' and '8-K' in filing_types:
                feeds_to_process[feed_name] = feed_url
            elif feed_name == 'quarterly_reports' and '10-Q' in filing_types:
                feeds_to_process[feed_name] = feed_url
            elif feed_name == 'annual_reports' and '10-K' in filing_types:
                feeds_to_process[feed_name] = feed_url
            elif feed_name in ['latest_filings', 'press_releases']:
                feeds_to_process[feed_name] = feed_url
    
    # Fetch all feeds
    feeds = {}
    for feed_name, feed_url in feeds_to_process.items():
        feed = fetch_sec_feed(feed_name, feed_url)
        if feed and feed.entries:
            feeds[feed_name] = feed
    
    # Process feeds for each bank
    results = {ticker: 0 for ticker in banks_to_process.keys()}
    
    for feed_name, feed in feeds.items():
        logger.info(f"Processing {feed_name} feed for {bank_type or 'all'} banks")
        
        # Limit number of entries to process per feed
        entries_to_process = feed.entries[:max_per_feed]
        
        for entry in entries_to_process:
            for ticker in banks_to_process.keys():
                # Custom processing for a bank requires us to mock the get_company_info function
                # that the SEC feed collector expects
                original_get_company_info = sys.modules.get('src.reference_data', None)
                
                try:
                    # Temporarily replace the module
                    class MockRefData:
                        @staticmethod
                        def get_company_info(ticker_arg=None):
                            if ticker_arg is None:
                                return get_bank_info()
                            return get_bank_info(ticker_arg)
                    
                    sys.modules['src.reference_data'] = MockRefData
                    
                    # Process the entry
                    processed_entry = process_entry_for_company(entry, ticker)
                    if processed_entry:
                        save_company_filing(ticker, processed_entry)
                        results[ticker] += 1
                        
                        # Create a symlink in the global/canadian directories for easier access
                        source_path = os.path.join(PROCESSED_DIR, ticker, f"{ticker}_{processed_entry['entry_id'].split('/')[-1]}.json")
                        if ticker in GLOBAL_BANKS:
                            link_path = os.path.join(PROCESSED_DIR, "global_banks", f"{ticker}_{processed_entry['entry_id'].split('/')[-1]}.json")
                        else:
                            link_path = os.path.join(PROCESSED_DIR, "canadian_banks", f"{ticker}_{processed_entry['entry_id'].split('/')[-1]}.json")
                        
                        # Only create symlink if the source exists and the link doesn't
                        if os.path.exists(source_path) and not os.path.exists(link_path):
                            try:
                                # On Windows, use a copy instead of a symlink
                                if os.name == 'nt':
                                    import shutil
                                    shutil.copy2(source_path, link_path)
                                else:
                                    os.symlink(source_path, link_path)
                            except Exception as e:
                                logger.warning(f"Could not create link for {ticker}: {e}")
                
                finally:
                    # Restore original module if it existed
                    if original_get_company_info:
                        sys.modules['src.reference_data'] = original_get_company_info
                    else:
                        sys.modules.pop('src.reference_data', None)
    
    # Log results
    logger.info("Filing collection completed")
    for ticker, count in results.items():
        if count > 0:
            bank_info = get_bank_info(ticker)
            logger.info(f"  {ticker} ({bank_info['company']}): {count} filings collected")
    
    return results

def main():
    """Main function to run the bank SEC feed collector."""
    parser = argparse.ArgumentParser(description='Download SEC filings for major banks')
    parser.add_argument('--global-only', action='store_true', help='Download only global bank filings')
    parser.add_argument('--canadian-only', action='store_true', help='Download only Canadian bank filings')
    parser.add_argument('--filing-types', nargs='+', choices=['8-K', '10-Q', '10-K'], 
                       help='Specific filing types to download (e.g., 8-K 10-Q 10-K)')
    parser.add_argument('--max-per-feed', type=int, default=100,
                       help='Maximum number of entries to process per feed')
    
    args = parser.parse_args()
    
    logger.info("Starting Bank SEC Feed Collector...")
    
    # Create directories
    ensure_bank_directories()
    
    # Determine bank type filter
    bank_type = None
    if args.global_only:
        bank_type = 'global'
    elif args.canadian_only:
        bank_type = 'canadian'
    
    # Process feeds
    start_time = datetime.datetime.now()
    results = process_feeds_for_banks(
        bank_type=bank_type, 
        filing_types=args.filing_types,
        max_per_feed=args.max_per_feed
    )
    end_time = datetime.datetime.now()
    
    # Create summary file
    summary = {
        'collection_date': datetime.datetime.now().isoformat(),
        'collection_duration': str(end_time - start_time),
        'bank_type': bank_type or 'all',
        'filing_types': args.filing_types,
        'banks': [
            {
                'ticker': ticker,
                'company': get_bank_info(ticker)['company'],
                'filings_collected': count
            }
            for ticker, count in results.items()
        ]
    }
    
    summary_path = os.path.join(SEC_DIR, f"bank_collection_summary_{datetime.datetime.now().strftime('%Y%m%d')}.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Collection summary saved to {summary_path}")
    
    # Print summary
    print("\n--- Bank SEC Filing Collection Summary ---")
    print(f"Collection date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Collection duration: {end_time - start_time}")
    print(f"Bank type: {bank_type or 'all'}")
    print(f"Filing types: {args.filing_types or 'all'}")
    print(f"Total filings collected: {sum(results.values())}")
    print("\nFilings by bank:")
    
    # Group by type for cleaner display
    print("\nGlobal Banks:")
    for ticker, count in sorted([(t, c) for t, c in results.items() if t in GLOBAL_BANKS], key=lambda x: x[1], reverse=True):
        if count > 0:
            company = get_bank_info(ticker)['company']
            print(f"  {ticker} ({company}): {count} filings")
    
    print("\nCanadian Banks:")
    for ticker, count in sorted([(t, c) for t, c in results.items() if t in CANADIAN_BANKS], key=lambda x: x[1], reverse=True):
        if count > 0:
            company = get_bank_info(ticker)['company']
            print(f"  {ticker} ({company}): {count} filings")
    
    return True

if __name__ == "__main__":
    main() 