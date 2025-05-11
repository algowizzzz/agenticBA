#!/usr/bin/env python3
"""
Test script for the improved earnings call tool
"""

import os
import logging
import sys
from langchain_anthropic import ChatAnthropic
from tools.earnings_call_tool import run_transcript_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get API key from environment
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    logger.warning("ANTHROPIC_API_KEY environment variable is not set")
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        logger.info(f"Using API key provided as command line argument")
    else:
        logger.error("Please provide an API key as a command line argument or set ANTHROPIC_API_KEY environment variable")
        print("Usage: python3 test_earnings_call_tool.py [API_KEY]")
        sys.exit(1)

# Initialize the LLM with Haiku for cost efficiency in testing
llm = ChatAnthropic(
    model="claude-3-haiku-20240307",  # Using Haiku for testing to minimize costs
    temperature=0,
    anthropic_api_key=api_key
)

# Test queries
test_queries = [
    "amzn vs aapl 2018 computing growth",
    "What were the key metrics for Microsoft in Q4 2019?",
    "Compare Apple and Google's revenue growth in 2018"
]

def run_test():
    """Run the test with the earnings call tool"""
    # Test with one query for now
    test_query = test_queries[0]
    logger.info(f"Testing earnings call tool with query: {test_query}")
    
    # Run the transcript agent with the query
    # Using task_complexity="simple" for testing to ensure we use the cost-efficient model
    response = run_transcript_agent(
        query=test_query, 
        llm=llm, 
        api_key=api_key,
        task_complexity="simple",  # Force using Haiku for testing
        verbose=True  # Show detailed agent steps
    )
    
    # Print the result
    logger.info("Response received:")
    print("\n" + "="*80)
    print(f"QUERY: {test_query}")
    print("="*80)
    print(response)
    print("="*80 + "\n")

if __name__ == "__main__":
    run_test() 