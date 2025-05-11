#!/usr/bin/env python3
"""
Morgan Stanley 10-Q Extractor
This script specifically targets the Morgan Stanley 10-Q filing we saw in the SEC feed.
"""

import os
import sys
import datetime
import logging
import json
from sec_feed_collector import (
    fetch_sec_feed, SEC_FEEDS, DATA_DIR, PROCESSED_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Target company info
MS_INFO = {
    "ticker": "MS",
    "company": "Morgan Stanley",
    "aliases": ["Morgan Stanley", "Morgan Stanley & Co", "Morgan Stanley Group"]
}

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(os.path.join(PROCESSED_DIR, "MS"), exist_ok=True)

def extract_morgan_stanley_10q():
    """Extract specifically the Morgan Stanley 10-Q filing"""
    # We're specifically focusing on the quarterly_reports feed
    feed_name = 'quarterly_reports'
    feed_url = SEC_FEEDS[feed_name]
    
    logger.info(f"Fetching SEC {feed_name} feed to locate Morgan Stanley 10-Q")
    feed = fetch_sec_feed(feed_name, feed_url)
    
    if not feed or not feed.entries:
        logger.error(f"Could not retrieve {feed_name} feed or feed has no entries")
        return 0
    
    filings_collected = 0
    ms_cik = "0000895421"  # Morgan Stanley's CIK number
    
    logger.info(f"Searching for Morgan Stanley (CIK: {ms_cik}) 10-Q in feed with {len(feed.entries)} entries")
    
    for entry in feed.entries:
        # Get the title which often contains the CIK and form type
        title = entry.get('title', '')
        logger.info(f"Checking entry: {title}")
        
        # Check if it's the Morgan Stanley 10-Q we're looking for
        if ms_cik in title and "10-Q" in title:
            logger.info(f"Found Morgan Stanley 10-Q: {title}")
            
            # Extract the filing data
            filing = {
                'ticker': "MS",
                'company': "Morgan Stanley",
                'title': title,
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'summary': entry.get('summary', ''),
                'content': str(entry.get('content', '')),
                'entry_id': entry.get('id', '') or datetime.datetime.now().isoformat(),
                'filing_type': "10-Q",
                'cik': ms_cik,
                'processed_date': datetime.datetime.now().isoformat()
            }
            
            # Create output path
            file_id = filing['entry_id'].split('/')[-1] if '/' in filing['entry_id'] else filing['entry_id']
            output_path = os.path.join(PROCESSED_DIR, "MS", f"MS_10Q_{file_id}.json")
            
            # Save the filing
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(filing, f, indent=2)
            
            logger.info(f"Successfully saved Morgan Stanley 10-Q to {output_path}")
            filings_collected += 1
            
            # Extract more data from the filing if available
            if hasattr(entry, 'edgar:xbrlFiling'):
                xbrl_data = getattr(entry, 'edgar:xbrlFiling')
                logger.info(f"XBRL data available: {xbrl_data}")
                
                # Save supplementary XBRL data if present
                xbrl_output_path = os.path.join(PROCESSED_DIR, "MS", f"MS_10Q_{file_id}_xbrl.json")
                with open(xbrl_output_path, 'w', encoding='utf-8') as f:
                    json.dump(str(xbrl_data), f, indent=2)
                
                logger.info(f"Saved supplementary XBRL data to {xbrl_output_path}")
    
    # If no filing found, provide a clear message
    if filings_collected == 0:
        logger.warning("Morgan Stanley 10-Q filing not found in the current SEC feed")
        
        # Create a report about our search
        search_report = {
            'search_date': datetime.datetime.now().isoformat(),
            'target': "Morgan Stanley 10-Q",
            'feed_searched': feed_name,
            'entries_examined': len(feed.entries),
            'success': False,
            'reason': "Target filing not found in current SEC feed"
        }
        
        report_path = os.path.join(PROCESSED_DIR, "MS", f"MS_search_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(search_report, f, indent=2)
            
        logger.info(f"Created search report at {report_path}")
        
        # Download a sample of other filings to examine the feed content
        sample_count = min(3, len(feed.entries))
        logger.info(f"Saving {sample_count} sample entries from feed for reference")
        
        samples = []
        for i in range(sample_count):
            sample_entry = feed.entries[i]
            sample = {
                'index': i,
                'title': sample_entry.get('title', ''),
                'link': sample_entry.get('link', ''),
                'id': sample_entry.get('id', '')
            }
            samples.append(sample)
        
        samples_path = os.path.join(PROCESSED_DIR, "MS", f"feed_samples_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(samples_path, 'w', encoding='utf-8') as f:
            json.dump(samples, f, indent=2)
            
        logger.info(f"Saved sample entries to {samples_path}")
    
    return filings_collected

def main():
    """Main function to extract Morgan Stanley 10-Q filing"""
    logger.info("Starting Morgan Stanley 10-Q extraction process")
    
    # Create directories
    ensure_directories()
    
    # Extract Morgan Stanley 10-Q
    filings_collected = extract_morgan_stanley_10q()
    
    # Print summary
    print("\n--- Morgan Stanley 10-Q Extraction Summary ---")
    print(f"Collection date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if filings_collected > 0:
        print(f"Successfully extracted {filings_collected} Morgan Stanley 10-Q filing(s)")
    else:
        print("No Morgan Stanley 10-Q filings found in the current SEC feed")
    
    # List the files saved
    ms_dir = os.path.join(PROCESSED_DIR, "MS")
    if os.path.exists(ms_dir):
        files = os.listdir(ms_dir)
        if files:
            print("\nFiles generated:")
            for file in files:
                print(f"  - {file}")
    
    return True

if __name__ == "__main__":
    main() 