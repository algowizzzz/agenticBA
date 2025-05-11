#!/usr/bin/env python3
"""
Download and extract an actual CC-NEWS article about Microsoft.
This script downloads a WARC file from Common Crawl, processes it,
and extracts articles that mention Microsoft.
"""

import os
import sys
import subprocess
import json
import datetime
from urllib.parse import urlparse
import tempfile
import requests
from warcio.archiveiterator import ArchiveIterator
from newspaper import Article
import logging
import re
import time
from bs4 import BeautifulSoup
import gzip
from xml.etree import ElementTree as ET

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Company info for Microsoft
COMPANY_INFO = {
    'ticker': 'MSFT',
    'company': 'Microsoft Corporation',
    'aliases': ['Microsoft', 'MSFT', 'Microsoft Corp', 'Microsoft Corporation']
}

def find_available_warc_files():
    """
    Query the Common Crawl CC-NEWS listings to find valid WARC files.
    
    Returns:
        List of available WARC file URLs
    """
    logger.info("Searching for available CC-NEWS WARC files...")
    
    # Use current year/month by default
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    
    # Try the current month or fallback to previous months
    attempts = [
        (year, month),
        (year, month-1 if month > 1 else 12),
        (year-1, 12),  # Previous year December
        (2024, 4),     # Known valid month
        (2023, 9)      # Another fallback
    ]
    
    warc_urls = []
    
    for year, month in attempts:
        try:
            # Format URL to get the list of WARC files for a specific year/month
            month_str = f"{month:02d}"
            paths_url = f"https://data.commoncrawl.org/crawl-data/CC-NEWS/{year}/{month_str}/warc.paths.gz"
            
            logger.info(f"Trying to get WARC file list from: {paths_url}")
            
            # Download the gzipped list of paths
            response = requests.get(paths_url)
            if response.status_code != 200:
                logger.warning(f"Failed to get WARC list for {year}/{month_str}: {response.status_code}")
                continue
                
            # Decompress and read the warc.paths.gz file
            content = gzip.decompress(response.content).decode('utf-8')
            paths = content.strip().split('\n')
            
            # Convert paths to full URLs
            for path in paths:
                warc_urls.append(f"https://data.commoncrawl.org/{path}")
            
            logger.info(f"Found {len(warc_urls)} WARC files for {year}/{month_str}")
            
            # If we found files, no need to check earlier months
            if warc_urls:
                break
                
        except Exception as e:
            logger.warning(f"Error getting WARC list for {year}/{month_str}: {e}")
    
    # If we didn't find any paths, try a direct bucket listing as a fallback
    if not warc_urls:
        try:
            # Try to get a direct bucket listing for the most recent month
            bucket_url = f"https://commoncrawl.s3.amazonaws.com/?prefix=crawl-data/CC-NEWS/{year}/{month_str}"
            logger.info(f"Trying direct bucket listing: {bucket_url}")
            
            response = requests.get(bucket_url)
            if response.status_code == 200:
                # Parse XML response from S3
                root = ET.fromstring(response.content)
                namespace = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
                
                # Find all Keys in the XML that end with .warc.gz
                for key in root.findall('.//s3:Key', namespace):
                    key_text = key.text
                    if key_text and key_text.endswith('.warc.gz'):
                        warc_urls.append(f"https://data.commoncrawl.org/{key_text}")
                
                logger.info(f"Found {len(warc_urls)} WARC files from bucket listing")
        except Exception as e:
            logger.warning(f"Error getting bucket listing: {e}")
    
    # If still no files, use hard-coded fallback URLs from known working periods
    if not warc_urls:
        logger.warning("No WARC files found, using fallback URLs")
        warc_urls = [
            "https://data.commoncrawl.org/crawl-data/CC-NEWS/2023/09/CC-NEWS-20230901000000-00000.warc.gz",
            "https://data.commoncrawl.org/crawl-data/CC-NEWS/2024/01/CC-NEWS-20240101000000-00000.warc.gz",
            "https://data.commoncrawl.org/crawl-data/CC-NEWS/2024/04/CC-NEWS-20240401000000-00000.warc.gz"
        ]
    
    # Sort in reverse chronological order and return
    warc_urls.sort(reverse=True)
    return warc_urls

def download_warc_file(output_dir="data/raw/ccnews"):
    """
    Download a single WARC file from Common Crawl CC-NEWS.
    
    Returns:
        Path to the downloaded file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find available WARC files
    warc_urls = find_available_warc_files()
    
    if not warc_urls:
        raise Exception("No WARC files found to download")
    
    # Try to download from each URL until one succeeds
    for warc_url in warc_urls[:3]:  # Try the first 3 most recent files
        try:
            # Get the filename from the URL
            warc_file = os.path.basename(warc_url)
            local_filename = os.path.join(output_dir, warc_file)
            
            logger.info(f"Downloading {warc_url} to {local_filename}")
            
            # Stream the download to handle large files
            with requests.get(warc_url, stream=True) as r:
                r.raise_for_status()  # Raise an exception for HTTP errors
                file_size = int(r.headers.get('content-length', 0))
                logger.info(f"File size: {file_size/1024/1024:.2f} MB")
                
                # Write the file in chunks
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            logger.info(f"Successfully downloaded to {local_filename}")
            return local_filename
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to download {warc_url}: {e}")
            # Continue to the next URL
    
    # If we got here, all downloads failed
    logger.error("All download attempts failed")
    raise Exception("Failed to download any WARC file")

def get_article_content(html, url):
    """
    Extract article content from HTML using newspaper3k.
    
    Args:
        html: HTML content
        url: URL of the article
    
    Returns:
        Dict with article information or None if extraction fails
    """
    try:
        article = Article(url)
        article.set_html(html)
        article.parse()
        
        # Skip articles without sufficient content
        if not article.title or len(article.text) < 200:
            return None
            
        return {
            'title': article.title,
            'text': article.text,
            'url': url,
            'pub_date': article.publish_date.isoformat() if article.publish_date else None,
            'authors': article.authors,
            'source': urlparse(url).netloc
        }
    except Exception as e:
        logger.warning(f"Failed to extract article from {url}: {e}")
        return None

def contains_company_mention(text, aliases):
    """
    Check if text contains mentions of the company.
    
    Args:
        text: Text to check
        aliases: List of company name variations
    
    Returns:
        True if company is mentioned, False otherwise
    """
    text_lower = text.lower()
    for alias in aliases:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(alias.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return True
    return False

def process_warc_file(warc_path, company_aliases, limit=5):
    """
    Process a WARC file and extract articles mentioning the company.
    
    Args:
        warc_path: Path to the WARC file
        company_aliases: List of company name variations to search for
        limit: Maximum number of articles to extract
    
    Returns:
        List of extracted articles
    """
    logger.info(f"Processing WARC file: {warc_path}")
    
    extracted_articles = []
    processed_count = 0
    matched_count = 0
    
    with open(warc_path, 'rb') as stream:
        for record in ArchiveIterator(stream):
            processed_count += 1
            
            # Only process response records with text/html content
            if record.rec_type != 'response' or 'text/html' not in record.http_headers.get_header('Content-Type', ''):
                continue
            
            url = record.rec_headers.get_header('WARC-Target-URI')
            
            try:
                html_content = record.content_stream().read().decode('utf-8', errors='replace')
                
                # Skip if HTML is too short (likely not an article)
                if len(html_content) < 1000:
                    continue
                    
                # Extract article content
                article_data = get_article_content(html_content, url)
                
                if article_data and (
                    contains_company_mention(article_data['title'], company_aliases) or 
                    contains_company_mention(article_data['text'], company_aliases)
                ):
                    matched_count += 1
                    extracted_articles.append(article_data)
                    logger.info(f"Found article about {company_aliases[0]}: {article_data['title']}")
                    
                    # Stop if we've reached the limit
                    if len(extracted_articles) >= limit:
                        break
            except Exception as e:
                logger.warning(f"Error processing record from {url}: {e}")
            
            # Print progress every 100 records
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count} records, found {matched_count} matches")
    
    logger.info(f"Completed processing. Examined {processed_count} records, found {len(extracted_articles)} relevant articles.")
    return extracted_articles

def main():
    """
    Main function to download and process a WARC file to find articles about Microsoft.
    """
    output_dir = "data/raw/ccnews"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Download a WARC file
        warc_file = download_warc_file(output_dir)
        
        # Process the WARC file to extract articles
        articles = process_warc_file(warc_file, COMPANY_INFO['aliases'], limit=3)
        
        if articles:
            # Save the extracted articles to a JSON file
            output_file = os.path.join(output_dir, "real_microsoft_articles.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2)
            
            logger.info(f"Saved {len(articles)} real Microsoft articles to {output_file}")
            
            # Preview the first article
            print("\n========== ARTICLE PREVIEW ==========")
            print(f"Title: {articles[0]['title']}")
            print(f"Source: {articles[0]['source']}")
            print(f"URL: {articles[0]['url']}")
            print(f"Date: {articles[0]['pub_date']}")
            print("\nExcerpt:")
            print(articles[0]['text'][:500] + "...\n")
            
            return True
        else:
            logger.warning("No Microsoft articles found in the WARC file.")
            return False
    
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise

if __name__ == "__main__":
    main() 