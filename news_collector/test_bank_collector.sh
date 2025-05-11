#!/bin/bash
# Test script that downloads a few filings for JPMorgan Chase only

echo "Starting Test Bank SEC Filing Download"
echo "-------------------------------------"

# Create necessary directories if they don't exist
mkdir -p data/raw/sec
mkdir -p data/processed/sec

# Create a temporary custom collector for this test
cat > test_jpm_collector.py << 'EOL'
#!/usr/bin/env python3
"""
Test Bank SEC Filing Collector - JPMorgan Chase Only
This script extends the SEC feed collector to specifically target JPM.
"""

import os
import sys
import datetime
import logging
import json
from sec_feed_collector import (
    fetch_sec_feed, process_entry_for_company, save_company_filing,
    SEC_FEEDS, DATA_DIR, SEC_DIR, PROCESSED_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define JPMorgan Chase info
JPM_INFO = {
    "ticker": "JPM",
    "company": "JPMorgan Chase & Co.",
    "aliases": ["JPMorgan", "JPMorgan Chase", "JP Morgan", "Chase"]
}

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(SEC_DIR, exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_DIR, "JPM"), exist_ok=True)

def get_company_info(ticker=None):
    """Mock company info function that only returns JPM."""
    if ticker is None or ticker == "JPM":
        return JPM_INFO
    return None

def process_feeds_for_jpm(max_entries=5):
    """Process SEC feeds for JPMorgan Chase only."""
    # Fetch all feeds
    feeds = {}
    for feed_name, feed_url in SEC_FEEDS.items():
        feed = fetch_sec_feed(feed_name, feed_url)
        if feed and feed.entries:
            feeds[feed_name] = feed
    
    filings_collected = 0
    
    for feed_name, feed in feeds.items():
        logger.info(f"Processing {feed_name} feed for JPMorgan Chase")
        
        # Limit entries to process
        entries_to_process = feed.entries[:max_entries]
        
        for entry in entries_to_process:
            # Custom processing for JPM
            original_get_company_info = sys.modules.get('src.reference_data', None)
            
            try:
                # Temporarily replace the module
                class MockRefData:
                    @staticmethod
                    def get_company_info(ticker_arg=None):
                        return get_company_info(ticker_arg)
                
                sys.modules['src.reference_data'] = MockRefData
                
                # Process the entry
                processed_entry = process_entry_for_company(entry, "JPM")
                if processed_entry:
                    save_company_filing("JPM", processed_entry)
                    filings_collected += 1
            
            finally:
                # Restore original module if it existed
                if original_get_company_info:
                    sys.modules['src.reference_data'] = original_get_company_info
                else:
                    sys.modules.pop('src.reference_data', None)
    
    return filings_collected

def main():
    """Main function to test JPM filing collection."""
    logger.info("Starting JPMorgan Chase SEC filing test collection")
    
    # Create directories
    ensure_directories()
    
    # Process feeds for JPM
    filings_collected = process_feeds_for_jpm(max_entries=5)
    
    # Print summary
    print("\n--- JPMorgan Chase Filing Collection Summary ---")
    print(f"Collection date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total filings collected: {filings_collected}")
    
    return True

if __name__ == "__main__":
    main()
EOL

# Make the test collector executable
chmod +x test_jpm_collector.py

# Make sure we have all dependencies
pip install feedparser requests beautifulsoup4

# Run the test collector
echo ""
echo "Downloading a few SEC filings for JPMorgan Chase only..."
python test_jpm_collector.py

echo ""
echo "-------------------------------------"
echo "Test complete!"
echo "Check data/processed/sec/JPM/ for any JPMorgan Chase filings found" 