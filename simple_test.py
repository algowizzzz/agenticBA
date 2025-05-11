#!/usr/bin/env python3
"""
Simple test script for earnings call analysis
"""

import os
import sys
import logging
from langchain_tools.tool2_category import category_summary_tool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        if len(sys.argv) > 1:
            api_key = sys.argv[1]
        else:
            print("Error: Please provide Anthropic API key as argument or set ANTHROPIC_API_KEY environment variable")
            sys.exit(1)
    
    # Test query and category
    query = "Compare computing growth in 2018"
    categories = ["AMZN", "AAPL"]
    
    print(f"\nTesting category summaries for query: '{query}'")
    
    # Call category tool for each ticker
    for category in categories:
        print(f"\n===== Analysis for {category} =====")
        result = category_summary_tool(query, category, api_key)
        
        if "error" in result and result["error"]:
            print(f"Error: {result['error']}")
        else:
            print(f"Thought: {result.get('thought', 'No thought provided')[:200]}...")
            print(f"\nAnswer: {result.get('answer', 'No answer provided')}")

if __name__ == "__main__":
    main() 