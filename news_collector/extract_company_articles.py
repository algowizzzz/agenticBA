#!/usr/bin/env python3
"""
Extract articles for a specific company from the existing WARC file.
This script processes the existing WARC file and extracts articles mentioning the target company.
"""

import os
import sys
import json
import datetime
import logging
import re
from urllib.parse import urlparse
from warcio.archiveiterator import ArchiveIterator
from newspaper import Article

# Add src directory to path to import reference_data
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.reference_data import get_company_info, is_us_news_domain

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RAW_DIR = os.path.join(DATA_DIR, "raw", "ccnews")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed", "ccnews")

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

def process_warc_for_company(warc_path, ticker, limit=None):
    """
    Process a WARC file and extract articles mentioning the specific company.
    
    Args:
        warc_path: Path to the WARC file
        ticker: Company ticker symbol
        limit: Maximum number of articles to extract (optional)
    
    Returns:
        List of extracted articles
    """
    logger.info(f"Processing WARC file: {warc_path} for ticker: {ticker}")
    
    # Get company info
    company_info = get_company_info(ticker)
    if not company_info:
        logger.error(f"Invalid ticker: {ticker}")
        return []
    
    # Get aliases for this company
    aliases = company_info.get('aliases', [])
    aliases.append(company_info['ticker'])
    aliases.append(company_info['company'])
    
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
            if not url:
                continue
                
            # Only process US news domains
            domain = urlparse(url).netloc
            if not is_us_news_domain(domain):
                continue
            
            try:
                html_content = record.content_stream().read().decode('utf-8', errors='replace')
                
                # Skip if HTML is too short (likely not an article)
                if len(html_content) < 1000:
                    continue
                    
                # Extract article content
                article_data = get_article_content(html_content, url)
                
                if article_data and (
                    contains_company_mention(article_data['title'], aliases) or 
                    contains_company_mention(article_data['text'], aliases)
                ):
                    matched_count += 1
                    extracted_articles.append(article_data)
                    logger.info(f"Found article about {company_info['company']}: {article_data['title']}")
                    
                    # Stop if we've reached the limit
                    if limit and len(extracted_articles) >= limit:
                        break
            except Exception as e:
                logger.warning(f"Error processing record from {url}: {e}")
            
            # Print progress every 500 records
            if processed_count % 500 == 0:
                logger.info(f"Processed {processed_count} records, found {matched_count} matches")
    
    logger.info(f"Completed processing. Examined {processed_count} records, found {len(extracted_articles)} relevant articles.")
    return extracted_articles

def save_company_articles(ticker, articles):
    """
    Save extracted articles to the appropriate company directory.
    
    Args:
        ticker: Company ticker symbol
        articles: List of article data
    """
    # Get company info
    company_info = get_company_info(ticker)
    if not company_info:
        logger.error(f"Invalid ticker: {ticker}")
        return
    
    # Create directory if it doesn't exist
    output_dir = os.path.join(PROCESSED_DIR, ticker)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create timestamp for filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{ticker}_articles_{timestamp}.json")
    
    # Save articles with metadata
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'ticker': ticker,
            'company': company_info['company'],
            'extraction_date': timestamp,
            'article_count': len(articles),
            'articles': articles
        }, f, indent=2)
    
    logger.info(f"Saved {len(articles)} articles for {ticker} to {output_file}")

def main():
    """
    Main function to extract articles for a specific company from the WARC file.
    """
    # Check if a WARC file exists in the raw data directory
    warc_files = [f for f in os.listdir(RAW_DIR) if f.endswith('.warc.gz')]
    if not warc_files:
        logger.error(f"No WARC files found in {RAW_DIR}")
        return False
    
    # Use the largest WARC file (likely the most recent and complete)
    warc_files.sort(key=lambda f: os.path.getsize(os.path.join(RAW_DIR, f)), reverse=True)
    warc_path = os.path.join(RAW_DIR, warc_files[0])
    logger.info(f"Using WARC file: {warc_path}")
    
    # Get ticker from command line or use default
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    else:
        ticker = "AAPL"  # Default to Apple
        
    # Get limit from command line (optional)
    limit = None
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            pass
    
    company_info = get_company_info(ticker)
    if not company_info:
        logger.error(f"Invalid ticker: {ticker}. Available tickers: {', '.join(get_company_info().keys())}")
        return False
    
    logger.info(f"Extracting articles for {company_info['company']} ({ticker})")
    
    # Process the WARC file to extract articles
    articles = process_warc_for_company(warc_path, ticker, limit)
    
    if articles:
        # Save the extracted articles to the appropriate directory
        save_company_articles(ticker, articles)
        
        # Preview the first article
        print("\n========== ARTICLE PREVIEW ==========")
        print(f"Company: {company_info['company']} ({ticker})")
        print(f"Title: {articles[0]['title']}")
        print(f"Source: {articles[0]['source']}")
        print(f"URL: {articles[0]['url']}")
        print(f"Date: {articles[0]['pub_date']}")
        print("\nExcerpt:")
        print(articles[0]['text'][:500] + "...\n")
        
        return True
    else:
        logger.warning(f"No articles found for {company_info['company']} in the WARC file.")
        return False

if __name__ == "__main__":
    main() 