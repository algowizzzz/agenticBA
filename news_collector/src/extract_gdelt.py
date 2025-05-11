#!/usr/bin/env python3
"""
Extract news from GDELT Global Knowledge Graph (GKG) for a specific company.
This script downloads a daily GKG CSV file and filters it for mentions of our target company.
"""

import os
import sys
import urllib.request
import gzip
import csv
import io
import datetime
from datetime import timedelta

def extract_gdelt_for_day(company_aliases, target_date, output_dir="data/raw/gdelt"):
    """
    Download and extract GDELT GKG data for a specific day, filtering for company mentions.
    
    Args:
        company_aliases: List of company name variations to search for
        target_date: Date to extract (datetime.date object)
        output_dir: Directory to save extracted data
    
    Returns:
        Path to output file if successful, None otherwise
    """
    # Format date for GDELT URL (YYYYMMDD)
    date_str = target_date.strftime("%Y%m%d")
    
    # GDELT GKG URL format for 15-minute updates
    # We'll just get the first file of the day (0000) for testing
    url = f"http://data.gdeltproject.org/gdeltv2/{date_str}0000.gkg.csv.zip"
    
    print(f"Downloading GDELT GKG data for {date_str} from {url}")
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{date_str}_microsoft.csv.gz")
        
        # Download the ZIP file
        temp_file, _ = urllib.request.urlretrieve(url)
        
        # Process the downloaded file (it's a CSV in ZIP format)
        with gzip.open(temp_file, 'rt', encoding='utf-8', errors='replace') as f_in:
            reader = csv.reader(f_in, delimiter='\t')
            
            # Open output file
            with gzip.open(output_file, 'wt') as f_out:
                writer = csv.writer(f_out, delimiter='\t')
                
                # Track counts
                checked = 0
                matched = 0
                
                # Process each row, checking for company mentions
                for row in reader:
                    checked += 1
                    if checked % 1000 == 0:
                        print(f"Checked {checked} rows, found {matched} matches", end='\r')
                    
                    # Skip rows with fewer than 15 columns (GKG format has at least 15)
                    if len(row) < 15:
                        continue
                    
                    # GDELT GKG format: column 2 (V2Locations) and column 3 (V2Persons) and column 4 (V2Organizations) 
                    # would contain company mentions
                    org_field = row[3] if len(row) > 3 else ""
                    text_field = row[9] if len(row) > 9 else ""  # Document text
                    
                    # Check if any alias appears in the organizations or text fields
                    found = False
                    for alias in company_aliases:
                        if alias in org_field or alias in text_field:
                            found = True
                            break
                    
                    if found:
                        writer.writerow(row)
                        matched += 1
                
                print(f"\nProcessed {checked} rows, found {matched} matches for {company_aliases}")
                
                if matched > 0:
                    print(f"Saved filtered results to {output_file}")
                    return output_file
                else:
                    print(f"No matches found for {company_aliases} on {date_str}")
                    # Remove empty output file
                    os.remove(output_file)
                    return None
    
    except Exception as e:
        print(f"Error processing GDELT data for {date_str}: {e}")
        return None
    finally:
        # Clean up temp file
        try:
            os.remove(temp_file)
        except:
            pass

def test_gdelt_extraction():
    """
    Test the GDELT extraction for Microsoft (MSFT) on a recent date.
    """
    # Microsoft aliases
    microsoft_aliases = ['Microsoft', 'MSFT', 'Microsoft Corp', 'Microsoft Corporation']
    
    # Try yesterday
    yesterday = datetime.date.today() - timedelta(days=1)
    
    # For a guaranteed test, we could use a specific date we know has Microsoft mentions
    # But for now, we'll try yesterday
    result = extract_gdelt_for_day(microsoft_aliases, yesterday)
    
    if result:
        print(f"✅ Successfully extracted GDELT data for Microsoft: {result}")
        
        # Show a sample of the extracted data
        with gzip.open(result, 'rt', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f, delimiter='\t')
            print("\nSample data (first 3 rows):")
            for i, row in enumerate(reader):
                if i >= 3:
                    break
                # Show sample fields (date, url, sample text)
                date = row[1] if len(row) > 1 else "No date"
                url = row[4] if len(row) > 4 else "No URL"
                text = row[9][:100] if len(row) > 9 and row[9] else "No text"
                print(f"Date: {date}")
                print(f"URL: {url}")
                print(f"Text snippet: {text}...")
                print("-" * 80)
    else:
        print("❌ Failed to extract GDELT data for Microsoft")

if __name__ == "__main__":
    test_gdelt_extraction() 