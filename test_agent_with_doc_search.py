#!/usr/bin/env python3
"""
Test script for agent integration with document-level search
"""

import os
import logging
import json
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from tools.earnings_call_tool import run_transcript_agent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get API key from environment
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# Initialize the LLM
llm = ChatAnthropic(
    model="claude-3-haiku-20240307",
    temperature=0,
    anthropic_api_key=api_key
)

# Test queries
test_queries = [
    "What was Apple's iPhone revenue in Q1 2020?",
    "How has Amazon's AWS business grown over time?",
    "What challenges did Intel face with manufacturing in 2019?",
    "Explain NVIDIA's AI strategy as discussed in their 2020 earnings calls."
]

def run_test():
    """Run the test on each query"""
    logger.info("Starting agent test with document-level search...")
    
    # Run each test query
    results = {}
    
    for query in test_queries:
        logger.info(f"Testing query: {query}")
        
        # Run the transcript agent with the query
        response = run_transcript_agent(query, llm, api_key)
        
        # Log and store the result
        logger.info(f"Response received: {response[:200]}...")
        results[query] = response
    
    # Save results to file
    with open("agent_doc_search_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info("Test completed. Results saved to agent_doc_search_results.json")

if __name__ == "__main__":
    run_test() 