#!/usr/bin/env python3
"""
Generate simulated WARC content for testing purposes.
This script creates a synthetic WARC-like file with news articles about our target companies.
"""

import os
import sys
import json
import logging
import random
import gzip
import datetime
import uuid
from io import BytesIO
from faker import Faker

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our reference data
from src.reference_data import get_company_info, get_all_company_aliases

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize faker for generating realistic content
fake = Faker()

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RAW_DIR = os.path.join(DATA_DIR, "raw", "ccnews")
WARC_FILE = os.path.join(RAW_DIR, "simulated_ccnews.warc.gz")

# US news domains for simulation
US_NEWS_DOMAINS = [
    "nytimes.com", "wsj.com", "washingtonpost.com", "usatoday.com",
    "cnn.com", "foxnews.com", "reuters.com", "bloomberg.com",
    "cnbc.com", "businessinsider.com", "forbes.com", "marketwatch.com",
    "thestreet.com", "investopedia.com", "finance.yahoo.com", "money.cnn.com"
]

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(RAW_DIR, exist_ok=True)

def generate_article_for_company(ticker, company_info):
    """
    Generate a simulated news article about a company.
    
    Args:
        ticker: Company ticker symbol
        company_info: Company information dictionary
        
    Returns:
        Dictionary with article data
    """
    # Select a random domain
    domain = random.choice(US_NEWS_DOMAINS)
    
    # Generate a realistic URL
    article_id = fake.uuid4().replace('-', '')
    url = f"https://www.{domain}/business/{ticker.lower()}/{article_id}"
    
    # Generate publication date (within last month)
    pub_date = fake.date_time_between(start_date="-30d", end_date="now")
    
    # Choose a random headline format and generate title
    headline_formats = [
        "{company} Reports {adj} {time_period} Results, {market_reaction}",
        "{company} Announces {event_type}, {stakeholder_reaction}",
        "{company}'s {product} {product_action}, {market_reaction}",
        "Analysts {analyst_action} {company} as {reason}",
        "{company} {business_action} in Response to {event}"
    ]
    
    # Generate article components
    company_name = company_info['company'] if random.random() > 0.3 else company_info['ticker']
    
    components = {
        "company": company_name,
        "adj": random.choice(["Strong", "Mixed", "Better-than-Expected", "Record", "Disappointing"]),
        "time_period": random.choice(["Q1", "Q2", "Q3", "Q4", "Annual", "Quarterly"]),
        "market_reaction": random.choice([
            "Stock Surges", "Shares Jump", "Stock Falls", "Investors React", 
            "Outlook Improves", "Future Looks Bright", "Concerns Remain"
        ]),
        "event_type": random.choice([
            "New CEO", "Acquisition", "Strategic Partnership", "Restructuring Plan",
            "Stock Buyback", "Dividend Increase", "Major Investment"
        ]),
        "stakeholder_reaction": random.choice([
            "Investors Applaud", "Analysts Cautious", "Market Reacts Positively",
            "Competitors Concerned", "Industry Takes Notice"
        ]),
        "product": random.choice([
            "Latest Product", "New Service", "Technology", "Platform", 
            "App", "Software", "Next-Generation Solution"
        ]),
        "product_action": random.choice([
            "Exceeds Expectations", "Faces Challenges", "Gains Traction",
            "Disrupts Market", "Sets New Standard"
        ]),
        "analyst_action": random.choice([
            "Upgrade", "Downgrade", "Maintain Buy Rating on", "Raise Price Target for",
            "Express Concern About", "Remain Bullish on"
        ]),
        "reason": random.choice([
            "Growth Potential", "Valuation Concerns", "Market Position Strengthens",
            "Competitive Pressures Mount", "Innovation Pipeline Expands"
        ]),
        "business_action": random.choice([
            "Expands Operations", "Cuts Costs", "Enters New Market", "Changes Strategy",
            "Increases Investment", "Forms Alliance", "Battles Regulations"
        ]),
        "event": random.choice([
            "Market Shifts", "Consumer Trends", "Regulatory Changes", "Supply Chain Issues",
            "Economic Headwinds", "Technological Disruption", "Competitor Moves"
        ])
    }
    
    headline_format = random.choice(headline_formats)
    title = headline_format.format(**components)
    
    # Generate article content with multiple paragraphs
    sector = company_info.get('sector', 'Business')
    paragraphs = []
    
    # First paragraph - summary with company name mentions
    first_paragraph = f"{fake.paragraph(nb_sentences=3)} {company_name} {fake.paragraph(nb_sentences=2)}"
    paragraphs.append(first_paragraph)
    
    # Middle paragraphs - industry context, quotes, and details
    industry_paragraph = f"The {sector} sector has been {fake.paragraph(nb_sentences=3)}"
    paragraphs.append(industry_paragraph)
    
    quote_paragraph = f'"{fake.sentence()} {company_name} {fake.sentence()}" said {fake.name()}, {random.choice(["CEO", "analyst", "industry expert", "CFO", "spokesperson"])}.'
    paragraphs.append(quote_paragraph)
    
    details_paragraph = f"{company_name}'s {fake.paragraph(nb_sentences=4)}"
    paragraphs.append(details_paragraph)
    
    # Final paragraph - outlook
    outlook_paragraph = f"Looking ahead, {fake.paragraph(nb_sentences=3)}"
    paragraphs.append(outlook_paragraph)
    
    # Compile the full text
    text = "\n\n".join(paragraphs)
    
    # Create article data
    article_data = {
        "url": url,
        "domain": domain,
        "title": title,
        "text": text,
        "date": pub_date.isoformat(),
        "authors": [fake.name()],
        "simulated": True
    }
    
    return article_data

def create_simulated_warc_record(domain, url, title, text, date, content_type="text/html"):
    """
    Create a simulated WARC record for a web page following the WARC 1.0 standard.
    
    Args:
        domain: Domain name
        url: Page URL
        title: Page title
        text: Page content text
        date: Publication date
        content_type: Content type
    
    Returns:
        Bytes representation of a WARC record
    """
    # Create a simple HTML document
    html = f"""<!DOCTYPE html>
<html>
<head>
<title>{title}</title>
<meta name="publication_date" content="{date}">
</head>
<body>
<h1>{title}</h1>
<div class="article-content">
{text.replace('\n\n', '<p>')}
</div>
</body>
</html>
"""
    html_bytes = html.encode('utf-8')
    
    # Create HTTP response header
    http_response = f"""HTTP/1.1 200 OK
Date: {datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}
Server: Apache
Content-Type: {content_type}
Content-Length: {len(html_bytes)}
Connection: close

""".encode('utf-8')
    
    # Combine HTTP response header and HTML content
    payload = http_response + html_bytes
    
    # Generate WARC record ID
    record_id = f"<urn:uuid:{uuid.uuid4()}>"
    warcinfo_id = f"<urn:uuid:{uuid.uuid4()}>"
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Create WARC record header
    warc_header = f"""WARC/1.0
WARC-Type: response
WARC-Date: {now}
WARC-Record-ID: {record_id}
WARC-Warcinfo-ID: {warcinfo_id}
WARC-Target-URI: {url}
WARC-IP-Address: {fake.ipv4()}
Content-Type: application/http; msgtype=response
Content-Length: {len(payload)}

""".encode('utf-8')
    
    # Combine WARC header and payload with proper WARC record separation
    return warc_header + payload + b"\r\n\r\n"

def create_warcinfo_record():
    """
    Create a WARC info record that describes the WARC file.
    
    Returns:
        Bytes representation of a WARC info record
    """
    info = f"""software: SimulatedCCNews/1.0
format: WARC File Format 1.0
creator: SimulatedCCNews
isPartOf: News-Collector-Simulated
description: Simulated news articles for testing
robots: ignore
http-header-user-agent: Mozilla/5.0 (compatible; SimulatedCCNews/1.0)
"""
    
    info_bytes = info.encode('utf-8')
    record_id = f"<urn:uuid:{uuid.uuid4()}>"
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Create WARC info record header
    warc_header = f"""WARC/1.0
WARC-Type: warcinfo
WARC-Date: {now}
WARC-Record-ID: {record_id}
Content-Type: application/warc-fields
Content-Length: {len(info_bytes)}

""".encode('utf-8')
    
    return warc_header + info_bytes + b"\r\n\r\n"

def generate_simulated_warc(num_articles_per_company=5):
    """
    Generate a simulated WARC file with news articles.
    
    Args:
        num_articles_per_company: Number of articles to generate per company
    
    Returns:
        Path to the generated WARC file
    """
    logger.info(f"Generating simulated WARC file with {num_articles_per_company} articles per company")
    
    # Create articles for each company
    all_articles = []
    company_articles = {}
    
    for ticker, company_info in get_company_info().items():
        company_articles[ticker] = []
        for _ in range(num_articles_per_company):
            article = generate_article_for_company(ticker, company_info)
            all_articles.append(article)
            company_articles[ticker].append(article)
    
    # Shuffle articles to simulate mixed order in WARC file
    random.shuffle(all_articles)
    
    # Create WARC file
    with gzip.open(WARC_FILE, 'wb') as f:
        # First write a WARC info record
        f.write(create_warcinfo_record())
        
        # Then write article records
        for article in all_articles:
            warc_record = create_simulated_warc_record(
                domain=article['domain'],
                url=article['url'],
                title=article['title'],
                text=article['text'],
                date=article['date']
            )
            f.write(warc_record)
    
    logger.info(f"Generated simulated WARC file at {WARC_FILE}")
    
    # Save article data for reference
    articles_json_path = os.path.join(RAW_DIR, "simulated_articles.json")
    with open(articles_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "generated_at": datetime.datetime.now().isoformat(),
            "total_articles": len(all_articles),
            "company_articles": {ticker: len(articles) for ticker, articles in company_articles.items()},
            "articles": company_articles
        }, f, indent=2)
    
    logger.info(f"Saved article data to {articles_json_path}")
    
    return WARC_FILE

if __name__ == "__main__":
    # Ensure directories exist
    ensure_directories()
    
    # Generate simulated WARC file
    num_articles = 5
    if len(sys.argv) > 1:
        try:
            num_articles = int(sys.argv[1])
        except ValueError:
            pass
    
    generate_simulated_warc(num_articles_per_company=num_articles) 