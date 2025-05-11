#!/usr/bin/env python3
"""
Simple script to test the document-level search directly
"""

import sys
import logging
from document_level_search import semantic_document_search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run a simple document search test"""
    # Check if query was provided as command line argument
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # Default query
        query = "Apple iPhone revenue in Q1 2020"
    
    # Print the query
    print(f"Searching for: {query}")
    
    # Perform semantic search
    results = semantic_document_search(query, max_results=5)
    
    # Print results
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results):
        print(f"\n{i+1}. {result['document_name']} ({result['ticker']})")
        print(f"   Similarity: {result['similarity']}")
        if 'excerpt' in result:
            print(f"   Excerpt: {result['excerpt'][:100]}...")

if __name__ == "__main__":
    main() 