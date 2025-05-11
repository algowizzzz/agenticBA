#!/usr/bin/env python3
"""
Simple test script for the enhanced earnings call tool with holistic workflow
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

def main():
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable is not set")
        print("Please set the ANTHROPIC_API_KEY environment variable.")
        return

    # Initialize the LLM
    llm = ChatAnthropic(
        model="claude-3-sonnet-20240229",  # Using a more capable model for testing the improved workflow
        temperature=0,
        anthropic_api_key=api_key
    )

    # Get query from command line or use default
    if len(sys.argv) > 1:
        test_query = sys.argv[1]
    else:
        test_query = "Compare Nvidia and Intel's AI strategies in 2018-2019"
        logger.info(f"No query provided, using default: '{test_query}'")

    logger.info(f"Testing enhanced earnings call tool with query: {test_query}")
    
    # Run the transcript agent with the query (verbose for debugging)
    response = run_transcript_agent(
        query=test_query, 
        llm=llm, 
        api_key=api_key,
        task_complexity="standard",  # Use standard complexity for this test
        verbose=True
    )
    
    # Print the result
    print("\n" + "="*80)
    print(f"QUERY: {test_query}")
    print("="*80)
    print(response)
    print("="*80 + "\n")

if __name__ == "__main__":
    main() 