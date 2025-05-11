#!/usr/bin/env python3
"""
Sample the first 200 records from a WARC file to get a quick overview.
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

def sample_warc_file(warc_path, max_records=200):
    """
    Sample the first N records from a WARC file.
    
    Args:
        warc_path: Path to the WARC file
        max_records: Maximum number of records to process
    
    Returns:
        Dictionary with analysis results
    """
    total_records = 0
    html_records = 0
    domains = {}
    dates = set()
    microsoft_urls = []
    
    # Date pattern for finding publication dates in HTML
    date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')
    
    with open(warc_path, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if total_records >= max_records:
                break
                
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
                # Read content (just start of HTML to check for dates & Microsoft mentions)
                html_content = record.content_stream().read(50000).decode('utf-8', errors='replace')
                
                # Check for Microsoft mentions
                if re.search(r'\b(microsoft|msft)\b', html_content.lower()):
                    microsoft_urls.append(url)
                
                # Get dates
                date_matches = date_pattern.findall(html_content)
                for date_str in date_matches:
                    try:
                        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        if 2020 <= date.year <= 2026:  # Only consider recent dates
                            dates.add(date.isoformat())
                    except ValueError:
                        pass
                        
            except Exception as e:
                logger.debug(f"Error processing record: {e}")
    
    # Calculate top domains
    top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Calculate date range
    date_list = sorted(list(dates))
    date_range = f"From {date_list[0]} to {date_list[-1]}" if date_list else "Unknown"
    
    results = {
        "total_records_sampled": total_records,
        "html_records": html_records,
        "microsoft_mentions": len(microsoft_urls),
        "top_domains": top_domains,
        "date_range": date_range,
        "unique_dates": len(dates),
        "microsoft_urls": microsoft_urls[:5]  # Only include first 5 URLs
    }
    
    return results

def main():
    """Main function to sample a WARC file."""
    warc_dir = "data/raw/ccnews"
    
    # Find the most recent WARC file
    warc_files = [f for f in os.listdir(warc_dir) if f.endswith('.warc.gz')]
    if not warc_files:
        logger.error(f"No WARC files found in {warc_dir}")
        return
    
    warc_files.sort(reverse=True)
    warc_path = os.path.join(warc_dir, warc_files[0])
    
    logger.info(f"Sampling WARC file: {warc_path}")
    
    # Sample
    results = sample_warc_file(warc_path)
    
    # Print results
    print("\n=== WARC Sample Analysis ===")
    print(f"File: {os.path.basename(warc_path)}")
    print(f"Records sampled: {results['total_records_sampled']}")
    print(f"HTML records: {results['html_records']}")
    print(f"Microsoft mentions: {results['microsoft_mentions']} URLs")
    print(f"Date range found: {results['date_range']}")
    print(f"Unique dates found: {results['unique_dates']}")
    
    print("\nTop domains:")
    for domain, count in results['top_domains']:
        print(f"  {domain}: {count} articles")
    
    print("\nSample Microsoft URLs:")
    for url in results['microsoft_urls']:
        print(f"  {url}")
    
    # Save results
    output_file = os.path.join(warc_dir, "sample_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        # Convert to serializable format
        serializable_results = results.copy()
        serializable_results['top_domains'] = [[domain, count] for domain, count in results['top_domains']]
        json.dump(serializable_results, f, indent=2)
    
    logger.info(f"Sample analysis results saved to {output_file}")

if __name__ == "__main__":
    main() 