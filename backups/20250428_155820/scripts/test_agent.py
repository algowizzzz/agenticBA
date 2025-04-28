#!/usr/bin/env python3
"""
Test script to verify the main agent with API key handling
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the main agent
from langchain_tools.agent import HierarchicalRetrievalAgent
from langchain_anthropic import ChatAnthropic # Import for testing

def test_main_agent():
    """Test the main agent with a simple query"""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY") # <-- Re-enable getting from env
    # Hardcode the key known to work from .env.anthropic for testing
    # api_key = "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"
    # logger.info("!!! USING HARDCODED API KEY FOR TESTING !!!") # <-- Remove log message
    
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        return False
    
    logger.info(f"Using API key from environment: length={len(api_key)}, first5={api_key[:5]}..., last5=...{api_key[-5:]}")
    
    # Test 1: Initialize the agent
    logger.info("Test 1: Initializing the agent")
    agent = None # Initialize agent to None
    try:
        agent = HierarchicalRetrievalAgent(api_key=api_key, debug=True)
        logger.info("✅ Agent initialization successful")
    except Exception as e:
        logger.error(f"❌ Agent initialization failed: {e}")
        return False
    
    # Test 1.5: Direct API call using agent's LLM instance
    logger.info("Test 1.5: Verifying agent's LLM instance with direct API call")
    if agent and hasattr(agent, 'llm') and isinstance(agent.llm, ChatAnthropic):
        try:
            test_prompt = "Say hello."
            response = agent.llm.invoke(test_prompt)
            logger.info(f"✅ Direct API call via agent.llm successful. Response: {response.content[:50]}...")
        except Exception as e:
            logger.error(f"❌ Direct API call via agent.llm failed: {e}")
            # If this fails, the key isn't being passed correctly to the agent's LLM
            return False 
    else:
        logger.error("❌ Agent object or agent.llm not properly initialized for testing.")
        return False
    
    # Test 2: Run a simple query
    logger.info("Test 2: Running a simple query through the agent")
    try:
        # Use a simple query that doesn't require extensive processing
        test_query = "List the tables in the financial database"
        
        # Execute the query
        result = agent.query(test_query)
        
        # Check if the result is valid
        if isinstance(result, dict) and "result" in result:
            if result.get("error"):
                logger.warning(f"Agent query returned an error: {result['error']}")
                return False
            else:
                logger.info(f"✅ Agent query succeeded with result: {result['result'][:100]}...")
        else:
            logger.error(f"❌ Agent query returned unexpected result format: {result}")
            return False
            
        logger.info("Agent query test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent query test failed with error: {e}")
        return False

if __name__ == "__main__":
    if test_main_agent():
        print("\n✅ Main agent test completed!")
        sys.exit(0)
    else:
        print("\n❌ Main agent test failed!")
        sys.exit(1) 
"""
Test script to verify the main agent with API key handling
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the main agent
from langchain_tools.agent import HierarchicalRetrievalAgent
from langchain_anthropic import ChatAnthropic # Import for testing

def test_main_agent():
    """Test the main agent with a simple query"""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY") # <-- Re-enable getting from env
    # Hardcode the key known to work from .env.anthropic for testing
    # api_key = "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"
    # logger.info("!!! USING HARDCODED API KEY FOR TESTING !!!") # <-- Remove log message
    
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        return False
    
    logger.info(f"Using API key from environment: length={len(api_key)}, first5={api_key[:5]}..., last5=...{api_key[-5:]}")
    
    # Test 1: Initialize the agent
    logger.info("Test 1: Initializing the agent")
    agent = None # Initialize agent to None
    try:
        agent = HierarchicalRetrievalAgent(api_key=api_key, debug=True)
        logger.info("✅ Agent initialization successful")
    except Exception as e:
        logger.error(f"❌ Agent initialization failed: {e}")
        return False
    
    # Test 1.5: Direct API call using agent's LLM instance
    logger.info("Test 1.5: Verifying agent's LLM instance with direct API call")
    if agent and hasattr(agent, 'llm') and isinstance(agent.llm, ChatAnthropic):
        try:
            test_prompt = "Say hello."
            response = agent.llm.invoke(test_prompt)
            logger.info(f"✅ Direct API call via agent.llm successful. Response: {response.content[:50]}...")
        except Exception as e:
            logger.error(f"❌ Direct API call via agent.llm failed: {e}")
            # If this fails, the key isn't being passed correctly to the agent's LLM
            return False 
    else:
        logger.error("❌ Agent object or agent.llm not properly initialized for testing.")
        return False
    
    # Test 2: Run a simple query
    logger.info("Test 2: Running a simple query through the agent")
    try:
        # Use a simple query that doesn't require extensive processing
        test_query = "List the tables in the financial database"
        
        # Execute the query
        result = agent.query(test_query)
        
        # Check if the result is valid
        if isinstance(result, dict) and "result" in result:
            if result.get("error"):
                logger.warning(f"Agent query returned an error: {result['error']}")
                return False
            else:
                logger.info(f"✅ Agent query succeeded with result: {result['result'][:100]}...")
        else:
            logger.error(f"❌ Agent query returned unexpected result format: {result}")
            return False
            
        logger.info("Agent query test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent query test failed with error: {e}")
        return False

if __name__ == "__main__":
    if test_main_agent():
        print("\n✅ Main agent test completed!")
        sys.exit(0)
    else:
        print("\n❌ Main agent test failed!")
        sys.exit(1) 
 
 