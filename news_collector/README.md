# News Collection System

A system for collecting, processing, and analyzing news articles about target companies from Common Crawl's CC-NEWS dataset.

## Overview

This system downloads Web Archive (WARC) files from Common Crawl's news dataset, extracts articles mentioning target companies, filters for US news sources, and provides analysis tools to understand the collected data.

## Phase 1 Implementation

The current implementation (Phase 1) includes:

- Support for 6 major companies across key sectors:
  - Financial: JPMorgan Chase (JPM), Goldman Sachs (GS)
  - Technology: Microsoft (MSFT), Apple (AAPL)
  - Energy: ExxonMobil (XOM)
  - Automotive: Tesla (TSLA)
- US news source filtering
- April 2025 data collection
- Comprehensive analysis and reporting tools

## Directory Structure

```
news_collector/
├── data/                   # Data directory
│   ├── raw/                # Raw WARC files 
│   ├── processed/          # Processed articles
│   ├── reference/          # Reference data
│   └── reports/            # Analysis reports
├── src/                    # Source code
│   ├── reference_data.py   # Company reference data
│   ├── download_ccnews.py  # WARC download and processing
│   └── analyze_results.py  # Results analysis
├── main.py                 # Main pipeline script
├── requirements.txt        # Dependencies
└── README.md               # Documentation
```

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the pipeline with default settings (test mode):

```bash
python main.py
```

Command line options:

```
--start N      Starting index for WARC files (default: 0)
--files N      Maximum number of WARC files to process (default: 1)
--articles N   Maximum articles per file for testing (default: 100)
--production   Run in production mode (no article limit)
```

Examples:

```bash
# Process 3 WARC files in test mode (limit 100 articles per file)
python main.py --files 3

# Process 1 WARC file with no article limit (production mode)
python main.py --production

# Process 5 WARC files starting from index 10 with limit of 200 articles each
python main.py --start 10 --files 5 --articles 200
```

## Components

### Reference Data (`reference_data.py`)

Provides structured information about target companies, including:
- Ticker symbols
- Company names
- Sectors
- Aliases for mention detection
- Country information

Also includes a list of US news domains for filtering.

### WARC Download and Processing (`download_ccnews.py`)

- Finds available WARC files from Common Crawl for April 2025
- Downloads selected files
- Processes HTML content to extract articles
- Filters for US news sources
- Detects company mentions
- Saves articles organized by company

### Analysis and Reporting (`analyze_results.py`)

- Counts articles by company
- Analyzes domains, dates, and content
- Generates visualizations (charts and graphs)
- Creates detailed reports in multiple formats (JSON, CSV, TXT)

## Future Development

This is Phase 1 of a multi-phase project. Future phases will:
- Expand company coverage to more S&P 500 companies
- Enhance entity recognition for better company detection
- Implement more efficient parallel processing
- Add more sophisticated US news filtering
- Cover longer time periods

## Dependencies

- beautifulsoup4: HTML parsing
- warcio: WARC file handling
- newspaper3k: Article extraction
- pandas: Data manipulation
- matplotlib: Visualization
- requests: HTTP requests

## License

Copyright (c) 2025 