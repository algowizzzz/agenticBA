#!/usr/bin/env python3
"""
Main script for the News Collection System.
This script coordinates the entire pipeline for collecting and processing news data.
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from src.reference_data import save_reference_data, get_company_info
from src.download_ccnews import process_latest_warcs
from src.analyze_results import main as analyze_results

# Import simulation modules
from src.simulate_warc import generate_simulated_warc
from src.simulate_process import process_simulated_warc

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("news_collection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create the necessary directory structure."""
    os.makedirs("data/raw/ccnews", exist_ok=True)
    os.makedirs("data/processed/ccnews", exist_ok=True)
    os.makedirs("data/reference", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)
    
    # Create company-specific directories
    for ticker in get_company_info():
        os.makedirs(f"data/processed/ccnews/{ticker}", exist_ok=True)
    
    logger.info("Directory structure created successfully")

def generate_reference_data():
    """Generate and save reference data."""
    logger.info("Generating reference data...")
    save_reference_data()
    logger.info("Reference data generated successfully")

def download_and_process_data(start_idx=0, max_files=1, max_articles=100, test_mode=True, use_simulation=False, company_ticker=None):
    """
    Download and process WARC files.
    
    Args:
        start_idx: Starting index in the WARC files list
        max_files: Maximum number of files to process
        max_articles: Maximum articles to extract per file (for testing)
        test_mode: If True, limit processing for testing purposes
        use_simulation: If True, use simulated data instead of downloading actual WARC files
        company_ticker: If provided, focus only on this company
    """
    logger.info("Starting download and processing phase...")
    
    if test_mode:
        logger.info("Running in TEST MODE with limited processing")
    
    if use_simulation:
        logger.info("Using SIMULATED DATA for testing")
        # Generate simulated WARC file
        generate_simulated_warc(num_articles_per_company=max_articles // 6)
        # Process the simulated WARC file
        process_simulated_warc(max_articles=max_articles, company_ticker=company_ticker)
    else:
        # Use actual CC-NEWS WARC files
        process_latest_warcs(
            start_idx=start_idx,
            max_files=max_files,
            max_articles_per_file=max_articles if test_mode else None,
            company_ticker=company_ticker
        )
    
    logger.info("Download and processing phase completed")

def analyze_data():
    """Analyze processed data and generate reports."""
    logger.info("Starting data analysis phase...")
    analyze_results()
    logger.info("Data analysis phase completed")

def run_pipeline(start_idx=0, max_files=1, max_articles=100, test_mode=True, use_simulation=False, company_ticker=None):
    """
    Run the complete news collection pipeline.
    
    Args:
        start_idx: Starting index in the WARC files list
        max_files: Maximum number of files to process
        max_articles: Maximum articles to extract per file (for testing)
        test_mode: If True, limit processing for testing purposes
        use_simulation: If True, use simulated data instead of downloading actual WARC files
        company_ticker: If provided, focus only on this company
    """
    pipeline_start = time.time()
    logger.info("Starting News Collection Pipeline")
    logger.info(f"Configuration: start_idx={start_idx}, max_files={max_files}, test_mode={test_mode}, use_simulation={use_simulation}")
    
    if company_ticker:
        logger.info(f"Focusing on single company: {company_ticker}")
        
        # Validate the company ticker
        if company_ticker not in get_company_info():
            logger.error(f"Invalid company ticker: {company_ticker}")
            print(f"Error: Invalid company ticker '{company_ticker}'. Available companies:")
            for ticker, info in get_company_info().items():
                print(f"  {ticker}: {info['company']}")
            return False
    
    # Step 1: Setup directories
    setup_directories()
    
    # Step 2: Generate reference data
    generate_reference_data()
    
    # Step 3: Download and process data
    download_and_process_data(start_idx, max_files, max_articles, test_mode, use_simulation, company_ticker)
    
    # Step 4: Analyze results
    analyze_data()
    
    # Calculate runtime
    runtime = time.time() - pipeline_start
    logger.info(f"Pipeline completed in {runtime:.2f} seconds")
    
    # Print completion message
    print("\n" + "="*50)
    print("NEWS COLLECTION PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Runtime: {runtime:.2f} seconds")
    print(f"Files processed: {max_files}")
    print(f"Mode: {'TEST' if test_mode else 'PRODUCTION'} {'(SIMULATED)' if use_simulation else ''}")
    if company_ticker:
        print(f"Focused on company: {company_ticker}")
    print("="*50 + "\n")
    
    return True

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='News Collection System')
    
    parser.add_argument('--start', type=int, default=0,
                        help='Starting index for WARC files (default: 0)')
    
    parser.add_argument('--files', type=int, default=1,
                        help='Maximum number of WARC files to process (default: 1)')
    
    parser.add_argument('--articles', type=int, default=100,
                        help='Maximum articles to extract per file for testing (default: 100)')
    
    parser.add_argument('--production', action='store_true',
                        help='Run in production mode (no article limit)')
    
    parser.add_argument('--simulate', action='store_true',
                        help='Use simulated data instead of downloading actual WARC files')
    
    parser.add_argument('--company', type=str,
                        help='Focus on a single company ticker (e.g., AAPL)')
    
    return parser.parse_args()

if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()
    
    # Run pipeline
    try:
        run_pipeline(
            start_idx=args.start,
            max_files=args.files,
            max_articles=args.articles,
            test_mode=not args.production,
            use_simulation=args.simulate,
            company_ticker=args.company
        )
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        print("\nPipeline interrupted by user. Partial results may be available.")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\nPipeline failed: {e}")
        sys.exit(1) 