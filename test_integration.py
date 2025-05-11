#!/usr/bin/env python3
"""
Test script to verify the integration of the document-level search tool
"""

import logging
from tools.earnings_call_tool import create_doc_level_search_wrapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test queries
TEST_QUERIES = [
    "Find earnings calls discussing NVIDIA AI chip strategy",
    "Which companies mentioned supply chain issues in Q1 2020?",
    "Find earnings calls where Apple discusses iPhone revenue growth",
    "Search for Intel's discussion of manufacturing challenges"
]

def test_doc_level_search_integration():
    """Test the integration of the document-level search tool"""
    logger.info("Testing document-level search tool integration...")
    
    for query in TEST_QUERIES:
        logger.info(f"Testing query: {query}")
        
        # Call the wrapper function
        result = create_doc_level_search_wrapper(query)
        
        # Print results
        if "result" in result:
            logger.info("Search Result:")
            logger.info(result["result"])
        else:
            logger.warning(f"Error in search: {result.get('error', 'Unknown error')}")
        
        logger.info("-" * 80)
    
    logger.info("Integration test completed")

if __name__ == "__main__":
    test_doc_level_search_integration() 