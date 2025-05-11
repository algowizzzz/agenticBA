# Bank SEC Filing Collection System

## Overview
This specialized extension of the SEC Feed Collection System focuses specifically on retrieving, processing, and analyzing regulatory filings from major global and Canadian banks. It provides a comprehensive way to obtain official regulatory data directly from SEC.gov, including financial statements, material event disclosures, and press releases.

## Covered Banks

### Global Banks (Top 15)
- **US Banks**
  - JPMorgan Chase (JPM)
  - Bank of America (BAC)
  - Citigroup (C)
  - Wells Fargo (WFC)
  - Goldman Sachs (GS)
  - Morgan Stanley (MS)
- **European Banks with ADRs**
  - HSBC Holdings (HSBC)
  - Barclays (BCS)
  - Deutsche Bank (DB)
  - UBS Group (UBS)
  - Credit Suisse Group (CS)
- **Asian Banks with ADRs**
  - Mitsubishi UFJ Financial Group (MUFG)
  - Sumitomo Mitsui Financial Group (SMFG)
  - Industrial and Commercial Bank of China (IDCBY)
  - Mizuho Financial Group (MFG)

### Canadian Banks (Top 5)
- Royal Bank of Canada (RY)
- Toronto-Dominion Bank (TD)
- Bank of Nova Scotia (BNS)
- Bank of Montreal (BMO)
- Canadian Imperial Bank of Commerce (CM)

## Core Filing Types
The system collects the following types of filings:

1. **8-K Reports** - Current reports of material events (acquisitions, executive changes, significant events)
2. **10-Q Reports** - Quarterly financial statements and analysis
3. **10-K Reports** - Annual comprehensive financial statements and company analysis
4. **Press Releases** - Official SEC announcements related to banks

## Key Data Available for Analysis

### Financial Data
- Income statements, balance sheets, and cash flow statements
- Financial ratios and performance metrics
- Capital adequacy and liquidity measures
- Loss reserves and loan portfolio performance

### Regulatory Events
- Material changes requiring disclosure
- Risk management updates
- Compliance status and regulatory actions
- Stress test results and capital planning

### Corporate Developments
- Mergers, acquisitions, and divestitures
- Leadership changes and executive appointments
- Strategic initiatives and restructuring plans
- Branch closures or expansions

### Risk Disclosures
- Credit risk factors and exposure
- Market risk assessments
- Operational risk updates
- Liquidity and funding risk
- Litigation and legal proceedings

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required packages:
  ```
  pip install feedparser requests beautifulsoup4 matplotlib
  ```

### Directory Structure
```
news_collector/
├── data/
│   ├── raw/
│   │   └── sec/                  # Raw SEC feed data & collection summaries
│   ├── processed/
│   │   └── sec/
│   │       ├── global_banks/     # Shortcut directory to global bank filings
│   │       ├── canadian_banks/   # Shortcut directory to Canadian bank filings
│   │       ├── JPM/              # JPMorgan Chase filings
│   │       ├── BAC/              # Bank of America filings
│   │       ├── ...               # Other bank directories
│   └── reports/
│       └── sec/                  # Analysis reports and visualizations
├── src/
│   └── analyze_sec_data.py       # SEC data analysis utilities
├── sec_feed_collector.py         # Base SEC collection script
├── bank_sec_collector.py         # Bank-specific SEC collection script  
├── download_bank_filings.sh      # Batch script to download all filings
└── README_BANK_SEC.md            # This documentation
```

## Usage

### Quick Start - Download All Bank Filings
To download all core filings for all banks, run:

```bash
chmod +x download_bank_filings.sh
./download_bank_filings.sh
```

This script will:
1. Download 8-K filings (current reports)
2. Download 10-Q filings (quarterly reports)
3. Download 10-K filings (annual reports)
4. Download SEC press releases mentioning banks
5. Generate separate collections for global and Canadian banks
6. Analyze the collected filings
7. Generate reports and visualizations

### Advanced Usage - Custom Collection
You can tailor the collection process using specific command-line arguments:

#### Download Only Global Bank Filings
```bash
python bank_sec_collector.py --global-only
```

#### Download Only Canadian Bank Filings
```bash
python bank_sec_collector.py --canadian-only
```

#### Download Specific Filing Types
```bash
# Download only 10-K (annual reports)
python bank_sec_collector.py --filing-types 10-K

# Download both 10-Q and 8-K
python bank_sec_collector.py --filing-types 10-Q 8-K
```

#### Control Collection Size
```bash
# Limit to 50 entries per feed
python bank_sec_collector.py --max-per-feed 50
```

#### Combine Options
```bash
# Get recent 10-K filings for Canadian banks only
python bank_sec_collector.py --canadian-only --filing-types 10-K --max-per-feed 20
```

## Analyzing Collected Filings
After downloading, you can analyze the filings using:

```bash
python src/analyze_sec_data.py
```

This generates:
1. Timeline visualization of filing activity
2. Filing type distribution charts
3. Keyword analysis from filing content
4. Comprehensive text report summarizing findings

## Example Analysis Findings

The analysis typically reveals:

1. **Disclosure Patterns** - Which banks have the most active disclosure practices
2. **Regulatory Focus** - Common regulatory concerns across banks
3. **Risk Evolution** - How risk disclosures change over time
4. **Financial Trends** - Patterns in financial performance and metrics
5. **Competitive Landscape** - Comparative positioning within the banking sector

## Data Limitations

Important notes about the data:
1. Only covers banks with SEC filings (US-listed or ADRs)
2. Non-US banks without ADRs won't have comprehensive coverage
3. Some foreign banks have different reporting requirements
4. Historical data is limited to what's currently available in SEC feeds

## Future Enhancements

Potential improvements:
1. Add CIK-based lookups for more precise filing matches
2. Incorporate XBRL data extraction for standardized financial metrics
3. Extend to include international regulatory sources (e.g., SEDAR for Canadian banks)
4. Add time-series analysis of financial performance
5. Create alerting system for significant filing events 