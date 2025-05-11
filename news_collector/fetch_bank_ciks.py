#!/usr/bin/env python3
"""
Bank CIK Finder
Retrieves CIK numbers for top global banks from the SEC EDGAR database.
"""

import os
import requests
import json
import pandas as pd
import time
from bs4 import BeautifulSoup

# Set up output directory
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reference")
os.makedirs(DATA_DIR, exist_ok=True)

# List of top global banks to search for
TOP_BANKS = [
    # US Banks
    {"name": "JPMorgan Chase & Co.", "ticker": "JPM", "country": "US"},
    {"name": "Bank of America Corporation", "ticker": "BAC", "country": "US"},
    {"name": "Citigroup Inc.", "ticker": "C", "country": "US"},
    {"name": "Wells Fargo & Company", "ticker": "WFC", "country": "US"},
    {"name": "Goldman Sachs Group Inc.", "ticker": "GS", "country": "US"},
    {"name": "Morgan Stanley", "ticker": "MS", "country": "US"},
    {"name": "U.S. Bancorp", "ticker": "USB", "country": "US"},
    {"name": "Truist Financial Corporation", "ticker": "TFC", "country": "US"},
    {"name": "PNC Financial Services Group", "ticker": "PNC", "country": "US"},
    
    # European Banks
    {"name": "HSBC Holdings plc", "ticker": "HSBC", "country": "UK"},
    {"name": "BNP Paribas", "ticker": "BNPQY", "country": "France"},
    {"name": "UBS Group AG", "ticker": "UBS", "country": "Switzerland"},
    {"name": "Deutsche Bank AG", "ticker": "DB", "country": "Germany"},
    {"name": "Barclays plc", "ticker": "BCS", "country": "UK"},
    {"name": "Credit Suisse Group AG", "ticker": "CS", "country": "Switzerland"},
    {"name": "Banco Santander, S.A.", "ticker": "SAN", "country": "Spain"},
    
    # Canadian Banks
    {"name": "Royal Bank of Canada", "ticker": "RY", "country": "Canada"},
    {"name": "Toronto-Dominion Bank", "ticker": "TD", "country": "Canada"},
    {"name": "Bank of Nova Scotia", "ticker": "BNS", "country": "Canada"},
    {"name": "Bank of Montreal", "ticker": "BMO", "country": "Canada"},
    {"name": "Canadian Imperial Bank of Commerce", "ticker": "CM", "country": "Canada"},
    
    # Asian Banks
    {"name": "Mitsubishi UFJ Financial Group", "ticker": "MUFG", "country": "Japan"},
    {"name": "Industrial and Commercial Bank of China", "ticker": "IDCBY", "country": "China"},
    {"name": "China Construction Bank", "ticker": "CICHY", "country": "China"},
    {"name": "Agricultural Bank of China", "ticker": "ACGBY", "country": "China"},
    {"name": "Bank of China", "ticker": "BACHY", "country": "China"},
    {"name": "Sumitomo Mitsui Financial Group", "ticker": "SMFG", "country": "Japan"},
    {"name": "Mizuho Financial Group", "ticker": "MFG", "country": "Japan"},
    {"name": "DBS Group Holdings", "ticker": "DBSDY", "country": "Singapore"},
    {"name": "HDFC Bank Limited", "ticker": "HDB", "country": "India"}
]

def search_edgar_for_cik(company_name, ticker):
    """
    Search SEC EDGAR database for a company's CIK number.
    
    Args:
        company_name: Name of the company
        ticker: Stock ticker symbol
        
    Returns:
        CIK number as string if found, None otherwise
    """
    # First try searching by ticker (more reliable)
    edgar_ticker_url = f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&owner=exclude&action=getcompany"
    headers = {
        "User-Agent": "Financial Research Project/1.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    print(f"Searching for {company_name} ({ticker})...")
    
    try:
        response = requests.get(edgar_ticker_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for the CIK in the page content
            cik_span = soup.find('span', {'class': 'companyName'})
            if cik_span:
                cik_text = cik_span.text
                # Extract CIK from format like "JPMORGAN CHASE & CO (0000019617)"
                if "(" in cik_text and ")" in cik_text:
                    cik = cik_text.split("(")[1].split(")")[0].strip()
                    # Remove leading zeros for consistency
                    cik = cik.lstrip("0")
                    return cik
            
            # Alternative method: check if CIK is in the page's header
            company_info_div = soup.find('div', {'class': 'companyInfo'})
            if company_info_div:
                cik_info = company_info_div.find('span', {'class': 'companyName'})
                if cik_info and '(' in cik_info.text and ')' in cik_info.text:
                    cik = cik_info.text.split('(')[1].split(')')[0].strip()
                    # Remove leading zeros for consistency
                    cik = cik.lstrip("0")
                    return cik
        
        # If ticker search fails, try by company name
        edgar_name_url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={company_name}&owner=exclude&action=getcompany"
        response = requests.get(edgar_name_url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for the CIK in search results
            company_tables = soup.find_all('table', {'summary': 'Results'})
            if company_tables and len(company_tables) > 0:
                rows = company_tables[0].find_all('tr')
                if len(rows) > 1:  # Skip header row
                    first_result = rows[1]
                    cells = first_result.find_all('td')
                    if len(cells) >= 1:
                        cik_link = cells[0].find('a')
                        if cik_link and '/CIK=' in cik_link['href']:
                            cik = cik_link['href'].split('CIK=')[1].split('&')[0]
                            # Remove leading zeros for consistency
                            cik = cik.lstrip("0")
                            return cik
    
    except Exception as e:
        print(f"Error searching for {company_name}: {e}")
    
    return None

def main():
    """Main function to fetch CIK numbers for all banks."""
    print("Starting Bank CIK Finder...")
    
    # Create a DataFrame to store results
    results = []
    
    for bank in TOP_BANKS:
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        cik = search_edgar_for_cik(bank["name"], bank["ticker"])
        bank_result = {
            "name": bank["name"],
            "ticker": bank["ticker"],
            "country": bank["country"],
            "cik": cik
        }
        
        results.append(bank_result)
        
        if cik:
            print(f"Found CIK for {bank['name']} ({bank['ticker']}): {cik}")
        else:
            print(f"Could not find CIK for {bank['name']} ({bank['ticker']})")
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    
    # Save results as CSV and JSON
    csv_path = os.path.join(DATA_DIR, "bank_ciks.csv")
    json_path = os.path.join(DATA_DIR, "bank_ciks.json")
    
    df.to_csv(csv_path, index=False)
    
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSearch completed. Results saved to:")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    
    # Print summary
    found_count = len([b for b in results if b["cik"] is not None])
    print(f"\nSummary: Found CIKs for {found_count} out of {len(TOP_BANKS)} banks.")
    
    return df

if __name__ == "__main__":
    main() 