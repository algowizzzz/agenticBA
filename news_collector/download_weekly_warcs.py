#!/usr/bin/env python3
"""
Download the past 7 days of WARC files from Common Crawl's CC-NEWS dataset.
This script identifies and downloads WARC files from the past week.
"""

import os
import sys
import datetime
import logging
import time
import requests
from bs4 import BeautifulSoup
import concurrent.futures

# Add src directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RAW_DIR = os.path.join(DATA_DIR, "raw", "ccnews")
CC_NEWS_BASE_URL = "https://data.commoncrawl.org/crawl-data/CC-NEWS/"

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(RAW_DIR, exist_ok=True)

def get_date_ranges(days=7):
    """
    Get date ranges for dates in 2023 (since we're in a future date context).
    
    Args:
        days: Number of days to look back
        
    Returns:
        List of (year, month, day) tuples 
    """
    # Use dates from 2023 (real available data)
    base_date = datetime.datetime(2023, 4, 15)  # April 15, 2023
    date_ranges = []
    
    for i in range(days):
        date = base_date - datetime.timedelta(days=i)
        date_ranges.append((date.year, date.month, date.day))
        
    return date_ranges

def get_warc_urls_for_date(year, month, day):
    """
    Get WARC file URLs for a specific date.
    
    Args:
        year: Year (YYYY)
        month: Month (MM)
        day: Day (DD)
        
    Returns:
        List of WARC file URLs for that date
    """
    # Format the path in CC-NEWS archive
    date_path = f"{year}/{month:02d}/"
    date_prefix = f"CC-NEWS-{year}{month:02d}{day:02d}"
    index_url = CC_NEWS_BASE_URL + date_path
    
    logger.info(f"Fetching WARC file list from {index_url} for {year}-{month:02d}-{day:02d}")
    
    try:
        response = requests.get(index_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')
        
        warc_files = []
        for link in links:
            href = link.get('href')
            if href and href.endswith('.warc.gz') and date_prefix in href:
                warc_url = index_url + href
                warc_files.append(warc_url)
        
        logger.info(f"Found {len(warc_files)} WARC files for {year}-{month:02d}-{day:02d}")
        return warc_files
        
    except Exception as e:
        logger.error(f"Error fetching WARC file listing for {year}-{month:02d}-{day:02d}: {e}")
        return []

def download_warc_file(warc_url):
    """
    Download a WARC file using direct HTTP request.
    
    Args:
        warc_url: URL of the WARC file
        
    Returns:
        Path to downloaded file or None if download failed
    """
    filename = os.path.basename(warc_url)
    output_path = os.path.join(RAW_DIR, filename)
    
    if os.path.exists(output_path):
        logger.info(f"WARC file already exists at {output_path}")
        return output_path
    
    logger.info(f"Downloading WARC file from {warc_url}")
    try:
        # Download with progress reporting
        with requests.get(warc_url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Print progress every 50MB
                        if downloaded % (50 * 1024 * 1024) == 0:
                            percent = 100 * downloaded / total_size if total_size > 0 else 0
                            logger.info(f"Downloaded {downloaded / (1024*1024):.1f}MB ({percent:.1f}%)")
        
        logger.info(f"WARC file downloaded successfully to {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error downloading WARC file: {e}")
        # Clean up partial download
        if os.path.exists(output_path):
            os.remove(output_path)
        return None

def download_multiple_warcs(urls, max_workers=3):
    """
    Download multiple WARC files in parallel.
    
    Args:
        urls: List of WARC file URLs
        max_workers: Maximum number of parallel downloads
        
    Returns:
        List of paths to downloaded files
    """
    if not urls:
        return []
        
    logger.info(f"Starting download of {len(urls)} WARC files using {max_workers} workers")
    
    downloaded_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(download_warc_file, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                file_path = future.result()
                if file_path:
                    downloaded_files.append(file_path)
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
    
    logger.info(f"Successfully downloaded {len(downloaded_files)} WARC files")
    return downloaded_files

def get_all_warc_urls(days=7, files_per_day=1):
    """
    Get WARC file URLs for the past N days.
    
    Args:
        days: Number of days to look back
        files_per_day: Maximum number of files to get per day
        
    Returns:
        List of WARC file URLs
    """
    date_ranges = get_date_ranges(days)
    all_urls = []
    
    for year, month, day in date_ranges:
        urls = get_warc_urls_for_date(year, month, day)
        # Sort URLs to get most recent files first
        urls.sort(reverse=True)
        # Take only the specified number of files per day
        all_urls.extend(urls[:files_per_day])
    
    return all_urls

def main():
    """Main function to download the past week of WARC files."""
    ensure_directories()
    
    # Get command line arguments
    days = 7
    files_per_day = 1
    max_workers = 3
    
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    
    if len(sys.argv) > 2:
        try:
            files_per_day = int(sys.argv[2])
        except ValueError:
            pass
    
    if len(sys.argv) > 3:
        try:
            max_workers = int(sys.argv[3])
        except ValueError:
            pass
    
    logger.info(f"Downloading WARC files for the past {days} days, {files_per_day} files per day")
    
    # Get all WARC URLs
    warc_urls = get_all_warc_urls(days, files_per_day)
    
    if not warc_urls:
        logger.error("No WARC files found for the specified date range")
        return False
    
    logger.info(f"Found {len(warc_urls)} WARC files to download")
    
    # Download all files
    downloaded_files = download_multiple_warcs(warc_urls, max_workers)
    
    logger.info(f"Download summary: {len(downloaded_files)} files downloaded")
    for file_path in downloaded_files:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"  - {os.path.basename(file_path)}: {file_size_mb:.1f} MB")
    
    return True

if __name__ == "__main__":
    main() 