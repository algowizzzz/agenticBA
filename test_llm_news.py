#!/usr/bin/env python3
"""
Test script for the simplified JSON-to-LLM financial news tool.
Tests the fallback functionality even when dependencies are missing.
"""

import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def color_print(text, color):
    """Print colored text to terminal."""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def main():
    """
    Test the simplified financial news tool with fallback functionality.
    """
    color_print("===== TESTING JSON-TO-LLM NEWS TOOL =====", "blue")

    # Import the financial news tool
    try:
        from tools.financial_news_tool import run_financial_news_search
        color_print("Successfully imported financial_news_tool", "green")
    except ImportError as e:
        color_print(f"ERROR: Failed to import financial_news_tool: {e}", "red")
        sys.exit(1)
    
    # Test queries
    test_queries = [
        "td bank news",
        "cloud computing and technology forecast",
        "bank ratings downgrade"
    ]
    
    for i, query in enumerate(test_queries, 1):
        color_print(f"\n----- Test Query {i}: '{query}' -----\n", "cyan")
        
        try:
            # Run the query and get results
            result = run_financial_news_search(query)
            
            # Display summary of the result
            if len(result) > 500:
                summary = result[:500] + "..."
            else:
                summary = result
                
            color_print("RESULT SUMMARY:", "green")
            print(summary)
            
        except Exception as e:
            color_print(f"ERROR: {type(e).__name__}: {e}", "red")
    
    color_print("\n===== TEST COMPLETE =====\n", "blue")

if __name__ == "__main__":
    main() 