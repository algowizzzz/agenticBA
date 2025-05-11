#!/usr/bin/env python3
"""
Download and process CC-NEWS WARC files.
This script downloads WARC files, processes them, and extracts articles
that mention our target companies from US news sources.
"""

import os
import sys
import datetime
import json
import time
import logging
import gzip
import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from newspaper import Article
from warcio.archiveiterator import ArchiveIterator

# Import our reference data
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reference_data import (
    get_company_info, 
    is_us_news_domain,
    get_all_company_aliases
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ccnews_download.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RAW_DIR = os.path.join(DATA_DIR, "raw", "ccnews")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed", "ccnews")
CC_NEWS_INDEX_URL = "https://data.commoncrawl.org/crawl-data/CC-NEWS/index.html"

# Sample WARC file URLs for testing
SAMPLE_WARC_URLS = [
    "https://data.commoncrawl.org/crawl-data/CC-NEWS/2024/04/CC-NEWS-20240401000617-01000.warc.gz",
    "https://data.commoncrawl.org/crawl-data/CC-NEWS/2024/05/CC-NEWS-20240501000651-01000.warc.gz",
    "https://data.commoncrawl.org/crawl-data/CC-NEWS/2024/04/CC-NEWS-20240415120619-01051.warc.gz"
]

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    for ticker in get_company_info():
        os.makedirs(os.path.join(PROCESSED_DIR, ticker), exist_ok=True)

def get_latest_warc_files(limit=10, use_sample_urls=False):
    """
    Get list of the most recent available WARC files.
    
    Args:
        limit: Maximum number of files to return
        use_sample_urls: If True, use predefined sample URLs instead of scraping the index
        
    Returns:
        List of available WARC file URLs, most recent first
    """
    if use_sample_urls:
        logger.info(f"Using sample WARC file URLs for testing")
        return SAMPLE_WARC_URLS[:limit]
    
    # List of known working WARC URLs (updated manually)
    # These are actual WARC files from Common Crawl that should work reliably
    KNOWN_WARC_URLS = [
        "https://data.commoncrawl.org/crawl-data/CC-NEWS/2023/03/CC-NEWS-20230331000549-00884.warc.gz",
        "https://data.commoncrawl.org/crawl-data/CC-NEWS/2023/03/CC-NEWS-20230331003116-00885.warc.gz",
        "https://data.commoncrawl.org/crawl-data/CC-NEWS/2023/03/CC-NEWS-20230331005602-00886.warc.gz",
        "https://data.commoncrawl.org/crawl-data/CC-NEWS/2023/02/CC-NEWS-20230201000547-00000.warc.gz",
        "https://data.commoncrawl.org/crawl-data/CC-NEWS/2023/02/CC-NEWS-20230201003116-00001.warc.gz"
    ]
    
    logger.info(f"Fetching latest WARC file listing from Common Crawl")
    
    try:
        response = requests.get(CC_NEWS_INDEX_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')
        
        warc_files = []
        for link in links:
            href = link.get('href')
            if href and href.endswith('.warc.gz') and 'CC-NEWS-' in href:
                # Convert to full URL
                if not href.startswith('http'):
                    href = "https://data.commoncrawl.org/crawl-data/CC-NEWS/" + href
                warc_files.append(href)
        
        # Sort by date (most recent first)
        warc_files.sort(reverse=True)
        
        # Return only the most recent files
        latest_files = warc_files[:limit]
        logger.info(f"Found {len(latest_files)} recent WARC files")
        
        if latest_files:
            return latest_files
        else:
            logger.info("No WARC files found, using known working URLs")
            return KNOWN_WARC_URLS[:limit]
        
    except Exception as e:
        logger.error(f"Error fetching WARC file listing: {e}")
        logger.info("Using known working WARC URLs")
        return KNOWN_WARC_URLS[:limit]

def download_warc_file(warc_url, output_path):
    """
    Download a WARC file using direct HTTP request.
    
    Args:
        warc_url: URL of the WARC file
        output_path: Path to save the file
        
    Returns:
        Path to downloaded file or None if download failed
    """
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

def extract_articles_from_warc(warc_path, max_articles=None, company_ticker=None):
    """
    Extract articles from a WARC file that mention our target companies.
    
    Args:
        warc_path: Path to the WARC file
        max_articles: Maximum number of articles to extract (for testing)
        company_ticker: If provided, only extract articles for this company
        
    Returns:
        Dictionary of extracted articles by company
    """
    logger.info(f"Extracting articles from {warc_path}")
    
    # Get company aliases map for efficient matching
    alias_map = get_all_company_aliases()
    
    # If filtering by company, validate the ticker
    if company_ticker and company_ticker not in get_company_info():
        logger.error(f"Invalid company ticker: {company_ticker}")
        return {}, {}
    
    # Initialize results structure
    if company_ticker:
        # Only track the specified company
        company_articles = {company_ticker: []}
    else:
        # Track all companies
        company_articles = {ticker: [] for ticker in get_company_info()}
    
    stats = {
        'total_records': 0,
        'html_records': 0,
        'us_news_articles': 0,
        'company_mentions': {ticker: 0 for ticker in company_articles},
        'domains': {}
    }
    
    with open(warc_path, 'rb') as stream:
        for record in ArchiveIterator(stream):
            stats['total_records'] += 1
            
            # Only process response records with text/html content
            if record.rec_type != 'response' or 'text/html' not in record.http_headers.get_header('Content-Type', ''):
                continue
                
            stats['html_records'] += 1
            
            url = record.rec_headers.get_header('WARC-Target-URI')
            if not url:
                continue
                
            # Only process US news domains
            domain = urlparse(url).netloc
            if not is_us_news_domain(domain):
                continue
                
            # Count domains
            stats['domains'][domain] = stats['domains'].get(domain, 0) + 1
            stats['us_news_articles'] += 1
            
            try:
                # Extract HTML content
                html_content = record.content_stream().read().decode('utf-8', errors='replace')
                
                # Skip if HTML is too short (likely not an article)
                if len(html_content) < 1000:
                    continue
                    
                # Process with newspaper
                article = Article(url)
                article.set_html(html_content)
                article.parse()
                
                # Skip articles without proper content
                if not article.title or len(article.text) < 200:
                    continue
                
                # Check for mentions of our target companies
                text_lower = article.title.lower() + " " + article.text.lower()
                
                # Find all company mentions
                companies_mentioned = set()
                
                # If filtering by company, only check for that company
                if company_ticker:
                    # Get aliases for just this company
                    ticker_aliases = [alias.lower() for alias in get_company_info(company_ticker)['aliases']]
                    ticker_aliases.append(company_ticker.lower())
                    ticker_aliases.append(get_company_info(company_ticker)['company'].lower())
                    
                    for alias in ticker_aliases:
                        if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                            companies_mentioned.add(company_ticker)
                            break
                else:
                    # Check all companies
                    for alias, ticker in alias_map.items():
                        if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                            companies_mentioned.add(ticker)
                
                # If any companies are mentioned, save the article
                for ticker in companies_mentioned:
                    stats['company_mentions'][ticker] += 1
                    
                    # Create article data
                    article_data = {
                        'url': url,
                        'domain': domain,
                        'title': article.title,
                        'text': article.text[:5000],  # Limit text length
                        'date': None,
                        'authors': article.authors,
                    }
                    
                    # Try to get publication date
                    if article.publish_date:
                        article_data['date'] = article.publish_date.isoformat()
                    
                    # Add to results
                    company_articles[ticker].append(article_data)
                
                # Check if we've reached the maximum articles (for testing)
                if max_articles and sum(len(articles) for articles in company_articles.values()) >= max_articles:
                    logger.info(f"Reached maximum articles limit ({max_articles})")
                    break
                
            except Exception as e:
                logger.debug(f"Error processing record from {url}: {e}")
            
            # Print progress
            if stats['total_records'] % 1000 == 0:
                mentions = sum(stats['company_mentions'].values())
                logger.info(f"Processed {stats['total_records']} records, found {mentions} company mentions")
    
    # Print final stats
    logger.info(f"WARC processing complete. Stats:")
    logger.info(f"  Total records: {stats['total_records']}")
    logger.info(f"  HTML records: {stats['html_records']}")
    logger.info(f"  US news articles: {stats['us_news_articles']}")
    logger.info(f"  Company mentions: {sum(stats['company_mentions'].values())}")
    for ticker, count in stats['company_mentions'].items():
        if count > 0:
            logger.info(f"    {ticker}: {count} mentions")
    
    return company_articles, stats

def save_articles(company_articles, warc_filename, stats=None):
    """
    Save extracted articles to JSON files by company.
    
    Args:
        company_articles: Dictionary of articles by company
        warc_filename: Original WARC filename (for reference)
        stats: Processing statistics
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for ticker, articles in company_articles.items():
        if not articles:
            continue
            
        # Create output filename
        output_path = os.path.join(
            PROCESSED_DIR, 
            ticker, 
            f"{ticker}_{os.path.basename(warc_filename).replace('.warc.gz', '')}_{timestamp}.json"
        )
        
        # Save articles
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'source_file': warc_filename,
                'extraction_time': timestamp,
                'ticker': ticker,
                'company_info': get_company_info(ticker),
                'articles': articles
            }, f, indent=2)
        
        logger.info(f"Saved {len(articles)} articles for {ticker} to {output_path}")
    
    # Save stats
    if stats:
        stats_path = os.path.join(
            PROCESSED_DIR,
            f"stats_{os.path.basename(warc_filename).replace('.warc.gz', '')}_{timestamp}.json"
        )
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            # Convert domains to list for JSON serialization
            stats['domains'] = [[d, c] for d, c in sorted(
                stats['domains'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20]]  # Just save top 20 domains
            
            json.dump(stats, f, indent=2)
        
        logger.info(f"Saved statistics to {stats_path}")

def process_single_warc(warc_url, max_articles=None, company_ticker=None):
    """
    Download and process a single WARC file.
    
    Args:
        warc_url: URL of the WARC file to process
        max_articles: Maximum articles to extract (for testing)
        company_ticker: If provided, only extract articles for this company
    """
    # Ensure directories exist
    ensure_directories()
    
    # Extract filename from URL
    warc_filename = os.path.basename(warc_url)
    warc_path = os.path.join(RAW_DIR, warc_filename)
    
    # Download the file
    downloaded_path = download_warc_file(warc_url, warc_path)
    if not downloaded_path:
        logger.error(f"Failed to download {warc_url}")
        return
    
    # Extract articles
    company_articles, stats = extract_articles_from_warc(downloaded_path, max_articles, company_ticker)
    
    # Save articles
    save_articles(company_articles, warc_filename, stats)
    
    logger.info(f"Processing complete for {warc_filename}")

def process_latest_warcs(start_idx=0, max_files=1, max_articles_per_file=None, company_ticker=None):
    """
    Process the most recent WARC files from Common Crawl.
    
    Args:
        start_idx: Starting index in the list of WARC files
        max_files: Maximum number of files to process
        max_articles_per_file: Maximum articles to extract per file (for testing)
        company_ticker: If provided, only extract articles for this company
    """
    # Get list of available WARC files
    warc_urls = get_latest_warc_files(limit=20)
    
    if not warc_urls:
        logger.error(f"No WARC files found")
        return
    
    logger.info(f"Starting processing of the latest WARC files")
    logger.info(f"Will process up to {max_files} files starting at index {start_idx}")
    
    if company_ticker:
        logger.info(f"Filtering for company: {company_ticker}")
    
    # Process each file
    end_idx = min(start_idx + max_files, len(warc_urls))
    for i in range(start_idx, end_idx):
        warc_url = warc_urls[i]
        logger.info(f"Processing file {i+1} of {end_idx} - {os.path.basename(warc_url)}")
        
        try:
            process_single_warc(warc_url, max_articles_per_file, company_ticker)
        except Exception as e:
            logger.error(f"Error processing {warc_url}: {e}")
        
        # Add a short delay between files
        if i < end_idx - 1:
            logger.info("Waiting 5 seconds before processing next file...")
            time.sleep(5)
    
    logger.info(f"Completed processing {end_idx - start_idx} WARC files")

if __name__ == "__main__":
    # Default behavior: process one WARC file for testing
    process_latest_warcs(max_files=1, max_articles_per_file=100) 