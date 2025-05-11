#!/usr/bin/env python3
"""
Test script for semantic document search
"""

import logging
import json
from document_level_search import semantic_document_search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test queries
test_queries = [
    "NVIDIA AI strategy in 2020",
    "Microsoft cloud business growth in 2019",
    "Apple iPhone revenue in Q1 2020",
    "AMD product roadmap for 2019",
    "Intel manufacturing challenges",
    "ASML EUV lithography adoption",
    "Amazon AWS revenue growth",
    "Cisco network security initiatives",
    "Google cloud computing market share",
    "Micron memory chip demand trends"
]

if __name__ == "__main__":
    logger.info("Testing semantic document search...")
    
    # Run each test query
    all_results = {}
    
    for query in test_queries:
        logger.info(f"Testing query: {query}")
        
        # Get search results
        results = semantic_document_search(query)
        
        # Log the results
        if results:
            logger.info(f"Found {len(results)} results for query: {query}")
            
            # Print the top 3 results
            for i, result in enumerate(results[:3]):
                logger.info(f"Result {i+1}:")
                logger.info(f"  Document: {result['document_name']}")
                logger.info(f"  Company: {result['ticker']}")
                logger.info(f"  Similarity: {result['similarity']}")
                
            # Store the results
            all_results[query] = results
        else:
            logger.warning(f"No results found for query: {query}")
            all_results[query] = []
    
    # Save all results to a file
    with open("semantic_search_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
        
    logger.info("Test completed. Results saved to semantic_search_results.json") 