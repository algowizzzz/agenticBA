#!/usr/bin/env python3
"""
Analyze SEC filing data collected from SEC.gov RSS feeds.
This script generates reports and insights from the collected filings.
"""

import os
import sys
import json
import datetime
import logging
import re
import matplotlib.pyplot as plt
from collections import Counter, defaultdict

# Add src directory to path to import reference_data
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reference_data import get_company_info

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed", "sec")
REPORTS_DIR = os.path.join(DATA_DIR, "reports", "sec")

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

def load_filings_for_company(ticker):
    """
    Load all filings for a specific company.
    
    Args:
        ticker: Company ticker symbol
        
    Returns:
        List of filing data dictionaries
    """
    company_dir = os.path.join(PROCESSED_DIR, ticker)
    if not os.path.exists(company_dir):
        return []
    
    filings = []
    for filename in os.listdir(company_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(company_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    filing = json.load(f)
                    filings.append(filing)
            except Exception as e:
                logger.error(f"Error reading filing {file_path}: {e}")
    
    return filings

def load_all_filings():
    """
    Load all filings for all companies.
    
    Returns:
        Dictionary mapping company tickers to lists of filing data
    """
    filings_by_company = {}
    
    for ticker in get_company_info():
        company_filings = load_filings_for_company(ticker)
        if company_filings:
            filings_by_company[ticker] = company_filings
    
    return filings_by_company

def extract_filing_dates(filings):
    """
    Extract dates from filing data.
    
    Args:
        filings: List of filing data dictionaries
        
    Returns:
        List of datetime objects
    """
    dates = []
    for filing in filings:
        if 'published' in filing and filing['published']:
            try:
                date_str = filing['published']
                # Handle various date formats
                date_obj = None
                # Try RFC 2822 format (common in RSS feeds)
                try:
                    from email.utils import parsedate_to_datetime
                    date_obj = parsedate_to_datetime(date_str)
                except:
                    pass
                
                # Try ISO format
                if not date_obj:
                    try:
                        date_obj = datetime.datetime.fromisoformat(date_str)
                    except:
                        pass
                
                # Try other formats if needed
                if not date_obj:
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d %b %Y']:
                        try:
                            date_obj = datetime.datetime.strptime(date_str, fmt)
                            break
                        except:
                            continue
                
                if date_obj:
                    dates.append(date_obj)
                
            except Exception as e:
                logger.warning(f"Could not parse date: {date_str} - {e}")
    
    return dates

def extract_filing_types(filings):
    """
    Extract filing types from filing data.
    
    Args:
        filings: List of filing data dictionaries
        
    Returns:
        Counter of filing types
    """
    filing_types = Counter()
    
    for filing in filings:
        if 'filing_type' in filing and filing['filing_type']:
            filing_type = filing['filing_type']
            # Clean up filing type
            filing_type = re.sub(r'\s*-.*$', '', filing_type).strip()
            if filing_type:
                filing_types[filing_type] += 1
    
    return filing_types

def analyze_filing_content(filings):
    """
    Analyze the content of filings.
    
    Args:
        filings: List of filing data dictionaries
        
    Returns:
        Dictionary with content analysis results
    """
    results = {
        'avg_content_length': 0,
        'keyword_mentions': Counter(),
        'has_content_count': 0
    }
    
    # Keywords to look for
    keywords = [
        'acquisition', 'merger', 'dividend', 'earnings', 'revenue', 'profit', 'loss',
        'guidance', 'forecast', 'outlook', 'strategy', 'growth', 'decline', 'investigation',
        'lawsuit', 'litigation', 'settlement', 'penalty', 'fine', 'executive', 'CEO', 'CFO',
        'board', 'director', 'appoint', 'resign', 'restructuring', 'layoff', 'stock',
        'share', 'repurchase', 'buyback', 'sustainability', 'ESG', 'climate', 'cyber',
        'hack', 'breach', 'risk', 'opportunity', 'innovation', 'technology', 'product',
        'launch', 'recall', 'regulatory', 'compliance', 'SEC', 'FDA', 'EPA'
    ]
    
    total_length = 0
    content_count = 0
    
    for filing in filings:
        if 'content' in filing and filing['content'] and isinstance(filing['content'], str):
            content = filing['content'].lower()
            content_count += 1
            total_length += len(content)
            
            # Count keyword mentions
            for keyword in keywords:
                matches = re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', content)
                if matches:
                    results['keyword_mentions'][keyword] += len(matches)
    
    if content_count > 0:
        results['avg_content_length'] = total_length / content_count
        results['has_content_count'] = content_count
    
    return results

def generate_filing_timeline(filings_by_company):
    """
    Generate timeline data for filings by company.
    
    Args:
        filings_by_company: Dictionary mapping company tickers to lists of filing data
        
    Returns:
        Dictionary mapping companies to lists of dates
    """
    timeline_data = {}
    
    for ticker, filings in filings_by_company.items():
        dates = extract_filing_dates(filings)
        if dates:
            # Sort dates in ascending order
            timeline_data[ticker] = sorted(dates)
    
    return timeline_data

def plot_filing_timeline(timeline_data, output_path):
    """
    Create a timeline plot of filings by company.
    
    Args:
        timeline_data: Dictionary mapping companies to lists of dates
        output_path: Path to save the plot
    """
    if not timeline_data:
        return
    
    plt.figure(figsize=(12, 6))
    
    companies = list(timeline_data.keys())
    for i, (ticker, dates) in enumerate(timeline_data.items()):
        company_name = get_company_info(ticker)['company']
        label = f"{ticker} ({company_name})"
        
        # Plot dates as points
        plt.scatter([date for date in dates], [i] * len(dates), 
                   marker='o', s=100, label=label)
    
    plt.yticks(range(len(companies)), companies)
    plt.title('SEC Filing Timeline by Company')
    plt.xlabel('Date')
    plt.tight_layout()
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Format x-axis to show dates nicely
    plt.gcf().autofmt_xdate()
    
    # Save the plot
    plt.savefig(output_path)
    plt.close()

def plot_filing_types(filings_by_company, output_path):
    """
    Create a bar chart of filing types.
    
    Args:
        filings_by_company: Dictionary mapping company tickers to lists of filing data
        output_path: Path to save the plot
    """
    all_filing_types = Counter()
    
    for ticker, filings in filings_by_company.items():
        filing_types = extract_filing_types(filings)
        all_filing_types.update(filing_types)
    
    if not all_filing_types:
        return
    
    # Get the top 10 filing types
    top_types = dict(all_filing_types.most_common(10))
    
    plt.figure(figsize=(10, 6))
    plt.bar(top_types.keys(), top_types.values())
    plt.title('Most Common SEC Filing Types')
    plt.xlabel('Filing Type')
    plt.ylabel('Count')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(output_path)
    plt.close()

def generate_keyword_summary(filings_by_company, output_path):
    """
    Generate a summary of keyword mentions across all filings.
    
    Args:
        filings_by_company: Dictionary mapping company tickers to lists of filing data
        output_path: Path to save the summary
    """
    all_keywords = Counter()
    company_keywords = {}
    
    for ticker, filings in filings_by_company.items():
        content_analysis = analyze_filing_content(filings)
        if content_analysis['keyword_mentions']:
            company_keywords[ticker] = content_analysis['keyword_mentions']
            all_keywords.update(content_analysis['keyword_mentions'])
    
    if not all_keywords:
        return
    
    # Get the top 20 keywords
    top_keywords = dict(all_keywords.most_common(20))
    
    # Create visualization
    plt.figure(figsize=(12, 8))
    plt.bar(top_keywords.keys(), top_keywords.values())
    plt.title('Top Keywords in SEC Filings')
    plt.xlabel('Keyword')
    plt.ylabel('Mentions')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(output_path)
    plt.close()
    
    return top_keywords, company_keywords

def generate_text_report(filings_by_company, timeline_data, top_keywords=None, company_keywords=None):
    """
    Generate a text report summarizing the SEC filing data.
    
    Args:
        filings_by_company: Dictionary mapping company tickers to lists of filing data
        timeline_data: Dictionary mapping companies to lists of dates
        top_keywords: Dictionary of top keywords overall
        company_keywords: Dictionary of keywords by company
        
    Returns:
        Text report
    """
    report = []
    
    # Report header
    report.append("="*80)
    report.append(f"SEC FILING ANALYSIS REPORT - {datetime.datetime.now().strftime('%Y-%m-%d')}")
    report.append("="*80)
    report.append("")
    
    # Summary of filings
    total_filings = sum(len(filings) for filings in filings_by_company.values())
    report.append(f"Total SEC filings collected: {total_filings}")
    report.append("")
    
    # Filings by company
    report.append("FILINGS BY COMPANY")
    report.append("-"*50)
    for ticker, filings in filings_by_company.items():
        company_name = get_company_info(ticker)['company']
        report.append(f"{ticker} ({company_name}): {len(filings)} filings")
        
        # Filing types breakdown
        filing_types = extract_filing_types(filings)
        if filing_types:
            report.append("  Filing types:")
            for filing_type, count in filing_types.most_common():
                report.append(f"    - {filing_type}: {count}")
        
        # Date range
        if ticker in timeline_data and timeline_data[ticker]:
            dates = timeline_data[ticker]
            report.append(f"  Date range: {min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}")
        
        # Content analysis
        content_analysis = analyze_filing_content(filings)
        if content_analysis['has_content_count'] > 0:
            report.append(f"  Content analysis:")
            report.append(f"    - {content_analysis['has_content_count']} filings with content")
            report.append(f"    - Average content length: {int(content_analysis['avg_content_length'])} characters")
            
            # Keywords specific to this company
            if company_keywords and ticker in company_keywords:
                top_company_keywords = company_keywords[ticker].most_common(5)
                if top_company_keywords:
                    report.append(f"    - Top keywords: {', '.join(f'{k} ({v})' for k, v in top_company_keywords)}")
        
        report.append("")
    
    # Overall keyword analysis
    if top_keywords:
        report.append("TOP KEYWORDS ACROSS ALL FILINGS")
        report.append("-"*50)
        for keyword, count in top_keywords.items():
            report.append(f"{keyword}: {count} mentions")
        report.append("")
    
    # Footer
    report.append("="*80)
    report.append(f"Report generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    
    return "\n".join(report)

def main():
    """Main function to analyze SEC filing data."""
    logger.info("Starting SEC Filing Data Analysis...")
    
    # Create directories
    ensure_directories()
    
    # Load all filings
    filings_by_company = load_all_filings()
    
    if not filings_by_company:
        logger.warning("No SEC filings found for analysis.")
        return
    
    logger.info(f"Loaded SEC filings for {len(filings_by_company)} companies")
    
    # Generate timeline data
    timeline_data = generate_filing_timeline(filings_by_company)
    
    # Create visualizations
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Timeline plot
    timeline_path = os.path.join(REPORTS_DIR, f"sec_filing_timeline_{timestamp}.png")
    plot_filing_timeline(timeline_data, timeline_path)
    logger.info(f"Generated filing timeline visualization: {timeline_path}")
    
    # Filing types plot
    types_path = os.path.join(REPORTS_DIR, f"sec_filing_types_{timestamp}.png")
    plot_filing_types(filings_by_company, types_path)
    logger.info(f"Generated filing types visualization: {types_path}")
    
    # Keyword analysis
    keywords_path = os.path.join(REPORTS_DIR, f"sec_filing_keywords_{timestamp}.png")
    keyword_results = generate_keyword_summary(filings_by_company, keywords_path)
    
    if keyword_results:
        top_keywords, company_keywords = keyword_results
        logger.info(f"Generated keyword visualization: {keywords_path}")
    else:
        top_keywords, company_keywords = None, None
    
    # Generate text report
    report = generate_text_report(filings_by_company, timeline_data, top_keywords, company_keywords)
    report_path = os.path.join(REPORTS_DIR, f"sec_filing_report_{timestamp}.txt")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"Generated SEC filing report: {report_path}")
    
    # Print summary to console
    print(f"\nSEC Filing Analysis Complete!")
    print(f"Analyzed {sum(len(filings) for filings in filings_by_company.values())} filings for {len(filings_by_company)} companies")
    print(f"Reports and visualizations saved to: {REPORTS_DIR}")
    print(f"Full report: {report_path}")
    
    return True

if __name__ == "__main__":
    main() 