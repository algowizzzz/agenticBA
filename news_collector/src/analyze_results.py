#!/usr/bin/env python3
"""
Analyze and summarize the extracted articles from WARC files.
This script provides summary statistics and insights from processed articles.
"""

import os
import sys
import json
import glob
import logging
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
import pandas as pd
from datetime import datetime

# Import our reference data
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reference_data import get_company_info

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed", "ccnews")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

def count_articles_by_company():
    """
    Count the number of articles extracted for each company.
    
    Returns:
        Dictionary of company ticker to article count
    """
    article_counts = {}
    
    for ticker in get_company_info():
        company_dir = os.path.join(PROCESSED_DIR, ticker)
        if not os.path.exists(company_dir):
            article_counts[ticker] = 0
            continue
            
        article_files = glob.glob(os.path.join(company_dir, "*.json"))
        total_articles = 0
        
        for file_path in article_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    total_articles += len(data.get('articles', []))
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
        
        article_counts[ticker] = total_articles
    
    return article_counts

def analyze_articles_by_company(ticker):
    """
    Analyze articles for a specific company.
    
    Args:
        ticker: Company ticker symbol
        
    Returns:
        Dictionary with analysis results
    """
    company_dir = os.path.join(PROCESSED_DIR, ticker)
    if not os.path.exists(company_dir):
        return None
    
    article_files = glob.glob(os.path.join(company_dir, "*.json"))
    if not article_files:
        return None
    
    # Initialize counters
    domains = Counter()
    dates = Counter()
    all_articles = []
    
    # Process each file
    for file_path in article_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                articles = data.get('articles', [])
                
                for article in articles:
                    all_articles.append(article)
                    
                    # Count domains
                    domain = article.get('domain', '')
                    if domain:
                        domains[domain] += 1
                    
                    # Count dates
                    date_str = article.get('date', '')
                    if date_str:
                        # Handle ISO format dates
                        try:
                            date_obj = datetime.fromisoformat(date_str)
                            dates[date_obj.strftime('%Y-%m-%d')] += 1
                        except ValueError:
                            # Skip invalid dates
                            pass
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
    
    # Create results dictionary
    results = {
        'ticker': ticker,
        'company_info': get_company_info(ticker),
        'total_articles': len(all_articles),
        'unique_domains': len(domains),
        'top_domains': domains.most_common(10),
        'date_distribution': sorted(dates.items()),
        'articles_sample': all_articles[:5] if all_articles else []  # First 5 articles as sample
    }
    
    return results

def analyze_all_companies():
    """
    Analyze articles for all companies and generate a comprehensive report.
    
    Returns:
        Dictionary with complete analysis results
    """
    ensure_directories()
    
    # Get article counts for all companies
    article_counts = count_articles_by_company()
    
    # Sort companies by article count
    sorted_companies = sorted(article_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Analyze each company with articles
    company_analyses = {}
    for ticker, count in sorted_companies:
        if count > 0:
            analysis = analyze_articles_by_company(ticker)
            if analysis:
                company_analyses[ticker] = analysis
    
    # Get overall statistics
    total_articles = sum(article_counts.values())
    companies_with_articles = sum(1 for count in article_counts.values() if count > 0)
    
    # Prepare the complete report
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_articles': total_articles,
        'companies_analyzed': len(get_company_info()),
        'companies_with_articles': companies_with_articles,
        'article_counts': article_counts,
        'company_analyses': company_analyses
    }
    
    return report

def generate_visualizations(report, output_dir=REPORTS_DIR):
    """
    Generate visualizations from the analysis report.
    
    Args:
        report: Analysis report dictionary
        output_dir: Directory to save visualizations
    """
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Plot 1: Articles by company
    plt.figure(figsize=(12, 6))
    
    # Sort companies by article count
    companies = sorted(report['article_counts'].items(), key=lambda x: x[1], reverse=True)
    tickers = [ticker for ticker, _ in companies]
    counts = [count for _, count in companies]
    
    # Create bar chart
    plt.bar(tickers, counts)
    plt.title('Number of News Articles by Company')
    plt.xlabel('Company Ticker')
    plt.ylabel('Number of Articles')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, 'articles_by_company.png'))
    plt.close()
    
    # Plot 2: Articles by sector (if we have enough companies)
    if len(report['article_counts']) >= 3:
        # Group by sector
        sector_counts = defaultdict(int)
        for ticker, count in report['article_counts'].items():
            company_info = get_company_info(ticker)
            if company_info:
                sector = company_info.get('sector', 'Unknown')
                sector_counts[sector] += count
        
        # Create pie chart
        plt.figure(figsize=(10, 10))
        plt.pie(
            sector_counts.values(), 
            labels=sector_counts.keys(), 
            autopct='%1.1f%%',
            shadow=True,
            startangle=90
        )
        plt.title('Articles by Sector')
        plt.axis('equal')
        plt.tight_layout()
        
        # Save figure
        plt.savefig(os.path.join(output_dir, 'articles_by_sector.png'))
        plt.close()
    
    # Generate individual company visualizations for those with enough data
    for ticker, analysis in report['company_analyses'].items():
        if analysis['total_articles'] < 5:
            continue
        
        # Plot domains
        plt.figure(figsize=(12, 6))
        domains = [domain for domain, _ in analysis['top_domains']]
        domain_counts = [count for _, count in analysis['top_domains']]
        
        plt.bar(domains, domain_counts)
        plt.title(f'Top News Sources for {ticker} ({analysis["company_info"]["company"]})')
        plt.xlabel('Domain')
        plt.ylabel('Article Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(os.path.join(output_dir, f'{ticker}_top_domains.png'))
        plt.close()
        
        # Plot date distribution if we have enough dates
        if len(analysis['date_distribution']) >= 3:
            plt.figure(figsize=(14, 6))
            dates = [date for date, _ in analysis['date_distribution']]
            date_counts = [count for _, count in analysis['date_distribution']]
            
            plt.plot(dates, date_counts, marker='o')
            plt.title(f'Article Date Distribution for {ticker} ({analysis["company_info"]["company"]})')
            plt.xlabel('Date')
            plt.ylabel('Article Count')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            plt.savefig(os.path.join(output_dir, f'{ticker}_date_distribution.png'))
            plt.close()

def save_report(report, output_dir=REPORTS_DIR):
    """
    Save the analysis report to JSON and CSV files.
    
    Args:
        report: Analysis report dictionary
        output_dir: Directory to save the report
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save full report as JSON
    json_path = os.path.join(output_dir, f'news_analysis_report_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        # Create a simplified version without full article text for the report
        simplified_report = report.copy()
        for ticker, analysis in simplified_report.get('company_analyses', {}).items():
            # Truncate article samples to just title and URL
            analysis['articles_sample'] = [
                {'title': article.get('title', ''), 'url': article.get('url', '')}
                for article in analysis.get('articles_sample', [])
            ]
        
        json.dump(simplified_report, f, indent=2)
    
    logger.info(f"Full report saved to {json_path}")
    
    # Save article counts as CSV
    csv_path = os.path.join(output_dir, f'article_counts_{timestamp}.csv')
    counts_df = pd.DataFrame(list(report['article_counts'].items()), columns=['Ticker', 'Article Count'])
    counts_df['Company'] = counts_df['Ticker'].apply(lambda x: get_company_info(x).get('company', '') if get_company_info(x) else '')
    counts_df['Sector'] = counts_df['Ticker'].apply(lambda x: get_company_info(x).get('sector', '') if get_company_info(x) else '')
    counts_df = counts_df.sort_values('Article Count', ascending=False)
    counts_df.to_csv(csv_path, index=False)
    
    logger.info(f"Article counts saved to {csv_path}")
    
    # Create a summary report
    summary_path = os.path.join(output_dir, f'summary_report_{timestamp}.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("==== NEWS COLLECTION SYSTEM REPORT ====\n\n")
        f.write(f"Report generated: {timestamp}\n\n")
        f.write(f"Total articles collected: {report['total_articles']}\n")
        f.write(f"Companies analyzed: {report['companies_analyzed']}\n")
        f.write(f"Companies with articles: {report['companies_with_articles']}\n\n")
        
        f.write("Top companies by article count:\n")
        top_companies = sorted(report['article_counts'].items(), key=lambda x: x[1], reverse=True)
        for i, (ticker, count) in enumerate(top_companies[:5], 1):
            company_info = get_company_info(ticker)
            company_name = company_info.get('company', ticker) if company_info else ticker
            f.write(f"{i}. {ticker} ({company_name}): {count} articles\n")
        
        f.write("\nSample headlines:\n")
        for ticker, analysis in list(report['company_analyses'].items())[:3]:
            company_name = analysis['company_info']['company']
            f.write(f"\n{ticker} ({company_name}):\n")
            for i, article in enumerate(analysis['articles_sample'][:3], 1):
                f.write(f"{i}. {article.get('title', 'No title')}\n")
    
    logger.info(f"Summary report saved to {summary_path}")

def main():
    """Run the full analysis and reporting process."""
    try:
        # Run analysis
        logger.info("Starting news article analysis...")
        report = analyze_all_companies()
        
        # Generate visualizations
        if report['total_articles'] > 0:
            logger.info("Generating visualizations...")
            generate_visualizations(report)
        
        # Save report
        logger.info("Saving analysis report...")
        save_report(report)
        
        logger.info("Analysis complete!")
        
        # Print quick summary
        print("\n=== NEWS COLLECTION SUMMARY ===")
        print(f"Total articles collected: {report['total_articles']}")
        print(f"Companies with articles: {report['companies_with_articles']} out of {report['companies_analyzed']}")
        
        if report['total_articles'] > 0:
            print("\nTop companies by article count:")
            top_companies = sorted(report['article_counts'].items(), key=lambda x: x[1], reverse=True)
            for i, (ticker, count) in enumerate(top_companies[:5], 1):
                if count > 0:
                    company_info = get_company_info(ticker)
                    company_name = company_info.get('company', ticker) if company_info else ticker
                    print(f"{i}. {ticker} ({company_name}): {count} articles")
        
    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        raise

if __name__ == "__main__":
    main() 