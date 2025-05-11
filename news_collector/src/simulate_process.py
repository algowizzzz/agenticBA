#!/usr/bin/env python3
"""
Process the simulated WARC file and extract articles mentioning our target companies.
This script integrates with the simulation pipeline as an alternative to fetching real WARC files.
"""

import os
import sys
import logging
import datetime
import json
from warcio.archiveiterator import ArchiveIterator
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our reference data
from src.reference_data import get_company_info, get_all_company_aliases
from src.simulate_warc import WARC_FILE, ensure_directories

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed", "ccnews")

def extract_articles_from_simulated_warc(max_articles=None, company_ticker=None):
    """
    Extract articles from the simulated WARC file mentioning target companies.
    
    Args:
        max_articles: Maximum number of articles to extract (for testing)
        company_ticker: If provided, only extract articles for this company
        
    Returns:
        Dictionary of extracted articles by company
    """
    logger.info(f"Extracting articles from simulated WARC file: {WARC_FILE}")
    
    # Get company aliases map for efficient matching
    alias_map = get_all_company_aliases()
    
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
    
    with open(WARC_FILE, 'rb') as stream:
        for record in ArchiveIterator(stream):
            stats['total_records'] += 1
            
            # Only process response records with text/html content
            if record.rec_type != 'response' or 'text/html' not in record.http_headers.get_header('Content-Type', ''):
                continue
                
            stats['html_records'] += 1
            
            url = record.rec_headers.get_header('WARC-Target-URI')
            if not url:
                continue
                
            # Parse domain
            domain = urlparse(url).netloc
            
            # Count domains
            stats['domains'][domain] = stats['domains'].get(domain, 0) + 1
            stats['us_news_articles'] += 1
            
            try:
                # Extract HTML content
                html_content = record.content_stream().read().decode('utf-8', errors='replace')
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract article data
                title = soup.title.string if soup.title else None
                
                # Get article content
                article_text = ""
                article_div = soup.find('div', class_='article-content')
                if article_div:
                    article_text = article_div.get_text(separator=" ", strip=True)
                else:
                    article_text = soup.get_text(separator=" ", strip=True)
                
                # Skip articles without proper content
                if not title or len(article_text) < 200:
                    continue
                
                # Check for mentions of our target companies
                text_lower = (title.lower() if title else "") + " " + article_text.lower()
                
                # Find all company mentions
                companies_mentioned = set()
                for alias, ticker in alias_map.items():
                    if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                        companies_mentioned.add(ticker)
                
                # Extract publication date
                pub_date = None
                meta_date = soup.find('meta', attrs={'name': 'publication_date'})
                if meta_date and meta_date.get('content'):
                    pub_date = meta_date['content']
                
                # If any companies are mentioned, save the article
                for ticker in companies_mentioned:
                    stats['company_mentions'][ticker] += 1
                    
                    # Create article data
                    article_data = {
                        'url': url,
                        'domain': domain,
                        'title': title,
                        'text': article_text[:5000],  # Limit text length
                        'date': pub_date,
                        'authors': [],
                        'simulated': True
                    }
                    
                    # Add to results
                    company_articles[ticker].append(article_data)
                
                # Check if we've reached the maximum articles (for testing)
                if max_articles and sum(len(articles) for articles in company_articles.values()) >= max_articles:
                    logger.info(f"Reached maximum articles limit ({max_articles})")
                    break
                
            except Exception as e:
                logger.debug(f"Error processing record from {url}: {e}")
            
            # Print progress occasionally
            if stats['total_records'] % 10 == 0:
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

def save_articles(company_articles, stats=None):
    """
    Save extracted articles to JSON files by company.
    
    Args:
        company_articles: Dictionary of articles by company
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
            f"{ticker}_simulated_{timestamp}.json"
        )
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save articles
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'source_file': WARC_FILE,
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
            f"stats_simulated_{timestamp}.json"
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

def process_simulated_warc(max_articles=None, company_ticker=None):
    """
    Process the simulated WARC file: extract articles and save results.
    
    Args:
        max_articles: Maximum number of articles to extract (for testing)
        company_ticker: If provided, only extract articles for this company
    """
    # Ensure directories exist
    ensure_directories()
    
    # Create directories only for companies we're processing
    if company_ticker:
        os.makedirs(os.path.join(PROCESSED_DIR, company_ticker), exist_ok=True)
    else:
        for ticker in get_company_info():
            os.makedirs(os.path.join(PROCESSED_DIR, ticker), exist_ok=True)
    
    # Extract articles
    company_articles, stats = extract_articles_from_simulated_warc(max_articles, company_ticker)
    
    # Save articles
    save_articles(company_articles, stats)
    
    logger.info(f"Processing complete for simulated WARC file")
    
    return company_articles, stats

if __name__ == "__main__":
    max_articles = None
    company_ticker = None
    if len(sys.argv) > 1:
        try:
            max_articles = int(sys.argv[1])
        except ValueError:
            pass
    if len(sys.argv) > 2:
        company_ticker = sys.argv[2]
    
    process_simulated_warc(max_articles, company_ticker) 