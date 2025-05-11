#!/usr/bin/env python3
"""
Quick analysis of a WARC file to check for Microsoft mentions and date ranges.
"""

import os
import json
import datetime
from urllib.parse import urlparse
from warcio.archiveiterator import ArchiveIterator
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def quick_analyze_warc(warc_path):
    """
    Quickly analyze a WARC file to extract basic stats about Microsoft mentions and dates.
    
    Args:
        warc_path: Path to the WARC file
    
    Returns:
        Dictionary with analysis results
    """
    total_records = 0
    html_records = 0
    microsoft_mentions = 0
    domains = {}
    dates = []
    
    earliest_date = None
    latest_date = None
    
    # Patterns for finding dates in HTML
    date_patterns = [
        r'datetime="(\d{4}-\d{2}-\d{2})',
        r'pubdate="(\d{4}-\d{2}-\d{2})',
        r'date="(\d{4}-\d{2}-\d{2})',
        r'<time[^>]*>(\d{4}-\d{2}-\d{2})',
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'
    ]
    compiled_patterns = [re.compile(pattern) for pattern in date_patterns]
    
    with open(warc_path, 'rb') as stream:
        for record in ArchiveIterator(stream):
            total_records += 1
            
            # Only process response records
            if record.rec_type != 'response':
                continue
                
            # Get content type and URL
            content_type = record.http_headers.get_header('Content-Type', '')
            url = record.rec_headers.get_header('WARC-Target-URI', '')
            
            if 'text/html' not in content_type or not url:
                continue
                
            html_records += 1
            
            # Get domain
            domain = urlparse(url).netloc
            domains[domain] = domains.get(domain, 0) + 1
            
            try:
                # Read content
                html_content = record.content_stream().read().decode('utf-8', errors='replace')
                
                # Check for Microsoft mentions
                if re.search(r'\b(microsoft|msft)\b', html_content.lower()):
                    microsoft_mentions += 1
                    if microsoft_mentions <= 5:  # Print first 5 URLs with Microsoft mentions
                        logger.info(f"Microsoft mention found in: {url}")
                
                # Extract dates from HTML
                for pattern in compiled_patterns:
                    matches = pattern.findall(html_content)
                    for match in matches:
                        try:
                            # Convert to date object
                            if 'T' in match:
                                # ISO format with time
                                match = match.split('T')[0]
                            
                            date_obj = datetime.datetime.strptime(match, '%Y-%m-%d').date()
                            
                            # Only consider reasonable dates (not in the distant past or future)
                            if date_obj.year > 2015 and date_obj.year < 2026:
                                dates.append(date_obj)
                                
                                # Update earliest and latest
                                if earliest_date is None or date_obj < earliest_date:
                                    earliest_date = date_obj
                                if latest_date is None or date_obj > latest_date:
                                    latest_date = date_obj
                                    
                                break  # Only need one date per pattern
                        except ValueError:
                            # Invalid date format
                            continue
                            
            except Exception as e:
                logger.debug(f"Error processing record: {e}")
            
            # Print progress
            if total_records % 100 == 0:
                logger.info(f"Processed {total_records} records, found {microsoft_mentions} Microsoft mentions")
    
    # Calculate top domains
    top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Calculate date range
    date_range = "Unknown"
    if earliest_date and latest_date:
        date_range = f"From {earliest_date.isoformat()} to {latest_date.isoformat()}"
    
    # Calculate unique dates
    unique_dates = len(set(dates))
    
    results = {
        "total_records": total_records,
        "html_records": html_records,
        "microsoft_mentions": microsoft_mentions,
        "microsoft_percentage": round((microsoft_mentions / html_records) * 100, 2) if html_records > 0 else 0,
        "top_domains": top_domains,
        "date_range": date_range,
        "unique_dates": unique_dates
    }
    
    return results

def main():
    """Main function to run the quick analysis."""
    warc_dir = "data/raw/ccnews"
    
    # Find the most recent WARC file
    warc_files = [f for f in os.listdir(warc_dir) if f.endswith('.warc.gz')]
    if not warc_files:
        logger.error(f"No WARC files found in {warc_dir}")
        return
    
    warc_files.sort(reverse=True)
    warc_path = os.path.join(warc_dir, warc_files[0])
    
    logger.info(f"Quick analyzing WARC file: {warc_path}")
    
    # Analyze
    results = quick_analyze_warc(warc_path)
    
    # Print results
    print("\n=== WARC Quick Analysis ===")
    print(f"File: {os.path.basename(warc_path)}")
    print(f"Total records: {results['total_records']}")
    print(f"HTML records: {results['html_records']}")
    print(f"Microsoft mentions: {results['microsoft_mentions']} ({results['microsoft_percentage']}% of HTML records)")
    print(f"Date range: {results['date_range']}")
    print(f"Unique dates found: {results['unique_dates']}")
    
    print("\nTop 10 Domains:")
    for domain, count in results['top_domains']:
        print(f"  {domain}: {count} articles")
    
    # Save results
    output_file = os.path.join(warc_dir, "quick_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        # Convert to serializable format
        serializable_results = results.copy()
        serializable_results['top_domains'] = [[domain, count] for domain, count in results['top_domains']]
        json.dump(serializable_results, f, indent=2)
    
    logger.info(f"Quick analysis results saved to {output_file}")

if __name__ == "__main__":
    main() 