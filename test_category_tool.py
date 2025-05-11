#!/usr/bin/env python3
"""
Simple script to test the category summary tool with a predefined query and category ID.
"""

import os
import sys
import json
import logging
from langchain_tools.tool2_category import category_summary_tool

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Set API key directly
    os.environ["ANTHROPIC_API_KEY"] = "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"
    
    # Test parameters - using ticker symbol as found in the database
    query = "What are the recent financial trends for Microsoft?"
    category_id = "MSFT"  # Using ticker symbol directly
    
    logger.info(f"Testing Category Summary Tool with Query: '{query}' and Category ID: '{category_id}'")

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Error: ANTHROPIC_API_KEY environment variable not set properly.")
        sys.exit(1)

    try:
        # Call the category tool function directly
        result = category_summary_tool(query=query, category_id=category_id)

        print("\n--- Category Summary Tool Result ---")
        print(json.dumps(result, indent=2))
        print("------------------------------------")

    except Exception as e:
        logger.error(f"An error occurred during category tool execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 