# SEC Feed Collection System

## Overview
The SEC Feed Collection System is a specialized module within the News Collector project that focuses on retrieving, processing, and analyzing official company filings and press releases directly from the U.S. Securities and Exchange Commission (SEC). This component provides authoritative, structured data from SEC.gov's RSS feeds, offering valuable regulatory and disclosure information about target companies.

## Features
- Downloads and processes SEC.gov RSS feeds for various filing types (8-K, 10-Q, 10-K, etc.)
- Targets specific companies based on ticker symbols and company names
- Extracts and structures filing data including publication dates, filing types, and full content
- Analyzes content for relevant keywords and topics
- Generates visualizations and reports for collected data
- Maintains a clean directory structure for raw and processed data

## Directory Structure
```
news_collector/
├── data/
│   ├── raw/
│   │   └── sec/                  # Raw SEC feed data & collection summaries
│   ├── processed/
│   │   └── sec/
│   │       ├── AAPL/             # Processed Apple filings
│   │       ├── GS/               # Processed Goldman Sachs filings
│   │       ├── JPM/              # Processed JPMorgan Chase filings
│   │       └── ...               # Other company folders
│   └── reports/
│       └── sec/                  # Analysis reports and visualizations
├── src/
│   ├── reference_data.py         # Company reference data
│   ├── analyze_sec_data.py       # SEC data analysis utilities
│   └── ...                       # Other source files
├── sec_feed_collector.py         # Main SEC collection script
├── README_SEC.md                 # This documentation
└── ...                           # Other project files
```

## Components

### 1. SEC Feed Collector (`sec_feed_collector.py`)
The main entry point for collecting SEC filing data. This script:
- Fetches SEC.gov RSS feeds for latest filings, press releases, 8-K forms, 10-Q reports, and 10-K reports
- Processes entries to identify company mentions
- Downloads full filing content when available
- Organizes and saves processed data by company

### 2. SEC Data Analyzer (`src/analyze_sec_data.py`)
Provides analysis and reporting capabilities for collected SEC filings, including:
- Loading and aggregating filings by company
- Extracting filing types, dates, and content
- Performing keyword analysis to identify important topics
- Generating timeline visualizations of filing activity
- Creating comprehensive text reports of findings

## SEC RSS Feed Sources
The system collects data from the following SEC.gov RSS feeds:
1. **Latest Filings** - Most recent EDGAR filings
2. **Press Releases** - Official SEC press releases and announcements
3. **8-K Reports** - Current reports of material events
4. **10-Q Reports** - Quarterly financial reports
5. **10-K Reports** - Annual financial reports

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required packages (installed via pip):
  - feedparser
  - requests
  - beautifulsoup4
  - matplotlib

### Installation
```bash
# Install required packages
pip install feedparser requests beautifulsoup4 matplotlib
```

## Usage

### Collecting SEC Filing Data
To collect SEC filings for all configured companies:

```bash
python sec_feed_collector.py
```

This will:
1. Fetch the latest SEC RSS feeds
2. Process entries for mentions of target companies
3. Download and extract filing content
4. Save processed data to company-specific directories
5. Generate a collection summary

### Analyzing SEC Filing Data
To analyze collected SEC filings and generate reports:

```bash
python src/analyze_sec_data.py
```

This will:
1. Load all processed filings
2. Generate timeline visualizations
3. Analyze filing types and content
4. Perform keyword extraction and analysis
5. Create a comprehensive text report and visualizations

## Sample Reports and Visualizations

### Text Report
The system generates detailed text reports containing:
- Filing counts by company
- Filing type breakdowns
- Date ranges of collected filings
- Content analysis with keyword statistics
- Cross-company keyword trends

### Visualizations
The system produces several visualizations:
1. **Filing Timeline** - Shows the distribution of filings over time by company
2. **Filing Types** - Bar chart of the most common filing types
3. **Keyword Analysis** - Bar chart of the most frequently mentioned keywords

## Extending the System

### Adding More Companies
Edit the `src/reference_data.py` file to add additional companies to track.

### Adding More SEC Feeds
Modify the `SEC_FEEDS` dictionary in `sec_feed_collector.py` to include additional RSS feed URLs.

### Customizing Keyword Analysis
Edit the `keywords` list in the `analyze_filing_content` function within `src/analyze_sec_data.py` to track different terms.

## Benefits Over Web Scraping
- **Authoritative Source** - Direct from SEC.gov, the official regulatory source
- **Structured Data** - RSS feeds provide well-structured, consistent data
- **No Authentication** - Publicly accessible with no API keys required
- **No Paywalls** - Avoids problems with paywalled content from news services
- **Clean Format** - XML/RSS format is stable and easier to parse than arbitrary web pages

## Future Enhancements
- Implement scheduled collection to run daily/weekly
- Add filtering by filing date ranges
- Develop alerting system for important filings
- Create company-specific keyword sets for more targeted analysis
- Improve content extraction for better text analysis
- Build integration with financial databases for cross-referencing 