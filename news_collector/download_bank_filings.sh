#!/bin/bash
# This script downloads core SEC filings (8-K, 10-Q, 10-K) for major global and Canadian banks

echo "Starting Bank SEC Filing Download Script"
echo "----------------------------------------"

# Create necessary directories if they don't exist
mkdir -p data/raw/sec
mkdir -p data/processed/sec

# Make sure we have all dependencies
pip install feedparser requests beautifulsoup4 matplotlib

# Step 1: Download 8-K filings (current reports)
echo ""
echo "Step 1: Downloading 8-K filings for all banks..."
python bank_sec_collector.py --filing-types 8-K --max-per-feed 200

# Step 2: Download 10-Q filings (quarterly reports)
echo ""
echo "Step 2: Downloading 10-Q filings for all banks..."
python bank_sec_collector.py --filing-types 10-Q --max-per-feed 100

# Step 3: Download 10-K filings (annual reports)
echo ""
echo "Step 3: Downloading 10-K filings for all banks..."
python bank_sec_collector.py --filing-types 10-K --max-per-feed 50

# Step 4: Download press releases related to banks
echo ""
echo "Step 4: Downloading SEC press releases mentioning banks..."
python bank_sec_collector.py --max-per-feed 300

# Step 5: Generate separate collections for global and Canadian banks (for convenience)
echo ""
echo "Step 5: Generating separate global bank collection..."
python bank_sec_collector.py --global-only --max-per-feed 50

echo ""
echo "Step 6: Generating separate Canadian bank collection..."
python bank_sec_collector.py --canadian-only --max-per-feed 50

# Step 7: Analyze the collected filings
echo ""
echo "Step 7: Analyzing collected bank filings..."
python src/analyze_sec_data.py

echo ""
echo "----------------------------------------"
echo "Bank SEC filing collection complete!"
echo "Check data/processed/sec/ for collected filings"
echo "Check data/reports/sec/ for analysis reports" 