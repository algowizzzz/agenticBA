#!/usr/bin/env python3
"""
Test script for CCR SQL tool to verify the fix.
"""

import os
import sys
import logging
from typing import Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the current directory to the path to import the required modules
sys.path.append(os.path.abspath('.'))

# Import the required modules
from tools.ccr_sql_tool import run_ccr_sql
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

def main():
    """Main function to test the CCR SQL tool."""
    print("\n===== TESTING CCR SQL TOOL =====")
    
    # Load environment variables
    load_dotenv()
    logger.info("Environment variables loaded.")
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment.")
        sys.exit(1)
    
    # Initialize LLM
    model_name = "claude-3-5-sonnet-20240620"
    llm = ChatAnthropic(
        model=model_name,
        temperature=0,
        anthropic_api_key=api_key
    )
    logger.info(f"LLM initialized with model: {model_name}")
    
    # Define DB path
    project_root = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(project_root, "scripts", "data", "ccr_reporting.db")
    logger.info(f"Using CCR DB path: {db_path}")
    
    # Check if DB exists
    if not os.path.exists(db_path):
        logger.error(f"CCR DB not found at {db_path}")
        sys.exit(1)
    
    # Test query
    test_query = "Show me Morgan Stanley's exposure"
    logger.info(f"Testing query: {test_query}")
    
    # Execute the query
    try:
        result = run_ccr_sql(query=test_query, llm=llm, db_path=db_path)
        
        # Print the result
        print("\n----- RESULT -----")
        print(f"SQL Query: {result.get('sql_query', 'N/A')}")
        print(f"SQL Result: {result.get('sql_result', 'N/A')}")
        print(f"Error: {result.get('error', 'None')}")
        print("-----------------\n")
        
        if result.get("error"):
            logger.error(f"Error executing query: {result['error']}")
            return 1
        else:
            logger.info("Query executed successfully.")
            return 0
    
    except Exception as e:
        logger.error(f"Error testing CCR SQL tool: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 