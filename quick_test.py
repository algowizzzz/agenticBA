#!/usr/bin/env python3
"""
Quick test for document-level semantic search using existing ChromaDB collection
"""

import json
import logging
from document_level_search import semantic_document_search, NEW_COLLECTION_NAME, MAX_RESULTS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test queries
TEST_QUERIES = [
    # Company specific queries
    "NVIDIA's AI chip strategy",
    "Apple iPhone revenue in Q1 2020", 
    "Microsoft cloud business growth",
    "Intel's manufacturing challenges",
    "Amazon AWS revenue growth"
]

def run_quick_tests():
    """Run quick search tests on existing collection"""
    
    logger.info("Running quick search test on existing collection...")
    
    for query in TEST_QUERIES:
        logger.info(f"Testing query: {query}")
        
        # Run search
        results = semantic_document_search(query, max_results=3)
        
        # Display results
        if results:
            logger.info(f"Query '{query}' returned {len(results)} results")
            for i, result in enumerate(results):
                logger.info(f"  Result {i+1}:")
                logger.info(f"    Document: {result.get('document_name', 'Unknown')}")
                logger.info(f"    Ticker: {result.get('ticker', 'Unknown')}")
                logger.info(f"    Similarity: {result.get('similarity', 'Unknown')}")
                if 'excerpt' in result:
                    logger.info(f"    Excerpt: {result.get('excerpt', '')[:100]}...")
        else:
            logger.warning(f"No results found for: {query}")
        
        logger.info("-" * 80)

if __name__ == "__main__":
    run_quick_tests() 