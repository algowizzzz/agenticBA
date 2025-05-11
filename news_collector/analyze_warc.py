#!/usr/bin/env python3
"""
Analyze the distribution of content and dates in a downloaded WARC file.
This script gives statistics about what topics and time periods are covered.
"""

import os
import json
import datetime
from collections import Counter, defaultdict
from urllib.parse import urlparse
import gzip
from warcio.archiveiterator import ArchiveIterator
from newspaper import Article
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_domains_and_dates(warc_path):
    """
    Extract domain and date information from a WARC file.
    
    Args:
        warc_path: Path to the WARC file
    
    Returns:
        domains: Counter of domain frequencies
        dates: Counter of publication dates
        language_count: Counter of article languages
        topics: Estimated topic distribution
    """
    domains = Counter()
    dates = Counter()
    language_count = Counter()
    topics = defaultdict(int)
    
    # Common keywords for topic categorization
    topic_keywords = {
        'technology': ['tech', 'technology', 'software', 'hardware', 'app', 'computer', 'digital', 'cyber', 'ai', 'artificial intelligence'],
        'business': ['business', 'company', 'market', 'stock', 'finance', 'investment', 'economy', 'trade', 'corporate'],
        'politics': ['politics', 'government', 'election', 'president', 'law', 'policy', 'vote', 'congress', 'parliament'],
        'sports': ['sport', 'football', 'soccer', 'basketball', 'baseball', 'tennis', 'olympic', 'tournament', 'championship'],
        'entertainment': ['entertainment', 'movie', 'film', 'tv', 'television', 'celebrity', 'music', 'actor', 'actress', 'hollywood'],
        'health': ['health', 'medical', 'doctor', 'disease', 'medicine', 'hospital', 'patient', 'treatment', 'covid', 'virus', 'vaccine'],
        'science': ['science', 'research', 'scientist', 'study', 'discovery', 'space', 'climate', 'physics', 'biology', 'chemistry'],
    }
    
    processed_count = 0
    extracted_articles = 0
    earliest_date = None
    latest_date = None
    
    with open(warc_path, 'rb') as stream:
        for record in ArchiveIterator(stream):
            processed_count += 1
            
            # Only process response records with text/html content
            if record.rec_type != 'response' or 'text/html' not in record.http_headers.get_header('Content-Type', ''):
                continue
            
            url = record.rec_headers.get_header('WARC-Target-URI')
            if not url:
                continue
                
            domain = urlparse(url).netloc
            domains[domain] += 1
            
            try:
                html_content = record.content_stream().read().decode('utf-8', errors='replace')
                
                # Skip if HTML is too short (likely not an article)
                if len(html_content) < 1000:
                    continue
                    
                # Use newspaper to extract article content
                article = Article(url)
                article.set_html(html_content)
                article.parse()
                
                # Skip articles without proper content
                if not article.title or len(article.text) < 200:
                    continue
                
                extracted_articles += 1
                
                # Count language
                article.nlp()  # Run NLP to get language
                if hasattr(article, 'meta_lang'):
                    language_count[article.meta_lang] += 1
                
                # Record publication date
                if article.publish_date:
                    date_str = article.publish_date.strftime('%Y-%m-%d')
                    dates[date_str] += 1
                    
                    # Update earliest and latest dates
                    if earliest_date is None or article.publish_date < earliest_date:
                        earliest_date = article.publish_date
                    if latest_date is None or article.publish_date > latest_date:
                        latest_date = article.publish_date
                
                # Basic topic categorization based on keywords
                text_lower = article.title.lower() + " " + article.text.lower()
                for topic, keywords in topic_keywords.items():
                    for keyword in keywords:
                        if keyword in text_lower:
                            topics[topic] += 1
                            break
                
                # Check if article mentions Microsoft
                if 'microsoft' in text_lower or 'msft' in text_lower:
                    topics['microsoft_related'] += 1
                
            except Exception as e:
                logger.debug(f"Error processing record from {url}: {e}")
            
            # Print progress every 100 records
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count} records, extracted {extracted_articles} articles")
    
    logger.info(f"Completed analysis. Examined {processed_count} records, extracted {extracted_articles} articles.")
    
    date_range = f"From {earliest_date.strftime('%Y-%m-%d') if earliest_date else 'unknown'} to {latest_date.strftime('%Y-%m-%d') if latest_date else 'unknown'}"
    
    return domains, dates, language_count, topics, extracted_articles, date_range

def main():
    """
    Main function to analyze the WARC file.
    """
    warc_dir = "data/raw/ccnews"
    
    # Find the most recent WARC file
    warc_files = [f for f in os.listdir(warc_dir) if f.endswith('.warc.gz')]
    if not warc_files:
        logger.error(f"No WARC files found in {warc_dir}")
        return
    
    warc_files.sort(reverse=True)
    warc_path = os.path.join(warc_dir, warc_files[0])
    
    logger.info(f"Analyzing WARC file: {warc_path}")
    
    # Analyze the WARC file
    domains, dates, languages, topics, article_count, date_range = extract_domains_and_dates(warc_path)
    
    # Print results
    print("\n=== WARC File Analysis ===")
    print(f"File: {os.path.basename(warc_path)}")
    print(f"Total articles extracted: {article_count}")
    print(f"Date range: {date_range}")
    
    print("\nTop 10 Domains:")
    for domain, count in domains.most_common(10):
        print(f"  {domain}: {count} articles")
    
    print("\nLanguage Distribution:")
    for lang, count in languages.most_common(10):
        print(f"  {lang}: {count} articles")
    
    print("\nTopic Distribution (articles may belong to multiple topics):")
    total_categorized = sum(topics.values())
    for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / article_count) * 100 if article_count > 0 else 0
        print(f"  {topic}: {count} articles ({percentage:.1f}%)")
    
    microsoft_count = topics.get('microsoft_related', 0)
    ms_percentage = (microsoft_count / article_count) * 100 if article_count > 0 else 0
    print(f"\nMicrosoft-related articles: {microsoft_count} ({ms_percentage:.1f}%)")
    
    # Save results to a JSON file
    results = {
        'file': os.path.basename(warc_path),
        'total_articles': article_count,
        'date_range': date_range,
        'top_domains': dict(domains.most_common(20)),
        'languages': dict(languages.most_common(10)),
        'topics': dict(sorted(topics.items(), key=lambda x: x[1], reverse=True)),
        'microsoft_percentage': ms_percentage
    }
    
    output_file = os.path.join(warc_dir, "warc_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Analysis results saved to {output_file}")

if __name__ == "__main__":
    main() 