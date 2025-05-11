#!/usr/bin/env python3
"""
Extract SEC press releases for a specific company.
This script fetches the SEC RSS feed and filters for entries related to our target company.
"""

import os
import sys
import feedparser
import requests
from bs4 import BeautifulSoup
import json
import datetime
from datetime import timedelta
import re

def extract_sec_press_releases(company_aliases, days_back=7, output_dir="data/raw/sec"):
    """
    Fetch SEC press releases for a specific company within a date range.
    
    Args:
        company_aliases: List of company name variations to search for
        days_back: Number of days to look back
        output_dir: Directory to save extracted data
    
    Returns:
        List of dicts with press release info if successful, empty list otherwise
    """
    # SEC press releases RSS feed URL
    url = "https://www.sec.gov/news/pressreleases.rss"
    
    print(f"Fetching SEC press releases from {url}")
    
    try:
        # Parse the RSS feed
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print("No entries found in the SEC RSS feed")
            return []
        
        print(f"Found {len(feed.entries)} SEC press releases in the feed")
        
        # Calculate the date range
        end_date = datetime.datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        matching_entries = []
        
        # Process each entry
        for entry in feed.entries:
            # Check publication date if available
            pub_date = None
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime.datetime(*entry.published_parsed[:6])
            
            # Skip if outside date range
            if pub_date and (pub_date < start_date or pub_date > end_date):
                continue
            
            # Check if any alias appears in the title or summary
            title = entry.title if hasattr(entry, 'title') else ""
            summary = entry.summary if hasattr(entry, 'summary') else ""
            link = entry.link if hasattr(entry, 'link') else ""
            
            # Check for company mention in title or summary
            found = False
            for alias in company_aliases:
                if alias.lower() in title.lower() or alias.lower() in summary.lower():
                    found = True
                    break
            
            if not found and link:
                # If not found in title or summary, fetch the full content
                try:
                    response = requests.get(link, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        content = soup.get_text()
                        
                        # Check the content for company mentions
                        for alias in company_aliases:
                            if alias.lower() in content.lower():
                                found = True
                                break
                except Exception as e:
                    print(f"Error fetching content from {link}: {e}")
            
            if found:
                # Create an entry dict with relevant info
                entry_dict = {
                    'title': title,
                    'summary': summary,
                    'link': link,
                    'pub_date': pub_date.isoformat() if pub_date else None
                }
                
                # Save the full content if available
                if link:
                    try:
                        response = requests.get(link, timeout=10)
                        if response.status_code == 200:
                            # Create a sanitized filename from the title
                            filename = re.sub(r'[^\w\s-]', '', title.lower())
                            filename = re.sub(r'[\s-]+', '_', filename)
                            filename = f"{filename[:50]}_{pub_date.strftime('%Y%m%d') if pub_date else 'unknown_date'}.html"
                            
                            # Save the HTML content
                            file_path = os.path.join(output_dir, filename)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(response.text)
                            
                            entry_dict['file_path'] = file_path
                    except Exception as e:
                        print(f"Error saving content from {link}: {e}")
                
                matching_entries.append(entry_dict)
        
        # Save the list of matching entries as JSON
        if matching_entries:
            json_file = os.path.join(output_dir, "matching_sec_releases.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(matching_entries, f, indent=2)
            
            print(f"Saved {len(matching_entries)} matching SEC press releases to {json_file}")
        else:
            print(f"No matching SEC press releases found for {company_aliases}")
        
        return matching_entries
    
    except Exception as e:
        print(f"Error processing SEC press releases: {e}")
        return []

def test_sec_extraction():
    """
    Test the SEC press release extraction for Microsoft (MSFT).
    """
    # Microsoft aliases
    microsoft_aliases = ['Microsoft', 'MSFT', 'Microsoft Corp', 'Microsoft Corporation']
    
    # Look back 30 days to increase chances of finding something
    results = extract_sec_press_releases(microsoft_aliases, days_back=30)
    
    if results:
        print(f"✅ Successfully extracted {len(results)} SEC press releases for Microsoft")
        
        # Show a sample of the extracted data
        print("\nSample data (first 3 entries):")
        for i, entry in enumerate(results[:3]):
            print(f"Title: {entry['title']}")
            print(f"Date: {entry['pub_date']}")
            print(f"Link: {entry['link']}")
            print(f"File: {entry.get('file_path', 'Not saved')}")
            print("-" * 80)
    else:
        print("❌ No SEC press releases found for Microsoft in the last 30 days")
        
        # Try a different company or a longer time period for a real test
        print("\nNote: If no Microsoft-related press releases were found, you might want to:")
        print("1. Try a longer time period (increase days_back)")
        print("2. Try a different company with more SEC activity")
        print("3. Check the SEC website manually to verify")

if __name__ == "__main__":
    test_sec_extraction() 