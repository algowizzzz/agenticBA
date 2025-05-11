#!/usr/bin/env python3
"""
Test Script for Document-Level Semantic Search

This script tests the document-level semantic search implementation.
It performs various test queries and evaluates the results.
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any

# Import the document-level search implementation
from document_level_search import semantic_document_search, create_document_level_embeddings
from langchain_tools.doc_level_search_tool import get_doc_level_search_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("document_level_search_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Test queries covering various scenarios
TEST_QUERIES = [
    # Company-specific queries
    "NVIDIA AI strategy in 2020",
    "Microsoft cloud business growth in 2019",
    "Apple iPhone revenue in Q1 2020",
    "AMD product roadmap for 2019",
    "Intel manufacturing challenges",
    "ASML EUV lithography adoption",
    "Amazon AWS revenue growth",
    "Cisco network security initiatives",
    "Google cloud computing market share",
    "Micron memory chip demand trends",
    
    # Multi-company queries
    "Compare NVIDIA and AMD GPU strategies in 2019",
    "Microsoft vs Google cloud services in 2020",
    
    # Specific time period queries 
    "Q4 2019 earnings trends in semiconductor industry",
    "First quarter 2020 impact of COVID-19 on tech companies",
    
    # Topic-specific queries
    "5G technology impact on semiconductor companies",
    "Artificial intelligence investments by tech companies",
    "Supply chain challenges for hardware manufacturers",
    "Data center growth trends from 2019 to 2020",
    "Remote work impact on technology companies in early 2020"
]

def run_test():
    """Run test for document-level search"""
    logger.info(f"Starting document-level search test at {datetime.now().isoformat()}")
    
    # Create the document-level search tool
    search_tool = get_doc_level_search_tool()
    
    # Dictionary to store results for each query
    results = {}
    
    # Run each test query
    for query in TEST_QUERIES:
        logger.info(f"Testing query: {query}")
        
        # Get search results
        search_results = search_tool(query)
        
        # Log the number of results
        num_results = len(search_results.get("identified_documents", []))
        logger.info(f"Query '{query}' returned {num_results} results")
        
        # Add results to dictionary
        results[query] = {
            "num_results": num_results,
            "results": search_results.get("identified_documents", []),
            "error": search_results.get("error")
        }
        
        # Print first few results
        if num_results > 0:
            logger.info("Top 3 results:")
            for i, result in enumerate(search_results.get("identified_documents", [])[:3]):
                logger.info(f"  {i+1}. {result.get('document_name', 'Unknown')} - {result.get('ticker', 'Unknown')} - {result.get('similarity', 'Unknown')}")
        else:
            logger.warning(f"No results found for query: {query}")
    
    # Save results to file
    with open("document_level_search_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    logger.info(f"Test completed at {datetime.now().isoformat()}")
    logger.info(f"Tested {len(TEST_QUERIES)} queries")
    
    # Calculate statistics
    queries_with_results = sum(1 for q in results if results[q]["num_results"] > 0)
    avg_results = sum(results[q]["num_results"] for q in results) / len(results) if results else 0
    
    logger.info(f"Queries with at least one result: {queries_with_results}/{len(TEST_QUERIES)}")
    logger.info(f"Average number of results per query: {avg_results:.2f}")
    
    # Company coverage analysis
    logger.info("Analyzing company coverage in results:")
    company_counts = {}
    for query in results:
        for result in results[query]["results"]:
            ticker = result.get("ticker", "Unknown")
            if ticker not in company_counts:
                company_counts[ticker] = 0
            company_counts[ticker] += 1
    
    # Log company coverage
    for ticker, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {ticker}: {count} occurrences")

def initialize_embedding_collection():
    """Initialize the embedding collection if needed"""
    logger.info("Initializing document-level embeddings collection...")
    try:
        create_document_level_embeddings()
        logger.info("Document-level embeddings collection created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create document-level embeddings collection: {e}")
        return False

if __name__ == "__main__":
    # Initialize the collection first
    if initialize_embedding_collection():
        # Run the test
        run_test()
    else:
        logger.error("Aborting test due to initialization failure") 