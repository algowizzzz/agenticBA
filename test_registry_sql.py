#!/usr/bin/env python3
"""
Test script for tool registry with SQL tools to verify the fix.
"""

import os
import sys
import logging
from typing import Dict, Any

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
from agent_core.tool_registry import ToolRegistry
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

class DummyLLMManager:
    """Dummy LLM Manager class for testing."""
    
    def __init__(self, llm):
        """Initialize with an LLM."""
        self.llm = llm

def main():
    """Main function to test the tool registry with SQL tools."""
    print("\n===== TESTING TOOL REGISTRY WITH SQL TOOLS =====")
    
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
    
    # Initialize LLM Manager
    llm_manager = DummyLLMManager(llm)
    logger.info("Dummy LLM Manager initialized.")
    
    # Initialize Tool Registry
    tool_registry = ToolRegistry(tools_dir="tools", load_profiles=True)
    tool_registry.register_default_tools()
    logger.info(f"Tool Registry initialized with {len(tool_registry.get_all_tools())} tools.")
    
    # Test CCR SQL Tool
    print("\n----- TESTING CCR SQL TOOL -----")
    test_query = "Show me Morgan Stanley's exposure"
    logger.info(f"Testing CCR SQL tool with query: {test_query}")
    
    try:
        result = tool_registry.execute_tool("CcrSql", test_query, llm_manager)
        
        # Print the result
        print("\n----- CCR SQL RESULT -----")
        print(f"SQL Query: {result.get('sql_query', 'N/A')}")
        print(f"SQL Result: {result.get('sql_result', 'N/A')}")
        print(f"Error: {result.get('error', 'None')}")
        print("-------------------------\n")
        
        if result.get("error"):
            logger.error(f"Error executing CCR SQL tool: {result['error']}")
        else:
            logger.info("CCR SQL tool executed successfully.")
    
    except Exception as e:
        logger.error(f"Error testing CCR SQL tool: {e}")
    
    # Test Financial SQL Tool
    print("\n----- TESTING FINANCIAL SQL TOOL -----")
    test_query = "Show me AAPL stock prices"
    logger.info(f"Testing Financial SQL tool with query: {test_query}")
    
    try:
        result = tool_registry.execute_tool("FinancialSql", test_query, llm_manager)
        
        # Print the result
        print("\n----- FINANCIAL SQL RESULT -----")
        print(f"SQL Query: {result.get('sql_query', 'N/A')}")
        print(f"SQL Result: {result.get('sql_result', 'N/A')}")
        print(f"Error: {result.get('error', 'None')}")
        print("--------------------------------\n")
        
        if result.get("error"):
            logger.error(f"Error executing Financial SQL tool: {result['error']}")
        else:
            logger.info("Financial SQL tool executed successfully.")
    
    except Exception as e:
        logger.error(f"Error testing Financial SQL tool: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 