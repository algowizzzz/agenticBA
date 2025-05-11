#!/usr/bin/env python3
"""
Reference data for company information.
This module contains structured reference data for companies we want to track.
"""

import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Phase 1 companies across key sectors
COMPANY_INFO = {
    # Financial
    'JPM': {
        'ticker': 'JPM',
        'company': 'JPMorgan Chase & Co.',
        'sector': 'Financial',
        'aliases': ['JPMorgan', 'JPMorgan Chase', 'JP Morgan', 'Chase Bank', 'Jamie Dimon'],
        'country': 'US'
    },
    'GS': {
        'ticker': 'GS',
        'company': 'Goldman Sachs Group Inc.',
        'sector': 'Financial',
        'aliases': ['Goldman', 'Goldman Sachs', 'GS'],
        'country': 'US'
    },
    
    # Technology
    'MSFT': {
        'ticker': 'MSFT',
        'company': 'Microsoft Corporation',
        'sector': 'Technology',
        'aliases': ['Microsoft', 'MSFT', 'Microsoft Corp', 'Satya Nadella'],
        'country': 'US'
    },
    'AAPL': {
        'ticker': 'AAPL',
        'company': 'Apple Inc.',
        'sector': 'Technology',
        'aliases': ['Apple', 'AAPL', 'Apple Inc', 'Tim Cook'],
        'country': 'US'
    },
    
    # Energy
    'XOM': {
        'ticker': 'XOM',
        'company': 'Exxon Mobil Corporation',
        'sector': 'Energy',
        'aliases': ['Exxon', 'ExxonMobil', 'Exxon Mobil', 'XOM'],
        'country': 'US'
    },
    
    # Automotive
    'TSLA': {
        'ticker': 'TSLA',
        'company': 'Tesla, Inc.',
        'sector': 'Automotive',
        'aliases': ['Tesla', 'TSLA', 'Tesla Motors', 'Elon Musk'],
        'country': 'US'
    }
}

# US news domains to prioritize
US_NEWS_DOMAINS = [
    # Major financial news
    'wsj.com', 'bloomberg.com', 'cnbc.com', 'finance.yahoo.com', 'marketwatch.com', 
    'reuters.com', 'ft.com', 'barrons.com', 'seekingalpha.com', 'investors.com',
    
    # Major general news
    'nytimes.com', 'washingtonpost.com', 'usatoday.com', 'cnn.com', 'foxbusiness.com',
    'apnews.com', 'forbes.com', 'businessinsider.com', 'fortune.com',
    
    # Tech news
    'techcrunch.com', 'theverge.com', 'wired.com', 'engadget.com', 'cnet.com',
    
    # Energy news
    'oilprice.com', 'energy.economictimes.com', 'rigzone.com',
    
    # Auto news
    'autonews.com', 'caranddriver.com', 'motortrend.com'
]

def get_company_info(ticker=None):
    """
    Get company information by ticker.
    
    Args:
        ticker: Company ticker symbol (optional)
        
    Returns:
        Dictionary of company information if ticker provided,
        otherwise the entire COMPANY_INFO dictionary
    """
    if ticker:
        return COMPANY_INFO.get(ticker.upper())
    return COMPANY_INFO

def save_reference_data(output_dir='data/reference'):
    """
    Save reference data to JSON files.
    
    Args:
        output_dir: Directory to save reference data
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save company info
    with open(os.path.join(output_dir, 'companies.json'), 'w') as f:
        json.dump(COMPANY_INFO, f, indent=2)
    
    # Save US news domains
    with open(os.path.join(output_dir, 'us_news_domains.json'), 'w') as f:
        json.dump(US_NEWS_DOMAINS, f, indent=2)
    
    logger.info(f"Reference data saved to {output_dir}")

def is_us_news_domain(domain):
    """
    Check if a domain is in our list of US news domains.
    
    Args:
        domain: Website domain to check
        
    Returns:
        Boolean indicating if domain is a US news source
    """
    return any(domain.endswith(us_domain) for us_domain in US_NEWS_DOMAINS)

def get_all_company_aliases():
    """
    Get a flat list of all company names and aliases for efficient matching.
    
    Returns:
        Dictionary mapping aliases to company tickers
    """
    alias_map = {}
    for ticker, info in COMPANY_INFO.items():
        # Add company name
        alias_map[info['company'].lower()] = ticker
        # Add ticker
        alias_map[ticker.lower()] = ticker
        # Add aliases
        for alias in info['aliases']:
            alias_map[alias.lower()] = ticker
    
    return alias_map

if __name__ == "__main__":
    # When run directly, save reference data
    save_reference_data()
    print("Company reference data:")
    for ticker, info in COMPANY_INFO.items():
        print(f"  {ticker}: {info['company']} ({info['sector']})")
    
    print(f"\nTotal companies: {len(COMPANY_INFO)}")
    print(f"Total US news domains: {len(US_NEWS_DOMAINS)}")
    
    # Create alias map for testing
    alias_map = get_all_company_aliases()
    print(f"Total aliases for matching: {len(alias_map)}") 