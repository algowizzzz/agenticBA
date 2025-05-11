#!/usr/bin/env python3
"""
Test script for the financial news tool to verify it's working correctly.
This script directly uses the run_financial_news_search function without any LLM.
"""

import sys
from tools.financial_news_tool import run_financial_news_search

def main():
    """Run the financial news search with the provided query or a default query."""
    # Use command line argument as query if provided, otherwise use default
    query = sys.argv[1] if len(sys.argv) > 1 else "Apple financial performance"
    
    print(f"Searching for financial news with query: '{query}'")
    print("-" * 80)
    
    # Run the search and print results
    results = run_financial_news_search(query)
    print(results)
    
    print("-" * 80)
    print("Financial news search completed.")

if __name__ == "__main__":
    main() 